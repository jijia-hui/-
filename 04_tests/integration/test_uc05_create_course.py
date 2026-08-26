# -*- coding: utf-8 -*-
"""INT-TC05 教师创建课程（UC05）：主成功流程（创建者自动成为授课教师）+ 异常流程（学生创建 403、编号重复 400、未登录 401）。"""
from .base import BaseAPITestCase
from apps.models import Course


class CourseCreateTest(BaseAPITestCase):
    """INT-TC05-1 主成功流程：教师创建课程，自动设为授课教师"""

    def test_teacher_can_create_course(self):
        res = self.client_for(self.teacher).post('/api/courses/', {
            'name': '计算机网络', 'code': 'CN101', 'description': '网络课程',
        })
        self.assertEqual(res.status_code, 201)
        course = Course.objects.get(id=res.data['id'])
        self.assertEqual(course.teacher, self.teacher)
        self.assertEqual(res.data['teacher_name'], 'teacher1')

    def test_created_course_visible_in_list(self):
        client = self.client_for(self.teacher)
        created = client.post('/api/courses/', {'name': '计算机网络', 'code': 'CN101'})
        res = client.get('/api/courses/')
        ids = [c['id'] for c in res.data['results']]
        self.assertIn(created.data['id'], ids)


class CourseCreateExceptionTest(BaseAPITestCase):
    """INT-TC05-2 异常流程：学生创建被拒、编号重复、未登录"""

    def test_student_cannot_create_course(self):
        res = self.client_for(self.student).post('/api/courses/', {
            'name': '越权课程', 'code': 'BAD101',
        })
        self.assertEqual(res.status_code, 403)
        self.assertFalse(Course.objects.filter(code='BAD101').exists())

    def test_duplicate_code_rejected(self):
        res = self.client_for(self.teacher).post('/api/courses/', {
            'name': '重复编号', 'code': 'OS101',
        })
        self.assertEqual(res.status_code, 400)

    def test_unauthenticated_cannot_create(self):
        from rest_framework.test import APIClient
        res = APIClient().post('/api/courses/', {'name': 'x', 'code': 'X101'})
        self.assertEqual(res.status_code, 403)  # DRF 3.12+ 未认证按 PermissionDenied 拒绝
