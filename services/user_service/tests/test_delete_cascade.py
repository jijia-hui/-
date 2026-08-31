"""删除用户的跨服务级联清理测试（场景 #8：失败 → 502 且用户不删除）。"""
from unittest import mock

from django.test import TestCase

from users.internal_client import InternalServiceError

from .helpers import client_for, create_user


class DeleteUserCascadeTests(TestCase):
    def setUp(self):
        self.teacher = create_user('del_tea', is_teacher=True)
        self.student = create_user('del_stu')

    def test_delete_success_calls_purge_then_deletes(self):
        with mock.patch('users.views.purge_user_everywhere') as purge:
            resp = client_for(self.teacher).delete(f'/api/users/{self.student.id}/')
        self.assertEqual(resp.status_code, 204, resp.content)
        purge.assert_called_once_with(self.student.id)
        self.assertFalse(__import__('users.models', fromlist=['User']).User.objects
                         .filter(id=self.student.id).exists())

    def test_delete_fails_when_downstream_purge_fails(self):
        with mock.patch('users.views.purge_user_everywhere',
                        side_effect=InternalServiceError('course-service down')) as purge:
            resp = client_for(self.teacher).delete(f'/api/users/{self.student.id}/')
        self.assertEqual(resp.status_code, 502)
        self.assertIn('用户未删除', resp.data['detail'])
        purge.assert_called_once()
        # fail-closed：下游清理失败时本地用户保留
        from users.models import User
        self.assertTrue(User.objects.filter(id=self.student.id).exists())

    def test_student_cannot_delete_other_user(self):
        # 学生可见范围只有自己：删除他人 → 404
        resp = client_for(self.student).delete(f'/api/users/{self.teacher.id}/')
        self.assertEqual(resp.status_code, 404)

    def test_delete_requires_authentication(self):
        resp = self.client.delete(f'/api/users/{self.student.id}/')
        self.assertEqual(resp.status_code, 403)  # 与单体版一致的未认证语义
