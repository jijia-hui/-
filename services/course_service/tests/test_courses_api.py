"""课程/选课对外接口测试（对应 UC03~UC06）。跨服务用户名补全一律 mock。"""
from unittest import mock

from django.test import TestCase

from courses.internal_client import InternalServiceError
from courses.models import Course, Enrollment

from .helpers import (STUDENT_ID, TEACHER2_ID, TEACHER_ID, client_for, enroll,
                      fake_users_map, make_course)


@mock.patch('courses.views.fetch_users_map')
class CourseApiTests(TestCase):
    def setUp(self):
        self.course = make_course()
        self.course2 = make_course(code='OS101', teacher_id=TEACHER2_ID, name='操作系统')

    def test_create_course_by_teacher(self, fum):
        fum.return_value = fake_users_map(TEACHER_ID)
        resp = client_for(TEACHER_ID, is_teacher=True).post(
            '/api/courses/', {'name': '计算机网络', 'code': 'CN101', 'description': 'x'})
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data['teacher'], TEACHER_ID)  # 创建者自动成为授课教师
        self.assertEqual(resp.data['teacher_name'], 'user101')

    def test_create_course_by_student_forbidden(self, fum):
        resp = client_for(STUDENT_ID).post(
            '/api/courses/', {'name': 'x', 'code': 'X101', 'description': ''})
        self.assertEqual(resp.status_code, 403)

    def test_create_course_duplicate_code_rejected(self, fum):
        resp = client_for(TEACHER_ID, is_teacher=True).post(
            '/api/courses/', {'name': 'x', 'code': 'CS101', 'description': ''})
        self.assertEqual(resp.status_code, 400)

    def test_list_teacher_sees_own_only(self, fum):
        fum.return_value = fake_users_map(TEACHER_ID, TEACHER2_ID)
        resp = client_for(TEACHER_ID, is_teacher=True).get('/api/courses/')
        rows = resp.data['results']
        self.assertEqual([c['code'] for c in rows], ['CS101'])

    def test_list_student_sees_all(self, fum):
        fum.return_value = fake_users_map(TEACHER_ID, TEACHER2_ID)
        resp = client_for(STUDENT_ID).get('/api/courses/')
        rows = resp.data['results']
        self.assertEqual(sorted(c['code'] for c in rows), ['CS101', 'OS101'])
        # 列表接口不返回学生明细（与单体版一致）
        self.assertTrue(all(c['students'] == [] for c in rows))

    def test_detail_is_enrolled(self, fum):
        fum.return_value = fake_users_map(TEACHER_ID, STUDENT_ID)
        enroll(self.course, STUDENT_ID)
        resp = client_for(STUDENT_ID).get(f'/api/courses/{self.course.id}/')
        self.assertTrue(resp.data['is_enrolled'])
        self.assertEqual(resp.data['student_count'], 1)
        self.assertEqual(resp.data['students'][0]['username'], 'user201')
        # 未选课学生看不到学生明细
        resp2 = client_for(STUDENT_ID + 1).get(f'/api/courses/{self.course.id}/')
        self.assertEqual(resp2.data['students'], [])
        self.assertFalse(resp2.data['is_enrolled'])

    def test_enroll_and_unenroll(self, fum):
        c = client_for(STUDENT_ID)
        resp = c.post(f'/api/courses/{self.course.id}/enroll/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'enrolled')
        # 幂等：重复选课不报错也不重复
        c.post(f'/api/courses/{self.course.id}/enroll/')
        self.assertEqual(Enrollment.objects.filter(student_id=STUDENT_ID).count(), 1)
        # 退课
        resp = c.post(f'/api/courses/{self.course.id}/unenroll/')
        self.assertEqual(resp.data['status'], 'unenrolled')
        self.assertEqual(Enrollment.objects.filter(student_id=STUDENT_ID).count(), 0)

    def test_teacher_cannot_enroll(self, fum):
        resp = client_for(TEACHER_ID, is_teacher=True).post(f'/api/courses/{self.course.id}/enroll/')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('教师不能选课', resp.data['detail'])

    def test_update_by_owner(self, fum):
        fum.return_value = fake_users_map(TEACHER_ID)
        resp = client_for(TEACHER_ID, is_teacher=True).patch(
            f'/api/courses/{self.course.id}/', {'name': '程序设计基础（改）'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['name'], '程序设计基础（改）')

    def test_update_by_other_teacher_forbidden(self, fum):
        # 与单体版一致：教师可见范围只有自己的课程 → 操作他人课程返回 404
        resp = client_for(TEACHER2_ID, is_teacher=True).patch(
            f'/api/courses/{self.course.id}/', {'name': '篡改'})
        self.assertIn(resp.status_code, (403, 404))

    def test_update_by_student_forbidden(self, fum):
        resp = client_for(STUDENT_ID).patch(f'/api/courses/{self.course.id}/', {'name': '篡改'})
        self.assertEqual(resp.status_code, 403)

    def test_delete_success_cascades_enrollments(self, fum):
        fum.return_value = fake_users_map(TEACHER_ID, STUDENT_ID)
        enroll(self.course, STUDENT_ID)
        with mock.patch('courses.views.purge_assignments_for_courses') as purge:
            resp = client_for(TEACHER_ID, is_teacher=True).delete(f'/api/courses/{self.course.id}/')
        self.assertEqual(resp.status_code, 204)
        purge.assert_called_once_with([self.course.id])
        self.assertFalse(Course.objects.filter(id=self.course.id).exists())
        self.assertFalse(Enrollment.objects.filter(course_id=self.course.id).exists())

    def test_delete_fails_when_assignment_purge_fails(self, fum):
        with mock.patch('courses.views.purge_assignments_for_courses',
                        side_effect=InternalServiceError('assignment-service down')):
            resp = client_for(TEACHER_ID, is_teacher=True).delete(f'/api/courses/{self.course.id}/')
        self.assertEqual(resp.status_code, 502)
        self.assertIn('课程未删除', resp.data['detail'])
        self.assertTrue(Course.objects.filter(id=self.course.id).exists())
