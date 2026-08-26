# -*- coding: utf-8 -*-
"""INT-TC08 查看作业详情与参考文档（UC08）：主成功流程 + 异常流程（不存在 404）。"""
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from .base import BaseAPITestCase


class AssignmentDetailTest(BaseAPITestCase):
    """INT-TC08-1 主成功流程：学生/教师查看作业详情与参考文档 URL"""

    def test_student_can_view_assignment_detail(self):
        res = self.client_for(self.student).get(f'/api/assignments/{self.assignment.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['title'], '作业一')
        self.assertEqual(res.data['description'], '描述')
        self.assertIn('deadline', res.data)
        self.assertIsNone(res.data['reference_file_url'])

    def test_teacher_can_view_assignment_detail(self):
        res = self.client_for(self.teacher).get(f'/api/assignments/{self.assignment.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['course'], self.course.id)

    def test_reference_file_url_returned_when_uploaded(self):
        ref = SimpleUploadedFile('guide.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
        self.client_for(self.teacher).post('/api/assignments/', {
            'course': self.course.id, 'title': '带参考文档', 'description': 'd',
            'deadline': (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'reference_file': ref,
        }, format='multipart')
        latest = self.course.assignments.order_by('-created_at').first()
        res = self.client_for(self.student).get(f'/api/assignments/{latest.id}/')
        self.assertTrue(res.data['reference_file_url'].startswith('/media/assignment_refs/'))


class AssignmentDetailExceptionTest(BaseAPITestCase):
    """INT-TC08-2 异常流程：不存在的作业 → 404"""

    def test_nonexistent_assignment_404(self):
        res = self.client_for(self.student).get('/api/assignments/999999/')
        self.assertEqual(res.status_code, 404)
