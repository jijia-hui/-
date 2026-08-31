"""assignment-service 测试公共夹具：JWT 主体 + 本地数据 + 课程服务 mock。

本服务没有用户/课程表，测试用 Principal 构造 JWT；课程归属/选课校验
通过 mock 内部客户端完成（不发起真实 HTTP 调用）。
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from assignments.jwt_auth import Principal, make_token
from assignments.internal_client import CourseNotFound, InternalServiceError
from assignments.models import Assignment, Submission

COURSE_ID = 11
COURSE2_ID = 12
TEACHER_ID = 101
TEACHER2_ID = 102
STUDENT_ID = 201
STUDENT2_ID = 202

INTERNAL_KEY = {'HTTP_X_INTERNAL_KEY': 'dev-internal-key'}


def client_for(user_id, username=None, is_teacher=False, is_staff=False):
    username = username or f'u{user_id}'
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f'Token {make_token(Principal(user_id, username, is_teacher, is_staff))}')
    return client


def make_assignment(course_id=COURSE_ID, title='作业一', days=1, teacher_seq=0):
    return Assignment.objects.create(
        course_id=course_id, title=title, description='描述',
        deadline=timezone.now() + timedelta(days=days))


def make_submission(assignment, student_id=STUDENT_ID, code='print(1)'):
    return Submission.objects.create(
        assignment=assignment, student_id=student_id, code=code)


def fake_course(course_id=COURSE_ID, teacher_id=TEACHER_ID):
    return {'id': course_id, 'code': 'CS101', 'name': '程序设计基础', 'teacher_id': teacher_id}


def fake_users_map(*user_ids):
    return {uid: {'id': uid, 'username': f'user{uid}', 'is_teacher': uid < 200,
                  'email': f'u{uid}@example.com', 'avatar': '', 'bio': ''}
            for uid in user_ids}


def course_env(course=None, students=None, teacher_courses=None):
    """构造一组内部客户端 mock（默认课程 11 归属教师 101、学生 201 已选课）。"""
    import contextlib
    from unittest import mock

    course = course or fake_course()
    students = [STUDENT_ID] if students is None else students
    teacher_courses = [COURSE_ID] if teacher_courses is None else teacher_courses

    @contextlib.contextmanager
    def _ctx():
        patches = [
            mock.patch('assignments.views.get_course', return_value=course),
            mock.patch('assignments.views.get_student_ids', return_value=students),
            mock.patch('assignments.views.get_teacher_course_ids', return_value=teacher_courses),
            mock.patch('assignments.views.fetch_users_map', return_value={}),
        ]
        for p in patches:
            p.start()
        try:
            yield
        finally:
            for p in patches:
                p.stop()

    return _ctx()
