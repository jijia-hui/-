#!/usr/bin/env python3
"""可复用的只读 HTTP 压测工具，输出单次实验的 JSON 原始结果。

单体版和微服务版必须使用同一个脚本，只替换 base URL、token 和容器列表。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


SCENARIOS = {
    "courses": "/api/courses/",
    "assignments": "/api/assignments/?course={course_id}",
    "submissions": "/api/submissions/?assignment={assignment_id}",
}


@dataclass
class RequestResult:
    latency_ms: float
    status: Optional[int]
    error: Optional[str]


class StatsSampler:
    """Periodically samples Docker stats for the explicitly named containers."""

    def __init__(self, containers: list[str], interval: float = 1.0) -> None:
        self.containers = containers
        self.interval = interval
        self.samples: list[dict] = []
        self.errors: list[str] = []
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if not self.containers:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.interval + 2)

    def _run(self) -> None:
        while not self._stop.is_set():
            self._sample()
            self._stop.wait(self.interval)

    def _sample(self) -> None:
        try:
            proc = subprocess.run(
                [
                    "docker", "stats", "--no-stream",
                    "--format", "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}",
                    *self.containers,
                ],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=10, check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self.errors.append(str(exc))
            return
        if proc.returncode != 0:
            message = (proc.stderr or proc.stdout or "docker stats failed").strip()
            if message not in self.errors:
                self.errors.append(message)
            return
        rows = []
        cpu_total = 0.0
        memory_total = 0.0
        for line in proc.stdout.splitlines():
            parts = line.split("\t", 2)
            if len(parts) != 3:
                continue
            name, cpu_text, memory_text = parts
            cpu = _parse_cpu(cpu_text)
            memory = _parse_memory(memory_text.split("/", 1)[0].strip())
            rows.append({"name": name, "cpu_percent": cpu, "memory_bytes": memory})
            if cpu is not None:
                cpu_total += cpu
            if memory is not None:
                memory_total += memory
        self.samples.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "containers": rows,
            "cpu_percent_total": cpu_total if rows else None,
            "memory_bytes_total": memory_total if rows else None,
        })


def _parse_cpu(value: str) -> Optional[float]:
    try:
        return float(value.strip().rstrip("%"))
    except ValueError:
        return None


def _parse_memory(value: str) -> Optional[float]:
    units = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3,
             "KB": 1000, "MB": 1000**2, "GB": 1000**3}
    value = value.strip()
    for unit, multiplier in sorted(units.items(), key=lambda item: -len(item[0])):
        if value.endswith(unit):
            try:
                return float(value[:-len(unit)].strip()) * multiplier
            except ValueError:
                return None
    return None


def _percentile(values: list[float], percentile: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def _request(url: str, token: str, timeout: float) -> RequestResult:
    started = time.perf_counter()
    request = urllib.request.Request(url, headers={"Authorization": f"Token {token}"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
            status = response.status
            error = None if 200 <= status < 300 else f"HTTP {status}"
    except urllib.error.HTTPError as exc:
        status = exc.code
        error = f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        status = None
        error = type(exc).__name__
    return RequestResult((time.perf_counter() - started) * 1000, status, error)


def run(args: argparse.Namespace) -> dict:
    path_template = SCENARIOS[args.scenario]
    path = path_template.format(course_id=args.course_id, assignment_id=args.assignment_id)
    url = args.base_url.rstrip("/") + path
    sampler = StatsSampler(args.containers)
    sampler.start()
    run_started_at = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    warmup_end = start + args.warmup
    end = warmup_end + args.duration
    results: list[RequestResult] = []
    lock = threading.Lock()

    def worker() -> None:
        while time.perf_counter() < end:
            result = _request(url, args.token, args.timeout)
            now = time.perf_counter()
            if now >= warmup_end:
                with lock:
                    results.append(result)

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(worker) for _ in range(args.concurrency)]
        for future in futures:
            future.result()
    sampler.stop()

    latencies = [item.latency_ms for item in results]
    errors = [item for item in results if item.error]
    status_counts: dict[str, int] = {}
    for item in results:
        key = str(item.status) if item.status is not None else "network_error"
        status_counts[key] = status_counts.get(key, 0) + 1
    measured_seconds = max(args.duration, 0.001)
    cpu_values = [s["cpu_percent_total"] for s in sampler.samples
                  if s["cpu_percent_total"] is not None]
    memory_values = [s["memory_bytes_total"] for s in sampler.samples
                     if s["memory_bytes_total"] is not None]
    return {
        "schema_version": 1,
        "started_at": run_started_at,
        "conditions": {
            "base_url": args.base_url.rstrip("/"),
            "scenario": args.scenario,
            "path": path,
            "concurrency": args.concurrency,
            "warmup_seconds": args.warmup,
            "duration_seconds": args.duration,
            "timeout_seconds": args.timeout,
            "course_id": args.course_id,
            "assignment_id": args.assignment_id,
            "containers": args.containers,
            "hostname": os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME"),
        },
        "summary": {
            "requests": len(results),
            "successes": len(results) - len(errors),
            "errors": len(errors),
            "error_rate": len(errors) / len(results) if results else None,
            "throughput_requests_per_second": len(results) / measured_seconds,
            "average_latency_ms": statistics.mean(latencies) if latencies else None,
            "p95_latency_ms": _percentile(latencies, 0.95),
            "min_latency_ms": min(latencies) if latencies else None,
            "max_latency_ms": max(latencies) if latencies else None,
            "status_counts": status_counts,
        },
        "raw": {
            "latencies_ms": latencies,
            "errors": [item.error for item in errors],
        },
        "resource_summary": {
            "docker_stats_samples": len(sampler.samples),
            "cpu_percent_total_average": statistics.mean(cpu_values) if cpu_values else None,
            "cpu_percent_total_peak": max(cpu_values) if cpu_values else None,
            "memory_bytes_total_average": statistics.mean(memory_values) if memory_values else None,
            "memory_bytes_total_peak": max(memory_values) if memory_values else None,
            "sampler_errors": sampler.errors,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", required=True, help="只在本机命令行传入，不要提交到仓库")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), required=True)
    parser.add_argument("--course-id", type=int, help="assignments 场景必填")
    parser.add_argument("--assignment-id", type=int, help="submissions 场景必填")
    parser.add_argument("--concurrency", type=int, required=True)
    parser.add_argument("--duration", type=float, default=60)
    parser.add_argument("--warmup", type=float, default=15)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--containers", default="", help="逗号分隔的 Docker 容器名，用于 CPU/内存采样")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.scenario == "assignments" and args.course_id is None:
        parser.error("assignments 场景需要 --course-id")
    if args.scenario == "submissions" and args.assignment_id is None:
        parser.error("submissions 场景需要 --assignment-id")
    if args.concurrency < 1 or args.duration <= 0 or args.warmup < 0:
        parser.error("并发数必须 >= 1，时长必须 > 0，预热时间不能为负数")
    args.containers = [item.strip() for item in args.containers.split(",") if item.strip()]
    return args


def main() -> int:
    args = parse_args()
    result = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = result["summary"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"原始结果已写入 {args.output}")
    return 0 if summary["requests"] and summary["error_rate"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
