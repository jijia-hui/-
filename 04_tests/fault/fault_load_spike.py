#!/usr/bin/env python3
"""故障期间叠加并发读请求（可选），验证降级路径在负载下仍返回 200。"""

from __future__ import annotations

import argparse
import json
import statistics
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

RAW_DIR = Path(__file__).parent / "raw"


def one_get(url: str, token: str | None) -> float:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
            return (time.perf_counter() - start) * 1000
    except urllib.error.HTTPError:
        return (time.perf_counter() - start) * 1000


def spike(base_url: str, path: str, token: str | None, concurrency: int, duration_s: float) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    stop = threading.Event()
    latencies: list[float] = []
    errors = 0
    lock = threading.Lock()

    def worker():
        nonlocal errors
        while not stop.is_set():
            try:
                ms = one_get(url, token)
                with lock:
                    latencies.append(ms)
            except Exception:
                with lock:
                    errors += 1

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for _ in range(concurrency):
            pool.submit(worker)
        time.sleep(duration_s)
        stop.set()
    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else None
    return {
        "url": url,
        "concurrency": concurrency,
        "duration_s": duration_s,
        "requests": len(latencies),
        "errors": errors,
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 2) if latencies else None,
            "p95": round(p95, 2) if p95 is not None else None,
        },
    }


def login(base_url: str, user: str, password: str) -> str | None:
    payload = json.dumps({"username": user, "password": password}).encode()
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/auth/token/",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = json.loads(resp.read().decode())
        return body.get("token")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--scenario", default="courses_read", choices=["courses_read"])
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--duration", type=float, default=15.0)
    args = parser.parse_args()

    token = login(args.base_url, "demo_student", "Demo@1234")
    result = spike(args.base_url, "/api/courses/", token, args.concurrency, args.duration)
    payload = {
        "experiment": "fault_load_spike",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scenario": args.scenario,
        "result": result,
        "note": "在 user-service 已 stop 时运行本脚本，可观察降级读路径仍返回 200",
    }
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RAW_DIR / f"fault_load_spike_{stamp}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
