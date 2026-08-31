from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)

urlpatterns = [
    # 运维探针（网关聚合探活也走这些路径）
    path('api/live/', views.live, name='live'),
    path('api/ready/', views.ready, name='ready'),
    path('api/health/', views.health, name='health'),
    # 认证
    path('api/auth/token/', views.ObtainTokenView.as_view(), name='api_token_auth'),
    path('api/auth/send-code/', views.SendVerificationCodeView.as_view(), name='send_verification_code'),
    # 对外用户接口
    path('api/', include(router.urls)),
    # 服务间内部接口（网关屏蔽，仅集群内可达）
    path('internal/users/', views.InternalUserListView.as_view(), name='internal_users'),
]
