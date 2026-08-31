"""course-service 内部接口契约测试（供 assignment/user 服务调用）。"""
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from courses.internal_client import InternalServiceError
from courses.models import Course, Enrollment

from .helpers import STUDENT_ID, TEACHER_ID, TEACHER2_ID, enroll, make_course

KEY = {'HTTP_X_INTERNAL_KEY': 'dev-internal-key'}


class InternalCourseApiTests(TestCase):
    def setUp(self):
        self.course = make_course()

    def test_course_detail_shape(self):
        resp = self.client.get(f'/internal/courses/{self.course.id}/', **KEY)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, {'id': self.course.id, 'code': 'CS101',
                                     'name': '程序设计基础', 'teacher_id': TEACHER_ID})

    def test_course_detail_404(self):
        resp = self.client.get('/internal/courses/9999/', **KEY)
        self.assertEqual(resp.status_code, 404)

    def test_students_shape(self):
        enroll(self.course, STUDENT_ID)
        resp = self.client.get(f'/internal/courses/{self.course.id}/students/', **KEY)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['student_ids'], [STUDENT_ID])

    def test_teacher_filter(self):
        make_course(code='OS101', teacher_id=TEACHER2_ID)
        resp = self.client.get('/internal/courses/', {'teacher_id': TEACHER_ID}, **KEY)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['course_ids'], [self.course.id])

    def test_teacher_filter_requires_param(self):
        resp = self.client.get('/internal/courses/', **KEY)
        self.assertEqual(resp.status_code, 400)

    def test_wrong_key_forbidden(self):
        resp = self.client.get(f'/internal/courses/{self.course.id}/',
                               HTTP_X_INTERNAL_KEY='bad')
        self.assertEqual(resp.status_code, 403)


class InternalUserPurgeTests(TestCase):
    def setUp(self):
        self.course = make_course()
        self.course2 = make_course(code='OS101', teacher_id=TEACHER2_ID)
        enroll(self.course, STUDENT_ID)

    def test_purge_deletes_courses_and_enrollments(self):
        with mock.patch('courses.views.purge_assignments_for_courses') as purge:
            resp = self.client.post(f'/internal/users/{TEACHER_ID}/purge/', **KEY)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data['deleted_courses'], 1)
        self.assertEqual(resp.data['course_ids'], [self.course.id])
        purge.assert_called_once_with([self.course.id])
        # 课程删除后，其选课记录随库内级联消失
        self.assertEqual(Enrollment.objects.count(), 0)
        # 其他教师的课程不受影响
        self.assertTrue(Course.objects.filter(id=self.course2.id).exists())

    def test_purge_deletes_users_enrollments_in_others_courses(self):
        # 学生 201 选了教师 102 的课（setUp 中已选教师 101 的课）→ purge 学生共删 2 条选课
        enroll(self.course2, STUDENT_ID)
        with mock.patch('courses.views.purge_assignments_for_courses'):
            resp = self.client.post(f'/internal/users/{STUDENT_ID}/purge/', **KEY)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['deleted_enrollments'], 2)
        self.assertTrue(Course.objects.filter(id=self.course2.id).exists())  # 课程保留

    def test_purge_fails_when_assignment_purge_fails(self):
        with mock.patch('courses.views.purge_assignments_for_courses',
                        side_effect=InternalServiceError('assignment down')):
            resp = self.client.post(f'/internal/users/{TEACHER_ID}/purge/', **KEY)
        self.assertEqual(resp.status_code, 502)
        # fail-closed：作业清理失败 → 课程保留
        self.assertTrue(Course.objects.filter(id=self.course.id).exists())

    def test_purge_idempotent(self):
        with mock.patch('courses.views.purge_assignments_for_courses'):
            self.client.post(f'/internal/users/{TEACHER_ID}/purge/', **KEY)
            resp = self.client.post(f'/internal/users/{TEACHER_ID}/purge/', **KEY)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['deleted_courses'], 0)


class EnrollmentModelTests(TestCase):
    def test_unique_course_student(self):
        from django.db import IntegrityError, transaction
        course = make_course()
        enroll(course, STUDENT_ID)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                enroll(course, STUDENT_ID)

    def test_created_at_auto(self):
        course = make_course()
        rec = enroll(course, STUDENT_ID)
        self.assertLessEqual(rec.enrolled_at, timezone.now() + timedelta(seconds=1))
