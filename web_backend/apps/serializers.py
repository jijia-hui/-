from rest_framework import serializers
from .models import User, Course, Assignment, Submission

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_teacher', 'avatar', 'bio','password')
        read_only_fields = ('id',)
        
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)   # 自动处理所有字段（包括 is_teacher）
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    

class CourseSerializer(serializers.ModelSerializer):
    teacher_name = serializers.ReadOnlyField(source='teacher.username')
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'teacher')

    def get_student_count(self, obj):
        return obj.students.count()

class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class SubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='student.username')
    assignment_title = serializers.ReadOnlyField(source='assignment.title')

    class Meta:
        model = Submission
        fields = '__all__'
        read_only_fields = ('created_at', 'status', 'score', 'output')