#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HPA 自动扩缩容实验——单轮数据分析。

把同一轮目录下的三份原始数据按时间对齐：
  - load_requests.csv    逐请求延迟/状态
  - load_summary.json    压测起止时间
  - metrics_timeline.csv 每 15s 的 HPA/Pod/资源采样

输出：
  - analysis_timeline.csv   以压测开始为原点、每 30s 一个桶：
       请求数、吞吐、平均/P95 延迟、错误率、当时副本数、CPU 利用率
  - 终端打印单轮摘要（高压阶段整体 + 扩容前/后对比）

用法：
  python hpa_analyze.py 05_management/HPA自动扩缩容实验/raw/round1
"""
import csv
import json
import math
import os
import sys

BUCKET_S = 30


def pct(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = max(0, min(len(s) - 1, math.ceil(p / 100.0 * len(s)) - 1))
    return round(s[k], 1)


def load_round(round_dir):
    with open(os.path.join(round_dir, "load_summary.json"), encoding="utf-8") as f:
        summary = json.load(f)
    reqs = []
    with open(os.path.join(round_dir, "load_requests.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            reqs.append({"t_rel": float(row["t_rel_s"]),
                         "lat": float(row["latency_ms"]),
                         "ok": row["ok"] == "True",
                         "status": int(row["status"])})
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
                            "util": num("hpa_current_util_pct"),
                            "cpu_m": num("cpu_m_sum")})
    return summary, reqs, metrics


def state_at(metrics, t_rel, key):
    """t_rel 时刻（取不早于该时刻的最近一个采样点之前、离得最近的采样值）。"""
    best, best_dt = None, 1e18
    for m in metrics:
        dt = abs(m["t_rel"] - t_rel)
        if dt < best_dt and m.get(key) is not None:
            best, best_dt = m[key], dt
    return best


def bucket_stats(reqs, lo, hi):
    sel = [r for r in reqs if lo <= r["t_rel"] < hi]
    if not sel:
        return {"n": 0}
    lats = [r["lat"] for r in sel]
    ok = sum(1 for r in sel if r["ok"])
    return {"n": len(sel), "rps": round(len(sel) / (hi - lo), 2),
            "avg": round(sum(lats) / len(lats), 0), "p95": pct(lats, 95),
            "err_pct": round(100.0 * (len(sel) - ok) / len(sel), 2)}


def main():
    round_dir = sys.argv[1]
    summary, reqs, metrics = load_round(round_dir)
    dur = summary["actual_duration_s"]

    # 逐 30s 分桶时间线
    out_csv = os.path.join(round_dir, "analysis_timeline.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t_range_s", "requests", "rps", "avg_ms", "p95_ms",
                    "err_pct", "replicas_mid", "cpu_util_pct_mid"])
        for lo in range(0, int(dur) + BUCKET_S, BUCKET_S):
            st = bucket_stats(reqs, lo, lo + BUCKET_S)
            w.writerow(["[%d,%d)" % (lo, lo + BUCKET_S), st.get("n", 0),
                        st.get("rps", ""), st.get("avg", ""), st.get("p95", ""),
                        st.get("err_pct", ""),
                        state_at(metrics, lo + BUCKET_S / 2, "replicas"),
                        state_at(metrics, lo + BUCKET_S / 2, "util")])

    # 整体 + 扩容前/后对比：以副本数首次达到峰值 80% 的时刻分段
    peak = max((m["replicas"] for m in metrics if m["replicas"] is not None),
               default=None)
    reach = next((m["t_rel"] for m in metrics
                  if m["replicas"] is not None and peak and m["replicas"] >= peak - 1
                  and m["t_rel"] <= dur), dur) if peak else dur
    seg_early = bucket_stats(reqs, 0, reach)
    seg_late = bucket_stats(reqs, reach, dur)

    def line(name, st):
        if not st or st.get("n", 0) == 0:
            return "%s: 无请求" % name
        return ("%s: n=%d rps=%.2f avg=%.0fms p95=%.0fms err=%.2f%%"
                % (name, st["n"], st.get("rps", 0), st.get("avg", 0),
                   st.get("p95", 0), st.get("err_pct", 0)))

    print("=== %s ===" % round_dir)
    print("峰值副本: %s | 达到峰值时刻: 压测开始后 %.0fs | 压测时长: %.0fs"
          % (peak, max(reach, 0), dur))
    print(line("高压阶段整体", bucket_stats(reqs, 0, dur)))
    print(line("扩容前段 [0,%.0f)" % max(reach, 0), seg_early))
    print(line("扩容后段 [%.0f,%.0f)" % (max(reach, 0), dur), seg_late))
    print("时间线明细 -> %s" % out_csv)


if __name__ == "__main__":
    main()
