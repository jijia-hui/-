"""course-service 测试公共夹具：JWT 主体 + 测试数据。

课程服务没有用户表，测试用 Principal 直接构造 JWT（与生产链路一致：
用户服务签发 → 课程服务本地验签）。
"""
from rest_framework.test import APIClient

from courses.jwt_auth import Principal, make_token
from courses.models import Course, Enrollment

TEACHER_ID = 101
TEACHER2_ID = 102
STUDENT_ID = 201
STUDENT2_ID = 202


def client_for(user_id, username=None, is_teacher=False, is_staff=False):
    username = username or (f'u{user_id}')
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {make_token(Principal(user_id, username, is_teacher, is_staff))}')
    return client


def make_course(code='CS101', teacher_id=TEACHER_ID, name='程序设计基础'):
    return Course.objects.create(code=code, name=name, description='desc', teacher_id=teacher_id)


def enroll(course, student_id):
    return Enrollment.objects.create(course=course, student_id=student_id)


def fake_users_map(*user_ids):
    """模拟用户服务内部接口的返回（tests 中不发起真实 HTTP 调用）。"""
    return {uid: {'id': uid, 'username': f'user{uid}', 'is_teacher': uid < 200,
                  'email': f'u{uid}@example.com', 'avatar': '', 'bio': ''}
            for uid in user_ids}
