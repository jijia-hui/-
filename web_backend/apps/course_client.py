"""调用课程服务内部接口；未配置 COURSE_SERVICE_URL 时回退本库查询（单测 / all 角色）。"""
import logging
import os

import requests

from .models import Course

logger = logging.getLogger(__name__)


def _internal_headers():
    token = os.environ.get('INTERNAL_TOKEN', '')
    return {'X-Internal-Token': token} if token else {}


def _course_base():
    return os.environ.get('COURSE_SERVICE_URL', '').rstrip('/')


def student_is_enrolled(course_id, user_id):
    base = _course_base()
    if base:
        url = f'{base}/internal/courses/{course_id}/enrollment/{user_id}/'
        try:
            res = requests.get(url, headers=_internal_headers(), timeout=5)
            res.raise_for_status()
            return bool(res.json().get('enrolled'))
        except Exception as exc:
            logger.warning('选课校验调用 course-service 失败 %s: %s', url, exc)
            return False
    course = Course.objects.filter(pk=course_id).first()
    if not course:
        return False
    return course.students.filter(id=user_id).exists()


def is_course_teacher(course_id, user_id):
    base = _course_base()
    if base:
        url = f'{base}/internal/courses/{course_id}/teacher/'
        try:
            res = requests.get(url, headers=_internal_headers(), timeout=5)
            res.raise_for_status()
            return res.json().get('teacher_id') == user_id
        except Exception as exc:
            logger.warning('教师校验调用 course-service 失败 %s: %s', url, exc)
            return False
    course = Course.objects.filter(pk=course_id).first()
    return bool(course and course.teacher_id == user_id)
