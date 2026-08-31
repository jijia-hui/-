"""
URL configuration for web_backend project.

SERVICE_ROLE 环境变量：
  all  （默认）本地单进程 / 自动化测试，注册+课程全部挂在本进程
  user 仅用户服务：注册、验证码、Token、/api/users/、Admin、内部查用户
  app  剩余单体：课程 / 作业 / 提交 / 媒体文件
"""
import os

from django.contrib import admin
from django.urls import path, re_path
from rest_framework.authtoken.views import obtain_auth_token
from django.conf import settings
from django.views.static import serve as static_serve

from apps.urls import user_urlpatterns, app_urlpatterns
from apps.views import health


def normalize_role(role=None):
    value = (role if role is not None else os.environ.get('SERVICE_ROLE', 'all')).strip().lower()
    if value not in ('all', 'user', 'app'):
        return 'all'
    return value


def build_urlpatterns(role=None):
    role = normalize_role(role)
    urlpatterns = [
        path('api/health/', health, name='health'),
    ]
    if role in ('all', 'user'):
        urlpatterns += [
            path('api/auth/token/', obtain_auth_token, name='api_token_auth'),
            path('admin/', admin.site.urls),
        ]
        urlpatterns += user_urlpatterns()
    if role in ('all', 'app'):
        urlpatterns += app_urlpatterns()
        urlpatterns += [
            re_path(r'^media/(?P<path>.*)$', static_serve,
                    {'document_root': settings.MEDIA_ROOT}, name='media_serve'),
            re_path(r'^static/(?P<path>.*)$', static_serve,
                    {'document_root': settings.STATIC_ROOT}, name='static_serve'),
        ]
    return urlpatterns


urlpatterns = build_urlpatterns()
