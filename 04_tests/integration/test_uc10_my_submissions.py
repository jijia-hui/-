# -*- coding: utf-8 -*-
"""INT-TC10 学生查看个人提交记录（UC10）：主成功流程（只看自己的、按作业过滤）+ 异常流程（防篡改）。"""
from .base import BaseAPITestCase
from apps.models import Submission


class MySubmissionsTest(BaseAPITestCase):
    """INT-TC10-1 主成功流程：学生只能看到自己的提交，且不串作业"""

    def setUp(self):
        super().setUp()
        self.mine = self.new_submission(code='我的代码')
        self.others = self.new_submission(student=self.other, code='别人的代码')

    def _ids(self, data):
        return [s['id'] for s in data.get('results', data)]

    def test_student_sees_only_own_submissions(self):
        res = self.client_for(self.student).get('/api/submissions/')
        self.assertEqual(res.status_code, 200)
        ids = self._ids(res.data)
        self.assertIn(self.mine.id, ids)
        self.assertNotIn(self.others.id, ids)

    def test_filter_by_assignment_isolates(self):
        res = self.client_for(self.student).get(
            f'/api/submissions/?assignment={self.expired.id}')
        self.assertNotIn(self.mine.id, self._ids(res.data))

    def test_filter_by_assignment_returns_mine(self):
        res = self.client_for(self.student).get(
            f'/api/submissions/?assignment={self.assignment.id}')
        self.assertIn(self.mine.id, self._ids(res.data))

    def test_student_without_submissions_sees_empty_list(self):
        # other 在本夹具中已有提交，用全新学生验证空列表
        from apps.models import User
        fresh = User.objects.create_user(username='fresh', password='x')
        res = self.client_for(fresh).get('/api/submissions/')
        self.assertEqual(self._ids(res.data), [])


class SubmissionUpdateTest(BaseAPITestCase):
    """INT-TC10-2 异常流程：PATCH 不能篡改 assignment/student（只读字段防篡改）"""

    def test_patch_cannot_change_assignment(self):
        submission = self.new_submission()
        res = self.client_for(self.student).patch(
            f'/api/submissions/{submission.id}/', {'assignment': self.expired.id})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['assignment'], self.assignment.id)

    def test_patch_cannot_change_student(self):
        submission = self.new_submission()
        res = self.client_for(self.student).patch(
            f'/api/submissions/{submission.id}/', {'student': self.other.id})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['student'], self.student.id)

    def test_patch_can_update_code(self):
        submission = self.new_submission()
        res = self.client_for(self.student).patch(
            f'/api/submissions/{submission.id}/', {'code': 'print(2)'})
        self.assertEqual(res.data['code'], 'print(2)')

    def test_student_cannot_modify_others_submission(self):
        submission = self.new_submission(student=self.other)
        res = self.client_for(self.student).patch(
            f'/api/submissions/{submission.id}/', {'code': 'x'})
        self.assertEqual(res.status_code, 404)
