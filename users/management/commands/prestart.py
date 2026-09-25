"""
Подготовка приложения при запуске контейнера.

Миграции, администратор и демо-данные выполняются за одну загрузку Django:
на слабом процессоре бесплатного хостинга каждый отдельный вызов manage.py
стоит несколько секунд.
"""
import os

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'migrate + ensure_admin + demo_data (если DEMO_DATA=True).'

    def handle(self, *args, **options):
        call_command('migrate', interactive=False)
        call_command('ensure_admin')
        if os.getenv('DEMO_DATA', 'False').strip().lower() in ('1', 'true', 'yes', 'on'):
            call_command('demo_data')
