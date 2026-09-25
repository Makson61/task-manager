"""
Наполняет пустой планировщик данными для демонстрации.

Создаёт пользователей dmitry и olga с паролем из DEMO_PASSWORD, их категории
и задачи: активные, просроченные, со сроком на днях и выполненные. Повторный
запуск ничего не дублирует, без DEMO_PASSWORD команда не делает ничего.
"""
import os
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from tasks.models import Category, Task

HIGH, NORMAL, LOW = Task.Priority.HIGH, Task.Priority.NORMAL, Task.Priority.LOW

# (название, описание, часов до срока или None, приоритет, выполнена, категория)
DEMO = {
    'dmitry': [
        ('Доделать практическую по Django', 'Три проекта: журнал, планировщик, блог.', 20, HIGH, False, 'Учёба'),
        ('Подготовить доклад', 'Десять слайдов и короткие тезисы.', 24 * 6, NORMAL, False, 'Учёба'),
        ('Оплатить интернет', '', -30, HIGH, False, 'Дом'),
        ('Забрать посылку', 'Пункт выдачи работает до 21:00.', 30, NORMAL, False, 'Дом'),
        ('Купить лампочки', '', None, LOW, False, 'Дом'),
        ('Прочитать главу про миграции', '', -80, NORMAL, True, 'Учёба'),
    ],
    'olga': [
        ('Собрать портфолио', 'Отобрать десять работ.', 48, HIGH, False, 'Работа'),
        ('Разобрать почту', '', None, LOW, False, None),
        ('Записаться к врачу', '', -6, NORMAL, True, None),
    ],
}


class Command(BaseCommand):
    help = 'Создать демонстрационных пользователей dmitry и olga с задачами.'

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.getenv('DEMO_PASSWORD', '')
        if not password:
            self.stdout.write('demo_data: DEMO_PASSWORD не задан, пропускаю.')
            return

        start = timezone.now().replace(minute=0, second=0, microsecond=0)
        for username, tasks in DEMO.items():
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                user.save()
            if Task.objects.filter(owner=user).exists():
                continue

            categories = {}
            for title, description, hours, priority, completed, category_name in tasks:
                category = None
                if category_name:
                    if category_name not in categories:
                        categories[category_name], _ = Category.objects.get_or_create(
                            owner=user, name=category_name)
                    category = categories[category_name]
                Task.objects.create(
                    owner=user, title=title, description=description, priority=priority,
                    completed=completed, category=category,
                    due_date=None if hours is None else start + timedelta(hours=hours),
                )
            self.stdout.write(f'demo_data: задачи для {username} созданы.')
