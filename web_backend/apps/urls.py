from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, CourseViewSet, AssignmentViewSet, SubmissionViewSet,
    SendVerificationCodeView, health,
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'courses', CourseViewSet)
router.register(r'assignments', AssignmentViewSet)
router.register(r'submissions', SubmissionViewSet)

urlpatterns = [
    path('api/health/', health, name='health'),
    path('api/auth/send-code/', SendVerificationCodeView.as_view(), name='send_verification_code'),
    path('api/', include(router.urls)),
]