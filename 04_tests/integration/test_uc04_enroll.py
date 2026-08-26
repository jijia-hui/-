# -*- coding: utf-8 -*-
"""INT-TC04 学生选课/退课（UC04）：主成功流程 + 备选/异常流程（教师选课被拒、退课、未登录）。"""
from .base import BaseAPITestCase


class EnrollTest(BaseAPITestCase):
    """INT-TC04-1 主成功流程：学生选课成功，状态生效"""

    def test_enroll_still_works_for_student(self):
        res = self.client_for(self.other).post(f'/api/courses/{self.course.id}/enroll/')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(self.course.students.filter(id=self.other.id).exists())

    def test_enroll_marks_is_enrolled(self):
        self.client_for(self.other).post(f'/api/courses/{self.course.id}/enroll/')
        res = self.client_for(self.other).get(f'/api/courses/{self.course.id}/')
        self.assertTrue(res.data['is_enrolled'])

    def test_enroll_is_idempotent(self):
        client = self.client_for(self.other)
        first = client.post(f'/api/courses/{self.course.id}/enroll/')
        second = client.post(f'/api/courses/{self.course.id}/enroll/')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(self.course.students.filter(id=self.other.id).count(), 1)


class UnenrollTest(BaseAPITestCase):
    """INT-TC04-2 备选流程：退课成功并从名单移除"""

    def test_student_can_unenroll(self):
        res = self.client_for(self.student).post(f'/api/courses/{self.course.id}/unenroll/')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(self.course.students.filter(id=self.student.id).exists())

    def test_unenroll_updates_detail(self):
        self.client_for(self.student).post(f'/api/courses/{self.course.id}/unenroll/')
        res = self.client_for(self.student).get(f'/api/courses/{self.course.id}/')
        self.assertFalse(res.data['is_enrolled'])


class EnrollExceptionTest(BaseAPITestCase):
    """INT-TC04-3 异常流程：教师选课被拒、未登录被拒"""

    def test_teacher_cannot_enroll(self):
        res = self.client_for(self.teacher).post(f'/api/courses/{self.course.id}/enroll/')
        self.assertEqual(res.status_code, 400)

    def test_unauthenticated_cannot_enroll(self):
        from rest_framework.test import APIClient
        res = APIClient().post(f'/api/courses/{self.course.id}/enroll/')
        self.assertEqual(res.status_code, 403)  # DRF 3.12+ 未认证按 PermissionDenied 拒绝
