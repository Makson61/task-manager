"""Модели планировщика: категория и задача."""
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

SOON = timedelta(hours=36)


class Category(models.Model):
    """Пользовательская категория задач: «учёба», «дом», «работа»."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name='categories', verbose_name='владелец')
    name = models.CharField('название', max_length=60)

    class Meta:
        ordering = ['name']
        verbose_name = 'категория'
        verbose_name_plural = 'категории'
        constraints = [
            models.UniqueConstraint(fields=['owner', 'name'], name='unique_category_per_owner'),
        ]

    def __str__(self):
        return self.name


class TaskQuerySet(models.QuerySet):
    def owned_by(self, user):
        return self.filter(owner=user)

    def sorted_for_list(self):
        """Порядок списка задач.

        Невыполненные раньше выполненных, затем высокий приоритет перед
        обычным и низким, затем ближайший срок (задачи без срока - в конце),
        при равенстве - более новые задачи выше.
        """
        return self.annotate(
            priority_weight=models.Case(
                *[models.When(priority=value, then=models.Value(weight))
                  for value, weight in Task.PRIORITY_WEIGHTS.items()],
                default=models.Value(9),
                output_field=models.IntegerField(),
            ),
        ).order_by('completed', 'priority_weight', models.F('due_date').asc(nulls_last=True), '-date_added')

    def open_tasks(self):
        return self.filter(completed=False)

    def finished(self):
        return self.filter(completed=True)

    def overdue(self):
        return self.filter(completed=False, due_date__lt=timezone.now())

    def due_soon(self):
        now = timezone.now()
        return self.filter(completed=False, due_date__gte=now, due_date__lte=now + SOON)


class Task(models.Model):
    """Задача одного пользователя."""

    class Priority(models.TextChoices):
        LOW = 'low', 'Низкий'
        NORMAL = 'normal', 'Обычный'
        HIGH = 'high', 'Высокий'

    PRIORITY_WEIGHTS = {Priority.HIGH: 0, Priority.NORMAL: 1, Priority.LOW: 2}

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name='tasks', verbose_name='владелец')
    title = models.CharField('название', max_length=200)
    description = models.TextField('описание', blank=True)
    date_added = models.DateTimeField('создана', auto_now_add=True)
    due_date = models.DateTimeField('срок выполнения', null=True, blank=True)
    priority = models.CharField('приоритет', max_length=10, choices=Priority.choices,
                                default=Priority.NORMAL)
    completed = models.BooleanField('выполнена', default=False)
    completed_at = models.DateTimeField('дата выполнения', null=True, blank=True, editable=False)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='tasks', verbose_name='категория')

    objects = TaskQuerySet.as_manager()

    class Meta:
        verbose_name = 'задача'
        verbose_name_plural = 'задачи'
        indexes = [models.Index(fields=['owner', 'completed', 'due_date'])]

    def __str__(self):
        """Понятное название задачи."""
        return self.title

    def get_absolute_url(self):
        return reverse('tasks:detail', args=[self.pk])

    def save(self, *args, **kwargs):
        # Дата выполнения проставляется и снимается сама, вручную её не задают.
        if self.completed and self.completed_at is None:
            self.completed_at = timezone.now()
        elif not self.completed:
            self.completed_at = None
        super().save(*args, **kwargs)

    @property
    def state(self):
        """Состояние задачи для оформления: done, overdue, soon или open."""
        if self.completed:
            return 'done'
        if self.due_date is None:
            return 'open'
        now = timezone.now()
        if self.due_date < now:
            return 'overdue'
        return 'soon' if self.due_date <= now + SOON else 'open'
