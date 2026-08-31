# API 网关镜像（Nginx）。网关不计入业务微服务，只做路径路由与内部接口屏蔽。
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8000/api/health/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
