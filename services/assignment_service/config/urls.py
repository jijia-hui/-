from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve as static_serve

urlpatterns = [
    path('', include('assignments.urls')),
    # 显式提供静态/媒体文件（生产模式 DEBUG=False 时 static() 不生效；
    # 由网关将 /static/assignment/ 与 /media/ 反向代理到本服务）
    re_path(r'^media/(?P<path>.*)$', static_serve,
            {'document_root': settings.MEDIA_ROOT}, name='media_serve'),
    re_path(r'^static/(?P<path>.*)$', static_serve,
            {'document_root': settings.STATIC_ROOT}, name='static_serve'),
]
