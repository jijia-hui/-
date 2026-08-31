from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve as static_serve

urlpatterns = [
    path('', include('courses.urls')),
    re_path(r'^static/(?P<path>.*)$', static_serve,
            {'document_root': settings.STATIC_ROOT}, name='static_serve'),
]
