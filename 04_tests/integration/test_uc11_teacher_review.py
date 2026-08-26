# -*- coding: utf-8 -*-
"""INT-TC11 教师查看某作业的全部提交（UC11）：主成功流程 + 异常流程（非授课教师不可见）。"""
from datetime import timedelta

from .base import BaseAPITestCase


class TeacherReviewTest(BaseAPITestCase):
    """INT-TC11-1 主成功流程：授课教师查看本课程作业的全部提交"""

    def setUp(self):
        super().setUp()
        self.sub1 = self.new_submission(student=self.student, code='答案A')
        self.sub2 = self.new_submission(student=self.other, code='答案B')

    def _ids(self, data):
        return [s['id'] for s in data.get('results', data)]

    def test_teacher_sees_all_students_submissions_of_own_course(self):
        res = self.client_for(self.teacher).get('/api/submissions/')
        self.assertEqual(res.status_code, 200)
        ids = self._ids(res.data)
        self.assertIn(self.sub1.id, ids)
        self.assertIn(self.sub2.id, ids)

    def test_teacher_filter_by_assignment(self):
        # auto_now_add 快速连续创建时时间戳可能相同，显式给定时间保证 -created_at 排序确定
        from django.utils import timezone
        base = timezone.now()
        self.sub1.created_at = base
        self.sub1.save(update_fields=['created_at'])
        self.sub2.created_at = base + timedelta(seconds=1)
        self.sub2.save(update_fields=['created_at'])
        res = self.client_for(self.teacher).get(
            f'/api/submissions/?assignment={self.assignment.id}')
        self.assertEqual(self._ids(res.data), [self.sub2.id, self.sub1.id])

    def test_teacher_sees_student_name_and_status(self):
        res = self.client_for(self.teacher).get('/api/submissions/')
        sub = next(s for s in res.data['results'] if s['id'] == self.sub1.id)
        self.assertEqual(sub['student_name'], 'student1')
        self.assertEqual(sub['assignment_title'], '作业一')
        self.assertEqual(sub['status'], 'pending')


class TeacherReviewIsolationTest(BaseAPITestCase):
    """INT-TC11-2 异常流程：非授课教师看不到其他教师课程的提交"""

    def setUp(self):
        super().setUp()
        self.sub = self.new_submission(student=self.student)

    def test_other_teacher_sees_no_submissions(self):
        res = self.client_for(self.teacher2).get('/api/submissions/')
        ids = [s['id'] for s in res.data.get('results', res.data)]
        self.assertNotIn(self.sub.id, ids)

    def test_other_teacher_filter_by_assignment_sees_nothing(self):
        res = self.client_for(self.teacher2).get(
            f'/api/submissions/?assignment={self.assignment.id}')
        self.assertEqual(res.data['results'], [])
