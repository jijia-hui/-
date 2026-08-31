"""作业与提交服务（assignment-service）配置。

独立 Django 工程：只包含课业产物域（assignments、submissions 表）。
- course_id / student_id 只存 ID；课程归属与选课校验经课程服务内部接口（fail-closed）。
- 参考文档（media）由本服务存储并对外提供 /media/。
- 数据库：默认 MySQL 库 otp_assignment；USE_SQLITE=1 时用 SQLite（本地测试/CI）。
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SERVICE_NAME = os.environ.get('SERVICE_NAME', 'assignment-service')
APP_VERSION = os.environ.get('APP_VERSION', 'dev')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or 'django-insecure-assignment-service-dev-key'
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    host.strip() for host in os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')
    if host.strip()
]

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'assignments',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'assignments.jwt_auth.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # 本服务不安装 django.contrib.auth（无用户表），未认证请求 user 置 None
    'UNAUTHENTICATED_USER': None,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# 数据库：微服务版每个服务一个库（同一 MySQL 实例）；测试/本地可用 USE_SQLITE=1
if os.environ.get('USE_SQLITE', '') == '1':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': str(BASE_DIR / 'db.sqlite3'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'otp_assignment'),
            'USER': os.environ.get('DB_USER', 'teach_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'teach_pass_2026'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
            'OPTIONS': {
                'charset': 'utf8mb4',
            },
        }
    }

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = os.environ.get('TZ', 'Asia/Shanghai')
USE_I18N = True
USE_TZ = True

# 每个服务的静态资源挂在独立前缀下（网关按前缀路由），避免互相冲突
STATIC_URL = os.environ.get('STATIC_URL', '/static/assignment/')
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# 参考文档上传与访问（由本服务负责）
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ---- 服务间调用（内部接口）配置 ----
INTERNAL_API_KEY = os.environ.get('INTERNAL_API_KEY', 'dev-internal-key')
USER_SERVICE_URL = os.environ.get('USER_SERVICE_URL', 'http://user-service:8000')
COURSE_SERVICE_URL = os.environ.get('COURSE_SERVICE_URL', 'http://course-service:8000')

# JWT：与用户服务共享密钥，本地验签（无状态，不查库）
JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-jwt-secret-change-me-please-override-in-prod-0123456789abcdef')
JWT_EXPIRE_HOURS = int(os.environ.get('JWT_EXPIRE_HOURS', '24'))
