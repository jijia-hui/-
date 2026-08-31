from rest_framework import serializers

from .models import Assignment, Submission


class AssignmentSerializer(serializers.ModelSerializer):
    """作业序列化：course 字段即课程服务的课程 ID（跨服务只存 ID，不建外键）。"""
    course = serializers.IntegerField(source='course_id')
    reference_file_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Assignment
        fields = ('id', 'course', 'title', 'description', 'deadline',
                  'reference_file', 'reference_file_url', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_reference_file_url(self, obj):
        if obj.reference_file:
            return obj.reference_file.url
        return None


class SubmissionSerializer(serializers.ModelSerializer):
    """提交序列化：assignment 为库内作业 ID；student 为用户服务的学生 ID。

    student_name 由用户服务内部接口补全（视图批量预取后挂在 `_student_info` 上），
    用户服务不可用时降级为 null（见《跨服务调用说明.md》场景 #2）。
    assignment_title 为本服务库内关联，无需跨服务调用。
    """
    assignment = serializers.IntegerField(source='assignment_id', read_only=True)
    student = serializers.IntegerField(source='student_id', read_only=True)
    student_name = serializers.SerializerMethodField()
    assignment_title = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = ('id', 'assignment', 'assignment_title', 'student', 'student_name',
                  'code', 'status', 'score', 'output', 'created_at')
        read_only_fields = ('id', 'assignment', 'student', 'status', 'score',
                            'output', 'created_at')

    def get_student_name(self, obj):
        info = getattr(obj, '_student_info', None)
        return info.get('username') if info else None

    def get_assignment_title(self, obj):
        return obj.assignment.title if obj.assignment_id else None
