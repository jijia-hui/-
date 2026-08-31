# -*- coding: utf-8 -*-
"""SERVICE_ROLE 第一刀：user 进程只挂用户接口，app 进程只挂课程/作业。"""
from django.urls.resolvers import URLPattern, URLResolver
from django.test import TestCase
from rest_framework.test import APIClient

from apps.models import User
from web_backend.urls import build_urlpatterns


def collect_names(patterns):
    names = []
    for p in patterns:
        if isinstance(p, URLPattern) and p.name:
            names.append(p.name)
        elif isinstance(p, URLResolver):
            names.extend(collect_names(p.url_patterns))
    return names


class ServiceRoleUrlTest(TestCase):
    def test_user_role_has_auth_not_courses(self):
        names = collect_names(build_urlpatterns('user'))
        self.assertIn('api_token_auth', names)
        self.assertIn('send_verification_code', names)
        self.assertIn('internal_user', names)
        self.assertNotIn('course-list', names)

    def test_app_role_has_courses_not_auth(self):
        names = collect_names(build_urlpatterns('app'))
        self.assertIn('course-list', names)
        self.assertIn('assignment-list', names)
        self.assertIn('submission-list', names)
        self.assertNotIn('api_token_auth', names)
        self.assertNotIn('send_verification_code', names)

    def test_all_role_has_both(self):
        names = collect_names(build_urlpatterns('all'))
        self.assertIn('api_token_auth', names)
        self.assertIn('course-list', names)


class InternalUserApiTest(TestCase):
    def test_lookup_by_id(self):
        user = User.objects.create_user(
            username='intra', password='pass1234', email='intra@example.com',
        )
        res = APIClient().get(f'/internal/users/{user.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['username'], 'intra')
        self.assertFalse(res.data['is_teacher'])
