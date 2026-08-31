import logging

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from .internal_client import (
    CourseNotFound, InternalServiceError, fetch_users_map, get_course,
    get_student_ids, get_teacher_course_ids,
)
from .models import Assignment, Submission
from .serializers import AssignmentSerializer, SubmissionSerializer

logger = logging.getLogger(__name__)

SERVICE_UNAVAILABLE_DETAIL = '课程服务暂不可用，请稍后重试'
ENROLL_CHECK_UNAVAILABLE_DETAIL = '选课校验服务暂不可用，请稍后重试'


class ServiceUnavailable(APIException):
    """依赖服务不可用：快速失败 503（fail-closed，绝不绕过校验）。"""
    status_code = 503
    default_detail = SERVICE_UNAVAILABLE_DETAIL


def live(request):
    """存活探针：进程可响应即 200（不查数据库）。"""
    return JsonResponse({'status': 'ok', 'service': settings.SERVICE_NAME,
                         'version': settings.APP_VERSION})


def _db_ok():
    try:
        connection.ensure_connection()
        return True
    except Exception:
        return False


def ready(request):
    """就绪探针：数据库可连接才 200。"""
    db_ok = _db_ok()
    payload = {'status': 'ok' if db_ok else 'degraded', 'db': db_ok,
               'service': settings.SERVICE_NAME, 'version': settings.APP_VERSION}
    return JsonResponse(payload, status=200 if db_ok else 503)


def health(request):
    """合并探活（兼容单体版 /api/health/ 路径），携带版本号。"""
    return ready(request)


