"""作业与提交服务 → 其他服务的内部调用客户端。

失败语义（见《跨服务调用说明.md》）：
- fetch_users_map（场景 #2，展示补全）：失败 → 降级返回 None，调用方把学生用户名置空；
- get_course / get_student_ids / get_teacher_course_ids（场景 #3~#6，授权与业务校验）：
  课程服务不可用 → InternalServiceError，调用方快速失败返回 503（fail-closed）；
  课程确实不存在 → CourseNotFound，调用方按业务返回 400/404。
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

TIMEOUT = (2, 3)  # (连接, 读取) 秒


class InternalServiceError(Exception):
    """内部调用失败（网络异常/超时/非约定响应码）。"""


class CourseNotFound(Exception):
    """课程在课程服务中不存在（业务判定，非故障）。"""


def _internal_headers():
    return {'X-Internal-Key': os.environ.get('INTERNAL_API_KEY', 'dev-internal-key')}


def _user_service_base():
    return os.environ.get('USER_SERVICE_URL', 'http://user-service:8000')


def _course_service_base():
    return os.environ.get('COURSE_SERVICE_URL', 'http://course-service:8000')


def _request_with_retry(method, url, **kwargs):
    """网络/超时类失败重试 1 次；返回 Response。"""
    last_error = None
    for attempt in (1, 2):
        try:
            return requests.request(method, url, timeout=TIMEOUT, **kwargs)
        except requests.RequestException as exc:
            last_error = str(exc)
            logger.warning('内部调用失败（第 %s 次）%s -> %s', attempt, url, last_error)
    raise InternalServiceError(f'{url} -> {last_error}')


def fetch_users_map(user_ids):
    """批量取用户基本信息 → {id: {...}}；失败降级返回 None（学生用户名展示为空）。"""
    ids = sorted({i for i in user_ids if i})
    if not ids:
        return {}
    url = f'{_user_service_base()}/internal/users/'
    try:
        resp = _request_with_retry('GET', url, params={'ids': ','.join(map(str, ids))},
                                   headers=_internal_headers())
    except InternalServiceError:
        logger.warning('用户服务不可用，提交列表将缺少学生用户名（降级）')
        return None
    if not 200 <= resp.status_code < 300:
        logger.warning('用户服务返回 %s，提交列表将缺少学生用户名（降级）', resp.status_code)
        return None
    return {u['id']: u for u in resp.json()}


def get_course(course_id):
    """课程详情（含授课教师 teacher_id）；不存在 → CourseNotFound；不可用 → InternalServiceError。"""
    url = f'{_course_service_base()}/internal/courses/{course_id}/'
    resp = _request_with_retry('GET', url, headers=_internal_headers())
    if resp.status_code == 404:
        raise CourseNotFound(f'course {course_id}')
    if not 200 <= resp.status_code < 300:
        raise InternalServiceError(f'{url} -> HTTP {resp.status_code}')
    return resp.json()


def get_student_ids(course_id):
    """课程的学生 ID 列表（提交前选课校验）。"""
    url = f'{_course_service_base()}/internal/courses/{course_id}/students/'
    resp = _request_with_retry('GET', url, headers=_internal_headers())
    if resp.status_code == 404:
        raise CourseNotFound(f'course {course_id}')
    if not 200 <= resp.status_code < 300:
        raise InternalServiceError(f'{url} -> HTTP {resp.status_code}')
    return resp.json().get('student_ids', [])


def get_teacher_course_ids(teacher_id):
    """教师授课的课程 ID 列表（教师查看提交列表时圈定授权范围）。"""
    url = f'{_course_service_base()}/internal/courses/'
    resp = _request_with_retry('GET', url, params={'teacher_id': teacher_id},
                               headers=_internal_headers())
    if not 200 <= resp.status_code < 300:
        raise InternalServiceError(f'{url} -> HTTP {resp.status_code}')
    return resp.json().get('course_ids', [])
