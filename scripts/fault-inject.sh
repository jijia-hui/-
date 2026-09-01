#!/bin/bash
# scripts/fault-inject.sh
# 用法: ./fault-inject.sh <故障编号> [恢复]

NAMESPACE="default"
ACTION=${2:-"inject"}

inject_fault() {
    case $1 in
        F1)
            echo "🔴 F1: 注入用户服务 OOM（调低内存限制至 64Mi）"
            kubectl patch deployment user-service -n $NAMESPACE \
                -p '{"spec":{"template":{"spec":{"containers":[{"name":"user-service","resources":{"limits":{"memory":"64Mi"}}}]}}}}'
            ;;
        F2)
            echo "🔴 F2: 注入课程服务镜像拉取失败"
            kubectl set image deployment/course-service \
                course-service=course-service:nonexistent-tag -n $NAMESPACE
            ;;
        F3)
            echo "🔴 F3: 注入作业服务健康检查失败（通过环境变量控制）"
            kubectl set env deployment/assignment-service \
                FAKE_UNHEALTHY=true -n $NAMESPACE
            ;;
        F4)
            echo "🔴 F4: 注入网关 502（将所有后端副本缩为 0）"
            kubectl scale deployment user-service course-service assignment-service \
                --replicas=0 -n $NAMESPACE
            ;;
        F5)
            echo "🔴 F5: 注入 MySQL 慢查询（通过 ConfigMap 注入 SQL）"
            kubectl exec -n $NAMESPACE deploy/assignment-service -- \
                python manage.py inject_slow_query --duration=30
            ;;
        F6)
            echo "🔴 F6: 注入跨服务调用超时（课程服务调用户服务超时）"
            kubectl set env deployment/course-service \
                USER_SERVICE_TIMEOUT_MS=1 -n $NAMESPACE
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
            echo "🟢 F1: 恢复用户服务内存限制"
            kubectl patch deployment user-service -n $NAMESPACE \
                -p '{"spec":{"template":{"spec":{"containers":[{"name":"user-service","resources":{"limits":{"memory":"256Mi"}}}]}}}}'
            ;;
        F2)
            echo "🟢 F2: 回滚课程服务到上一版本"
            kubectl rollout undo deployment/course-service -n $NAMESPACE
            ;;
        F3)
            echo "🟢 F3: 恢复作业服务健康检查"
            kubectl set env deployment/assignment-service \
                FAKE_UNHEALTHY- -n $NAMESPACE
            ;;
        F4)
            echo "🟢 F4: 恢复所有服务副本"
            kubectl scale deployment user-service --replicas=2 -n $NAMESPACE
            kubectl scale deployment course-service --replicas=2 -n $NAMESPACE
            kubectl scale deployment assignment-service --replicas=2 -n $NAMESPACE
            ;;
        F5)
            echo "🟢 F5: 终止慢查询"
            kubectl exec -n $NAMESPACE deploy/assignment-service -- \
                python manage.py kill_slow_query
            ;;
        F6)
            echo "🟢 F6: 恢复跨服务调用超时设置"
            kubectl set env deployment/course-service \
                USER_SERVICE_TIMEOUT_MS- -n $NAMESPACE
            ;;
    esac
}

if [ "$ACTION" = "recover" ]; then
    recover_fault "$1"
else
    inject_fault "$1"
fi
