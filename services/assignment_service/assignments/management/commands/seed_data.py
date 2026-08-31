# 作业服务演示数据（幂等）：每门演示课程 2 个作业。
# 依赖 user-service、course-service 已执行 seed_data。
from datetime import timedelta

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from assignments.internal_client import (
    InternalServiceError, _course_service_base, _internal_headers, _user_service_base,
)
from assignments.models import Assignment

DEMO_TEACHER = 'demo_teacher'


class Command(BaseCommand):
    help = '创建演示作业（幂等）。前置条件：user-service 与 course-service 已执行 seed_data'

    def handle(self, *args, **options):
        # 1) 经用户服务内部接口定位演示教师 ID
        resp = requests.get(f'{_user_service_base()}/internal/users/',
                            params={'username': DEMO_TEACHER},
                            headers=_internal_headers(), timeout=(2, 3))
        resp.raise_for_status()
        users = resp.json()
        if not users:
            self.stdout.write(self.style.ERROR(
                f'未找到演示教师 {DEMO_TEACHER}，请先在 user-service 执行 seed_data'))
            return
        teacher_id = users[0]['id']

        # 2) 经课程服务内部接口拿该教师的课程列表（跨服务只拿 ID，不直连课程库）
        resp = requests.get(f'{_course_service_base()}/internal/courses/',
                            params={'teacher_id': teacher_id},
                            headers=_internal_headers(), timeout=(2, 3))
        resp.raise_for_status()
        course_ids = resp.json().get('course_ids', [])
        if not course_ids:
            self.stdout.write(self.style.ERROR(
                '演示教师名下没有课程，请先在 course-service 执行 seed_data'))
            return

        # 3) 每门课程创建 2 个作业（标题带课程名，与单体版演示数据一致）
        for course_id in course_ids:
            detail = requests.get(f'{_course_service_base()}/internal/courses/{course_id}/',
                                  headers=_internal_headers(), timeout=(2, 3))
            detail.raise_for_status()
            course = detail.json()
            for seq, (days, desc) in enumerate([
                (7, '第一次作业：完成课后习题第 1~5 题。'),
                (14, '第二次作业：完成课程实验并提交实验报告。'),
            ], start=1):
                Assignment.objects.get_or_create(
                    course_id=course_id, title=f"{course['name']}作业{seq}",
                    defaults={
                        'description': f"{course['name']}{desc}",
                        'deadline': timezone.now() + timedelta(days=days),
                    },
                )
            self.stdout.write(self.style.SUCCESS(
                f"课程就绪: {course['code']} {course['name']}（含 2 个作业）"))
        self.stdout.write(self.style.SUCCESS('作业服务演示数据准备完成'))
