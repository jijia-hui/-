# -*- coding: utf-8 -*-
"""INT-TC09 学生提交作业（UC09）：主成功流程（201/pending）+ 异常流程（教师 403、未选课 403、过期 400、参数缺失 400、作业不存在 400）。"""
from .base import BaseAPITestCase
from apps.models import Submission


class SubmissionCreateTest(BaseAPITestCase):
    """INT-TC09-1 主成功流程：已选课学生提交 → 201，状态 pending，数据正确"""

    def test_enrolled_student_can_submit(self):
        res = self.client_for(self.student).post(
            '/api/submissions/', {'assignment': self.assignment.id, 'code': 'print(1)'})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'pending')
        self.assertEqual(res.data['score'], 0)
        self.assertEqual(res.data['student_name'], 'student1')
        self.assertEqual(res.data['assignment_title'], '作业一')

    def test_submit_creates_db_record(self):
        self.client_for(self.student).post(
            '/api/submissions/', {'assignment': self.assignment.id, 'code': 'print(1)'})
        sub = Submission.objects.get(student=self.student, assignment=self.assignment)
        self.assertEqual(sub.code, 'print(1)')
        self.assertEqual(sub.status, 'pending')


class SubmissionCreateExceptionTest(BaseAPITestCase):
    """INT-TC09-2 异常流程：教师/未选课/过期/缺参/作业不存在"""

    def test_teacher_cannot_submit(self):
        res = self.client_for(self.teacher).post(
            '/api/submissions/', {'assignment': self.assignment.id, 'code': 'x'})
        self.assertEqual(res.status_code, 403)

    def test_unenrolled_student_cannot_submit(self):
        res = self.client_for(self.other).post(
            '/api/submissions/', {'assignment': self.assignment.id, 'code': 'x'})
        self.assertEqual(res.status_code, 403)

    def test_expired_assignment_rejected(self):
        res = self.client_for(self.student).post(
            '/api/submissions/', {'assignment': self.expired.id, 'code': 'x'})
        self.assertEqual(res.status_code, 400)

    def test_missing_assignment_rejected(self):
        res = self.client_for(self.student).post('/api/submissions/', {'code': 'x'})
        self.assertEqual(res.status_code, 400)

    def test_missing_code_rejected(self):
        res = self.client_for(self.student).post(
            '/api/submissions/', {'assignment': self.assignment.id})
        self.assertEqual(res.status_code, 400)

    def test_nonexistent_assignment_rejected(self):
        res = self.client_for(self.student).post(
            '/api/submissions/', {'assignment': 999999, 'code': 'x'})
        self.assertEqual(res.status_code, 400)

    def test_unauthenticated_cannot_submit(self):
        from rest_framework.test import APIClient
        res = APIClient().post('/api/submissions/', {'assignment': self.assignment.id, 'code': 'x'})
        self.assertEqual(res.status_code, 403)  # DRF 3.12+ 未认证按 PermissionDenied 拒绝
