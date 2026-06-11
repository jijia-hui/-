# Register your models here.
from django.contrib import admin
from .models import User, Course, Assignment, Submission

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_teacher', 'is_staff')
    list_filter = ('is_teacher', 'is_staff')
    search_fields = ('username', 'email')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'teacher', 'created_at')
    filter_horizontal = ('students',)
    search_fields = ('name', 'code')

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'deadline', 'created_at')
    list_filter = ('course', 'deadline')
    search_fields = ('title',)

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'assignment', 'student', 'status', 'score', 'created_at')
    list_filter = ('status', 'assignment')
    search_fields = ('student__username',)