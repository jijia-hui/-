# -*- coding: utf-8 -*-
"""模型层单元测试（UNIT-TC：UC01 用户 / UC04 选课 / UC07 作业 / UC09 提交 / UC12 评分 / UC13 个人信息）。

直接构造模型对象验证字段默认值、__str__、排序与业务规则（is_expired），不经过 HTTP 层。
"""
from datetime import timedelta

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.models import Assignment, Course, Submission, User


class UserModelTest(TestCase):
    """UNIT-TC01 / UNIT-TC13：用户模型的字段与默认值"""

    def test_defaults_student_not_teacher(self):
        user = User.objects.create_user(username='stu', password='x', email='stu@example.com')
        self.assertFalse(user.is_teacher)
        self.assertEqual(user.avatar, '')
        self.assertEqual(user.bio, '')

    def test_teacher_flag(self):
        user = User.objects.create_user(username='tea', password='x', is_teacher=True)
        self.assertTrue(user.is_teacher)

    def test_str_is_username(self):
        user = User.objects.create_user(username='alice', password='x')
        self.assertEqual(str(user), 'alice')

    def test_password_is_hashed(self):
        user = User.objects.create_user(username='bob', password='plain123')
        self.assertNotEqual(user.password, 'plain123')
        self.assertTrue(user.check_password('plain123'))


class CourseModelTest(TestCase):
    """UNIT-TC05：课程创建 / 课程编号唯一性"""

    def setUp(self):
        self.teacher = User.objects.create_user(username='tea', password='x', is_teacher=True)

    def test_str_is_name(self):
        course = Course.objects.create(name='操作系统', code='OS101', teacher=self.teacher)
        self.assertEqual(str(course), '操作系统')

    def test_related_names(self):
        course = Course.objects.create(name='网络', code='NET101', teacher=self.teacher)
        student = User.objects.create_user(username='stu', password='x')
        student.enrolled_courses.add(course)
        self.assertIn(course, student.enrolled_courses.all())
        self.assertIn(course, self.teacher.taught_courses.all())

    def test_code_unique(self):
        Course.objects.create(name='课程A', code='C001', teacher=self.teacher)
        with self.assertRaises(IntegrityError):
            Course.objects.create(name='课程B', code='C001', teacher=self.teacher)


class AssignmentModelTest(TestCase):
    """UNIT-TC07 / UNIT-TC08 / UNIT-TC09：作业字段、排序与截止时间业务规则"""

    def setUp(self):
        self.teacher = User.objects.create_user(username='tea', password='x', is_teacher=True)
        self.course = Course.objects.create(name='操作系统', code='OS101', teacher=self.teacher)

    def _assignment(self, deadline_offset):
        return Assignment.objects.create(
            course=self.course,
            title='作业',
            description='描述',
            deadline=timezone.now() + timedelta(days=deadline_offset),
        )

    def test_str_contains_course_and_title(self):
        a = self._assignment(1)
        self.assertEqual(str(a), '操作系统 - 作业')

    def test_ordering_by_deadline_desc(self):
        later = self._assignment(5)
        sooner = self._assignment(1)
        self.assertEqual(list(Assignment.objects.all()), [later, sooner])

    def test_reference_file_blank_null_by_default(self):
        a = self._assignment(1)
        self.assertFalse(a.reference_file)

    def test_is_expired_false_when_deadline_in_future(self):
        a = self._assignment(1)
        self.assertFalse(a.is_expired())

    def test_is_expired_true_when_deadline_in_past(self):
        a = self._assignment(-1)
        self.assertTrue(a.is_expired())


class SubmissionModelTest(TestCase):
    """UNIT-TC09 / UNIT-TC10 / UNIT-TC12：提交记录的默认状态、排序与字符串"""

    def setUp(self):
        teacher = User.objects.create_user(username='tea', password='x', is_teacher=True)
        course = Course.objects.create(name='操作系统', code='OS101', teacher=teacher)
        self.assignment = Assignment.objects.create(
            course=course, title='作业一', description='描述',
            deadline=timezone.now() + timedelta(days=1))
        self.student = User.objects.create_user(username='stu', password='x')

    def _submission(self):
        return Submission.objects.create(
            assignment=self.assignment, student=self.student, code='print(1)')

    def test_defaults_pending_score_zero(self):
        s = self._submission()
        self.assertEqual(s.status, 'pending')
        self.assertEqual(s.score, 0)
        self.assertEqual(s.output, '')
        self.assertIn(s.status, dict(Submission.STATUS_CHOICES))

    def test_ordering_by_created_at_desc(self):
        base = timezone.now()
        s1 = Submission.objects.create(
            assignment=self.assignment, student=self.student, code='print(1)')
        s2 = Submission.objects.create(
            assignment=self.assignment, student=self.student, code='print(2)')
        # auto_now_add 在快速连续创建时可能相同，显式给定时间保证排序断言确定
        s1.created_at = base
        s1.save(update_fields=['created_at'])
        s2.created_at = base + timedelta(seconds=1)
        s2.save(update_fields=['created_at'])
        self.assertEqual(list(Submission.objects.all()), [s2, s1])

    def test_str_contains_student_and_title(self):
        s = self._submission()
        self.assertEqual(str(s), 'stu - 作业一')

    def test_grade_updates_status_and_score(self):
        s = self._submission()
        s.score = 92
        s.status = 'graded'
        s.save()
        s.refresh_from_db()
        self.assertEqual(s.status, 'graded')
        self.assertEqual(s.score, 92)
