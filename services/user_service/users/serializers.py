from rest_framework import serializers

from .models import EmailVerificationCode, User


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
