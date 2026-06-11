from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import User, Course, Assignment, Submission
from .serializers import UserSerializer, CourseSerializer, AssignmentSerializer, SubmissionSerializer
from .permissions import IsTeacherOrReadOnly, IsOwnerOrTeacher

# 简单的测试视图（保留你原来的 hello）
from django.http import HttpResponse
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
    # 新增 me 接口
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeacherOrReadOnly]

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
            # 教师可以看自己课程的所有提交
            return Submission.objects.filter(assignment__course__teacher=user)
        else:
            # 学生只看自己的提交
            return Submission.objects.filter(student=user)

    def perform_create(self, serializer):
        # 创建提交记录，触发异步评测任务
        submission = serializer.save(student=self.request.user, status='pending')
        # 异步调用评测任务（先占位，后续实现 Celery 任务）
        from .tasks import run_code_check
        run_code_check.delay(submission.id)