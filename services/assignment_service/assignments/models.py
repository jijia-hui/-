from django.db import models
from django.utils import timezone


class Assignment(models.Model):
    """作业/实验（assignments 表，归作业与提交服务所有）。

    course_id 只存课程服务的课程 ID（普通整数列 + 索引），不建跨服务外键；
    课程归属/选课校验经课程服务内部接口完成（见《跨服务调用说明.md》）。
    """
    course_id = models.BigIntegerField(db_index=True, verbose_name="所属课程 ID")
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
        return f"{self.course_id} - {self.title}"

    def is_expired(self):
        """作业是否已过截止时间（提交校验的业务规则，供视图与单元测试复用）"""
        return self.deadline < timezone.now()


class Submission(models.Model):
    """代码提交记录（submissions 表，归作业与提交服务所有）。

    assignment 是库内外键（同库真实外键 + 级联）；student_id 只存用户 ID。
    评分（status/score）与提交同一聚合、同一事务，不拆独立评分服务。
    """
    STATUS_CHOICES = [
        ('pending', '待评分'),
        ('graded', '已评分'),
    ]
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE,
                                   related_name='submissions', verbose_name="作业")
    student_id = models.BigIntegerField(db_index=True, verbose_name="提交学生用户 ID")
    code = models.TextField(verbose_name="提交的代码")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending',
                              verbose_name="评分状态")
    score = models.IntegerField(default=0, verbose_name="得分 (0-100)")
    output = models.TextField(blank=True, verbose_name="教师评语")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'submissions'
        verbose_name = '提交记录'
        verbose_name_plural = '提交记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'student={self.student_id} assignment={self.assignment_id}'
