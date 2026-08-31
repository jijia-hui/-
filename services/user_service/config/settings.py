"""用户服务（user-service）配置。

独立 Django 工程：只包含用户/认证域（users 表、email_verification_codes 表）。
- 认证：无状态 JWT（HS256 共享密钥），登录时签发，各服务本地验签，不落库。
- 数据库：默认 MySQL 库 otp_user；USE_SQLITE=1 时用 SQLite（本地测试/CI）。
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SERVICE_NAME = os.environ.get('SERVICE_NAME', 'user-service')
APP_VERSION = os.environ.get('APP_VERSION', 'dev')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or 'django-insecure-user-service-dev-key'
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    host.strip() for host in os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')
    if host.strip()
]

# 经网关（Nginx 反代）访问 Django Admin 时需要可信来源
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.environ.get(
        'DJANGO_CSRF_TRUSTED_ORIGINS',
        'http://localhost:8080,http://127.0.0.1:8080',
    ).split(',')
    if origin.strip()
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'users',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'users.jwt_auth.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

AUTH_USER_MODEL = 'users.User'

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
            'NAME': os.environ.get('DB_NAME', 'otp_user'),
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

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = os.environ.get('TZ', 'Asia/Shanghai')
USE_I18N = True
USE_TZ = True

# 每个服务的静态资源挂在独立前缀下（网关按前缀路由），避免互相冲突
STATIC_URL = os.environ.get('STATIC_URL', '/static/user/')
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# 邮件发送配置（注册验证码）：SMTP 未成套配置时退回控制台后端，验证码打印到日志
EMAIL_BACKEND = (
    'django.core.mail.backends.smtp.EmailBackend'
    if os.environ.get('EMAIL_HOST_USER') and os.environ.get('EMAIL_HOST_PASSWORD')
    else 'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.qq.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '465'))
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'True') == 'True'
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'False') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or '在线教学平台 <noreply@example.com>'

# ---- 服务间调用（内部接口）配置 ----
# 内部接口共享密钥（编排层注入；网关屏蔽 /internal/*，不经外部暴露）
INTERNAL_API_KEY = os.environ.get('INTERNAL_API_KEY', 'dev-internal-key')
# 跨服务级联清理目标
COURSE_SERVICE_URL = os.environ.get('COURSE_SERVICE_URL', 'http://course-service:8000')
ASSIGNMENT_SERVICE_URL = os.environ.get('ASSIGNMENT_SERVICE_URL', 'http://assignment-service:8000')

# JWT：签发与验签共用密钥；有效期默认 24 小时
JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-jwt-secret-change-me-please-override-in-prod-0123456789abcdef')
JWT_EXPIRE_HOURS = int(os.environ.get('JWT_EXPIRE_HOURS', '24'))
