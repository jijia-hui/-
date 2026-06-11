from django.contrib.auth.backends import ModelBackend
from .models import User

class PlainTextAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(username=username)
            # 明文比对
            if user.password == password:
                return user
        except User.DoesNotExist:
            return None