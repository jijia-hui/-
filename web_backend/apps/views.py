from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import User, Course, Assignment, Submission
from .serializers import UserSerializer, CourseSerializer, AssignmentSerializer, SubmissionSerializer
from .permissions import IsTeacherOrReadOnly, IsOwnerOrTeacher

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

class CourseViewSet(viewsets.ModelViewSet):
    # 空的 queryset 满足 DRF router 要求，实际查询由 get_queryset 动态决定
    queryset = Course.objects.none()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeacherOrReadOnly]

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

    def perform_create(self, serializer):
        # 自动将当前用户设为课程的教师
        serializer.save(teacher=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def enroll(self, request, pk=None):
        """学生选课"""
        course = self.get_object()
        if request.user.is_teacher:
            return Response({'detail': '教师不能选课'}, status=status.HTTP_400_BAD_REQUEST)
        course.students.add(request.user)
        return Response({'status': 'enrolled'})

    @action(detail=True, methods=['post'])
    def unenroll(self, request, pk=None):
        course = self.get_object()
        course.students.remove(request.user)
        return Response({'status': 'unenrolled'})

class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeacherOrReadOnly]

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
        if user.is_teacher:
            return Submission.objects.filter(assignment__course__teacher=user)
        return Submission.objects.filter(student=user)

    def create(self, request, *args, **kwargs):
        # 手动处理创建逻辑，绕过序列化器对某些字段的验证
        assignment_id = request.data.get('assignment')
        code = request.data.get('code')
        if not assignment_id or not code:
            return Response({'detail': '缺少 assignment 或 code'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response({'detail': '作业不存在'}, status=status.HTTP_400_BAD_REQUEST)
        
        submission = Submission.objects.create(
            assignment=assignment,
            student=request.user,
            code=code,
            status='success',
            score=0,
            output='提交成功，无需评测。'
        )
        serializer = self.get_serializer(submission)
        return Response(serializer.data, status=status.HTTP_201_CREATED)