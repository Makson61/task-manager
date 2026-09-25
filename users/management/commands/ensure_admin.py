"""
Создаёт администратора по переменным окружения, если его ещё нет.

Нужна для хостинга без доступа к консоли: команда выполняется при каждом
запуске контейнера. Без DJANGO_SUPERUSER_USERNAME и DJANGO_SUPERUSER_PASSWORD
ничего не делает.
"""
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Создать или обновить администратора по переменным DJANGO_SUPERUSER_*.'

    def handle(self, *args, **options):
        username = os.getenv('DJANGO_SUPERUSER_USERNAME', '').strip()
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', '')
        if not (username and password):
            self.stdout.write('ensure_admin: переменные не заданы, пропускаю.')
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': os.getenv('DJANGO_SUPERUSER_EMAIL', '')},
        )
        # Пароль из окружения главнее сохранённого: так его можно сменить без консоли.
        if created or not user.is_superuser or not user.check_password(password):
            user.is_staff = user.is_superuser = user.is_active = True
            user.set_password(password)
            user.save()
        self.stdout.write(f'ensure_admin: {username} - {"создан" if created else "обновлён"}.')
