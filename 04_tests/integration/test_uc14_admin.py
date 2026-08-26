# -*- coding: utf-8 -*-
"""INT-TC14 管理员后台管理（UC14）：Django Admin 各模型管理页可访问；非管理员被重定向。"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import Client


class AdminAccessTest(TestCase):
    """INT-TC14-1 主成功流程：管理员可访问后台与四个模型管理页"""

    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username='root', password='admin123', is_staff=True, is_superuser=True)
        self.teacher = get_user_model().objects.create_user(
            username='tea', password='x', is_teacher=True)
        self.client = Client()
        self.client.force_login(self.admin)

    def test_admin_index_accessible(self):
        res = self.client.get('/admin/')
        self.assertEqual(res.status_code, 200)

    def test_model_changelists_accessible(self):
        for path in ('/admin/apps/user/', '/admin/apps/course/',
                     '/admin/apps/assignment/', '/admin/apps/submission/'):
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f'{path} 不可访问')

    def test_models_registered(self):
        from django.contrib import admin
        from apps.models import Assignment, Course, Submission, User
        self.assertTrue(admin.site.is_registered(User))
        self.assertTrue(admin.site.is_registered(Course))
        self.assertTrue(admin.site.is_registered(Assignment))
        self.assertTrue(admin.site.is_registered(Submission))


class AdminPermissionTest(TestCase):
    """INT-TC14-2 异常流程：非管理员访问后台被重定向到登录页"""

    def test_teacher_redirected_to_login(self):
        teacher = get_user_model().objects.create_user(username='tea', password='x', is_teacher=True)
        client = Client()
        client.force_login(teacher)
        res = client.get('/admin/')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/admin/login/', res.url)

    def test_anonymous_redirected_to_login(self):
        res = Client().get('/admin/')
        self.assertEqual(res.status_code, 302)
