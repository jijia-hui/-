#!/usr/bin/env python3
"""聚合微服务故障相关单元/API 测试，输出可提交的原始 JSON。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = Path(__file__).parent / "raw"

# 与各服务 tests/ 中 503、降级、502 用例对应
FAULT_TEST_TARGETS = [
    {
        "service": "course_service",
        "dir": ROOT / "services" / "course_service",
        "labels": ["degrade", "fail_closed"],
        "modules": [
            "tests.test_degrade",
            "tests.test_internal",
        ],
    },
    {
        "service": "assignment_service",
        "dir": ROOT / "services" / "assignment_service",
        "labels": ["503", "degrade", "fail_closed"],
        "modules": [
            "tests.test_submissions",
            "tests.test_assignments_api",
            "tests.test_internal",
        ],
    },
    {
        "service": "user_service",
        "dir": ROOT / "services" / "user_service",
        "labels": ["502", "cascade"],
        "modules": [
            "tests.test_delete_cascade",
        ],
    },
]


def run_service_tests(target: dict) -> dict:
    service_dir = target["dir"]
    if not service_dir.is_dir():
        return {
            "service": target["service"],
            "status": "skipped",
            "reason": f"目录不存在: {service_dir}（请在 main 分支或已合并 services/ 后运行）",
            "modules": target["modules"],
        }

    env = os.environ.copy()
    env["USE_SQLITE"] = "1"
    cmd = [
        sys.executable,
        "manage.py",
        "test",
        *target["modules"],
        "-v",
        "2",
    ]
    proc = subprocess.run(
        cmd,
        cwd=service_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    return {
        "service": target["service"],
        "labels": target["labels"],
        "modules": target["modules"],
        "status": "passed" if proc.returncode == 0 else "failed",
        "exit_code": proc.returncode,
        "stdout": proc.stdout[-12000:] if proc.stdout else "",
        "stderr": proc.stderr[-8000:] if proc.stderr else "",
    }


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results = [run_service_tests(t) for t in FAULT_TEST_TARGETS]
    payload = {
        "experiment": "fault_unit_tests",
        "timestamp_utc": ts,
        "description": "故障语义自动化测试：503 fail-closed、降级、502 级联",
        "targets": results,
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.get("status") == "passed"),
            "failed": sum(1 for r in results if r.get("status") == "failed"),
            "skipped": sum(1 for r in results if r.get("status") == "skipped"),
        },
    }
    out = RAW_DIR / f"unit_tests_{ts}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0 if payload["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
