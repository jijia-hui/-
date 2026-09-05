#!/usr/bin/env bash
# HPA 自动扩缩容实验——单轮实验编排脚本。
#
# 一轮实验的完整时序（时间轴供报告对齐使用）：
#   t=0            启动指标采样器（每 15s 采一次 HPA/Pod/资源）
#   t=0   ~ +60s   基线观察（无负载，副本应稳定在 minReplicas=2）
#   t=60  ~ +60+L  高压阶段：并发 C 持续压测登录接口（L 秒）→ 观察 Pod 扩容
#   之后          冷却阶段（K 秒）：负载归零 → 观察 300s 稳定期后的缩容
#   结束          取证：HPA describe（含扩缩容事件）、事件表、最终状态
#
# 用法：
#   ./hpa_experiment.sh <轮次名> [并发数C=12] [压测时长L=240] [冷却时长K=720]
#
# 前置条件：
#   - kubectl 当前上下文可访问 online-teach-micro 命名空间
#   - HPA（min 2 / max 8 / CPU 70%）与 user-service Deployment 已部署
#   - 实验开始前副本数应已回到 minReplicas=2（上一轮冷却完成）
set -euo pipefail

ROUND=${1:?用法: hpa_experiment.sh <轮次名> [并发数] [压测时长s] [冷却时长s]}
CONC=${2:-12}
LOAD_DUR=${3:-240}
COOLDOWN=${4:-720}
BASELINE=${BASELINE:-60}
NS=online-teach-micro
URL=http://localhost:30081/api/auth/token/

ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT="$ROOT/05_management/HPA自动扩缩容实验/raw/$ROUND"
mkdir -p "$OUT"

# 防覆盖：该轮已有完整数据时拒绝重跑（避免误删已完成实验的原始数据）。
# 确要覆盖时显式 FORCE=1 ./hpa_experiment.sh round1 ...
if [ -f "$OUT/load_summary.json" ] && [ "${FORCE:-0}" != "1" ]; then
    echo "错误：$OUT 已有压测数据（load_summary.json）。换一个轮次名，或 FORCE=1 强制覆盖。" >&2
    exit 1
fi

# Python 解释器探测：本机 Git Bash 可能没有 python（cmd 启动时 PATH 不同），
# 依次尝试 python / py -3 / python3；也可用 HPA_PYTHON=/d/py312/python 显式指定。
py_run() {
    if [ -n "${HPA_PYTHON:-}" ]; then
        "$HPA_PYTHON" "$@"
    elif command -v python >/dev/null 2>&1; then
        python "$@"
    elif command -v py >/dev/null 2>&1; then
        py -3 "$@"
    elif command -v python3 >/dev/null 2>&1; then
        python3 "$@"
    else
        echo "错误：找不到 Python 解释器（python / py / python3 均不可用）。" >&2
        echo "      安装 Python 或设置 HPA_PYTHON=<python路径> 后重试。" >&2
        return 127
    fi
}

# 本机 Git Bash 的 /usr/bin/sleep 不可执行（Permission denied），用 Python 等待
sleep_s() { py_run -c "import time,sys; time.sleep(float(sys.argv[1]))" "$1"; }

echo "[$ROUND] $(date '+%F %T') 前置检查：HPA 状态（应处于 minReplicas=2 且低负载）"
kubectl get hpa user-service-hpa -n "$NS"

echo "[$ROUND] $(date '+%F %T') 启动指标采样器：间隔 15s，总时长 $((BASELINE+LOAD_DUR+COOLDOWN))s"
py_run "$ROOT/scripts/hpa_metrics_sampler.py" \
    --interval 15 --duration $((BASELINE+LOAD_DUR+COOLDOWN)) \
    --out "$OUT/metrics_timeline.csv" > "$OUT/sampler.log" 2>&1 &
SAMPLER_PID=$!
trap 'kill "$SAMPLER_PID" 2>/dev/null || true' EXIT

echo "[$ROUND] $(date '+%F %T') 基线观察 ${BASELINE}s（无负载）"
sleep_s "$BASELINE"

echo "[$ROUND] $(date '+%F %T') 高压阶段：并发 $CONC，持续 ${LOAD_DUR}s，目标 $URL"
py_run "$ROOT/scripts/hpa_loadtest.py" \
    --url "$URL" --username demo_teacher --password 'Demo@1234' \
    --concurrency "$CONC" --duration "$LOAD_DUR" \
    --out-dir "$OUT" --label "$ROUND-high" > "$OUT/load_console.log" 2>&1
cat "$OUT/load_console.log"

echo "[$ROUND] $(date '+%F %T') 冷却阶段：负载归零，观察缩容，等待 ${COOLDOWN}s"
sleep_s "$COOLDOWN"

kill "$SAMPLER_PID" 2>/dev/null || true
sleep_s 2

echo "[$ROUND] $(date '+%F %T') 取证：HPA describe / 事件 / 最终状态"
kubectl describe hpa user-service-hpa -n "$NS" > "$OUT/hpa_describe.txt"
kubectl get events -n "$NS" --sort-by=.lastTimestamp > "$OUT/events_all.txt"
# 本机 Git Bash 的 grep 不可用，改用 Python 过滤事件
py_run - "$OUT/events_all.txt" "$OUT/events.txt" <<'PYEOF'
import sys
src, dst = sys.argv[1], sys.argv[2]
keys = ("user-service-hpa", "user-service-", "scaled")
with open(src, encoding="utf-8") as f, open(dst, "w", encoding="utf-8") as g:
    for line in f:
        if any(k.lower() in line.lower() for k in keys):
            g.write(line)
PYEOF
{
    kubectl get hpa user-service-hpa -n "$NS"
    echo
    kubectl get pods -n "$NS" -l app=user-service -o wide
} > "$OUT/final_state.txt"

echo "[$ROUND] $(date '+%F %T') 完成。原始数据目录：$OUT"
