# -*- coding: utf-8 -*-
"""INT-TC01 用户注册（UC01）：主成功流程（学生/教师）+ 备选/异常流程（缺邮箱、非法邮箱、重复用户名、密码缺失）。"""
from django.core import mail
from django.test import TestCase
from rest_framework.test import APIClient

from apps.models import User


def register(payload):
    return APIClient().post('/api/users/', payload)


class RegistrationSuccessTest(TestCase):
    """INT-TC01-1 主成功流程：学生/教师注册成功，密码不返回，账号可登录"""

    def test_register_student(self):
        res = register({'username': 'newbie', 'password': 'pass1234', 'email': 'newbie@example.com'})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['username'], 'newbie')
        self.assertNotIn('password', res.data)
        user = User.objects.get(username='newbie')
        self.assertFalse(user.is_teacher)
        self.assertTrue(user.check_password('pass1234'))

    def test_register_teacher(self):
        res = register({'username': 'teanew', 'password': 'pass1234',
                        'email': 'teanew@example.com', 'is_teacher': True})
        self.assertEqual(res.status_code, 201)
        self.assertTrue(User.objects.get(username='teanew').is_teacher)


class RegistrationEmailTest(TestCase):
    """INT-TC01-2 备选流程：注册成功邮件通知（outbox 断言）"""

    def test_register_sends_welcome_email(self):
        res = register({'username': 'newbie', 'password': 'pass1234',
                        'email': 'newbie@example.com'})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['newbie@example.com'])
        self.assertIn('注册成功', mail.outbox[0].subject)
        self.assertIn('newbie', mail.outbox[0].body)
        self.assertTrue(User.objects.filter(username='newbie').exists())


class RegistrationValidationTest(TestCase):
    """INT-TC01-3 异常流程：缺邮箱 / 非法邮箱 / 重复用户名 / 缺密码 → 400 且不产生账号"""

    def test_register_requires_email(self):
        res = register({'username': 'newbie', 'password': 'pass1234'})
        self.assertEqual(res.status_code, 400)
        self.assertIn('email', res.data)

    def test_register_rejects_invalid_email(self):
        res = register({'username': 'newbie', 'password': 'pass1234', 'email': 'not-an-email'})
        self.assertEqual(res.status_code, 400)
        self.assertIn('email', res.data)

    def test_register_rejects_missing_password(self):
        res = register({'username': 'newbie', 'email': 'newbie@example.com'})
        self.assertEqual(res.status_code, 400)
        self.assertIn('password', res.data)

    def test_register_rejects_duplicate_username(self):
        User.objects.create_user(username='taken', password='x', email='taken@example.com')
        res = register({'username': 'taken', 'password': 'pass1234', 'email': 'other@example.com'})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(User.objects.filter(username='taken').count(), 1)
