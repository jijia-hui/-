from rest_framework import serializers
from .models import User, Course, Assignment, Submission, EmailVerificationCode

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(required=True, error_messages={
        'required': '邮箱为必填项',
        'invalid': '请输入有效的邮箱地址',
    })
    verification_code = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=6,
        error_messages={'max_length': '验证码为 6 位数字'},
    )

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_teacher', 'avatar', 'bio', 'password', 'verification_code')
        read_only_fields = ('id',)

    def validate_email(self, value):
        return EmailVerificationCode.normalize_email(value)

    def validate(self, attrs):
        if self.instance is None:
            code = (attrs.get('verification_code') or '').strip()
            if not code:
                raise serializers.ValidationError({'verification_code': '请填写邮箱验证码'})
            email = attrs.get('email') or ''
            pending = (
                EmailVerificationCode.objects.filter(
                    email=email, code=code, used_at__isnull=True)
                .order_by('-created_at')
                .first()
            )
            if not pending or pending.is_expired():
                raise serializers.ValidationError({'verification_code': '验证码错误或已过期，请重新获取'})
        return attrs

    def create(self, validated_data):
        code = validated_data.pop('verification_code', '')
        email = validated_data.get('email', '')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        EmailVerificationCode.consume(email, code)
        return user

    def update(self, instance, validated_data):
        validated_data.pop('verification_code', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class CourseSerializer(serializers.ModelSerializer):
    teacher_name = serializers.ReadOnlyField(source='teacher.username')
    student_count = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()   # 新增：当前用户是否已选课

    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'teacher')

    def get_student_count(self, obj):
        return obj.students.count()

    def get_students(self, obj):
        """只在详情接口返回详细学生列表，列表接口返回空数组（避免性能问题）"""
        request = self.context.get('request')
        if not request:
            return []
        view = self.context.get('view')
        if view and getattr(view, 'action', None) == 'list':
            return []
        user = request.user
        if user.is_authenticated and (user.is_staff or obj.teacher == user or obj.students.filter(id=user.id).exists()):
            return UserSerializer(obj.students.all(), many=True, context=self.context).data
        return []

    def get_is_enrolled(self, obj):
        """判断当前认证用户是否已选此课程"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.students.filter(id=request.user.id).exists()
        return False


class AssignmentSerializer(serializers.ModelSerializer):
    reference_file_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Assignment
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def get_reference_file_url(self, obj):
        if obj.reference_file:
            return obj.reference_file.url
        return None


class SubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='student.username')
    assignment_title = serializers.ReadOnlyField(source='assignment.title')

    class Meta:
        model = Submission
        fields = '__all__'
        read_only_fields = ('created_at', 'status', 'score', 'output', 'student', 'assignment')