"""assignment-service 内部接口与模型规则测试。"""
from django.test import TestCase
from django.utils import timezone

from .helpers import (COURSE2_ID, COURSE_ID, STUDENT2_ID, STUDENT_ID, INTERNAL_KEY,
                      make_assignment, make_submission)


class InternalPurgeTests(TestCase):
    def setUp(self):
        self.a1 = make_assignment(COURSE_ID, title='C1作业')
        self.a2 = make_assignment(COURSE2_ID, title='C2作业')
        self.sub1 = make_submission(self.a1, STUDENT_ID)
        self.sub2 = make_submission(self.a2, STUDENT2_ID)

    def test_courses_purge_deletes_assignments_and_submissions(self):
        resp = self.client.post('/internal/courses/purge/',
                                {'course_ids': [COURSE_ID]},
                                content_type='application/json', **INTERNAL_KEY)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data['deleted_assignments'], 1)
        self.assertEqual(resp.data['deleted_submissions'], 1)
        # 其他课程的作业不受影响
        from assignments.models import Assignment, Submission
        self.assertTrue(Assignment.objects.filter(id=self.a2.id).exists())
        self.assertTrue(Submission.objects.filter(id=self.sub2.id).exists())

    def test_courses_purge_idempotent(self):
        self.client.post('/internal/courses/purge/', {'course_ids': [COURSE_ID]},
                         content_type='application/json', **INTERNAL_KEY)
        resp = self.client.post('/internal/courses/purge/', {'course_ids': [COURSE_ID]},
                                content_type='application/json', **INTERNAL_KEY)
        self.assertEqual(resp.data['deleted_assignments'], 0)

    def test_courses_purge_rejects_bad_payload(self):
        resp = self.client.post('/internal/courses/purge/', {'course_ids': 'x'}, **INTERNAL_KEY)
        self.assertEqual(resp.status_code, 400)

    def test_user_purge_deletes_student_submissions(self):
        resp = self.client.post(f'/internal/users/{STUDENT_ID}/purge/', **INTERNAL_KEY)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['deleted_submissions'], 1)
        from assignments.models import Submission
        self.assertFalse(Submission.objects.filter(student_id=STUDENT_ID).exists())
        self.assertTrue(Submission.objects.filter(id=self.sub2.id).exists())

    def test_wrong_key_forbidden(self):
        resp = self.client.post('/internal/courses/purge/', {'course_ids': [1]},
                                HTTP_X_INTERNAL_KEY='bad')
        self.assertEqual(resp.status_code, 403)


class ModelRuleTests(TestCase):
    def test_assignment_is_expired(self):
        past = make_assignment(days=-1)
        future = make_assignment(days=1)
        self.assertTrue(past.is_expired())
        self.assertFalse(future.is_expired())

    def test_submission_defaults(self):
        a = make_assignment()
        s = make_submission(a, STUDENT_ID)
        self.assertEqual(s.status, 'pending')
        self.assertEqual(s.score, 0)
        self.assertLessEqual(s.created_at, timezone.now())
