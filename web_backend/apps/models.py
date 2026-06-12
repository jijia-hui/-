# Create your models here.
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
    test_cases = models.JSONField(default=list, verbose_name="测试用例")
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


class Submission(models.Model):
    """代码提交记录"""
    STATUS_CHOICES = [
        ('pending', '等待评测'),
        ('running', '评测中'),
        ('success', '通过'),
        ('failed', '未通过'),
        ('error', '系统错误'),
    ]
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions', verbose_name="作业")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions', verbose_name="提交学生")
    code = models.TextField(verbose_name="提交的代码")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="评测状态")
    score = models.IntegerField(default=0, verbose_name="得分 (0-100)")
    output = models.TextField(blank=True, verbose_name="运行输出")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'submissions'
        verbose_name = '提交记录'
        verbose_name_plural = '提交记录'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"