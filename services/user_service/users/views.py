import logging

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import connection
from django.http import JsonResponse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .internal_client import InternalServiceError, purge_user_everywhere
from .jwt_auth import make_token
from .models import EmailVerificationCode, User
from .serializers import UserSerializer

logger = logging.getLogger(__name__)


def _version_payload(db_ok):
    return {
        'status': 'ok' if db_ok else 'degraded',
        'db': db_ok,
        'service': settings.SERVICE_NAME,
        'version': settings.APP_VERSION,
    }


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
    return JsonResponse(_version_payload(db_ok), status=200 if db_ok else 503)


def health(request):
    """合并探活（兼容单体版 /api/health/ 路径），携带版本号。"""
    return ready(request)


class InternalOnly(permissions.BasePermission):
    """内部接口：仅接受携带正确 X-Internal-Key 的调用（网关对 /internal/* 一律 403）。"""

    def has_permission(self, request, view):
        key = request.headers.get('X-Internal-Key', '')
        return key == settings.INTERNAL_API_KEY


class ObtainTokenView(APIView):
    """登录：校验用户名密码，签发无状态 JWT（响应与单体版一致：{"token": ...}）。"""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        username = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''
        if not username or not password:
            return Response({'non_field_errors': ['请输入用户名和密码']},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'non_field_errors': ['无法使用提供的凭证登录']},
                            status=status.HTTP_400_BAD_REQUEST)
        if not user.check_password(password):
            return Response({'non_field_errors': ['无法使用提供的凭证登录']},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({'token': make_token(user)})


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

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        # JWT 主体只带 id，这里回读用户服务自己的 users 表
        try:
            user = User.objects.get(id=request.user.id)
        except User.DoesNotExist:
            return Response({'detail': '用户不存在'}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """删除用户：先跨服务级联清理课程/选课/作业/提交，全部成功后才删本地用户。

        失败处理见《跨服务调用说明.md》场景 #8：清理失败 → 502，用户不删除（可重试）。
        """
        instance = self.get_object()
        try:
            purge_user_everywhere(instance.id)
        except InternalServiceError as exc:
            logger.warning('删除用户 %s 前级联清理失败: %s', instance.username, exc)
            return Response({'detail': f'关联数据清理失败，用户未删除（{exc}）'},
                            status=status.HTTP_502_BAD_GATEWAY)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SendVerificationCodeView(APIView):
    """向邮箱发送 6 位注册验证码。匿名可访问。"""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        email = EmailVerificationCode.normalize_email(request.data.get('email'))
        if not email:
            return Response({'email': ['请输入邮箱']}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_email(email)
        except DjangoValidationError:
            return Response({'email': ['请输入有效的邮箱地址']}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email__iexact=email).exists():
            return Response({'email': ['该邮箱已被注册']}, status=status.HTTP_400_BAD_REQUEST)

        wait = EmailVerificationCode.seconds_until_resend(email)
        if wait > 0:
            return Response(
                {'detail': f'发送过于频繁，请 {wait} 秒后再试', 'retry_after': wait},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        rec = EmailVerificationCode.issue(email)
        try:
            subject = '注册验证码 - 在线教学平台'
            message = (
                f'你的注册验证码是：{rec.code}\n\n'
                '验证码 10 分钟内有效，请勿泄露给他人。\n'
                '如非本人操作，请忽略本邮件。\n'
            )
            html_message = (
                f'<p>你的注册验证码是：</p>'
                f'<p style="font-size:28px;letter-spacing:6px;font-weight:700">{rec.code}</p>'
                '<p>验证码 <strong>10 分钟</strong>内有效，请勿泄露给他人。</p>'
                '<p style="color:#999;font-size:12px">如非本人操作，请忽略本邮件。</p>'
            )
            send_mail(subject, message, None, [email], html_message=html_message)
        except Exception as e:
            logger.warning('发送注册验证码失败 <%s>: %s', email, e)
            rec.delete()
            return Response({'detail': '验证码发送失败，请稍后重试'}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'detail': '验证码已发送，请查收邮箱', 'ttl_seconds': 600})


class InternalUserListView(APIView):
    """内部接口：按 ids 批量 / 按 username 精确查询用户基本信息（用于其他服务展示补全）。

    仅供携带 X-Internal-Key 的服务间调用；网关屏蔽 /internal/*。
    """
    permission_classes = [InternalOnly]
    authentication_classes = []

    def get(self, request):
        username = request.query_params.get('username')
        ids_param = request.query_params.get('ids', '')
        qs = User.objects.all()
        if username:
            qs = qs.filter(username=username)
        elif ids_param:
            try:
                ids = [int(x) for x in ids_param.split(',') if x.strip()]
            except ValueError:
                return Response({'detail': 'ids 参数必须为逗号分隔的整数'}, status=400)
            qs = qs.filter(id__in=ids)
        else:
            return Response({'detail': '必须提供 username 或 ids 参数'}, status=400)
        data = [
            {'id': u.id, 'username': u.username, 'is_teacher': u.is_teacher,
             'email': u.email, 'avatar': u.avatar, 'bio': u.bio}
            for u in qs.order_by('id')
        ]
        return Response(data)
