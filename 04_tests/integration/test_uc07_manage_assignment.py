# -*- coding: utf-8 -*-
"""INT-TC07 教师管理作业（UC07）：创建（含参考文档上传）/编辑/删除 + 异常流程（学生创建 403、他人作业 403）。"""
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from .base import BaseAPITestCase
from apps.models import Assignment

DEADLINE = (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')


class AssignmentCreateTest(BaseAPITestCase):
    """INT-TC07-1 主成功流程：教师创建作业（含参考文档）"""

    def test_teacher_can_create_assignment(self):
        res = self.client_for(self.teacher).post('/api/assignments/', {
            'course': self.course.id, 'title': '实验二', 'description': '实现排序', 'deadline': DEADLINE,
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['title'], '实验二')
        self.assertEqual(res.data['course'], self.course.id)

    def test_teacher_can_create_assignment_with_reference_file(self):
        ref = SimpleUploadedFile('guide.pdf', b'%PDF-1.4 fake content',
                                 content_type='application/pdf')
        res = self.client_for(self.teacher).post('/api/assignments/', {
            'course': self.course.id, 'title': '带参考文档', 'description': '描述',
            'deadline': DEADLINE, 'reference_file': ref,
        }, format='multipart')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data['reference_file_url'].startswith('/media/assignment_refs/'))


class AssignmentEditDeleteTest(BaseAPITestCase):
    """INT-TC07-2 主成功流程：授课教师编辑/删除自己的作业"""

    def test_teacher_can_edit_own_assignment(self):
        res = self.client_for(self.teacher).patch(
            f'/api/assignments/{self.assignment.id}/', {'title': '改标题'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['title'], '改标题')

    def test_teacher_can_delete_own_assignment(self):
        res = self.client_for(self.teacher).delete(f'/api/assignments/{self.assignment.id}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Assignment.objects.filter(id=self.assignment.id).exists())


class AssignmentPermissionTest(BaseAPITestCase):
    """INT-TC07-3 异常流程：学生创建/修改、非授课教师修改/删除被拒"""

    def test_student_cannot_create_assignment(self):
        res = self.client_for(self.student).post('/api/assignments/', {
            'course': self.course.id, 'title': '越权作业', 'description': 'x', 'deadline': DEADLINE,
        })
        self.assertEqual(res.status_code, 403)

    def test_teacher_cannot_edit_others_assignment(self):
        res = self.client_for(self.teacher2).patch(
            f'/api/assignments/{self.assignment.id}/', {'title': '篡改'})
        self.assertEqual(res.status_code, 403)

    def test_teacher_cannot_delete_others_assignment(self):
        res = self.client_for(self.teacher2).delete(f'/api/assignments/{self.assignment.id}/')
        self.assertEqual(res.status_code, 403)
