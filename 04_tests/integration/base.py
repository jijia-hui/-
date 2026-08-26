# -*- coding: utf-8 -*-
"""集成测试公共基类：构造教师/学生/课程/作业/提交等基础数据与 Token 客户端。"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.models import Assignment, Course, Submission, User


class BaseAPITestCase(TestCase):
    """所有集成测试的公共夹具：两个教师、两个学生、一门课程、一个进行中作业、一个过期作业"""

    def setUp(self):
        self.teacher = User.objects.create_user(username='teacher1', password='x', is_teacher=True)
        self.teacher2 = User.objects.create_user(username='teacher2', password='x', is_teacher=True)
        self.student = User.objects.create_user(username='student1', password='x')
        self.other = User.objects.create_user(username='student2', password='x')
        self.course = Course.objects.create(name='操作系统', code='OS101', teacher=self.teacher)
        self.course.students.add(self.student)
        self.assignment = Assignment.objects.create(
            course=self.course,
            title='作业一',
            description='描述',
            deadline=timezone.now() + timedelta(days=1),
        )
        self.expired = Assignment.objects.create(
            course=self.course,
            title='过期作业',
            description='描述',
            deadline=timezone.now() - timedelta(days=1),
        )

    def client_for(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        return client

    def new_submission(self, assignment=None, student=None, code='print(1)'):
        return Submission.objects.create(
            assignment=assignment or self.assignment,
            student=student or self.student,
            code=code,
        )
