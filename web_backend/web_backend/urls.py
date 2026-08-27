"""
URL configuration for web_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path, re_path
from rest_framework.authtoken.views import obtain_auth_token
from django.conf import settings
from django.views.static import serve as static_serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.urls')),
    path('api/auth/token/', obtain_auth_token, name='api_token_auth'),
    # 显式提供媒体/静态文件（生产模式 DEBUG=False 时 static() 不生效；
    # 由 Nginx 将 /media/ 与 /static/ 反向代理到本服务）
    re_path(r'^media/(?P<path>.*)$', static_serve,
            {'document_root': settings.MEDIA_ROOT}, name='media_serve'),
    re_path(r'^static/(?P<path>.*)$', static_serve,
            {'document_root': settings.STATIC_ROOT}, name='static_serve'),
]
