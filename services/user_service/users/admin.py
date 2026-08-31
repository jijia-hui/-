from django.contrib import admin

from .models import EmailVerificationCode, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'is_teacher', 'is_staff', 'date_joined')
    list_filter = ('is_teacher', 'is_staff')
    search_fields = ('username', 'email')


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('email', 'code', 'created_at', 'used_at')
    search_fields = ('email',)
