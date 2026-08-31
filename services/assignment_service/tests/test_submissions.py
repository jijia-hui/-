"""提交与评分接口测试（UC09~UC12）：选课校验/教师归属校验走 mock，覆盖降级与 503。"""
from unittest import mock

from django.test import TestCase

from assignments.internal_client import CourseNotFound, InternalServiceError

from .helpers import (COURSE_ID, STUDENT2_ID, STUDENT_ID, TEACHER2_ID, TEACHER_ID,
                      client_for, course_env, fake_course, fake_users_map,
                      make_assignment, make_submission)


class SubmitTests(TestCase):
    def setUp(self):
        self.a1 = make_assignment()

    def test_enrolled_student_submits_pending(self):
        with course_env(students=[STUDENT_ID]):
            resp = client_for(STUDENT_ID).post(
                '/api/submissions/', {'assignment': self.a1.id, 'code': 'print(1)'})
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data['status'], 'pending')
        self.assertEqual(resp.data['score'], 0)
        self.assertEqual(resp.data['assignment'], self.a1.id)

    def test_teacher_cannot_submit(self):
        with course_env(students=[STUDENT_ID]):
            resp = client_for(TEACHER_ID, is_teacher=True).post(
                '/api/submissions/', {'assignment': self.a1.id, 'code': 'x'})
        self.assertEqual(resp.status_code, 403)

    def test_not_enrolled_student_forbidden(self):
        with course_env(students=[STUDENT2_ID]):
            resp = client_for(STUDENT_ID).post(
                '/api/submissions/', {'assignment': self.a1.id, 'code': 'x'})
        self.assertEqual(resp.status_code, 403)
        self.assertIn('请先选课', resp.data['detail'])

    def test_course_service_down_returns_503_not_bypass(self):
        # 场景 #4：选课校验服务不可用 → 快速失败，绝不绕过校验
        with mock.patch('assignments.views.get_student_ids',
                        side_effect=InternalServiceError('course-service down')):
            resp = client_for(STUDENT_ID).post(
                '/api/submissions/', {'assignment': self.a1.id, 'code': 'x'})
        self.assertEqual(resp.status_code, 503)
        self.assertIn('选课校验服务暂不可用', resp.data['detail'])

    def test_expired_assignment_rejected(self):
        expired = make_assignment(days=-1, title='过期作业')
        with course_env(students=[STUDENT_ID]):
            resp = client_for(STUDENT_ID).post(
                '/api/submissions/', {'assignment': expired.id, 'code': 'x'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('已截止', resp.data['detail'])

    def test_unknown_assignment_400(self):
        with course_env():
            resp = client_for(STUDENT_ID).post(
                '/api/submissions/', {'assignment': 99999, 'code': 'x'})
        self.assertEqual(resp.status_code, 400)

    def test_missing_fields_400(self):
        with course_env():
            resp = client_for(STUDENT_ID).post('/api/submissions/', {'code': 'x'})
        self.assertEqual(resp.status_code, 400)


class SubmissionListTests(TestCase):
    def setUp(self):
        self.a1 = make_assignment(title='作业一')
        self.a2 = make_assignment(course_id=99, title='他人作业')
        self.s1 = make_submission(self.a1, STUDENT_ID)
        self.s2 = make_submission(self.a1, STUDENT2_ID)

    def test_student_sees_own_only(self):
        with course_env():
            resp = client_for(STUDENT_ID).get('/api/submissions/')
        rows = resp.data['results']
        self.assertEqual([s['id'] for s in rows], [self.s1.id])

    def test_assignment_filter(self):
        make_submission(self.a2, STUDENT_ID)
        with course_env():
            resp = client_for(STUDENT_ID).get(f'/api/submissions/?assignment={self.a1.id}')
        rows = resp.data['results']
        self.assertEqual([s['id'] for s in rows], [self.s1.id])

    def test_teacher_scope_from_course_service(self):
        # 场景 #6：教师 101 授课课程（mock 返回 [COURSE_ID]）下的全部提交可见
        with course_env(teacher_courses=[COURSE_ID]):
            resp = client_for(TEACHER_ID, is_teacher=True).get(
                f'/api/submissions/?assignment={self.a1.id}')
        rows = resp.data['results']
        self.assertCountEqual([s['id'] for s in rows], [self.s1.id, self.s2.id])

    def test_teacher_list_503_when_course_service_down(self):
        with mock.patch('assignments.views.get_teacher_course_ids',
                        side_effect=InternalServiceError('down')):
            resp = client_for(TEACHER_ID, is_teacher=True).get('/api/submissions/')
        self.assertEqual(resp.status_code, 503)

    def test_student_names_enriched_and_degraded(self):
        # 用户服务正常：补全学生用户名；用户服务不可用：student_name 降级为 null
        with course_env(), mock.patch('assignments.views.fetch_users_map',
                                      return_value=fake_users_map(STUDENT_ID, STUDENT2_ID)):
            resp = client_for(STUDENT_ID).get('/api/submissions/')
            self.assertEqual(resp.data['results'][0]['student_name'], 'user201')
        with course_env(), mock.patch('assignments.views.fetch_users_map', return_value=None):
            resp = client_for(STUDENT_ID).get('/api/submissions/')
            self.assertIsNone(resp.data['results'][0]['student_name'])
            self.assertEqual(resp.data['results'][0]['assignment_title'], '作业一')  # 本地字段不受影响


class GradeTests(TestCase):
    def setUp(self):
        self.a1 = make_assignment()
        self.sub = make_submission(self.a1, STUDENT_ID)

    def test_owner_teacher_grades(self):
        with course_env():
            resp = client_for(TEACHER_ID, is_teacher=True).post(
                f'/api/submissions/{self.sub.id}/grade/', {'score': 92})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data['status'], 'graded')
        self.assertEqual(resp.data['score'], 92)

    def test_student_cannot_grade(self):
        with course_env():
            resp = client_for(STUDENT_ID).post(
                f'/api/submissions/{self.sub.id}/grade/', {'score': 90})
        self.assertEqual(resp.status_code, 403)

    def test_other_teacher_cannot_grade(self):
        with course_env():
            resp = client_for(TEACHER2_ID, is_teacher=True).post(
                f'/api/submissions/{self.sub.id}/grade/', {'score': 90})
        self.assertEqual(resp.status_code, 403)
        self.assertIn('无权评分', resp.data['detail'])

    def test_score_out_of_range_rejected(self):
        with course_env():
            resp = client_for(TEACHER_ID, is_teacher=True).post(
                f'/api/submissions/{self.sub.id}/grade/', {'score': 150})
        self.assertEqual(resp.status_code, 400)

    def test_missing_score_rejected(self):
        with course_env():
            resp = client_for(TEACHER_ID, is_teacher=True).post(
                f'/api/submissions/{self.sub.id}/grade/', {})
        self.assertEqual(resp.status_code, 400)

    def test_course_service_down_503(self):
        # get_queryset 也会调课程服务（圈定教师范围），故整体 mock + 单点覆盖 get_course
        with course_env(), mock.patch('assignments.views.get_course',
                                      side_effect=InternalServiceError('down')):
            resp = client_for(TEACHER_ID, is_teacher=True).post(
                f'/api/submissions/{self.sub.id}/grade/', {'score': 90})
        self.assertEqual(resp.status_code, 503)
