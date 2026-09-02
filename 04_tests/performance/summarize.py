#!/usr/bin/env python3
"""Aggregate load_test.py JSON files into CSV and Markdown summaries."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path


FIELDS = [
    "version", "scenario", "concurrency", "runs", "requests_mean",
    "throughput_mean", "throughput_stdev", "average_latency_mean",
    "p95_latency_mean", "error_rate_mean", "cpu_average_mean",
    "cpu_peak_mean", "memory_average_mib_mean", "memory_peak_mib_mean",
]


def mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def stdev(values: list[float]) -> float | None:
    return statistics.stdev(values) if len(values) > 1 else 0.0 if values else None


def aggregate(files: list[Path]) -> list[dict]:
    groups: dict[tuple[str, str, int], list[dict]] = {}
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        c = data["conditions"]
        s = data["summary"]
        resource = data.get("resource_summary", {})
        version = "micro" if path.name.startswith("micro_") else "monolith"
        key = (version, c["scenario"], int(c["concurrency"]))
        groups.setdefault(key, []).append({
            "requests": s["requests"],
            "throughput": s["throughput_requests_per_second"],
            "average_latency": s["average_latency_ms"],
            "p95_latency": s["p95_latency_ms"],
            "error_rate": s["error_rate"],
            "cpu_average": resource.get("cpu_percent_total_average"),
            "cpu_peak": resource.get("cpu_percent_total_peak"),
            "memory_average_mib": (resource.get("memory_bytes_total_average") or 0) / 1024**2,
            "memory_peak_mib": (resource.get("memory_bytes_total_peak") or 0) / 1024**2,
        })
    rows = []
    for (version, scenario, concurrency), values in sorted(groups.items()):
        rows.append({
            "version": version,
            "scenario": scenario,
            "concurrency": concurrency,
            "runs": len(values),
            "requests_mean": mean([v["requests"] for v in values]),
            "throughput_mean": mean([v["throughput"] for v in values]),
            "throughput_stdev": stdev([v["throughput"] for v in values]),
            "average_latency_mean": mean([v["average_latency"] for v in values]),
            "p95_latency_mean": mean([v["p95_latency"] for v in values]),
            "error_rate_mean": mean([v["error_rate"] for v in values]),
            "cpu_average_mean": mean([v["cpu_average"] for v in values if v["cpu_average"] is not None]),
            "cpu_peak_mean": mean([v["cpu_peak"] for v in values if v["cpu_peak"] is not None]),
            "memory_average_mib_mean": mean([v["memory_average_mib"] for v in values]),
            "memory_peak_mib_mean": mean([v["memory_peak_mib"] for v in values]),
        })
    return rows


def fmt(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def write_outputs(rows: list[dict], csv_path: Path, md_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# 单体版 vs 微服务版性能对比汇总",
        "",
        "测试条件：同一台机器；同一批演示数据；同一压测脚本；每个条件 3 次；预热 5 秒，测量 15 秒。",
        "吞吐量单位为 requests/s，延迟单位为 ms，内存单位为 MiB；CPU/内存为指定 Docker 容器合计采样的平均/峰值。",
        "",
        "| " + " | ".join(FIELDS) + " |",
        "|" + "|".join("---" for _ in FIELDS) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row[field]) for field in FIELDS) + " |")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=Path(__file__).parent / "raw")
    parser.add_argument("--csv", type=Path, default=Path(__file__).parent / "性能对比汇总.csv")
    parser.add_argument("--markdown", type=Path, default=Path(__file__).parent / "性能对比汇总.md")
    args = parser.parse_args()
    files = sorted(args.raw.glob("monolith_*.json")) + sorted(args.raw.glob("micro_*.json"))
    if not files:
        parser.error(f"未找到原始结果：{args.raw}")
    rows = aggregate(files)
    write_outputs(rows, args.csv, args.markdown)
    print(f"已汇总 {len(files)} 个原始结果，生成 {len(rows)} 行条件汇总")
    print(args.csv)
    print(args.markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
