from django.db import models


class Course(models.Model):
    """课程（courses 表，归课程服务所有）。

    teacher_id 只存用户服务的用户 ID（普通整数列 + 索引），不建跨服务外键；
    需要教师用户名等展示信息时调用用户服务内部接口。
    """
    name = models.CharField(max_length=128, verbose_name="课程名称")
    code = models.CharField(max_length=20, unique=True, verbose_name="课程编号")
    description = models.TextField(blank=True, verbose_name="课程描述")
    teacher_id = models.BigIntegerField(db_index=True, verbose_name="授课教师用户 ID")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses'
        verbose_name = '课程'
        verbose_name_plural = '课程'
        ordering = ['id']  # 分页需要稳定排序

    def __str__(self):
        return self.name


class Enrollment(models.Model):
    """选课关系（enrollments 表，归课程服务所有）。

    course 是库内外键（同库真实外键 + 级联）；student_id 只存用户 ID。
    单体版的 courses.students 多对多在此显式建模，选课/退课即本表的增删。
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments',
                               verbose_name="课程")
    student_id = models.BigIntegerField(db_index=True, verbose_name="学生用户 ID")
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'enrollments'
        verbose_name = '选课记录'
        verbose_name_plural = '选课记录'
        constraints = [
            models.UniqueConstraint(fields=['course', 'student_id'], name='uniq_course_student'),
        ]

    def __str__(self):
        return f'course={self.course_id} student={self.student_id}'