class TeacherOrReadOnly(permissions.BasePermission):
    """写操作要求教师身份（身份来自 JWT 本地验签）；对象级归属在视图里经课程服务校验。"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated and user.is_teacher)


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated, TeacherOrReadOnly]

    def get_queryset(self):
        # 与单体版一致：支持 ?course={id} 过滤，默认返回全部
        course_id = self.request.query_params.get('course')
        if course_id:
            return Assignment.objects.filter(course_id=course_id)
        return Assignment.objects.all()

    def _check_course_owner(self, course_id, user):
        """经课程服务校验课程存在且当前教师为授课教师（场景 #3）。

        抛出：CourseNotFound（业务错误，调用方转 400/404）、
        ServiceUnavailable（课程服务不可用 → 503 fail-closed）、PermissionDenied（403）。
        """
        try:
            course = get_course(course_id)
        except InternalServiceError:
            raise ServiceUnavailable(SERVICE_UNAVAILABLE_DETAIL)
        except CourseNotFound:
            raise
        if course['teacher_id'] != user.id:
            self.permission_denied(self.request, message='你无权管理该课程的作业')
        return course

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self._check_course_owner(serializer.validated_data['course_id'], request.user)
        except CourseNotFound:
            # 与单体版外键校验一致：课程不存在 → 400
            return Response({'course': ['课程不存在']}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        # 目标课程若被修改，按新课程校验归属；否则按原课程
        target_course_id = serializer.validated_data.get('course_id', instance.course_id)
        try:
            self._check_course_owner(target_course_id, request.user)
        except CourseNotFound:
            return Response({'course': ['课程不存在']}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self._check_course_owner(instance.course_id, request.user)
        except CourseNotFound:
            return Response({'detail': '课程不存在'}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()  # submissions 由库内外键级联删除
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_teacher:
            # 教师只能看到自己授课课程下的提交；课程范围需经课程服务圈定（场景 #6）。
            # 课程服务不可用 → 503 快速失败（无法圈定授权范围时宁可报错）。
            try:
                course_ids = get_teacher_course_ids(user.id)
            except InternalServiceError:
                raise ServiceUnavailable(SERVICE_UNAVAILABLE_DETAIL)
            queryset = Submission.objects.filter(assignment__course_id__in=course_ids)
        else:
            queryset = Submission.objects.filter(student_id=user.id)

        # 支持按作业 ID 过滤（避免跨作业显示提交）
        assignment_id = self.request.query_params.get('assignment')
        if assignment_id:
            queryset = queryset.filter(assignment_id=assignment_id)
        return queryset

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        items = page if page is not None else list(qs)
        users = fetch_users_map([s.student_id for s in items])
        for s in items:
            s._student_info = (users or {}).get(s.student_id)
        serializer = self.get_serializer(items, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        users = fetch_users_map([obj.student_id])
        obj._student_info = (users or {}).get(obj.student_id)
        return Response(self.get_serializer(obj).data)

    def create(self, request, *args, **kwargs):
        """学生提交作业：教师 403 → 选课校验（fail-closed）→ 截止校验 → 落库 pending。"""
        assignment_id = request.data.get('assignment')
        code = request.data.get('code')
        if not assignment_id or not code:
            return Response({'detail': '缺少 assignment 或 code'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response({'detail': '作业不存在'}, status=status.HTTP_400_BAD_REQUEST)

        # 权限：教师不能提交作业（本地 JWT 判定，无需跨服务）
        if request.user.is_teacher:
            return Response({'detail': '教师不能提交作业'}, status=status.HTTP_403_FORBIDDEN)
        # 权限：必须先选该课程（课程服务内部接口，场景 #4；不可用 → 503，不绕过）
        try:
            student_ids = get_student_ids(assignment.course_id)
        except CourseNotFound:
            return Response({'detail': '作业不存在'}, status=status.HTTP_400_BAD_REQUEST)
        except InternalServiceError:
            return Response({'detail': ENROLL_CHECK_UNAVAILABLE_DETAIL},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if request.user.id not in student_ids:
            return Response({'detail': '请先选课再提交作业'}, status=status.HTTP_403_FORBIDDEN)
        # 截止时间校验（本地业务规则）
        if assignment.is_expired():
            return Response({'detail': '作业已截止，无法提交'}, status=status.HTTP_400_BAD_REQUEST)

        submission = Submission.objects.create(
            assignment=assignment,
            student_id=request.user.id,
            code=code,
            status='pending',      # 待教师评分
            score=0,
            output='等待教师评分。'
        )
        # 响应与单体版一致：补全学生用户名（展示类调用，用户服务不可用时降级为 null）
        users = fetch_users_map([submission.student_id])
        submission._student_info = (users or {}).get(submission.student_id)
        serializer = self.get_serializer(submission)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def grade(self, request, pk=None):
        """教师评分：先经课程服务确认是授课教师（场景 #5），再本地更新状态与得分。"""
        submission = self.get_object()
        if not request.user.is_teacher:
            return Response({'detail': '只有教师可以评分'}, status=status.HTTP_403_FORBIDDEN)
        try:
            course = get_course(submission.assignment.course_id)
        except CourseNotFound:
            return Response({'detail': '作业所属课程不存在'}, status=status.HTTP_404_NOT_FOUND)
        except InternalServiceError:
            return Response({'detail': SERVICE_UNAVAILABLE_DETAIL},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if course['teacher_id'] != request.user.id:
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
        users = fetch_users_map([submission.student_id])
        submission._student_info = (users or {}).get(submission.student_id)
        serializer = self.get_serializer(submission)
        return Response(serializer.data)


# ---------------- 内部接口（服务间调用，X-Internal-Key 鉴权，网关屏蔽） ----------------

class InternalOnly(permissions.BasePermission):
    """内部接口：仅接受携带正确 X-Internal-Key 的调用（网关对 /internal/* 一律 403）。"""

    def has_permission(self, request, view):
        key = request.headers.get('X-Internal-Key', '')
        return key == settings.INTERNAL_API_KEY


class InternalCoursesPurgeView(APIView):
    """课程服务删除课程时的级联清理入口：按 course_ids 删除作业（提交随库内外键级联）。幂等。"""
    permission_classes = [InternalOnly]
    authentication_classes = []

    def post(self, request):
        course_ids = request.data.get('course_ids') or []
        if not isinstance(course_ids, list):
            return Response({'detail': 'course_ids 必须为列表'}, status=400)
        qs = Assignment.objects.filter(course_id__in=course_ids)
        submission_count = sum(a.submissions.count() for a in qs)
        deleted_assignments = qs.count()
        qs.delete()  # submissions 随库内外键级联删除
        return Response({'deleted_assignments': deleted_assignments,
                         'deleted_submissions': submission_count})


class InternalUserPurgeView(APIView):
    """用户服务删除用户时的级联清理入口：删除该学生的全部提交记录。幂等。"""
    permission_classes = [InternalOnly]
    authentication_classes = []

    def post(self, request, user_id):
        deleted, _ = Submission.objects.filter(student_id=user_id).delete()
        return Response({'deleted_submissions': deleted})
