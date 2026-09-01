#!/usr/bin/env bash
# 部署脚本：把平台部署到 Kubernetes（kind / minikube / k3d / 任意集群均可）
# 用法: ./scripts/deploy_k8s.sh <镜像版本标签，如 v1.0.0>
# 前置: kubectl 已配置目标集群；镜像已推送到 GHCR（或已在集群节点上，如 kind load）
set -euo pipefail

TAG="${1:?用法: ./scripts/deploy_k8s.sh <镜像版本标签>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
K8S_DIR="$ROOT/k8s"
NS="online-teach"

command -v kubectl >/dev/null 2>&1 || { echo "错误: 缺少 kubectl"; exit 1; }
kubectl cluster-info >/dev/null 2>&1 || { echo "错误: 无法连接集群"; exit 1; }

echo "==> 1/5 检查存储类（kind/k3d 等本地集群无存储类时安装 local-path-provisioner）"
if ! kubectl get storageclass >/dev/null 2>&1 || [ -z "$(kubectl get storageclass --no-headers 2>/dev/null)" ]; then
    kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.30/deploy/local-path-storage.yaml
    kubectl -n local-path-storage rollout status deploy/local-path-provisioner --timeout=180s
    kubectl patch storageclass local-path -p \
        '{"metadata": {"annotations": {"storageclass.kubernetes.io/is-default-class": "true"}}}'
fi

echo "==> 2/5 应用命名空间、密钥与 MySQL"
kubectl apply -f "$K8S_DIR/namespace.yaml"
kubectl apply -f "$K8S_DIR/secret.yaml"
kubectl apply -f "$K8S_DIR/mysql.yaml"
kubectl -n "$NS" rollout status deploy/mysql --timeout=300s

echo "==> 3/5 部署三个业务服务与前端（镜像版本: $TAG）"
kubectl create configmap nginx-config --from-file=nginx.conf="$ROOT/web_frontend/nginx.conf" \
    -n "$NS" -o yaml --dry-run=client | kubectl apply -f -
sed "s|__IMAGE_TAG__|$TAG|g" "$K8S_DIR/user-service.yaml" | kubectl apply -f -
sed "s|__IMAGE_TAG__|$TAG|g" "$K8S_DIR/course-service.yaml" | kubectl apply -f -
sed "s|__IMAGE_TAG__|$TAG|g" "$K8S_DIR/assignment-service.yaml" | kubectl apply -f -
sed "s|__IMAGE_TAG__|$TAG|g" "$K8S_DIR/frontend.yaml" | kubectl apply -f -
kubectl -n "$NS" rollout status deploy/user-service --timeout=300s
kubectl -n "$NS" rollout status deploy/course-service --timeout=300s
kubectl -n "$NS" rollout status deploy/assignment-service --timeout=300s
kubectl -n "$NS" rollout status deploy/frontend --timeout=300s

echo "==> 4/5 健康检查（前端首页 + 后端 /api/health/）"
kubectl -n "$NS" get pods
kubectl -n "$NS" port-forward svc/frontend 8080:80 --address 127.0.0.1 >/dev/null 2>&1 &
PF_PID=$!
trap 'kill "$PF_PID" 2>/dev/null || true' EXIT
for ((i = 1; i <= 30; i++)); do
    if curl -fsS -o /dev/null http://127.0.0.1:8080/ 2>/dev/null; then
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "错误: 前端首页不可达（port-forward 后 60 秒）"
        exit 1
    fi
    sleep 2
done
HEALTH=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/api/health/ || true)
if [ "$HEALTH" != "200" ]; then
    echo "错误: 后端健康检查失败（期望 /api/health/ HTTP 200，实际 $HEALTH）"
    exit 1
fi
CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/api/users/me/ || true)
if [ "$CODE" != "401" ] && [ "$CODE" != "403" ]; then
    echo "错误: 后端 API 鉴权检查失败（期望 401/403，实际 HTTP $CODE）"
    exit 1
fi
echo "==> 健康检查通过: 前端首页 200，/api/health/ 200，/api/users/me/ $CODE"

echo "==> 5/5 部署完成"
echo "    本机访问: kubectl -n $NS port-forward svc/frontend 8080:80"
echo "    初始化演示数据: kubectl -n $NS exec deploy/assignment-service -- python manage.py seed_data"
