# -*- coding: utf-8 -*-
"""INT-TC12 教师评分（UC12）：主成功流程（graded/得分生效、学生可见）+ 异常流程（学生 403、非授课教师 403、分数缺失/越界/非整数 400）。"""
from .base import BaseAPITestCase


class GradeTest(BaseAPITestCase):
    """INT-TC12-1 主成功流程：授课教师评分 → 200，状态 graded，得分更新且学生可见"""

    def test_teacher_can_grade(self):
        submission = self.new_submission()
        res = self.client_for(self.teacher).post(
            f'/api/submissions/{submission.id}/grade/', {'score': 92})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], 'graded')
        self.assertEqual(res.data['score'], 92)

    def test_score_persisted_in_db(self):
        submission = self.new_submission()
        self.client_for(self.teacher).post(
            f'/api/submissions/{submission.id}/grade/', {'score': 85})
        submission.refresh_from_db()
        self.assertEqual(submission.score, 85)
        self.assertEqual(submission.status, 'graded')

    def test_student_sees_graded_score(self):
        submission = self.new_submission()
        self.client_for(self.teacher).post(
            f'/api/submissions/{submission.id}/grade/', {'score': 88})
        res = self.client_for(self.student).get(
            f'/api/submissions/?assignment={self.assignment.id}')
        data = next(s for s in res.data['results'] if s['id'] == submission.id)
        self.assertEqual(data['status'], 'graded')
        self.assertEqual(data['score'], 88)


class GradeBoundaryTest(BaseAPITestCase):
    """INT-TC12-2 边界值：0 与 100 合法"""

    def test_score_zero_allowed(self):
        submission = self.new_submission()
        res = self.client_for(self.teacher).post(
            f'/api/submissions/{submission.id}/grade/', {'score': 0})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['score'], 0)

    def test_score_hundred_allowed(self):
        submission = self.new_submission()
        res = self.client_for(self.teacher).post(
            f'/api/submissions/{submission.id}/grade/', {'score': 100})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['score'], 100)


class GradeExceptionTest(BaseAPITestCase):
    """INT-TC12-3 异常流程：学生评分、非授课教师评分、分数缺失/越界/非整数"""

    def setUp(self):
        super().setUp()
        self.submission = self.new_submission()

    def test_student_cannot_grade(self):
        res = self.client_for(self.student).post(
            f'/api/submissions/{self.submission.id}/grade/', {'score': 100})
        self.assertEqual(res.status_code, 403)

    def test_other_teacher_cannot_grade(self):
        # 提交列表按授课教师隔离：非授课教师查询不到该提交（404），而非 403
        res = self.client_for(self.teacher2).post(
            f'/api/submissions/{self.submission.id}/grade/', {'score': 100})
        self.assertEqual(res.status_code, 404)

    def test_missing_score_rejected(self):
        res = self.client_for(self.teacher).post(
            f'/api/submissions/{self.submission.id}/grade/', {})
        self.assertEqual(res.status_code, 400)

    def test_score_above_range_rejected(self):
        res = self.client_for(self.teacher).post(
            f'/api/submissions/{self.submission.id}/grade/', {'score': 101})
        self.assertEqual(res.status_code, 400)

    def test_score_below_range_rejected(self):
        res = self.client_for(self.teacher).post(
            f'/api/submissions/{self.submission.id}/grade/', {'score': -1})
        self.assertEqual(res.status_code, 400)

    def test_non_integer_score_rejected(self):
        res = self.client_for(self.teacher).post(
            f'/api/submissions/{self.submission.id}/grade/', {'score': 'abc'})
        self.assertEqual(res.status_code, 400)

    def test_rejected_grade_does_not_change_status(self):
        self.client_for(self.teacher).post(
            f'/api/submissions/{self.submission.id}/grade/', {'score': 999})
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, 'pending')
