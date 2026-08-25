from rest_framework import permissions
from .models import Course


class IsCourseTeacherOrReadOnly(permissions.BasePermission):
    """教师可创建，但只有该课程授课教师（或管理员）能修改/删除"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.is_teacher

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        course = obj if isinstance(obj, Course) else obj.course
        return course.teacher == request.user
