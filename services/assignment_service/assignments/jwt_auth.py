"""无状态 JWT 认证（三个服务各持一份相同实现，保证服务间零代码耦合）。

各服务用 JWTAuthentication 本地验签，构造轻量 Principal 作为 request.user，
鉴权不产生任何跨服务调用。请求头格式与原前端/测试兼容：`Authorization: Token <jwt>`。
"""
import os
import time

import jwt
from rest_framework import authentication, exceptions

JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-jwt-secret-change-me-please-override-in-prod-0123456789abcdef')
JWT_EXPIRE_HOURS = int(os.environ.get('JWT_EXPIRE_HOURS', '24'))


class Principal:
    """JWT 主体：仅承载鉴权所需字段，不查数据库。"""

    def __init__(self, user_id, username, is_teacher=False, is_staff=False):
        self.id = user_id
        self.pk = user_id
        self.username = username or ''
        self.is_teacher = bool(is_teacher)
        self.is_staff = bool(is_staff)
        self.is_superuser = bool(is_staff)
        self.is_authenticated = True

    def __str__(self):
        return f'Principal({self.id}, {self.username})'


def make_token(user):
    """登录成功后签发 JWT（sub=user_id + 角色 + 过期时间）。"""
    now = int(time.time())
    payload = {
        'sub': str(user.id),
        'username': user.username,
        'is_teacher': bool(user.is_teacher),
        'is_staff': bool(user.is_staff),
        'iat': now,
        'exp': now + JWT_EXPIRE_HOURS * 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


class JWTAuthentication(authentication.BaseAuthentication):
    """解析 `Authorization: Token <jwt>` 并本地验签。"""

    keyword = 'Token'

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() not in (b'token', b'bearer'):
            return None  # 未携带凭据，交给权限类判定（匿名 → 401）
        if len(header) != 2:
            raise exceptions.AuthenticationFailed('Authorization 头格式错误')
        token = header[1].decode('utf-8', errors='replace')
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token 已过期，请重新登录')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('无效的 Token')
        try:
            user_id = int(payload.get('sub'))
        except (TypeError, ValueError):
            raise exceptions.AuthenticationFailed('无效的 Token')
        principal = Principal(
            user_id, payload.get('username'),
            payload.get('is_teacher'), payload.get('is_staff'),
        )
        return (principal, payload)
