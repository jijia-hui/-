#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HPA 自动扩缩容实验——登录接口压测工具。

对 user-service 的 /api/auth/token/ 发起固定并发数的 HTTP POST 压测。
该接口做 PBKDF2 密码校验（CPU 密集型），是驱动 CPU 利用率型 HPA 的理想负载。

每个请求记录：相对/绝对时间戳、延迟、HTTP 状态码、成功与否、错误类型，
输出两类原始数据：
  - load_requests.csv   逐请求原始记录
  - load_summary.json   汇总指标（吞吐量、平均/P50/P95/P99 延迟、错误率）

用法：
  python hpa_loadtest.py --url http://localhost:30081/api/auth/token/ \
      --username demo_teacher --password 'Demo@1234' \
      --concurrency 12 --duration 240 \
      --out-dir 05_management/HPA自动扩缩容实验/raw/round1 --label round1-high
"""
import argparse
import csv
import json
import math
import os
import threading
import time
from datetime import datetime, timezone

import requests

_results = []            # (seq, epoch_start, latency_ms, status, ok, err)
_lock = threading.Lock()
_seq = 0


def worker(idx: int, url: str, payload: dict, deadline: float, timeout: tuple):
    """单压测线程：持续发登录请求直到 deadline。"""
    global _seq
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    while time.time() < deadline:
        err, status, ok = "", 0, False
        t0 = time.time()
        try:
            r = session.post(url, json=payload, timeout=timeout)
            status = r.status_code
            ok = (status == 200)
            r.close()
            if not ok:
                err = "http_%d" % status
        except requests.exceptions.Timeout:
            err = "timeout"
        except requests.exceptions.ConnectionError:
            err = "conn_error"
        except Exception as e:                       # 其余异常按类型名记录
            err = type(e).__name__
        t1 = time.time()
        with _lock:
            _seq += 1
            _results.append((_seq, t0, (t1 - t0) * 1000.0, status, ok, err))
        if not ok:
            time.sleep(0.05)                         # 出错时退避，避免空转刷错误


def pct(sorted_vals, p):
    """nearest-rank 百分位。"""
    if not sorted_vals:
        return None
    k = max(0, min(len(sorted_vals) - 1, math.ceil(p / 100.0 * len(sorted_vals)) - 1))
    return sorted_vals[k]


def main():
    ap = argparse.ArgumentParser(description="user-service 登录接口压测工具（HPA 实验用）")
    ap.add_argument("--url", default="http://localhost:30081/api/auth/token/")
    ap.add_argument("--username", default="demo_teacher")
    ap.add_argument("--password", default="Demo@1234")
    ap.add_argument("--concurrency", type=int, default=12, help="并发线程数")
    ap.add_argument("--duration", type=float, default=240, help="压测持续秒数")
    ap.add_argument("--timeout", type=float, default=30, help="单请求超时（秒）")
    ap.add_argument("--out-dir", required=True, help="原始数据输出目录")
    ap.add_argument("--label", default="load", help="本轮压测标签（写入汇总文件名）")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    payload = {"username": args.username, "password": args.password}

    # 先发一次冒烟请求，凭据/链路不通时立刻失败，避免空跑
    smoke = requests.post(args.url, json=payload, timeout=(5, args.timeout))
    if smoke.status_code != 200:
        raise SystemExit("冒烟请求失败 status=%s body=%s" % (smoke.status_code, smoke.text[:200]))

    threads = []
    start_gate = threading.Barrier(args.concurrency + 1)
    deadline = time.time() + args.duration

    def gated_worker(i):
        start_gate.wait()
        worker(i, args.url, payload, deadline, (5, args.timeout))

    for i in range(args.concurrency):
        t = threading.Thread(target=gated_worker, args=(i,), daemon=True)
        t.start()
        threads.append(t)

    t_start = time.time()
    start_gate.wait()                                # 所有线程同一时刻起跑
    for t in threads:
        t.join()
    t_end = time.time()

    rows = sorted(_results, key=lambda r: r[0])
    lat_sorted = sorted(r[2] for r in rows if r[4])
    total = len(rows)
    ok_n = sum(1 for r in rows if r[4])
    http_err = sum(1 for r in rows if not r[4] and r[3] > 0)
    client_err = sum(1 for r in rows if not r[4] and r[3] == 0)
    elapsed = max(t_end - t_start, 1e-9)

    summary = {
        "label": args.label,
        "url": args.url,
        "concurrency": args.concurrency,
        "planned_duration_s": args.duration,
        "actual_duration_s": round(elapsed, 3),
        "start_epoch": t_start,
        "end_epoch": t_end,
        "start_iso": datetime.fromtimestamp(t_start).astimezone().isoformat(),
        "total_requests": total,
        "success_200": ok_n,
        "http_errors": http_err,
        "client_errors": client_err,
        "error_rate_pct": round(100.0 * (total - ok_n) / total, 4) if total else None,
        "throughput_rps": round(total / elapsed, 2),
        "latency_ms": {
            "avg": round(sum(lat_sorted) / len(lat_sorted), 2) if lat_sorted else None,
            "p50": pct(lat_sorted, 50) and round(pct(lat_sorted, 50), 2),
            "p90": pct(lat_sorted, 90) and round(pct(lat_sorted, 90), 2),
            "p95": pct(lat_sorted, 95) and round(pct(lat_sorted, 95), 2),
            "p99": pct(lat_sorted, 99) and round(pct(lat_sorted, 99), 2),
            "max": round(max(lat_sorted), 2) if lat_sorted else None,
        },
        "latency_ms_all_requests": {                 # 含失败请求的延迟（观察超时/排队）
            "avg": round(sum(r[2] for r in rows) / total, 2) if total else None,
            "p95": pct([r[2] for r in rows], 95) and round(pct(sorted(r[2] for r in rows), 95), 2),
        },
    }

    req_csv = os.path.join(args.out_dir, "load_requests.csv")
    with open(req_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["seq", "epoch_start", "t_rel_s", "latency_ms", "status", "ok", "error"])
        for seq, ts, lat, status, ok, err in rows:
            w.writerow([seq, round(ts, 3), round(ts - t_start, 3), round(lat, 2), status, ok, err])

    sum_json = os.path.join(args.out_dir, "load_summary.json")
    with open(sum_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("原始数据: %s / %s" % (req_csv, sum_json))


if __name__ == "__main__":
    main()
