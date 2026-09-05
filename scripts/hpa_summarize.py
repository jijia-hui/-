#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HPA 自动扩缩容实验——跨轮汇总。

读取 raw/round1..roundN 各轮的 load_summary.json 与 metrics_timeline.csv，
产出 Markdown 格式的跨轮对比表：
  - 高压阶段整体：吞吐 / 平均延迟 / P95 / 错误率 / 峰值副本
  - 副本阶段拆分：按 30s 桶内副本数（2/4/6-8）聚合延迟，验证“扩容降延迟”

用法：
  python hpa_summarize.py 05_management/HPA自动扩缩容实验/raw
"""
import csv
import glob
import json
import math
import os
import re
import sys


def pct(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = max(0, min(len(s) - 1, math.ceil(p / 100.0 * len(s)) - 1))
    return round(s[k], 0)


def load_round(round_dir):
    with open(os.path.join(round_dir, "load_summary.json"), encoding="utf-8") as f:
        summary = json.load(f)
    reqs = []
    with open(os.path.join(round_dir, "load_requests.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            reqs.append({"t_rel": float(row["t_rel_s"]),
                         "lat": float(row["latency_ms"]),
                         "ok": row["ok"] == "True"})
    metrics = []
    with open(os.path.join(round_dir, "metrics_timeline.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            def num(key):
                try:
                    return float(row[key]) if row[key] != "" else None
                except ValueError:
                    return None
            metrics.append({"t_rel": float(row["epoch"]) - summary["start_epoch"],
                            "replicas": num("hpa_current_replicas"),
                            "util": num("hpa_current_util_pct")})
    return summary, reqs, metrics


def stats(reqs):
    lats = [r["lat"] for r in reqs]
    ok = sum(1 for r in reqs if r["ok"])
    if not lats:
        return {"n": 0, "rps": 0, "avg": 0, "p95": 0, "err": 0.0}
    return {"n": len(lats),
            "rps": round(len(lats) / 240.0, 2),          # 各轮压测均按 240s 计
            "avg": round(sum(lats) / len(lats), 0),
            "p95": pct(lats, 95),
            "err": round(100.0 * (len(lats) - ok) / len(lats), 2)}


def replicas_near(metrics, t):
    best, dt = None, 1e18
    for m in metrics:
        if m["replicas"] is None:
            continue
        d = abs(m["t_rel"] - t)
        if d < dt:
            best, dt = m["replicas"], d
    return best


def phase_split(reqs, metrics):
    """把请求按当时副本数归组：<4 → 2 副本期；4~5 → 4 副本期；>=6 → 6-8 副本期。"""
    groups = {"2": [], "4": [], "6-8": []}
    for r in reqs:
        n = replicas_near(metrics, r["t_rel"]) or 2
        key = "2" if n < 4 else ("4" if n < 6 else "6-8")
        groups[key].append(r)
    return groups


def main():
    raw_dir = sys.argv[1]
    rounds = sorted(glob.glob(os.path.join(raw_dir, "round*")))
    rows, phase_rows = [], []
    peak_util = []
    for rd in rounds:
        name = os.path.basename(rd)
        summary, reqs, metrics = load_round(rd)
        s = stats(reqs)
        peak = max((m["replicas"] for m in metrics if m["replicas"] is not None), default=0)
        pu = max((m["util"] for m in metrics if m["util"] is not None and 0 < m["t_rel"] < 240),
                 default=None)
        peak_util.append(pu)
        rows.append((name, summary["total_requests"], s["rps"], s["avg"], s["p95"],
                     s["err"], int(peak), pu))
        for phase, group in phase_split(reqs, metrics).items():
            if group:
                ps = stats(group)
                phase_rows.append((name, phase, ps["n"], ps["avg"], ps["p95"]))

    print("| 轮次 | 请求数 | 吞吐 RPS | 平均延迟 ms | P95 ms | 错误率 % | 峰值副本 | 压测期峰值 CPU%% |")
    print("|---|---|---|---|---|---|---|---|")
    for r in rows:
        print("| %s | %d | %.2f | %.0f | %.0f | %.2f | %d | %s%% |"
              % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], int(r[7]) if r[7] else "-"))

    print()
    print("| 轮次 | 副本阶段 | 请求数 | 平均延迟 ms | P95 ms |")
    print("|---|---|---|---|---|")
    for r in phase_rows:
        print("| %s | %s | %d | %.0f | %.0f |" % r)

    avgs = [r[3] for r in rows]
    print()
    print("三轮平均：吞吐 %.2f RPS，平均延迟 %.0f ms，P95 %.0f ms，错误率 %.2f%%"
          % (sum(r[2] for r in rows) / len(rows), sum(avgs) / len(avgs),
             sum(r[4] for r in rows) / len(rows), sum(r[5] for r in rows) / len(rows)))


if __name__ == "__main__":
    main()
