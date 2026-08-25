from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import User, Course, Assignment, Submission


class BaseAPITestCase(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='teacher1', password='x', is_teacher=True)
        self.teacher2 = User.objects.create_user(username='teacher2', password='x', is_teacher=True)
        self.student = User.objects.create_user(username='student1', password='x')
        self.other = User.objects.create_user(username='student2', password='x')
        self.course = Course.objects.create(name='操作系统', code='OS101', teacher=self.teacher)
        self.course.students.add(self.student)
        self.assignment = Assignment.objects.create(
            course=self.course,
            title='作业一',
            description='描述',
            deadline=timezone.now() + timedelta(days=1),
            test_cases=[],
        )
        self.expired = Assignment.objects.create(
            course=self.course,
            title='过期作业',
            description='描述',
            deadline=timezone.now() - timedelta(days=1),
            test_cases=[],
        )

    def client_for(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        return client


class CoursePermissionTest(BaseAPITestCase):
    def test_teacher_can_delete_own_course(self):
        res = self.client_for(self.teacher).delete(f'/api/courses/{self.course.id}/')
        self.assertEqual(res.status_code, 204)

    def test_teacher_cannot_delete_others_course(self):
        # 其他教师的课程对当前教师不可见（404），或对象权限拒绝（403），二者都算拒绝
        res = self.client_for(self.teacher2).delete(f'/api/courses/{self.course.id}/')
        self.assertIn(res.status_code, (403, 404))
        self.assertTrue(Course.objects.filter(id=self.course.id).exists())

    def test_student_cannot_delete_course(self):
        res = self.client_for(self.student).delete(f'/api/courses/{self.course.id}/')
        self.assertEqual(res.status_code, 403)

    def test_enroll_still_works_for_student(self):
        res = self.client_for(self.other).post(f'/api/courses/{self.course.id}/enroll/')
        self.assertEqual(res.status_code, 200)


class AssignmentPermissionTest(BaseAPITestCase):
    def test_teacher_can_edit_own_assignment(self):
        res = self.client_for(self.teacher).patch(
            f'/api/assignments/{self.assignment.id}/', {'title': '改标题'})
        self.assertEqual(res.status_code, 200)

    def test_teacher_cannot_edit_others_assignment(self):
        res = self.client_for(self.teacher2).patch(
            f'/api/assignments/{self.assignment.id}/', {'title': '篡改'})
        self.assertEqual(res.status_code, 403)

    def test_teacher_cannot_delete_others_assignment(self):
        res = self.client_for(self.teacher2).delete(f'/api/assignments/{self.assignment.id}/')
        self.assertEqual(res.status_code, 403)


class SubmissionCreateTest(BaseAPITestCase):
    def test_enrolled_student_can_submit(self):
        res = self.client_for(self.student).post(
            '/api/submissions/', {'assignment': self.assignment.id, 'code': 'print(1)'})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'pending')

    def test_teacher_cannot_submit(self):
        res = self.client_for(self.teacher).post(
            '/api/submissions/', {'assignment': self.assignment.id, 'code': 'x'})
        self.assertEqual(res.status_code, 403)

    def test_unenrolled_student_cannot_submit(self):
        res = self.client_for(self.other).post(
            '/api/submissions/', {'assignment': self.assignment.id, 'code': 'x'})
        self.assertEqual(res.status_code, 403)

    def test_expired_assignment_rejected(self):
        res = self.client_for(self.student).post(
            '/api/submissions/', {'assignment': self.expired.id, 'code': 'x'})
        self.assertEqual(res.status_code, 400)


class SubmissionUpdateTest(BaseAPITestCase):
    def test_patch_cannot_change_assignment(self):
        submission = Submission.objects.create(
            assignment=self.assignment, student=self.student, code='x')
        res = self.client_for(self.student).patch(
            f'/api/submissions/{submission.id}/', {'assignment': self.expired.id})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['assignment'], self.assignment.id)

    def test_patch_cannot_change_student(self):
        submission = Submission.objects.create(
            assignment=self.assignment, student=self.student, code='x')
        res = self.client_for(self.student).patch(
            f'/api/submissions/{submission.id}/', {'student': self.other.id})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['student'], self.student.id)


class RegistrationEmailTest(TestCase):
    def test_register_requires_email(self):
        res = APIClient().post('/api/users/', {
            'username': 'newbie',
            'password': 'pass1234',
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('email', res.data)

    def test_register_rejects_invalid_email(self):
        res = APIClient().post('/api/users/', {
            'username': 'newbie',
            'password': 'pass1234',
            'email': 'not-an-email',
        })
        self.assertEqual(res.status_code, 400)

    def test_register_sends_welcome_email(self):
        res = APIClient().post('/api/users/', {
            'username': 'newbie',
            'password': 'pass1234',
            'email': 'newbie@example.com',
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['newbie@example.com'])
        self.assertIn('注册成功', mail.outbox[0].subject)
        self.assertIn('newbie', mail.outbox[0].body)
        self.assertTrue(User.objects.filter(username='newbie').exists())
