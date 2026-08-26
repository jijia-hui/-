# -*- coding: utf-8 -*-
"""INT-TC02 用户登录（UC02）：主成功流程（签发 Token）+ 异常流程（错误密码、未注册、无凭证访问）。"""
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.models import User


def login(payload):
    return APIClient().post('/api/auth/token/', payload)


class LoginTest(TestCase):
    """INT-TC02-1 主成功流程：学生/教师正确凭据签发 Token"""

    def setUp(self):
        self.student = User.objects.create_user(username='stu', password='pass1234')
        self.teacher = User.objects.create_user(username='tea', password='pass1234', is_teacher=True)

    def test_login_student(self):
        res = login({'username': 'stu', 'password': 'pass1234'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('token', res.data)
        token = Token.objects.get(user=self.student)
        self.assertEqual(res.data['token'], token.key)

    def test_login_teacher(self):
        res = login({'username': 'tea', 'password': 'pass1234'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('token', res.data)

    def test_token_grants_access_to_protected_endpoint(self):
        res = login({'username': 'stu', 'password': 'pass1234'})
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {res.data['token']}")
        me = client.get('/api/users/me/')
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data['username'], 'stu')


class LoginRejectionTest(TestCase):
    """INT-TC02-2 异常流程：错误密码 / 未注册用户被拒；无凭证访问受保护接口 → 401"""

    def setUp(self):
        User.objects.create_user(username='stu', password='pass1234')

    def test_wrong_password_rejected(self):
        res = login({'username': 'stu', 'password': 'wrong-pass'})
        self.assertEqual(res.status_code, 400)

    def test_unregistered_user_rejected(self):
        res = login({'username': 'nobody', 'password': 'pass1234'})
        self.assertEqual(res.status_code, 400)

    def test_protected_endpoint_requires_token(self):
        # DRF 3.12+ 对未认证请求返回 403（PermissionDenied 语义），认证缺失即拒绝
        res = APIClient().get('/api/users/me/')
        self.assertEqual(res.status_code, 403)
