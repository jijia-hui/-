#!/bin/sh
# 后端容器启动脚本：
# 1) 等待 MySQL 就绪  2) 执行迁移  3) 收集静态文件  4) 启动 gunicorn
set -e

echo "Waiting for MySQL at ${DB_HOST:-mysql}:${DB_PORT:-3306} ..."
while ! python -c "import socket,sys; s=socket.socket(); s.settimeout(2); s.connect((sys.argv[1], int(sys.argv[2]))); s.close()" "${DB_HOST:-mysql}" "${DB_PORT:-3306}" 2>/dev/null; do
    sleep 2
done
echo "MySQL is ready."

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting gunicorn..."
exec gunicorn web_backend.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120
