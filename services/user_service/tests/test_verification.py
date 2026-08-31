"""邮箱验证码：模型规则（单元）+ 发送接口（UC01 异常路径）。"""
from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.utils import timezone

from users.models import EmailVerificationCode

from .helpers import create_user

SEND_CODE = '/api/auth/send-code/'


class EmailVerificationCodeModelTests(TestCase):
    def test_issue_creates_6_digit_code(self):
        rec = EmailVerificationCode.issue('A@Example.COM ')
        self.assertEqual(rec.email, 'a@example.com')  # 归一化
        self.assertEqual(len(rec.code), 6)
        self.assertTrue(rec.code.isdigit())
        self.assertFalse(rec.is_expired())

    def test_is_expired_after_ttl(self):
        rec = EmailVerificationCode.issue('b@example.com')
        EmailVerificationCode.objects.filter(id=rec.id).update(
            created_at=timezone.now() - EmailVerificationCode.TTL - timedelta(seconds=1))
        rec.refresh_from_db()
        self.assertTrue(rec.is_expired())

    def test_consume_marks_used_and_rejects_reuse(self):
        rec = EmailVerificationCode.issue('c@example.com')
        self.assertTrue(EmailVerificationCode.consume('c@example.com', rec.code))
        self.assertFalse(EmailVerificationCode.consume('c@example.com', rec.code))

    def test_consume_rejects_wrong_code(self):
        EmailVerificationCode.issue('d@example.com')
        self.assertFalse(EmailVerificationCode.consume('d@example.com', '000000'))

    def test_seconds_until_resend(self):
        self.assertEqual(EmailVerificationCode.seconds_until_resend('e@example.com'), 0)
        EmailVerificationCode.issue('e@example.com')
        wait = EmailVerificationCode.seconds_until_resend('e@example.com')
        self.assertTrue(0 < wait <= 60)


class SendCodeApiTests(TestCase):
    def test_send_code_ok_and_records_code(self):
        resp = self.client.post(SEND_CODE, {'email': 'new@example.com'})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(EmailVerificationCode.objects.filter(email='new@example.com').count(), 1)
        # console 邮件后端会把验证码打印到 outbox/日志
        self.assertEqual(len(mail.outbox), 1)

    def test_send_code_invalid_email_rejected(self):
        resp = self.client.post(SEND_CODE, {'email': 'not-an-email'})
        self.assertEqual(resp.status_code, 400)

    def test_send_code_registered_email_rejected(self):
        create_user('reg1', email='reg1@example.com')
        resp = self.client.post(SEND_CODE, {'email': 'reg1@example.com'})
        self.assertEqual(resp.status_code, 400)

    def test_send_code_rate_limited(self):
        EmailVerificationCode.issue('rl@example.com')
        resp = self.client.post(SEND_CODE, {'email': 'rl@example.com'})
        self.assertEqual(resp.status_code, 429)
        self.assertIn('retry_after', resp.data)
