from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, CourseViewSet, AssignmentViewSet, SubmissionViewSet,
    SendVerificationCodeView, InternalUserView, health,
)

# 对外路由由 web_backend.urls 按 SERVICE_ROLE 组装：
#   user = 注册/登录/用户/Admin
#   app  = 课程/作业/提交（当前剩余单体）
#   all  = 本地 runserver / 单测，一个进程提供全部接口


def user_urlpatterns():
    router = DefaultRouter()
    router.register(r'users', UserViewSet)
    return [
        path('api/auth/send-code/', SendVerificationCodeView.as_view(), name='send_verification_code'),
        path('api/', include(router.urls)),
        path('internal/users/<int:pk>/', InternalUserView.as_view(), name='internal_user'),
    ]


def app_urlpatterns():
    router = DefaultRouter()
    router.register(r'courses', CourseViewSet)
    router.register(r'assignments', AssignmentViewSet)
    router.register(r'submissions', SubmissionViewSet)
    return [
        path('api/', include(router.urls)),
    ]


urlpatterns = [
    path('api/health/', health, name='health'),
    *user_urlpatterns(),
    *app_urlpatterns(),
]
