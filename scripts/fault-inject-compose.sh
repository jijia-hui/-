#!/usr/bin/env bash
# Compose 故障注入（与答辩 P23 一致：docker compose stop/start）
# 用法:
#   ./scripts/fault-inject-compose.sh inject user-service
#   ./scripts/fault-inject-compose.sh recover user-service
#   ./scripts/fault-inject-compose.sh status

set -euo pipefail
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.micro.yml}"
ACTION="${1:-status}"
TARGET="${2:-user-service}"

cd "$(dirname "$0")/.."

case "$ACTION" in
  inject)
    echo "🔴 注入故障: stop $TARGET"
    docker compose -f "$COMPOSE_FILE" stop "$TARGET"
    docker compose -f "$COMPOSE_FILE" ps "$TARGET" || true
    ;;
  recover)
    echo "🟢 恢复服务: start $TARGET"
    docker compose -f "$COMPOSE_FILE" start "$TARGET"
    sleep 5
    docker compose -f "$COMPOSE_FILE" ps "$TARGET" || true
    ;;
  status)
    docker compose -f "$COMPOSE_FILE" ps
    ;;
  *)
    echo "用法: $0 {inject|recover|status} [user-service|course-service|assignment-service]"
    exit 1
    ;;
esac
