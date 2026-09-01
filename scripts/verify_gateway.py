# -*- coding: utf-8 -*-
"""校验 Nginx 网关是否把三类 API 转到三个业务服务。

用法（Compose 已启动且可访问 http://localhost:8080）：
  python scripts/verify_gateway.py
  python scripts/verify_gateway.py --base http://127.0.0.1:8080
"""
import argparse
import sys
import urllib.error
import urllib.request

CHECKS = (
    ('/', (200,), '前端首页'),
    ('/api/health/', (200,), '作业服务探活（经网关 /api/health/）'),
    ('/api/users/me/', (401, 403), '用户服务（未登录应拒绝）'),
    ('/api/courses/', (401, 403), '课程服务（未登录应拒绝）'),
    ('/api/assignments/', (401, 403), '作业服务（未登录应拒绝）'),
)


def http_status(url):
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except urllib.error.URLError as exc:
        raise SystemExit(f'无法连接 {url}: {exc.reason}') from exc


def main():
    parser = argparse.ArgumentParser(description='校验三服务网关路由')
    parser.add_argument('--base', default='http://127.0.0.1:8080')
    args = parser.parse_args()
    base = args.base.rstrip('/')
    failed = 0
    for path, expected, title in CHECKS:
        url = base + path
        code = http_status(url)
        ok = code in expected
        mark = 'OK' if ok else 'FAIL'
        print(f'[{mark}] {title}: {url} -> {code}（期望 {list(expected)}）')
        if not ok:
            failed += 1
    if failed:
        print(f'未通过 {failed} 项，请确认 docker compose ps 中三服务均为 healthy。')
        sys.exit(1)
    print('网关路由校验通过：user / course / assignment 均可经 8080 访问。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
