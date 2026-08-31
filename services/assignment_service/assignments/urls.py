from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'assignments', views.AssignmentViewSet)
router.register(r'submissions', views.SubmissionViewSet)

urlpatterns = [
    # 运维探针
    path('api/live/', views.live, name='live'),
    path('api/ready/', views.ready, name='ready'),
    path('api/health/', views.health, name='health'),
    # 对外作业/提交接口
    path('api/', include(router.urls)),
    # 服务间内部接口（网关屏蔽，仅集群内可达）
    path('internal/courses/purge/', views.InternalCoursesPurgeView.as_view(),
         name='internal_courses_purge'),
    path('internal/users/<int:user_id>/purge/', views.InternalUserPurgeView.as_view(),
         name='internal_user_purge'),
]
