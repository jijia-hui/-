"""
URL configuration for web_backend project.

SERVICE_ROLE 环境变量：
  all         （默认）本地单进程 / 自动化测试，全部接口挂在本进程
  user        用户服务：注册、验证码、Token、/api/users/、Admin、内部查用户
  course      课程服务：课程 CRUD、选课/退课、内部选课/教师校验
  assignment  作业服务：作业 / 提交 / 评分 / 媒体文件
  app         assignment 的旧别名
"""
import os

from django.contrib import admin
from django.urls import path, re_path
from rest_framework.authtoken.views import obtain_auth_token
from django.conf import settings
from django.views.static import serve as static_serve

from apps.urls import user_urlpatterns, course_urlpatterns, assignment_urlpatterns
from apps.views import health


def normalize_role(role=None):
    value = (role if role is not None else os.environ.get('SERVICE_ROLE', 'all')).strip().lower()
    if value == 'app':
        return 'assignment'
    if value not in ('all', 'user', 'course', 'assignment'):
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
    if role in ('all', 'course'):
        urlpatterns += course_urlpatterns()
    if role in ('all', 'assignment'):
        urlpatterns += assignment_urlpatterns()
        urlpatterns += [
            re_path(r'^media/(?P<path>.*)$', static_serve,
                    {'document_root': settings.MEDIA_ROOT}, name='media_serve'),
            re_path(r'^static/(?P<path>.*)$', static_serve,
                    {'document_root': settings.STATIC_ROOT}, name='static_serve'),
        ]
    return urlpatterns


urlpatterns = build_urlpatterns()
