"""user-service 测试公共夹具。"""
from rest_framework.test import APIClient

from users.jwt_auth import make_token
from users.models import User


def client_for(user, **extra_headers):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {make_token(user)}', **extra_headers)
    return client


def create_user(username='stu1', password='pass1234', is_teacher=False, email=None, **kwargs):
    return User.objects.create_user(
        username=username, password=password, is_teacher=is_teacher,
        email=email or f'{username}@example.com', **kwargs)
