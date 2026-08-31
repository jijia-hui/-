"""用户服务 → 其他服务的内部调用客户端（仅用于删除用户时的级联清理）。

失败语义（见《跨服务调用说明.md》场景 #8）：任一下游清理失败即抛 InternalServiceError，
用户不会被删除（fail-closed）；清理操作幂等，失败后可重试。
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

TIMEOUT = (2, 3)  # (连接, 读取) 秒


class InternalServiceError(Exception):
    """内部调用失败（网络异常/超时/非 2xx）。"""


def _internal_headers():
    return {'X-Internal-Key': os.environ.get('INTERNAL_API_KEY', 'dev-internal-key')}


def _post(url):
    """POST 一次 + 网络类失败重试 1 次；非 2xx 视为失败。"""
    last_error = None
    for attempt in (1, 2):
        try:
            resp = requests.post(url, json={}, headers=_internal_headers(), timeout=TIMEOUT)
            if 200 <= resp.status_code < 300:
                return resp.json()
            last_error = f'HTTP {resp.status_code}: {resp.text[:120]}'
        except requests.RequestException as exc:
            last_error = str(exc)
        logger.warning('内部调用失败（第 %s 次）%s -> %s', attempt, url, last_error)
    raise InternalServiceError(f'{url} -> {last_error}')


def purge_user_everywhere(user_id):
    """删除用户前，级联清理其在课程服务与作业服务的数据。"""
    course_base = os.environ.get('COURSE_SERVICE_URL', 'http://course-service:8000')
    assignment_base = os.environ.get('ASSIGNMENT_SERVICE_URL', 'http://assignment-service:8000')
    # 顺序：先课程（其内部会级联清理这些课程的作业），再作业服务清掉该学生的其余提交
    _post(f'{course_base}/internal/users/{user_id}/purge/')
    _post(f'{assignment_base}/internal/users/{user_id}/purge/')
