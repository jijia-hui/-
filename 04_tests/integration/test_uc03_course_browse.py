# -*- coding: utf-8 -*-
"""INT-TC03 浏览课程列表与详情（UC03）：主成功流程 + 异常流程（不存在 → 404、未登录 → 401）。"""
from .base import BaseAPITestCase


class CourseBrowseTest(BaseAPITestCase):
    """INT-TC03-1 主成功流程：学生浏览列表（含 is_enrolled/student_count），查看详情"""

    def test_student_sees_all_courses_in_list(self):
        res = self.client_for(self.student).get('/api/courses/')
        self.assertEqual(res.status_code, 200)
        items = res.data['results']
        ids = [c['id'] for c in items]
        self.assertIn(self.course.id, ids)
        course = next(c for c in items if c['id'] == self.course.id)
        self.assertEqual(course['name'], '操作系统')
        self.assertEqual(course['teacher_name'], 'teacher1')
        self.assertEqual(course['student_count'], 1)
        self.assertTrue(course['is_enrolled'])

    def test_unenrolled_student_sees_is_enrolled_false(self):
        res = self.client_for(self.other).get('/api/courses/')
        course = next(c for c in res.data['results'] if c['id'] == self.course.id)
        self.assertFalse(course['is_enrolled'])

    def test_course_detail(self):
        res = self.client_for(self.student).get(f'/api/courses/{self.course.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['name'], '操作系统')
        students = [u['username'] for u in res.data['students']]
        self.assertIn('student1', students)

    def test_teacher_sees_only_own_courses(self):
        res = self.client_for(self.teacher2).get('/api/courses/')
        ids = [c['id'] for c in res.data['results']]
        self.assertNotIn(self.course.id, ids)


class CourseBrowseExceptionTest(BaseAPITestCase):
    """INT-TC03-2 异常流程：课程不存在 → 404；未登录 → 401"""

    def test_nonexistent_course_404(self):
        res = self.client_for(self.student).get('/api/courses/999999/')
        self.assertEqual(res.status_code, 404)

    def test_unauthenticated_request_401(self):
        from rest_framework.test import APIClient
        res = APIClient().get('/api/courses/')
        self.assertEqual(res.status_code, 403)  # DRF 3.12+ 未认证按 PermissionDenied 拒绝
