from rest_framework import serializers

from .models import Course, Enrollment


class CourseSerializer(serializers.ModelSerializer):
    """课程序列化。

    teacher_name / students 的用户信息来自用户服务内部接口的补全结果（视图预取后
    挂在对象属性 `_teacher_info` / `_students_info` 上）；用户服务不可用时降级为
    null/[]（见《跨服务调用说明.md》场景 #1），课程数据本身正常返回。
    """
    teacher = serializers.IntegerField(source='teacher_id', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ('id', 'name', 'code', 'description', 'teacher', 'teacher_name',
                  'student_count', 'students', 'is_enrolled', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at', 'teacher')

    def get_teacher_name(self, obj):
        info = getattr(obj, '_teacher_info', None)
        return info.get('username') if info else None

    def get_student_count(self, obj):
        return obj.enrollments.count()

    def get_students(self, obj):
        """只在详情接口返回学生列表（视图已按可见性预取），列表接口返回空数组。"""
        view = self.context.get('view')
        if view and getattr(view, 'action', None) == 'list':
            return []
        return getattr(obj, '_students_info', None) or []

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            return Enrollment.objects.filter(course=obj, student_id=request.user.id).exists()
        return False
