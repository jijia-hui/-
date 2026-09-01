# 测试/演示数据脚本（幂等，可重复执行）
# 用法：
#   本地:  python web_backend/manage.py seed_data
#   容器:  docker compose exec assignment-service python manage.py seed_data
#   删除演示账号/课程：按用户名/课程编号删除后重新执行即可
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.models import Assignment, Course, User

DEMO_TEACHER = 'demo_teacher'
DEMO_STUDENT = 'demo_student'
DEMO_PASSWORD = 'Demo@1234'
DEMO_COURSES = [
    ('CS101', '程序设计基础', 'Python 程序设计入门课程，涵盖语法、函数与面向对象。'),
    ('OS101', '操作系统', '进程管理、内存管理、文件系统与并发控制。'),
    ('CN101', '计算机网络', 'TCP/IP 协议栈、网络编程与常见应用协议。'),
]


class Command(BaseCommand):
    help = '创建演示数据：教师/学生账号、示例课程与作业（幂等，重复执行不会产生重复数据）'

    def handle(self, *args, **options):
        # 教师与学生会话账号
        teacher, _ = User.objects.get_or_create(
            username=DEMO_TEACHER,
            defaults={'email': f'{DEMO_TEACHER}@example.com', 'is_teacher': True},
        )
        teacher.set_password(DEMO_PASSWORD)
        teacher.save()
        student, _ = User.objects.get_or_create(
            username=DEMO_STUDENT,
            defaults={'email': f'{DEMO_STUDENT}@example.com'},
        )
        student.set_password(DEMO_PASSWORD)
        student.save()
        self.stdout.write(self.style.SUCCESS(f'用户就绪: {DEMO_TEACHER} / {DEMO_STUDENT}（密码 {DEMO_PASSWORD}）'))

        # 示例课程与作业
        for code, name, desc in DEMO_COURSES:
            course, created = Course.objects.get_or_create(
                code=code, defaults={'name': name, 'description': desc, 'teacher': teacher},
            )
            Assignment.objects.get_or_create(
                course=course, title=f'{name}作业1',
                defaults={
                    'description': f'{name}第一次作业：完成课后习题第 1~5 题。',
                    'deadline': timezone.now() + timedelta(days=7),
                },
            )
            Assignment.objects.get_or_create(
                course=course, title=f'{name}作业2',
                defaults={
                    'description': f'{name}第二次作业：完成课程实验并提交实验报告。',
                    'deadline': timezone.now() + timedelta(days=14),
                },
            )
            self.stdout.write(self.style.SUCCESS(
                f'课程就绪: {code} {name}（{"新建" if created else "已存在"}，含 2 个作业）'))

        self.stdout.write(self.style.SUCCESS('演示数据准备完成，可在 http://localhost:8080 登录体验'))
