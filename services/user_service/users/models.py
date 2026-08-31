import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """自定义用户模型，增加教师标识（users 表，归用户服务所有）"""
    is_teacher = models.BooleanField(default=False, verbose_name="是否为教师")
    avatar = models.URLField(blank=True, default='')
    bio = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return self.username


class EmailVerificationCode(models.Model):
    """注册邮箱验证码：6 位数字，10 分钟有效，同一邮箱 60 秒内不可重复发送。"""
    TTL = timedelta(minutes=10)
    RESEND_INTERVAL = timedelta(seconds=60)

    email = models.EmailField(verbose_name='邮箱')
    code = models.CharField(max_length=6, verbose_name='验证码')
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True, verbose_name='使用时间')

    class Meta:
        db_table = 'email_verification_codes'
        verbose_name = '邮箱验证码'
        verbose_name_plural = '邮箱验证码'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', '-created_at']),
        ]

    def __str__(self):
        return f'{self.email} {self.code}'

    def is_expired(self):
        return timezone.now() > self.created_at + self.TTL

    @classmethod
    def normalize_email(cls, email):
        return (email or '').strip().lower()

    @classmethod
    def issue(cls, email):
        rec = cls.objects.create(
            email=cls.normalize_email(email),
            code=f'{secrets.randbelow(1_000_000):06d}',
        )
        return rec

    @classmethod
    def seconds_until_resend(cls, email):
        last = cls.objects.filter(email=cls.normalize_email(email)).order_by('-created_at').first()
        if not last:
            return 0
        wait = last.created_at + cls.RESEND_INTERVAL - timezone.now()
        return max(0, int(wait.total_seconds()))

    @classmethod
    def consume(cls, email, code):
        email = cls.normalize_email(email)
        code = (code or '').strip()
        rec = (
            cls.objects.filter(email=email, code=code, used_at__isnull=True)
            .order_by('-created_at')
            .first()
        )
        if not rec or rec.is_expired():
            return False
        rec.used_at = timezone.now()
        rec.save(update_fields=['used_at'])
        return True
