# -*- coding: utf-8 -*-
"""INT-TC01 用户注册（UC01）：主成功流程（学生/教师）+ 备选/异常流程（验证码、缺邮箱、非法邮箱、重复用户名、密码缺失）。"""
from django.core import mail
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.models import EmailVerificationCode, User


def issue_code(email):
    return EmailVerificationCode.issue(email).code


def register(payload):
    return APIClient().post('/api/users/', payload)


def register_ok(username, email, password='pass1234', is_teacher=False):
    payload = {
        'username': username,
        'password': password,
        'email': email,
        'verification_code': issue_code(email),
    }
    if is_teacher:
        payload['is_teacher'] = True
    return register(payload)


class RegistrationSuccessTest(TestCase):
    """INT-TC01-1 主成功流程：学生/教师注册成功，密码不返回，账号可登录"""

    def test_register_student(self):
        res = register_ok('newbie', 'newbie@example.com')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['username'], 'newbie')
        self.assertNotIn('password', res.data)
        self.assertNotIn('verification_code', res.data)
        user = User.objects.get(username='newbie')
        self.assertFalse(user.is_teacher)
        self.assertTrue(user.check_password('pass1234'))

    def test_register_teacher(self):
        res = register_ok('teanew', 'teanew@example.com', is_teacher=True)
        self.assertEqual(res.status_code, 201)
        self.assertTrue(User.objects.get(username='teanew').is_teacher)


class RegistrationEmailTest(TestCase):
    """INT-TC01-2 备选流程：发送注册验证码（outbox 断言）"""

    def test_send_code_delivers_six_digits(self):
        res = APIClient().post('/api/auth/send-code/', {'email': 'newbie@example.com'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['newbie@example.com'])
        self.assertIn('验证码', mail.outbox[0].subject)
        rec = EmailVerificationCode.objects.get(email='newbie@example.com')
        self.assertEqual(len(rec.code), 6)
        self.assertIn(rec.code, mail.outbox[0].body)

    def test_send_code_then_register_consumes_code(self):
        APIClient().post('/api/auth/send-code/', {'email': 'newbie@example.com'})
        code = EmailVerificationCode.objects.get(email='newbie@example.com').code
        res = register({'username': 'newbie', 'password': 'pass1234',
                        'email': 'newbie@example.com', 'verification_code': code})
        self.assertEqual(res.status_code, 201)
        rec = EmailVerificationCode.objects.get(email='newbie@example.com')
        self.assertIsNotNone(rec.used_at)

    def test_send_code_rejects_registered_email(self):
        User.objects.create_user(username='taken', password='x', email='taken@example.com')
        res = APIClient().post('/api/auth/send-code/', {'email': 'taken@example.com'})
        self.assertEqual(res.status_code, 400)

    def test_send_code_rate_limited(self):
        client = APIClient()
        first = client.post('/api/auth/send-code/', {'email': 'rate@example.com'})
        self.assertEqual(first.status_code, 200)
        second = client.post('/api/auth/send-code/', {'email': 'rate@example.com'})
        self.assertEqual(second.status_code, 429)


class RegistrationValidationTest(TestCase):
    """INT-TC01-3 异常流程：缺验证码 / 错验证码 / 缺邮箱 / 非法邮箱 / 重复用户名 / 缺密码 → 400"""

    def test_register_requires_verification_code(self):
        res = register({'username': 'newbie', 'password': 'pass1234', 'email': 'newbie@example.com'})
        self.assertEqual(res.status_code, 400)
        self.assertIn('verification_code', res.data)
        self.assertFalse(User.objects.filter(username='newbie').exists())

    def test_register_rejects_wrong_code(self):
        issue_code('newbie@example.com')
        res = register({'username': 'newbie', 'password': 'pass1234',
                        'email': 'newbie@example.com', 'verification_code': '000000'})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(User.objects.filter(username='newbie').exists())

    def test_register_rejects_expired_code(self):
        rec = EmailVerificationCode.issue('newbie@example.com')
        rec.created_at = timezone.now() - EmailVerificationCode.TTL
        rec.save(update_fields=['created_at'])
        res = register({'username': 'newbie', 'password': 'pass1234',
                        'email': 'newbie@example.com', 'verification_code': rec.code})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(User.objects.filter(username='newbie').exists())

    def test_register_requires_email(self):
        res = register({'username': 'newbie', 'password': 'pass1234'})
        self.assertEqual(res.status_code, 400)
        self.assertIn('email', res.data)

    def test_register_rejects_invalid_email(self):
        res = register({'username': 'newbie', 'password': 'pass1234', 'email': 'not-an-email'})
        self.assertEqual(res.status_code, 400)
        self.assertIn('email', res.data)

    def test_register_rejects_missing_password(self):
        res = register({'username': 'newbie', 'email': 'newbie@example.com',
                        'verification_code': issue_code('newbie@example.com')})
        self.assertEqual(res.status_code, 400)
        self.assertIn('password', res.data)

    def test_register_rejects_duplicate_username(self):
        User.objects.create_user(username='taken', password='x', email='taken@example.com')
        res = register({'username': 'taken', 'password': 'pass1234',
                        'email': 'other@example.com',
                        'verification_code': issue_code('other@example.com')})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(User.objects.filter(username='taken').count(), 1)
