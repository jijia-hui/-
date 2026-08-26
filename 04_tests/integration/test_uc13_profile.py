# -*- coding: utf-8 -*-
"""INT-TC13 查看个人信息（UC13）：主成功流程（me 接口）+ 异常流程（用户列表权限隔离）。"""
from .base import BaseAPITestCase


class ProfileTest(BaseAPITestCase):
    """INT-TC13-1 主成功流程：/api/users/me/ 返回本人信息"""

    def test_student_me(self):
        res = self.client_for(self.student).get('/api/users/me/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['username'], 'student1')
        self.assertEqual(res.data['email'], self.student.email)
        self.assertFalse(res.data['is_teacher'])

    def test_teacher_me(self):
        res = self.client_for(self.teacher).get('/api/users/me/')
        self.assertEqual(res.data['username'], 'teacher1')
        self.assertTrue(res.data['is_teacher'])


class UserListIsolationTest(BaseAPITestCase):
    """INT-TC13-2 异常流程：普通学生列表只能看到自己，教师可看全部"""

    def test_student_user_list_only_self(self):
        res = self.client_for(self.student).get('/api/users/')
        users = [u['username'] for u in res.data.get('results', res.data)]
        self.assertEqual(users, ['student1'])

    def test_teacher_user_list_sees_all(self):
        res = self.client_for(self.teacher).get('/api/users/')
        users = [u['username'] for u in res.data.get('results', res.data)]
        self.assertIn('student1', users)
        self.assertIn('teacher2', users)
