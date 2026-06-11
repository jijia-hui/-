import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_backend.settings')
django.setup()

from apps.models import User
from rest_framework.authtoken.models import Token

def create_tokens_for_all_users():
    for user in User.objects.all():
        token, created = Token.objects.get_or_create(user=user)
        print(f"{user.username} (is_teacher={user.is_teacher}) -> {token.key}")

if __name__ == "__main__":
    create_tokens_for_all_users()