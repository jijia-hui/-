from django.shortcuts import render

# Create your views here.
import logging
import os

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.http import JsonResponse, HttpResponse
from django.db import connection
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from .models import User, Course, Assignment, Submission, EmailVerificationCode
from .serializers import UserSerializer, CourseSerializer, AssignmentSerializer, SubmissionSerializer
from .permissions import IsCourseTeacherOrReadOnly
from .course_client import student_is_enrolled, is_course_teacher

logger = logging.getLogger(__name__)


def health(request):
    """容器 / K8s 探活用：确认进程可响应且数据库可连接。无需登录。"""
    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False
    payload = {'status': 'ok' if db_ok else 'degraded', 'db': db_ok}
    return JsonResponse(payload, status=200 if db_ok else 503)


# 简单的测试视图
def hello(request):
    return HttpResponse("Hello teaching")

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        # 注册（create）允许匿名，其他操作需要登录
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        # 普通用户只能看自己，教师和管理员可看所有
        if self.request.user.is_teacher or self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class SendVerificationCodeView(APIView):
    """向邮箱发送 6 位注册验证码。匿名可访问。"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = EmailVerificationCode.normalize_email(request.data.get('email'))
        if not email:
            return Response({'email': ['请输入邮箱']}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_email(email)
        except DjangoValidationError:
            return Response({'email': ['请输入有效的邮箱地址']}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email__iexact=email).exists():
            return Response({'email': ['该邮箱已被注册']}, status=status.HTTP_400_BAD_REQUEST)

        wait = EmailVerificationCode.seconds_until_resend(email)
        if wait > 0:
            return Response(
                {'detail': f'发送过于频繁，请 {wait} 秒后再试', 'retry_after': wait},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        rec = EmailVerificationCode.issue(email)
        try:
            subject = '注册验证码 - 在线教学平台'
            message = (
                f'你的注册验证码是：{rec.code}\n\n'
                '验证码 10 分钟内有效，请勿泄露给他人。\n'
                '如非本人操作，请忽略本邮件。\n'
            )
            html_message = (
                f'<p>你的注册验证码是：</p>'
                f'<p style="font-size:28px;letter-spacing:6px;font-weight:700">{rec.code}</p>'
                '<p>验证码 <strong>10 分钟</strong>内有效，请勿泄露给他人。</p>'
                '<p style="color:#999;font-size:12px">如非本人操作，请忽略本邮件。</p>'
            )
            send_mail(subject, message, None, [email], html_message=html_message)
        except Exception as e:
            logger.warning('发送注册验证码失败 <%s>: %s', email, e)
            rec.delete()
            return Response({'detail': '验证码发送失败，请稍后重试'}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'detail': '验证码已发送，请查收邮箱', 'ttl_seconds': 600})


def _reject_if_bad_internal_token(request):
    expected = os.environ.get('INTERNAL_TOKEN', '')
    if not expected:
        return None
    if request.headers.get('X-Internal-Token', '') != expected:
        return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
    return None


class InternalUserView(APIView):
    """供课程/作业服务按 ID 查用户。不经 Nginx 对外暴露，仅集群内访问。"""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        denied = _reject_if_bad_internal_token(request)
        if denied:
            return denied
        user = get_object_or_404(User, pk=pk)
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_teacher': user.is_teacher,
            'is_staff': user.is_staff,
        })


class CourseViewSet(viewsets.ModelViewSet):
    # 空的 queryset 满足 DRF router 要求，实际查询由 get_queryset 动态决定
    queryset = Course.objects.none()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseTeacherOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        # 管理员：所有课程
        if user.is_staff:
            return Course.objects.all().prefetch_related('students')
        # 教师：只看到自己创建的课程
        if user.is_teacher:
            return Course.objects.filter(teacher=user).prefetch_related('students')
        # 学生：看到所有课程（以便选课）
        return Course.objects.all().prefetch_related('students')
    def create(self, request, *args, **kwargs):
        print("创建课程请求数据:", request.data)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("序列化器错误:", serializer.errors)   # 添加这一行
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)
    def perform_create(self, serializer):
        # 自动将当前用户设为课程的教师
        serializer.save(teacher=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def enroll(self, request, pk=None):
        """学生选课（选课不属于修改课程，故不要求课程教师权限）"""
        course = self.get_object()
        if request.user.is_teacher:
            return Response({'detail': '教师不能选课'}, status=status.HTTP_400_BAD_REQUEST)
        course.students.add(request.user)
        return Response({'status': 'enrolled'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def unenroll(self, request, pk=None):
        course = self.get_object()
        course.students.remove(request.user)
        return Response({'status': 'unenrolled'})


class InternalCourseEnrollmentView(APIView):
    """作业服务提交前校验：该用户是否已选此课。"""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk, user_id):
        denied = _reject_if_bad_internal_token(request)
        if denied:
            return denied
        course = get_object_or_404(Course, pk=pk)
        return Response({
            'course_id': course.id,
            'user_id': int(user_id),
            'enrolled': course.students.filter(id=user_id).exists(),
        })


class InternalCourseTeacherView(APIView):
    """作业服务评分前校验授课教师。"""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        denied = _reject_if_bad_internal_token(request)
        if denied:
            return denied
        course = get_object_or_404(Course, pk=pk)
        return Response({
            'course_id': course.id,
            'teacher_id': course.teacher_id,
            'username': course.teacher.username,
        })


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseTeacherOrReadOnly]

    def get_queryset(self):
        # 根据课程过滤
        course_id = self.request.query_params.get('course')
        if course_id:
            return Assignment.objects.filter(course_id=course_id)
        return Assignment.objects.all()

class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # 基础权限过滤
        if user.is_teacher:
            queryset = Submission.objects.filter(assignment__course__teacher=user)
        else:
            queryset = Submission.objects.filter(student=user)

        # 关键修复：支持按作业 ID 过滤（避免跨作业显示提交）
        assignment_id = self.request.query_params.get('assignment')
        if assignment_id:
            queryset = queryset.filter(assignment_id=assignment_id)
        return queryset

    def create(self, request, *args, **kwargs):
        # 学生提交时，状态为 pending，等待教师评分
        assignment_id = request.data.get('assignment')
        code = request.data.get('code')
        if not assignment_id or not code:
            return Response({'detail': '缺少 assignment 或 code'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response({'detail': '作业不存在'}, status=status.HTTP_400_BAD_REQUEST)

        # 权限：教师不能提交作业
        if request.user.is_teacher:
            return Response({'detail': '教师不能提交作业'}, status=status.HTTP_403_FORBIDDEN)
        if not student_is_enrolled(assignment.course_id, request.user.id):
            return Response({'detail': '请先选课再提交作业'}, status=status.HTTP_403_FORBIDDEN)
        # 截止时间校验
        if assignment.is_expired():
            return Response({'detail': '作业已截止，无法提交'}, status=status.HTTP_400_BAD_REQUEST)

        submission = Submission.objects.create(
            assignment=assignment,
            student=request.user,
            code=code,
            status='pending',      # 待教师评分
            score=0,
            output='等待教师评分。'
        )
        serializer = self.get_serializer(submission)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def grade(self, request, pk=None):
        """教师评分接口"""
        submission = self.get_object()
        # 权限：只有教师（且是该课程教师）可以评分
        if not request.user.is_teacher:
            return Response({'detail': '只有教师可以评分'}, status=status.HTTP_403_FORBIDDEN)
        if not is_course_teacher(submission.assignment.course_id, request.user.id):
            return Response({'detail': '你无权评分此提交'}, status=status.HTTP_403_FORBIDDEN)

        score = request.data.get('score')
        if score is None:
            return Response({'detail': '缺少分数'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            score = int(score)
            if score < 0 or score > 100:
                raise ValueError
        except (ValueError, TypeError):
            return Response({'detail': '分数必须是0-100的整数'}, status=status.HTTP_400_BAD_REQUEST)

        submission.score = score
        submission.status = 'graded'
        submission.save()
        serializer = self.get_serializer(submission)
        return Response(serializer.data)