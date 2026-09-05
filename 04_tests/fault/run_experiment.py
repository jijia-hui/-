#!/usr/bin/env python3
"""微服务 Compose 故障实验：停服注入 + HTTP 探测，输出原始 JSON。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = Path(__file__).parent / "raw"
DEFAULT_COMPOSE_FILE = "docker-compose.micro.prod.yml"


def http_json(method: str, url: str, token: str | None = None, data: bytes | None = None, timeout: float = 10) -> dict:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            elapsed_ms = (time.perf_counter() - started) * 1000
            try:
                parsed = json.loads(body) if body else None
            except json.JSONDecodeError:
                parsed = body[:500]
            return {
                "ok": True,
                "status": resp.status,
                "elapsed_ms": round(elapsed_ms, 2),
                "body": parsed,
            }
    except urllib.error.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body else None
        except json.JSONDecodeError:
            parsed = body[:500]
        return {
            "ok": False,
            "status": exc.code,
            "elapsed_ms": round(elapsed_ms, 2),
            "body": parsed,
        }
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {"ok": False, "status": None, "elapsed_ms": round(elapsed_ms, 2), "error": str(exc)}


def login(base_url: str, username: str, password: str) -> str | None:
    payload = json.dumps({"username": username, "password": password}).encode()
    res = http_json("POST", f"{base_url.rstrip('/')}/api/auth/token/", data=payload)
    if res.get("status") == 200 and isinstance(res.get("body"), dict):
        return res["body"].get("token")
    return None


def compose_cmd(compose_file: str, *args: str) -> dict:
    cmd = ["docker", "compose", "-f", compose_file, *args]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "stdout": (proc.stdout or "")[-4000:],
        "stderr": (proc.stderr or "")[-4000:],
    }


def wait_http(url: str, expect_status: int | None = None, retries: int = 20, sleep_s: float = 2) -> dict:
    last = None
    for _ in range(retries):
        last = http_json("GET", url)
        if expect_status is None or last.get("status") == expect_status:
            return last
        time.sleep(sleep_s)
    return last or {"ok": False, "error": "no response"}


def run_scenarios(
    base_url: str,
    student_user: str,
    student_pass: str,
    dry_run: bool,
    compose_file: str,
) -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    scenarios: list[dict] = []

    def record(step: str, **extra):
        scenarios.append({"step": step, "timestamp_utc": datetime.now(timezone.utc).isoformat(), **extra})

    record("SC00_baseline_health", probe=wait_http(f"{base_url}/api/health/"))

    token = login(base_url, student_user, student_pass)
    record("SC00_login", success=bool(token))

    courses_url = f"{base_url}/api/courses/"
    record("SC00_courses_list", probe=http_json("GET", courses_url, token=token))

    # 找一门课与作业 ID（演示数据）
    course_id = assignment_id = None
    courses_probe = scenarios[-1]["probe"]
    if isinstance(courses_probe.get("body"), dict):
        results = courses_probe["body"].get("results") or []
        if results:
            course_id = results[0].get("id")
    if course_id:
        assign_probe = http_json("GET", f"{base_url}/api/assignments/?course={course_id}", token=token)
        record("SC00_assignments_list", probe=assign_probe)
        body = assign_probe.get("body")
        if isinstance(body, dict):
            items = body.get("results") or []
            if items:
                assignment_id = items[0].get("id")

    if dry_run:
        record("SC01_user_service_down", dry_run=True, note="跳过 docker stop")
        record("SC02_user_service_recover", dry_run=True)
        return {
            "experiment": "compose_fault_drill",
            "timestamp_utc": ts,
            "base_url": base_url,
            "dry_run": True,
            "scenarios": scenarios,
        }

    record("SC01_inject_stop_user_service", compose=compose_cmd(compose_file, "stop", "user-service"))
    time.sleep(3)
    courses_down = http_json("GET", courses_url, token=token)
    record(
        "SC01_courses_while_user_down",
        probe=courses_down,
        expect="HTTP 200，teacher_name 可为 null（降级）",
    )
    if assignment_id:
        submit_payload = json.dumps(
            {"assignment": assignment_id, "code": "print('fault test')"}
        ).encode()
        submit_probe = http_json(
            "POST",
            f"{base_url}/api/submissions/",
            token=token,
            data=submit_payload,
        )
        record(
            "SC01_submit_while_user_down",
            probe=submit_probe,
            expect="HTTP 503 或 401/403（fail-closed，不绕过校验）",
            assignment_id=assignment_id,
        )

    record("SC02_recover_start_user_service", compose=compose_cmd(compose_file, "start", "user-service"))
    time.sleep(8)
    record("SC02_health_after_recover", probe=wait_http(f"{base_url}/api/health/", expect_status=200))
    record("SC02_courses_after_recover", probe=http_json("GET", courses_url, token=token))

    record("SC03_inject_stop_course_service", compose=compose_cmd(compose_file, "stop", "course-service"))
    time.sleep(3)
    if assignment_id:
        submit_payload = json.dumps(
            {"assignment": assignment_id, "code": "print('fault test 2')"}
        ).encode()
        record(
            "SC03_submit_while_course_down",
            probe=http_json("POST", f"{base_url}/api/submissions/", token=token, data=submit_payload),
            expect="HTTP 503（选课/归属校验 fail-closed）",
            assignment_id=assignment_id,
        )
    record("SC03_recover_start_course_service", compose=compose_cmd(compose_file, "start", "course-service"))
    time.sleep(8)
    record("SC03_health_after_recover", probe=wait_http(f"{base_url}/api/health/", expect_status=200))

    return {
        "experiment": "compose_fault_drill",
        "timestamp_utc": ts,
        "base_url": base_url,
        "course_id": course_id,
        "assignment_id": assignment_id,
        "scenarios": scenarios,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compose 故障实验采集")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--student-user", default="demo_student")
    parser.add_argument("--student-pass", default="Demo@1234")
    parser.add_argument("--dry-run", action="store_true", help="不执行 docker stop/start，仅结构探测")
    parser.add_argument(
        "--compose-file",
        default=DEFAULT_COMPOSE_FILE,
        help="Compose 文件（默认 prod 拉取版，无需本地 build）",
    )
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    payload = run_scenarios(
        args.base_url,
        args.student_user,
        args.student_pass,
        args.dry_run,
        args.compose_file,
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RAW_DIR / f"compose_fault_{stamp}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
