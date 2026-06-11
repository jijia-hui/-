from rest_framework import permissions

class IsTeacherOrReadOnly(permissions.BasePermission):
    """教师可写，其他人只读"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.is_teacher

class IsOwnerOrTeacher(permissions.BasePermission):
    """本人或教师可访问"""
    def has_object_permission(self, request, view, obj):
        if request.user.is_teacher:
            return True
        # 假设 obj 有 student 或 user 属性
        if hasattr(obj, 'student'):
            return obj.student == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return obj == request.user