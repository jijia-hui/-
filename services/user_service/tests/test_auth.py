"""注册 / 登录（JWT）/ 个人信息 接口测试（对应 UC01/UC02/UC13）。"""
import jwt as pyjwt
from django.test import TestCase

from users.jwt_auth import JWT_SECRET
from users.models import EmailVerificationCode

from .helpers import client_for, create_user

REGISTER = '/api/users/'


def register_payload(username, email=None, is_teacher=False, code=None):
    payload = {
        'username': username,
        'password': 'pass1234',
        'email': email or f'{username}@example.com',
    }
    if code is not None:
        payload['verification_code'] = code
    if is_teacher:
        payload['is_teacher'] = True
    return payload


class RegisterTests(TestCase):
    def test_register_requires_verification_code(self):
        resp = self.client.post(REGISTER, register_payload('a1'))
        self.assertEqual(resp.status_code, 400)
        self.assertIn('verification_code', resp.data)

    def test_register_with_valid_code_creates_user(self):
        EmailVerificationCode.objects.create(email='a2@example.com', code='123456')
        resp = self.client.post(REGISTER, register_payload('a2', code='123456'))
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertFalse(resp.data['is_teacher'])
        # 验证码应被核销（不可重复使用）
        again = self.client.post(REGISTER, register_payload('a2b', email='a2b@example.com',
                                                            code='123456'))
        self.assertEqual(again.status_code, 400)

    def test_register_teacher_flag(self):
        EmailVerificationCode.objects.create(email='t1@example.com', code='111222')
        resp = self.client.post(REGISTER, register_payload('t1', is_teacher=True, code='111222'))
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data['is_teacher'])

    def test_register_missing_email_rejected(self):
        resp = self.client.post(REGISTER, {'username': 'x1', 'password': 'pass1234'})
        self.assertEqual(resp.status_code, 400)

    def test_register_duplicate_username_rejected(self):
        create_user('dup1')
        EmailVerificationCode.objects.create(email='dup2@example.com', code='333444')
        resp = self.client.post(REGISTER, register_payload('dup1', email='dup2@example.com',
                                                           code='333444'))
        self.assertEqual(resp.status_code, 400)


class LoginTests(TestCase):
    def setUp(self):
        self.user = create_user('login_stu', is_teacher=False)
        self.teacher = create_user('login_tea', is_teacher=True)

    def test_login_returns_jwt_with_role_claims(self):
        resp = self.client.post('/api/auth/token/',
                                {'username': 'login_stu', 'password': 'pass1234'})
        self.assertEqual(resp.status_code, 200, resp.content)
        token = resp.data['token']
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        self.assertEqual(int(payload['sub']), self.user.id)
        self.assertEqual(payload['username'], 'login_stu')
        self.assertFalse(payload['is_teacher'])

    def test_login_teacher_claims(self):
        resp = self.client.post('/api/auth/token/',
                                {'username': 'login_tea', 'password': 'pass1234'})
        payload = pyjwt.decode(resp.data['token'], JWT_SECRET, algorithms=['HS256'])
        self.assertTrue(payload['is_teacher'])

    def test_login_wrong_password_rejected(self):
        resp = self.client.post('/api/auth/token/',
                                {'username': 'login_stu', 'password': 'wrong'})
        self.assertEqual(resp.status_code, 400)

    def test_login_unknown_user_rejected(self):
        resp = self.client.post('/api/auth/token/', {'username': 'nobody', 'password': 'x'})
        self.assertEqual(resp.status_code, 400)

    def test_login_missing_fields_rejected(self):
        resp = self.client.post('/api/auth/token/', {'username': 'login_stu'})
        self.assertEqual(resp.status_code, 400)


class MeTests(TestCase):
    def test_me_returns_own_info(self):
        user = create_user('me_stu', email='me@example.com')
        resp = client_for(user).get('/api/users/me/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['username'], 'me_stu')
        self.assertEqual(resp.data['email'], 'me@example.com')

    def test_me_requires_authentication(self):
        # 与单体版一致：未携带凭据 → 403（无 WWW-Authenticate 挑战）
        resp = self.client.get('/api/users/me/')
        self.assertEqual(resp.status_code, 403)

    def test_list_visibility_teacher_sees_all_student_sees_self(self):
        teacher = create_user('v_tea', is_teacher=True)
        stu1 = create_user('v_stu1')
        create_user('v_stu2')
        rows_t = client_for(teacher).get('/api/users/').data['results']
        self.assertEqual(len(rows_t), 3)  # 教师可见全部
        rows_s = client_for(stu1).get('/api/users/').data['results']
        self.assertEqual([u['id'] for u in rows_s], [stu1.id])  # 学生只可见自己

    def test_retrieve_other_user_forbidden_for_student(self):
        teacher = create_user('v_tea2', is_teacher=True)
        stu = create_user('v_stu3')
        # 学生可见范围只有自己 → 查看他人 404
        resp = client_for(stu).get(f'/api/users/{teacher.id}/')
        self.assertEqual(resp.status_code, 404)
        # 查看自己 200
        resp2 = client_for(stu).get(f'/api/users/{stu.id}/')
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.data['username'], 'v_stu3')

    def test_expired_token_rejected(self):
        user = create_user('me_stu2')
        from datetime import datetime, timedelta, timezone as tz
        import time
        import jwt as pyjwt2
        now = int(time.time()) - 25 * 3600
        token = pyjwt2.encode(
            {'sub': str(user.id), 'username': user.username,
             'exp': now + 3600, 'iat': now}, JWT_SECRET, algorithm='HS256')
        resp = self.client.get('/api/users/me/', HTTP_AUTHORIZATION=f'Token {token}')
        self.assertEqual(resp.status_code, 403)  # 与单体版一致的未认证语义
