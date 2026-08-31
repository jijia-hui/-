# 课程服务演示数据（幂等）：三门示例课程。
# 依赖 user-service 已执行 seed_data（通过内部接口定位演示教师的用户 ID）。
import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from courses.internal_client import _internal_headers, _user_service_base
from courses.models import Course

DEMO_TEACHER = 'demo_teacher'
DEMO_COURSES = [
    ('CS101', '程序设计基础', 'Python 程序设计入门课程，涵盖语法、函数与面向对象。'),
    ('OS101', '操作系统', '进程管理、内存管理、文件系统与并发控制。'),
    ('CN101', '计算机网络', 'TCP/IP 协议栈、网络编程与常见应用协议。'),
]


class Command(BaseCommand):
    help = '创建演示课程（幂等）。前置条件：user-service 已执行 seed_data'

    def handle(self, *args, **options):
        url = f'{_user_service_base()}/internal/users/'
        resp = requests.get(url, params={'username': DEMO_TEACHER},
                            headers=_internal_headers(), timeout=(2, 3))
        resp.raise_for_status()
        users = resp.json()
        if not users:
            self.stdout.write(self.style.ERROR(
                f'未找到演示教师 {DEMO_TEACHER}，请先在 user-service 执行 seed_data'))
            return
        teacher_id = users[0]['id']

        for code, name, desc in DEMO_COURSES:
            course, created = Course.objects.get_or_create(
                code=code,
                defaults={'name': name, 'description': desc, 'teacher_id': teacher_id},
            )
            if not created and course.teacher_id != teacher_id:
                course.teacher_id = teacher_id
                course.save(update_fields=['teacher_id'])
            self.stdout.write(self.style.SUCCESS(
                f'课程就绪: {code} {name}（{"新建" if created else "已存在"}，teacher_id={teacher_id}）'))
        self.stdout.write(self.style.SUCCESS('课程服务演示数据准备完成'))
