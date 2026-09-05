#!/bin/bash
# scripts/fault-inject.sh — K8s 故障注入/恢复（online-teach-micro 命名空间）
# 用法: ./fault-inject.sh <F1-F6> [inject|recover]

NAMESPACE="${FAULT_NAMESPACE:-online-teach-micro}"
ACTION=${2:-"inject"}

inject_fault() {
    case $1 in
        F1)
            echo "🔴 F1: 用户服务 OOM（内存限制 64Mi）"
            kubectl patch deployment user-service -n "$NAMESPACE" \
                -p '{"spec":{"template":{"spec":{"containers":[{"name":"user-service","resources":{"limits":{"memory":"64Mi"}}}]}}}}'
            ;;
        F2)
            echo "🔴 F2: 课程服务镜像拉取失败"
            kubectl set image deployment/course-service \
                course-service=ghcr.io/nonexistent/bad:tag -n "$NAMESPACE"
            ;;
        F3)
            echo "🔴 F3: 作业服务副本缩为 0"
            kubectl scale deployment assignment-service --replicas=0 -n "$NAMESPACE"
            ;;
        F4)
            echo "🔴 F4: 三业务服务副本缩为 0"
            kubectl scale deployment user-service course-service assignment-service \
                --replicas=0 -n "$NAMESPACE"
            ;;
        F5)
            echo "🔴 F5: 停止 user-service（用户名补全降级）"
            kubectl scale deployment user-service --replicas=0 -n "$NAMESPACE"
            ;;
        F6)
            echo "🔴 F6: 停止 course-service（提交校验 fail-closed）"
            kubectl scale deployment course-service --replicas=0 -n "$NAMESPACE"
            ;;
        *)
            echo "❌ 未知故障编号: $1"
            exit 1
            ;;
    esac
}

recover_fault() {
    case $1 in
        F1)
            echo "🟢 F1: 恢复用户服务内存"
            kubectl patch deployment user-service -n "$NAMESPACE" \
                -p '{"spec":{"template":{"spec":{"containers":[{"name":"user-service","resources":{"limits":{"memory":"512Mi"}}}]}}}}'
            kubectl rollout status deployment/user-service -n "$NAMESPACE" --timeout=120s
            ;;
        F2)
            echo "🟢 F2: 回滚课程服务"
            kubectl rollout undo deployment/course-service -n "$NAMESPACE"
            kubectl rollout status deployment/course-service -n "$NAMESPACE" --timeout=120s
            ;;
        F3)
            kubectl scale deployment assignment-service --replicas=2 -n "$NAMESPACE"
            ;;
        F4)
            kubectl scale deployment user-service --replicas=2 -n "$NAMESPACE"
            kubectl scale deployment course-service --replicas=2 -n "$NAMESPACE"
            kubectl scale deployment assignment-service --replicas=2 -n "$NAMESPACE"
            ;;
        F5)
            kubectl scale deployment user-service --replicas=2 -n "$NAMESPACE"
            ;;
        F6)
            kubectl scale deployment course-service --replicas=2 -n "$NAMESPACE"
            ;;
    esac
}

if [ "$ACTION" = "recover" ]; then
    recover_fault "$1"
else
    inject_fault "$1"
fi

echo "完成: $1 $ACTION (namespace=$NAMESPACE)"
