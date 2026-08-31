# 用户服务演示数据（幂等）：演示教师/学生账号。
# 微服务版演示数据分属三个服务，请按顺序执行：
#   1) user-service:       python manage.py seed_data
#   2) course-service:     python manage.py seed_data
#   3) assignment-service: python manage.py seed_data
from django.core.management.base import BaseCommand

from users.models import User

DEMO_TEACHER = 'demo_teacher'
DEMO_STUDENT = 'demo_student'
DEMO_PASSWORD = 'Demo@1234'


class Command(BaseCommand):
    help = '创建演示账号：教师 demo_teacher / 学生 demo_student（幂等，可重复执行）'

    def handle(self, *args, **options):
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
        self.stdout.write(self.style.SUCCESS(
            f'用户服务演示账号就绪: {DEMO_TEACHER}(id={teacher.id}) / {DEMO_STUDENT}(id={student.id})'
            f'（密码 {DEMO_PASSWORD}）'))
        self.stdout.write('提示: 教师用户 id 供 course-service/assignment-service 的 seed_data 使用。')
