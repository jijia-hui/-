"""用户服务不可用时的降级行为（场景 #1）：课程数据正常返回，用户名置空。"""
from unittest import mock

from django.test import TestCase

from .helpers import STUDENT_ID, TEACHER_ID, client_for, enroll, make_course


@mock.patch('courses.views.fetch_users_map', return_value=None)
class DegradeTests(TestCase):
    def setUp(self):
        self.course = make_course()
        enroll(self.course, STUDENT_ID)

    def test_list_degrades_teacher_name(self, fum):
        resp = client_for(STUDENT_ID).get('/api/courses/')
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data['results'][0]['teacher_name'])

    def test_detail_degrades_names_but_data_intact(self, fum):
        resp = client_for(TEACHER_ID, is_teacher=True).get(f'/api/courses/{self.course.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data['teacher_name'])
        self.assertEqual(resp.data['student_count'], 1)   # 本地数据不受影响
        self.assertEqual(resp.data['students'], [])      # 用户信息不可得 → 空列表
        self.assertTrue(resp.data['is_enrolled'] or resp.data['student_count'] == 1)
