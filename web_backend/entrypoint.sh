#!/bin/sh
# 后端容器启动脚本：
# 1) 等到 MySQL 能用账号登录  2) 迁移  3) 收集静态文件  4) gunicorn
set -e

if [ "${USE_SQLITE:-}" != "1" ]; then
    echo "Waiting for MySQL at ${DB_HOST:-mysql}:${DB_PORT:-3306} ..."
    python - <<'PY'
import os, sys, time
import pymysql

host = os.environ.get("DB_HOST", "mysql")
port = int(os.environ.get("DB_PORT", "3306"))
user = os.environ.get("DB_USER", "teach_user")
password = os.environ.get("DB_PASSWORD", "")
for attempt in range(1, 31):
    try:
        conn = pymysql.connect(
            host=host, port=port, user=user, password=password, connect_timeout=3,
        )
        conn.close()
        print("MySQL is ready.")
        sys.exit(0)
    except Exception as exc:
        print(f"Waiting for MySQL ({attempt}/30): {exc}")
        time.sleep(2)
print("MySQL not ready after 60s", file=sys.stderr)
sys.exit(1)
PY
fi

mkdir -p /app/media /app/staticfiles

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

WORKERS="${GUNICORN_WORKERS:-2}"
echo "Starting gunicorn (workers=${WORKERS})..."
exec gunicorn web_backend.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${WORKERS}" \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile - \
    --capture-output
