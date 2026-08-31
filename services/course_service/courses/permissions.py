from rest_framework import permissions


class InternalOnly(permissions.BasePermission):
    """内部接口：仅接受携带正确 X-Internal-Key 的调用（网关对 /internal/* 一律 403）。"""

    def has_permission(self, request, view):
        from django.conf import settings
        key = request.headers.get('X-Internal-Key', '')
        return key == settings.INTERNAL_API_KEY


class IsCourseTeacherOrReadOnly(permissions.BasePermission):
    """教师可创建，但只有该课程授课教师（或管理员）能修改/删除。

    微服务版按 teacher_id 判定归属（用户名/角色来自 JWT 本地验签，无跨服务调用）。
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated and user.is_teacher)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        return obj.teacher_id == request.user.id
