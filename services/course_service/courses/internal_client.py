"""课程服务 → 其他服务的内部调用客户端。

失败语义（见《跨服务调用说明.md》）：
- fetch_users_map（场景 #1，展示补全）：失败 → 降级返回 None，调用方把用户名置空；
- purge_assignments_for_courses（场景 #7，级联清理）：失败 → 抛 InternalServiceError，
  课程不删除（fail-closed）。
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


def _user_service_base():
    return os.environ.get('USER_SERVICE_URL', 'http://user-service:8000')


def _assignment_service_base():
    return os.environ.get('ASSIGNMENT_SERVICE_URL', 'http://assignment-service:8000')


def fetch_users_map(user_ids):
    """批量取用户基本信息 → {id: {...}}；失败降级返回 None（用户名展示为空）。"""
    ids = sorted({i for i in user_ids if i})
    if not ids:
        return {}
    url = f'{_user_service_base()}/internal/users/'
    for attempt in (1, 2):
        try:
            resp = requests.get(url, params={'ids': ','.join(map(str, ids))},
                                headers=_internal_headers(), timeout=TIMEOUT)
            if 200 <= resp.status_code < 300:
                return {u['id']: u for u in resp.json()}
            last_error = f'HTTP {resp.status_code}'
        except requests.RequestException as exc:
            last_error = str(exc)
        logger.warning('内部调用失败（第 %s 次）%s -> %s', attempt, url, last_error)
    logger.warning('用户服务不可用，课程展示将缺少教师/学生用户名（降级）')
    return None


def purge_assignments_for_courses(course_ids):
    """删除课程前，通知作业服务清理这些课程的作业与提交；失败抛异常（课程不删除）。"""
    if not course_ids:
        return {'deleted_assignments': 0, 'deleted_submissions': 0}
    url = f'{_assignment_service_base()}/internal/courses/purge/'
    last_error = None
    for attempt in (1, 2):
        try:
            resp = requests.post(url, json={'course_ids': list(course_ids)},
                                 headers=_internal_headers(), timeout=TIMEOUT)
            if 200 <= resp.status_code < 300:
                return resp.json()
            last_error = f'HTTP {resp.status_code}: {resp.text[:120]}'
        except requests.RequestException as exc:
            last_error = str(exc)
        logger.warning('内部调用失败（第 %s 次）%s -> %s', attempt, url, last_error)
    raise InternalServiceError(f'{url} -> {last_error}')
