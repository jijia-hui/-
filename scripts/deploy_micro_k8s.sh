#!/usr/bin/env bash
# 微服务版部署脚本：把 3 个业务微服务 + 网关 + 前端部署到 Kubernetes（kind/minikube/k3d/任意集群）
# 用法: ./scripts/deploy_micro_k8s.sh [服务=镜像标签 ...]
#   例: ./scripts/deploy_micro_k8s.sh user=sha123 course=latest assignment=sha123
# 未指定的服务默认使用 latest；前端镜像标签由 FRONTEND_TAG 环境变量指定（默认 latest）。
# 支持按服务指定不同标签（只改一个服务时只滚动更新它自己）；CI 里统一以当前版本部署。
# 前置: kubectl 已配置目标集群；镜像已推送 GHCR（或已 kind load 到节点）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
K8S_DIR="$ROOT/k8s/micro"
NS="online-teach-micro"

USER_TAG="latest"
COURSE_TAG="latest"
ASSIGNMENT_TAG="latest"
FRONTEND_TAG="${FRONTEND_TAG:-latest}"
for kv in "$@"; do
    case "$kv" in
        user=*) USER_TAG="${kv#user=}" ;;
        course=*) COURSE_TAG="${kv#course=}" ;;
        assignment=*) ASSIGNMENT_TAG="${kv#assignment=}" ;;
        frontend=*) FRONTEND_TAG="${kv#frontend=}" ;;
        *) echo "未知参数: $kv（支持 user/course/assignment/frontend=<tag>）"; exit 1 ;;
    esac
done

command -v kubectl >/dev/null 2>&1 || { echo "错误: 缺少 kubectl"; exit 1; }
kubectl cluster-info >/dev/null 2>&1 || { echo "错误: 无法连接集群"; exit 1; }

echo "==> 1/6 检查存储类（kind/k3d 等本地集群无存储类时安装 local-path-provisioner）"
if ! kubectl get storageclass >/dev/null 2>&1 || [ -z "$(kubectl get storageclass --no-headers 2>/dev/null)" ]; then
    kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.30/deploy/local-path-storage.yaml
    kubectl -n local-path-storage rollout status deploy/local-path-provisioner --timeout=180s
    kubectl patch storageclass local-path -p \
        '{"metadata": {"annotations": {"storageclass.kubernetes.io/is-default-class": "true"}}}'
fi

echo "==> 2/6 应用命名空间、密钥与 MySQL（三库初始化）"
kubectl apply -f "$K8S_DIR/namespace.yaml"
kubectl apply -f "$K8S_DIR/secret.yaml"
kubectl apply -f "$K8S_DIR/mysql.yaml"
kubectl -n "$NS" rollout status deploy/mysql --timeout=300s

echo "==> 3/6 部署三个业务微服务（user=$USER_TAG course=$COURSE_TAG assignment=$ASSIGNMENT_TAG）"
for svc in user course assignment; do
    TAG_VAR="${svc^^}_TAG"
    TAG="${!TAG_VAR}"
    sed -e "s|__TAG__|$TAG|g" "$K8S_DIR/${svc}-service.yaml" | kubectl apply -f -
done

echo "==> 4/6 部署网关与前端（frontend=$FRONTEND_TAG）"
kubectl create configmap gateway-config --from-file=default.conf="$ROOT/services/gateway/nginx.conf" \
    -n "$NS" -o yaml --dry-run=client | kubectl apply -f -
kubectl create configmap nginx-config --from-file=default.conf="$ROOT/web_frontend/nginx.conf" \
    -n "$NS" -o yaml --dry-run=client | kubectl apply -f -
kubectl apply -f "$K8S_DIR/gateway.yaml"
sed "s|__TAG__|$FRONTEND_TAG|g" "$K8S_DIR/frontend.yaml" | kubectl apply -f -

for deploy in user-service course-service assignment-service gateway frontend; do
    kubectl -n "$NS" rollout status "deploy/$deploy" --timeout=300s
done

echo "==> 5/6 健康检查（网关聚合 + 逐服务探活/版本号 + 鉴权 + 内部接口屏蔽）"
kubectl -n "$NS" get pods
kubectl -n "$NS" port-forward svc/frontend 8080:80 --address 127.0.0.1 >/dev/null 2>&1 &
PF_PID=$!
kubectl -n "$NS" port-forward svc/backend 8000:8000 --address 127.0.0.1 >/dev/null 2>&1 &
PF_PID2=$!
trap 'kill "$PF_PID" "$PF_PID2" 2>/dev/null || true' EXIT
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

fail=0
check() { # check <base> <路径> <期望状态码> <说明>
    code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${1}${2}" || true)
    if [ "$code" != "$3" ]; then
        echo "错误: $4（$2 期望 $3，实际 $code）"
        fail=1
    else
        echo "    $4: $3 ✓"
    fi
}
check 8080 /api/health/ 200 "网关 /api/health/（经前端）"
check 8080 /api/health/user/ 200 "user-service 探活"
check 8080 /api/health/course/ 200 "course-service 探活"
check 8080 /api/health/assignment/ 200 "assignment-service 探活"
# 内部接口屏蔽：网关直连必须 403（前端本身不代理 /internal，路径不可达）
check 8000 /internal/users/?ids=1 403 "网关屏蔽内部接口（直连网关）"

auth_code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/api/users/me/ || true)
if [ "$auth_code" != "401" ] && [ "$auth_code" != "403" ]; then
    echo "错误: 鉴权检查失败（期望 401/403，实际 $auth_code）"
    fail=1
else
    echo "    未登录访问 /api/users/me/: $auth_code ✓"
fi

echo "    各服务版本号（应与本次部署标签一致）:"
for s in user course assignment; do
    curl -s "http://127.0.0.1:8080/api/health/$s/" | sed 's/^/      /'
    echo
done

[ "$fail" -eq 0 ] || { echo "健康检查未全部通过"; exit 1; }

echo "==> 6/6 部署完成"
echo "    本机访问: kubectl -n $NS port-forward svc/frontend 8080:80"
echo "    演示数据（按顺序）:"
echo "      kubectl -n $NS exec deploy/user-service -- python manage.py seed_data"
echo "      kubectl -n $NS exec deploy/course-service -- python manage.py seed_data"
echo "      kubectl -n $NS exec deploy/assignment-service -- python manage.py seed_data"
echo "    服务日志: kubectl -n $NS logs deploy/<user|course|assignment>-service --tail=100"
