"""作业对外接口测试（UC07/UC08）：课程归属校验走 mock 的课程服务内部接口。"""
from unittest import mock

from django.test import TestCase

from assignments.internal_client import CourseNotFound, InternalServiceError

from .helpers import (COURSE_ID, COURSE2_ID, STUDENT_ID, TEACHER2_ID, TEACHER_ID,
                      client_for, course_env, fake_course, make_assignment)


class AssignmentCreateTests(TestCase):
    PAYLOAD = {'title': '新作业', 'description': '说明', 'deadline': '2026-09-30T23:59:59Z'}

    def test_owner_teacher_creates(self):
        with course_env():
            resp = client_for(TEACHER_ID, is_teacher=True).post(
                '/api/assignments/', {**self.PAYLOAD, 'course': COURSE_ID})
            self.assertEqual(resp.status_code, 201, resp.content)
            self.assertEqual(resp.data['course'], COURSE_ID)

    def test_student_cannot_create(self):
        with course_env():
            resp = client_for(STUDENT_ID).post(
                '/api/assignments/', {**self.PAYLOAD, 'course': COURSE_ID})
            self.assertEqual(resp.status_code, 403)

    def test_other_teacher_cannot_create(self):
        with course_env():
            resp = client_for(TEACHER2_ID, is_teacher=True).post(
                '/api/assignments/', {**self.PAYLOAD, 'course': COURSE_ID})
            self.assertEqual(resp.status_code, 403)

    def test_unknown_course_rejected_400(self):
        with mock.patch('assignments.views.get_course',
                        side_effect=CourseNotFound('course 999')):
            resp = client_for(TEACHER_ID, is_teacher=True).post(
                '/api/assignments/', {**self.PAYLOAD, 'course': 999})
            self.assertEqual(resp.status_code, 400)
            self.assertIn('课程不存在', resp.data['course'])

    def test_course_service_down_503(self):
        with mock.patch('assignments.views.get_course',
                        side_effect=InternalServiceError('course-service down')):
            resp = client_for(TEACHER_ID, is_teacher=True).post(
                '/api/assignments/', {**self.PAYLOAD, 'course': COURSE_ID})
            self.assertEqual(resp.status_code, 503)
            self.assertIn('课程服务暂不可用', resp.data['detail'])

    def test_missing_deadline_rejected(self):
        with course_env():
            resp = client_for(TEACHER_ID, is_teacher=True).post(
                '/api/assignments/', {'course': COURSE_ID, 'title': 'x', 'description': 'y'})
            self.assertEqual(resp.status_code, 400)


class AssignmentQueryTests(TestCase):
    def test_filter_by_course(self):
        a1 = make_assignment(COURSE_ID, title='C1作业')
        a2 = make_assignment(COURSE2_ID, title='C2作业')
        with course_env():
            resp = client_for(STUDENT_ID).get(f'/api/assignments/?course={COURSE_ID}')
        rows = resp.data['results']
        self.assertEqual([a['id'] for a in rows], [a1.id])
        self.assertEqual(rows[0]['title'], 'C1作业')
        self.assertEqual(rows[0]['course'], COURSE_ID)

    def test_detail(self):
        a1 = make_assignment()
        with course_env():
            resp = client_for(STUDENT_ID).get(f'/api/assignments/{a1.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['title'], '作业一')


class AssignmentUpdateDeleteTests(TestCase):
    def test_owner_updates(self):
        a1 = make_assignment()
        with course_env():
            resp = client_for(TEACHER_ID, is_teacher=True).patch(
                f'/api/assignments/{a1.id}/', {'title': '改标题'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['title'], '改标题')

    def test_other_teacher_forbidden(self):
        a1 = make_assignment()
        with course_env():
            resp = client_for(TEACHER2_ID, is_teacher=True).patch(
                f'/api/assignments/{a1.id}/', {'title': '篡改'})
        self.assertEqual(resp.status_code, 403)

    def test_owner_deletes(self):
        a1 = make_assignment()
        with course_env():
            resp = client_for(TEACHER_ID, is_teacher=True).delete(f'/api/assignments/{a1.id}/')
        self.assertEqual(resp.status_code, 204)

    def test_delete_when_course_gone_404(self):
        a1 = make_assignment()
        with mock.patch('assignments.views.get_course', side_effect=CourseNotFound('gone')):
            resp = client_for(TEACHER_ID, is_teacher=True).delete(f'/api/assignments/{a1.id}/')
        self.assertEqual(resp.status_code, 404)
