import logging

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .internal_client import InternalServiceError, fetch_users_map, purge_assignments_for_courses
from .models import Course, Enrollment
from .permissions import InternalOnly, IsCourseTeacherOrReadOnly
from .serializers import CourseSerializer

logger = logging.getLogger(__name__)


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


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.none()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsCourseTeacherOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        # 管理员：所有课程；教师：只看到自己创建的；学生：看到所有课程（以便选课）
        if user.is_staff:
            return Course.objects.all()
        if user.is_teacher:
            return Course.objects.filter(teacher_id=user.id)
        return Course.objects.all()

    def perform_create(self, serializer):
        # 自动将当前用户设为课程的教师（只存用户 ID）
        serializer.save(teacher_id=self.request.user.id)

    def _attach_teacher_info(self, course):
        """创建/更新后的响应与单体版一致，需要补全教师用户名（展示类调用，失败降级）。"""
        users = fetch_users_map([course.teacher_id])
        course._teacher_info = (users or {}).get(course.teacher_id)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        self._attach_teacher_info(serializer.instance)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        self._attach_teacher_info(serializer.instance)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        items = page if page is not None else list(qs)
        users = fetch_users_map([c.teacher_id for c in items])
        for c in items:
            c._teacher_info = (users or {}).get(c.teacher_id)
        serializer = self.get_serializer(items, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        users = fetch_users_map([obj.teacher_id])
        obj._teacher_info = (users or {}).get(obj.teacher_id)
        student_ids = list(obj.enrollments.values_list('student_id', flat=True))
        viewer = request.user
        # 与单体版一致：管理员/授课教师/已选课学生可在详情看到学生列表
        can_see_students = viewer.is_staff or obj.teacher_id == viewer.id or viewer.id in student_ids
        if can_see_students:
            smap = fetch_users_map(student_ids)
            obj._students_info = [smap[sid] for sid in student_ids if smap and smap.get(sid)]
        else:
            obj._students_info = []
        return Response(self.get_serializer(obj).data)

    def destroy(self, request, *args, **kwargs):
        """删除课程：先通知作业服务级联清理作业与提交，成功后才删课程（及选课记录）。

        失败处理见《跨服务调用说明.md》场景 #7：清理失败 → 502，课程不删除（可重试）。
        """
        course = self.get_object()
        try:
            purge_assignments_for_courses([course.id])
        except InternalServiceError as exc:
            logger.warning('删除课程 %s 前级联清理失败: %s', course.code, exc)
            return Response({'detail': f'关联作业数据清理失败，课程未删除（{exc}）'},
                            status=status.HTTP_502_BAD_GATEWAY)
        course.delete()  # enrollments 由库内外键级联删除
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def enroll(self, request, pk=None):
        """学生选课（选课不属于修改课程，故不要求课程教师权限）。重复选课幂等。"""
        course = self.get_object()
        if request.user.is_teacher:
            return Response({'detail': '教师不能选课'}, status=status.HTTP_400_BAD_REQUEST)
        Enrollment.objects.get_or_create(course=course, student_id=request.user.id)
        return Response({'status': 'enrolled'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def unenroll(self, request, pk=None):
        course = self.get_object()
        Enrollment.objects.filter(course=course, student_id=request.user.id).delete()
        return Response({'status': 'unenrolled'})


# ---------------- 内部接口（服务间调用，X-Internal-Key 鉴权，网关屏蔽） ----------------

class InternalCourseDetailView(APIView):
    """作业服务用它校验课程存在与授课教师归属（创建/编辑作业、评分）。"""
    permission_classes = [InternalOnly]
    authentication_classes = []

    def get(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({'detail': '课程不存在'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'id': course.id, 'code': course.code, 'name': course.name,
                         'teacher_id': course.teacher_id})


class InternalCourseStudentsView(APIView):
    """作业服务用它校验学生是否已选课（提交作业前的 fail-closed 校验）。"""
    permission_classes = [InternalOnly]
    authentication_classes = []

    def get(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({'detail': '课程不存在'}, status=status.HTTP_404_NOT_FOUND)
        student_ids = list(course.enrollments.values_list('student_id', flat=True))
        return Response({'course_id': course.id, 'student_ids': student_ids})


class InternalCourseIdsView(APIView):
    """按授课教师查其课程 ID 列表（作业服务圈定教师可见的提交范围）。"""
    permission_classes = [InternalOnly]
    authentication_classes = []

    def get(self, request):
        teacher_id = request.query_params.get('teacher_id')
        if not teacher_id:
            return Response({'detail': '必须提供 teacher_id 参数'}, status=400)
        ids = list(Course.objects.filter(teacher_id=teacher_id).values_list('id', flat=True))
        return Response({'teacher_id': int(teacher_id), 'course_ids': ids})


class InternalUserPurgeView(APIView):
    """用户服务删除用户时的级联清理入口（幂等，可重试）。

    删除该用户的所有选课记录与其授课的课程；课程删除前会先通知作业服务
    清理这些课程下的作业与提交（见《跨服务调用说明.md》第 4 节编排图）。
    """
    permission_classes = [InternalOnly]
    authentication_classes = []

    def post(self, request, user_id):
        deleted_enrollments = Enrollment.objects.filter(student_id=user_id).count()
        Enrollment.objects.filter(student_id=user_id).delete()
        courses_qs = Course.objects.filter(teacher_id=user_id)
        course_ids = list(courses_qs.values_list('id', flat=True))
        deleted_courses = courses_qs.count()
        try:
            purge_assignments_for_courses(course_ids)
        except InternalServiceError as exc:
            logger.warning('清理用户 %s 的课程数据时作业服务清理失败: %s', user_id, exc)
            return Response({'detail': f'作业数据清理失败: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)
        courses_qs.delete()
        return Response({'deleted_enrollments': deleted_enrollments,
                         'deleted_courses': deleted_courses, 'course_ids': course_ids})
