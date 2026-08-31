# -*- coding: utf-8 -*-
"""SERVICE_ROLE：user / course / app 三进程拆分的路由与内部接口。"""
from django.urls.resolvers import URLPattern, URLResolver
from django.test import TestCase
from rest_framework.test import APIClient

from apps.models import Course, User
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

    def test_course_role_has_courses_not_assignments(self):
        names = collect_names(build_urlpatterns('course'))
        self.assertIn('course-list', names)
        self.assertIn('internal_course_enrollment', names)
        self.assertIn('internal_course_teacher', names)
        self.assertNotIn('assignment-list', names)
        self.assertNotIn('api_token_auth', names)

    def test_app_role_has_assignments_not_courses(self):
        names = collect_names(build_urlpatterns('app'))
        self.assertIn('assignment-list', names)
        self.assertIn('submission-list', names)
        self.assertNotIn('course-list', names)
        self.assertNotIn('api_token_auth', names)
        self.assertNotIn('send_verification_code', names)

    def test_all_role_has_user_course_and_app(self):
        names = collect_names(build_urlpatterns('all'))
        self.assertIn('api_token_auth', names)
        self.assertIn('course-list', names)
        self.assertIn('assignment-list', names)


class InternalUserApiTest(TestCase):
    def test_lookup_by_id(self):
        user = User.objects.create_user(
            username='intra', password='pass1234', email='intra@example.com',
        )
        res = APIClient().get(f'/internal/users/{user.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['username'], 'intra')
        self.assertFalse(res.data['is_teacher'])


class InternalCourseApiTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username='cteach', password='x', is_teacher=True, email='ct@example.com',
        )
        self.student = User.objects.create_user(
            username='cstu', password='x', email='cs@example.com',
        )
        self.course = Course.objects.create(name='操作系统', code='OS101', teacher=self.teacher)
        self.course.students.add(self.student)

    def test_enrollment_true_and_false(self):
        enrolled = APIClient().get(
            f'/internal/courses/{self.course.id}/enrollment/{self.student.id}/',
        )
        self.assertEqual(enrolled.status_code, 200)
        self.assertTrue(enrolled.data['enrolled'])
        outsider = User.objects.create_user(username='cout', password='x', email='co@example.com')
        missing = APIClient().get(
            f'/internal/courses/{self.course.id}/enrollment/{outsider.id}/',
        )
        self.assertEqual(missing.status_code, 200)
        self.assertFalse(missing.data['enrolled'])

    def test_teacher_lookup(self):
        res = APIClient().get(f'/internal/courses/{self.course.id}/teacher/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['teacher_id'], self.teacher.id)
        self.assertEqual(res.data['username'], 'cteach')
