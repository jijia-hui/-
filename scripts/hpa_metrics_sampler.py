#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HPA 自动扩缩容实验——集群指标周期采样器。

每 interval 秒采集一次并追加写入 CSV：
  - HPA 状态：当前副本 / 期望副本 / 目标 CPU% / 实测 CPU 利用率% / 最近扩缩容时间
  - Pod 状态：user-service 各 Pod 的运行态、重启次数
  - 实际资源用量：kubectl top pod（逐 Pod CPU 毫核、内存 MiB 及合计）

时间戳使用 epoch 秒 + 本地 ISO 两种形式，便于与压测脚本的
load_requests.csv / load_summary.json 按时间对齐。

用法：
  python hpa_metrics_sampler.py --interval 15 --duration 1260 \
      --out 05_management/HPA自动扩缩容实验/raw/round1/metrics_timeline.csv
"""
import argparse
import csv
import json
import os
import subprocess
import time
from datetime import datetime

FIELDS = [
    "epoch", "time_iso",
    "hpa_current_replicas", "hpa_desired_replicas",
    "hpa_target_util_pct", "hpa_current_util_pct",
    "hpa_last_scale_time",
    "pods_running", "pods_pending", "restarts_sum",
    "cpu_m_sum", "mem_mi_sum", "per_pod_detail",
]


def run_kubectl(args, timeout_s=20):
    """执行 kubectl，返回 (stdout, stderr)。超时/失败返回 (None, err)。"""
    try:
        r = subprocess.run(["kubectl"] + args, capture_output=True, text=True,
                           timeout=timeout_s, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            return None, (r.stderr or r.stdout or "").strip()[:200]
        return r.stdout, None
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except Exception as e:
        return None, type(e).__name__


def sample_hpa(ns, hpa_name):
    out, err = run_kubectl(["get", "hpa", hpa_name, "-n", ns, "-o", "json",
                            "--request-timeout=10s"])
    if out is None:
        return {}, err
    try:
        d = json.loads(out)
    except ValueError:
        return {}, "bad json"
    st = d.get("status", {})
    util = None
    for m in st.get("currentMetrics", []) or []:
        if m.get("type") == "Resource" and m.get("resource", {}).get("name") == "cpu":
            util = m["resource"].get("current", {}).get("averageUtilization")
    return {
        "hpa_current_replicas": st.get("currentReplicas"),
        "hpa_desired_replicas": st.get("desiredReplicas"),
        "hpa_target_util_pct": (d.get("spec", {}).get("metrics") or [{}])[0]
            .get("resource", {}).get("target", {}).get("averageUtilization"),
        "hpa_current_util_pct": util,
        "hpa_last_scale_time": st.get("lastScaleTime"),
    }, None


def sample_pods(ns, selector):
    out, err = run_kubectl(["get", "pods", "-n", ns, "-l", selector, "-o", "json",
                            "--request-timeout=10s"])
    if out is None:
        return {}, err
    running = pending = 0
    restarts = 0
    for p in json.loads(out).get("items", []):
        s = p.get("status", {}).get("phase")
        if s == "Running":
            running += 1
        elif s == "Pending":
            pending += 1
        for cs in p.get("status", {}).get("containerStatuses", []) or []:
            restarts += cs.get("restartCount", 0)
    return {"pods_running": running, "pods_pending": pending,
            "restarts_sum": restarts}, None


def sample_top(ns, selector):
    out, err = run_kubectl(["top", "pod", "-n", ns, "-l", selector, "--no-headers"])
    if out is None:
        return {}, err
    cpu_sum = mem_sum = 0.0
    detail = []
    for line in out.strip().splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        name, cpu_s, mem_s = parts[0], parts[1], parts[2]
        cpu = float(cpu_s.rstrip("m")) if cpu_s.endswith("m") else float(cpu_s) * 1000
        mem = float(mem_s[:-2]) if mem_s.endswith("Mi") else float(mem_s[:-2]) / 1024 \
            if mem_s.endswith("Ki") else float(mem_s.rstrip("Gi")) * 1024
        cpu_sum += cpu
        mem_sum += mem
        detail.append("%s:%dm,%.0fMi" % (name.replace("user-service-", ""), cpu, mem))
    return {"cpu_m_sum": round(cpu_sum, 1), "mem_mi_sum": round(mem_sum, 1),
            "per_pod_detail": " | ".join(detail)}, None


def main():
    ap = argparse.ArgumentParser(description="HPA/Pod/资源指标周期采样器")
    ap.add_argument("--namespace", default="online-teach-micro")
    ap.add_argument("--hpa-name", default="user-service-hpa")
    ap.add_argument("--selector", default="app=user-service")
    ap.add_argument("--interval", type=float, default=15)
    ap.add_argument("--duration", type=float, required=True, help="采样总时长（秒）")
    ap.add_argument("--out", required=True, help="输出 CSV 路径")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    end_at = time.time() + args.duration

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        n = 0
        while True:
            now = time.time()
            row = {"epoch": round(now, 1),
                   "time_iso": datetime.fromtimestamp(now).strftime("%H:%M:%S")}
            for fn in (sample_hpa, sample_pods, sample_top):
                data, err = fn(args.namespace,
                               args.hpa_name if fn is sample_hpa else args.selector)
                row.update(data)
                if err:
                    print("[sampler] %s 采集失败: %s" % (fn.__name__, err), flush=True)
            w.writerow(row)
            f.flush()
            n += 1
            if now >= end_at:
                break
            time.sleep(max(0, min(args.interval, end_at - time.time())))
    print("[sampler] 完成，共 %d 个采样点 -> %s" % (n, args.out), flush=True)


if __name__ == "__main__":
    main()
