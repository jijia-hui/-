# -*- coding: utf-8 -*-
"""序列化器单元测试（UNIT-TC：UC01 注册 / UC03 浏览课程 / UC08 作业详情 / UC10/11/12 提交与评分字段）。

验证字段校验规则、密码哈希、只读字段与计算字段，不经过 HTTP 层。
"""
from datetime import timedelta

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.models import Assignment, Course, Submission, User
from apps.serializers import (
    AssignmentSerializer,
    CourseSerializer,
    SubmissionSerializer,
    UserSerializer,
)


class UserSerializerTest(TestCase):
    """UNIT-TC01：注册序列化器——邮箱必填/格式、密码 write_only 且哈希存储"""

    def test_create_hashes_password(self):
        data = {'username': 'stu', 'password': 'pass1234', 'email': 'stu@example.com'}
        user = UserSerializer(data=data)
        self.assertTrue(user.is_valid(), user.errors)
        saved = user.save()
        self.assertTrue(saved.check_password('pass1234'))
        self.assertNotEqual(saved.password, 'pass1234')

    def test_password_not_serialized(self):
        user = User.objects.create_user(username='stu', password='pass1234', email='a@b.com')
        data = UserSerializer(user).data
        self.assertNotIn('password', data)

    def test_email_required(self):
        serializer = UserSerializer(data={'username': 'stu', 'password': 'pass1234'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_email_invalid(self):
        serializer = UserSerializer(data={
            'username': 'stu', 'password': 'pass1234', 'email': 'not-an-email'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_password_required(self):
        serializer = UserSerializer(data={'username': 'stu', 'email': 'a@b.com'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)


class CourseSerializerTest(TestCase):
    """UNIT-TC03 / UNIT-TC04：课程计算字段——student_count / is_enrolled / 列表不返回学生明细"""

    def setUp(self):
        self.teacher = User.objects.create_user(username='tea', password='x', is_teacher=True)
        self.student = User.objects.create_user(username='stu', password='x')
        self.course = Course.objects.create(name='操作系统', code='OS101', teacher=self.teacher)
        self.course.students.add(self.student)

    def test_student_count(self):
        data = CourseSerializer(self.course).data
        self.assertEqual(data['student_count'], 1)

    def test_is_enrolled_for_current_user(self):
        request = type('R', (), {'user': self.student})()
        data = CourseSerializer(self.course, context={'request': request}).data
        self.assertTrue(data['is_enrolled'])
        other = User.objects.create_user(username='other', password='x')
        request2 = type('R', (), {'user': other})()
        data2 = CourseSerializer(self.course, context={'request': request2}).data
        self.assertFalse(data2['is_enrolled'])

    def test_students_empty_in_list_action(self):
        view = type('V', (), {'action': 'list'})()
        request = type('R', (), {'user': self.student})()
        data = CourseSerializer(self.course, context={'request': request, 'view': view}).data
        self.assertEqual(data['students'], [])

    def test_students_returned_in_detail_action(self):
        view = type('V', (), {'action': 'retrieve'})()
        request = type('R', (), {'user': self.student})()
        data = CourseSerializer(self.course, context={'request': request, 'view': view}).data
        names = [u['username'] for u in data['students']]
        self.assertIn('stu', names)


class AssignmentSerializerTest(TestCase):
    """UNIT-TC08：作业序列化器——参考文档 URL 字段"""

    def setUp(self):
        teacher = User.objects.create_user(username='tea', password='x', is_teacher=True)
        course = Course.objects.create(name='操作系统', code='OS101', teacher=teacher)
        self.assignment = Assignment.objects.create(
            course=course, title='作业一', description='描述',
            deadline=timezone.now() + timedelta(days=1))

    def test_reference_file_url_none_without_file(self):
        data = AssignmentSerializer(self.assignment).data
        self.assertIsNone(data['reference_file_url'])
        self.assertIsNone(data['reference_file'])

    def test_serializes_required_fields(self):
        data = AssignmentSerializer(self.assignment).data
        self.assertEqual(data['title'], '作业一')
        self.assertEqual(data['description'], '描述')
        self.assertIn('deadline', data)


class SubmissionSerializerTest(TestCase):
    """UNIT-TC10 / UNIT-TC12：提交序列化器——只读字段与只读来源字段"""

    def setUp(self):
        teacher = User.objects.create_user(username='tea', password='x', is_teacher=True)
        course = Course.objects.create(name='操作系统', code='OS101', teacher=teacher)
        self.assignment = Assignment.objects.create(
            course=course, title='作业一', description='描述',
            deadline=timezone.now() + timedelta(days=1))
        self.student = User.objects.create_user(username='stu', password='x')

    def test_read_only_fields(self):
        submission = Submission.objects.create(
            assignment=self.assignment, student=self.student, code='print(1)')
        serializer = SubmissionSerializer(submission)
        meta = SubmissionSerializer.Meta
        for field in ('created_at', 'status', 'score', 'output', 'student', 'assignment'):
            self.assertIn(field, meta.read_only_fields)

    def test_source_fields_present(self):
        submission = Submission.objects.create(
            assignment=self.assignment, student=self.student, code='print(1)')
        data = SubmissionSerializer(submission).data
        self.assertEqual(data['student_name'], 'stu')
        self.assertEqual(data['assignment_title'], '作业一')
        self.assertEqual(data['status'], 'pending')
