from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, CourseViewSet, AssignmentViewSet, SubmissionViewSet,
    SendVerificationCodeView, InternalUserView,
    InternalCourseEnrollmentView, InternalCourseTeacherView, health,
)

# 对外路由由 web_backend.urls 按 SERVICE_ROLE 组装：
#   user   = 注册/登录/用户/Admin
#   course = 课程 CRUD / 选课退课
#   assignment = 作业/提交/评分/媒体
#   all        = 本地 runserver / 单测，一个进程提供全部接口


def user_urlpatterns():
    router = DefaultRouter()
    router.register(r'users', UserViewSet)
    return [
        path('api/auth/send-code/', SendVerificationCodeView.as_view(), name='send_verification_code'),
        path('api/', include(router.urls)),
        path('internal/users/<int:pk>/', InternalUserView.as_view(), name='internal_user'),
    ]


def course_urlpatterns():
    router = DefaultRouter()
    router.register(r'courses', CourseViewSet)
    return [
        path('api/', include(router.urls)),
        path(
            'internal/courses/<int:pk>/enrollment/<int:user_id>/',
            InternalCourseEnrollmentView.as_view(),
            name='internal_course_enrollment',
        ),
        path(
            'internal/courses/<int:pk>/teacher/',
            InternalCourseTeacherView.as_view(),
            name='internal_course_teacher',
        ),
    ]


def assignment_urlpatterns():
    router = DefaultRouter()
    router.register(r'assignments', AssignmentViewSet)
    router.register(r'submissions', SubmissionViewSet)
    return [
        path('api/', include(router.urls)),
    ]


app_urlpatterns = assignment_urlpatterns  # 兼容旧名


urlpatterns = [
    path('api/health/', health, name='health'),
    *user_urlpatterns(),
    *course_urlpatterns(),
    *assignment_urlpatterns(),
]
