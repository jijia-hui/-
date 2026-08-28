# Create your models here.
import secrets
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    """自定义用户模型，增加教师标识"""
    is_teacher = models.BooleanField(default=False, verbose_name="是否为教师")
    # 可选：头像、昵称等
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


class Course(models.Model):
    """课程模型"""
    name = models.CharField(max_length=128, verbose_name="课程名称")
    code = models.CharField(max_length=20, unique=True, verbose_name="课程编号")
    description = models.TextField(blank=True, verbose_name="课程描述")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='taught_courses', limit_choices_to={'is_teacher': True}, verbose_name="授课教师")
    students = models.ManyToManyField(User, related_name='enrolled_courses', blank=True, verbose_name="选课学生")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses'
        verbose_name = '课程'
        verbose_name_plural = '课程'

    def __str__(self):
        return self.name



class Assignment(models.Model):
    """作业/实验模型"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments', verbose_name="所属课程")
    title = models.CharField(max_length=200, verbose_name="作业标题")
    description = models.TextField(verbose_name="作业描述")
    deadline = models.DateTimeField(verbose_name="截止时间")
    reference_file = models.FileField(
        upload_to='assignment_refs/',
        blank=True,
        null=True,
        verbose_name="参考文档"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assignments'
        verbose_name = '作业'
        verbose_name_plural = '作业'
        ordering = ['-deadline']

    def __str__(self):
        return f"{self.course.name} - {self.title}"

    def is_expired(self):
        """作业是否已过截止时间（提交校验的业务规则，供视图与单元测试复用）"""
        return self.deadline < timezone.now()


class Submission(models.Model):
    """代码提交记录"""
    STATUS_CHOICES = [
        ('pending', '待评分'),
        ('graded', '已评分'),
    ]
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions', verbose_name="作业")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions', verbose_name="提交学生")
    code = models.TextField(verbose_name="提交的代码")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="评分状态")
    score = models.IntegerField(default=0, verbose_name="得分 (0-100)")
    output = models.TextField(blank=True, verbose_name="教师评语")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'submissions'
        verbose_name = '提交记录'
        verbose_name_plural = '提交记录'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"