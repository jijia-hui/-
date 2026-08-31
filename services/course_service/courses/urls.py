from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'courses', views.CourseViewSet)

urlpatterns = [
    # 运维探针
    path('api/live/', views.live, name='live'),
    path('api/ready/', views.ready, name='ready'),
    path('api/health/', views.health, name='health'),
    # 对外课程接口
    path('api/', include(router.urls)),
    # 服务间内部接口（网关屏蔽，仅集群内可达）
    path('internal/courses/', views.InternalCourseIdsView.as_view(), name='internal_course_ids'),
    path('internal/courses/<int:course_id>/students/', views.InternalCourseStudentsView.as_view(),
         name='internal_course_students'),
    path('internal/courses/<int:course_id>/', views.InternalCourseDetailView.as_view(),
         name='internal_course_detail'),
    path('internal/users/<int:user_id>/purge/', views.InternalUserPurgeView.as_view(),
         name='internal_user_purge'),
]
