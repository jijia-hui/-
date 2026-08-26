from django.shortcuts import render

# Create your views here.
import logging

from django.core.mail import send_mail
from django.http import HttpResponse
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from .models import User, Course, Assignment, Submission
from .serializers import UserSerializer, CourseSerializer, AssignmentSerializer, SubmissionSerializer
from .permissions import IsCourseTeacherOrReadOnly

logger = logging.getLogger(__name__)

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

    def perform_create(self, serializer):
        user = serializer.save()
        self._send_registration_email(user)

    def _send_registration_email(self, user):
        """注册成功后向用户邮箱发送欢迎邮件（发送失败不影响注册结果）"""
        if not user.email:
            return
        try:
            subject = '注册成功 - 在线教学平台'
            message = (
                f'你好，{user.username}！\n\n'
                '恭喜你成功注册在线教学平台。\n'
                '请使用注册时的用户名和密码登录系统，开始使用课程与作业功能。\n\n'
                '此邮件由系统自动发送，请勿回复。'
            )
            html_message = (
                f'<p>你好，<strong>{user.username}</strong>！</p>'
                '<p>恭喜你成功注册<strong>在线教学平台</strong>。</p>'
                '<p>请使用注册时的用户名和密码登录系统，开始使用课程与作业功能。</p>'
                '<p style="color:#999;font-size:12px">此邮件由系统自动发送，请勿回复。</p>'
            )
            send_mail(subject, message, None, [user.email], html_message=html_message)
        except Exception as e:
            logger.warning('发送注册邮件失败 %s <%s>: %s', user.username, user.email, e)

    def get_queryset(self):
        # 普通用户只能看自己，教师和管理员可看所有
        if self.request.user.is_teacher or self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

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
        # 权限：必须先选该课程
        if not assignment.course.students.filter(id=request.user.id).exists():
            return Response({'detail': '请先选课再提交作业'}, status=status.HTTP_403_FORBIDDEN)
        # 截止时间校验
        if assignment.deadline < timezone.now():
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
        # 检查教师是否是该作业课程的教师
        if submission.assignment.course.teacher != request.user:
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