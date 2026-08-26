# -*- coding: utf-8 -*-
"""INT-TC06 教师编辑/删除课程（UC06）：主成功流程 + 异常流程（他人课程 403/404、学生 403、编号重复 400）。"""
from .base import BaseAPITestCase
from apps.models import Course


class CourseEditTest(BaseAPITestCase):
    """INT-TC06-1 主成功流程：授课教师编辑/删除自己的课程"""

    def test_teacher_can_edit_own_course(self):
        res = self.client_for(self.teacher).patch(
            f'/api/courses/{self.course.id}/', {'name': '新名称'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['name'], '新名称')

    def test_teacher_can_delete_own_course(self):
        res = self.client_for(self.teacher).delete(f'/api/courses/{self.course.id}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Course.objects.filter(id=self.course.id).exists())

    def test_delete_cascades_assignments_and_submissions(self):
        from apps.models import Submission
        Submission.objects.create(assignment=self.assignment, student=self.student, code='x')
        self.client_for(self.teacher).delete(f'/api/courses/{self.course.id}/')
        self.assertEqual(self.assignment.submissions.count(), 0)
        self.assertFalse(Course.objects.filter(id=self.course.id).exists())


class CoursePermissionTest(BaseAPITestCase):
    """INT-TC06-2 异常流程：非授课教师、学生的修改/删除被拒"""

    def test_teacher_cannot_edit_others_course(self):
        res = self.client_for(self.teacher2).patch(
            f'/api/courses/{self.course.id}/', {'name': '篡改'})
        self.assertIn(res.status_code, (403, 404))

    def test_teacher_cannot_delete_others_course(self):
        res = self.client_for(self.teacher2).delete(f'/api/courses/{self.course.id}/')
        self.assertIn(res.status_code, (403, 404))
        self.assertTrue(Course.objects.filter(id=self.course.id).exists())

    def test_student_cannot_edit_course(self):
        res = self.client_for(self.student).patch(
            f'/api/courses/{self.course.id}/', {'name': '篡改'})
        self.assertEqual(res.status_code, 403)

    def test_student_cannot_delete_course(self):
        res = self.client_for(self.student).delete(f'/api/courses/{self.course.id}/')
        self.assertEqual(res.status_code, 403)

    def test_duplicate_code_rejected_on_patch(self):
        self.client_for(self.teacher).post('/api/courses/', {'name': '另一门', 'code': 'CN101'})
        res = self.client_for(self.teacher).patch(
            f'/api/courses/{self.course.id}/', {'code': 'CN101'})
        self.assertEqual(res.status_code, 400)
