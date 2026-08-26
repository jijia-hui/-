# -*- coding: utf-8 -*-
"""权限类单元测试（UNIT-TC：UC06 课程编辑删除 / UC07 作业管理 / UC11 教师查看提交）。

用假请求/假对象直测 IsCourseTeacherOrReadOnly 的判定逻辑，验证权限规则与异常分支。
"""
from django.test import SimpleTestCase

from apps.permissions import IsCourseTeacherOrReadOnly


class FakeUser:
    def __init__(self, authenticated=True, teacher=False, staff=False):
        self.is_authenticated = authenticated
        self.is_teacher = teacher
        self.is_staff = staff


class FakeRequest:
    def __init__(self, method='GET', user=None):
        self.method = method
        self.user = user


class FakeView:
    pass


class FakeCourse:
    def __init__(self, teacher):
        self.teacher = teacher
        self.course = self  # 权限类通过 isinstance(obj, Course) 区分课程与作业，假对象需具备 .course


class FakeAssignment:
    def __init__(self, course):
        self.course = course


class IsCourseTeacherOrReadOnlyTest(SimpleTestCase):
    """UNIT-TC06 / UNIT-TC07 / UNIT-TC11：课程/作业写操作的教师身份与归属校验"""

    def setUp(self):
        self.perm = IsCourseTeacherOrReadOnly()
        self.teacher = FakeUser(teacher=True)
        self.student = FakeUser(teacher=False)
        self.other_teacher = FakeUser(teacher=True)
        self.course = FakeCourse(self.teacher)
        self.assignment = FakeAssignment(self.course)

    # ---------- has_permission：安全方法人人可读，写操作仅限已登录教师 ----------

    def test_safe_method_allowed_for_anyone(self):
        for user in (self.teacher, self.student, FakeUser(authenticated=False)):
            for method in ('GET', 'HEAD', 'OPTIONS'):
                req = FakeRequest(method=method, user=user)
                self.assertTrue(self.perm.has_permission(req, FakeView()), f'{method} {user}')

    def test_write_denied_for_student(self):
        req = FakeRequest(method='POST', user=self.student)
        self.assertFalse(self.perm.has_permission(req, FakeView()))

    def test_write_denied_for_anonymous(self):
        req = FakeRequest(method='POST', user=FakeUser(authenticated=False))
        self.assertFalse(self.perm.has_permission(req, FakeView()))

    def test_write_allowed_for_teacher(self):
        req = FakeRequest(method='POST', user=self.teacher)
        self.assertTrue(self.perm.has_permission(req, FakeView()))

    # ---------- has_object_permission：对象归属（课程/作业）与管理员豁免 ----------

    def test_safe_method_allowed_on_object(self):
        req = FakeRequest(method='GET', user=self.student)
        self.assertTrue(self.perm.has_object_permission(req, FakeView(), self.course))

    def test_course_teacher_can_modify_own_course(self):
        req = FakeRequest(method='PATCH', user=self.teacher)
        self.assertTrue(self.perm.has_object_permission(req, FakeView(), self.course))

    def test_other_teacher_cannot_modify_course(self):
        req = FakeRequest(method='DELETE', user=self.other_teacher)
        self.assertFalse(self.perm.has_object_permission(req, FakeView(), self.course))

    def test_student_cannot_modify_course(self):
        req = FakeRequest(method='PATCH', user=self.student)
        self.assertFalse(self.perm.has_object_permission(req, FakeView(), self.course))

    def test_staff_can_modify_any_course(self):
        req = FakeRequest(method='DELETE', user=FakeUser(staff=True))
        self.assertTrue(self.perm.has_object_permission(req, FakeView(), self.course))

    def test_assignment_uses_its_course_teacher(self):
        req = FakeRequest(method='PUT', user=self.other_teacher)
        self.assertFalse(self.perm.has_object_permission(req, FakeView(), self.assignment))
        req2 = FakeRequest(method='PUT', user=self.teacher)
        self.assertTrue(self.perm.has_object_permission(req2, FakeView(), self.assignment))
