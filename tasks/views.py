"""
Представления планировщика - классовые.

Общий миксин OwnedByUser отдаёт выборку только из задач текущего
пользователя, поэтому detail, edit, delete и toggle отвечают 404 и на чужой,
и на несуществующий идентификатор. Проверка живёт в представлении, а не
в шаблоне: адрес можно набрать руками.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import (CreateView, DeleteView, DetailView, ListView, TemplateView,
                                  UpdateView)

from .forms import CategoryForm, TaskForm
from .models import Category, Task

# Наборы задач для вкладок списка.
TABS = {
    'all': ('Все', lambda tasks: tasks),
    'open': ('Активные', lambda tasks: tasks.open_tasks()),
    'overdue': ('Просроченные', lambda tasks: tasks.overdue()),
    'done': ('Выполненные', lambda tasks: tasks.finished()),
}


class OwnedByUser(LoginRequiredMixin):
    """Ограничивает выборку объектами текущего пользователя."""

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


def safe_back(request, default):
    """Адрес возврата из формы - только если он ведёт на этот же сайт."""
    target = request.POST.get('next') or request.GET.get('next')
    if target and url_has_allowed_host_and_scheme(target, {request.get_host()},
                                                  require_https=request.is_secure()):
        return target
    return default


class HomeView(TemplateView):
    """Главная: рассказ о сервисе для гостя, сводка для вошедшего."""

    template_name = 'tasks/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.user.is_authenticated:
            return context

        tasks = Task.objects.owned_by(self.request.user)
        context.update(
            open_count=tasks.open_tasks().count(),
            overdue_count=tasks.overdue().count(),
            done_count=tasks.finished().count(),
            soon=tasks.due_soon().sorted_for_list()[:5],
            next_tasks=tasks.open_tasks().sorted_for_list()[:5],
        )
        return context


class TaskListView(LoginRequiredMixin, ListView):
    """Список задач текущего пользователя: вкладки, поиск, категория, страницы."""

    template_name = 'tasks/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 10

    @property
    def tab(self):
        requested = self.request.GET.get('tab', 'open')
        return requested if requested in TABS else 'open'

    def get_queryset(self):
        tasks = Task.objects.owned_by(self.request.user).select_related('category')
        tasks = TABS[self.tab][1](tasks)

        query = self.request.GET.get('q', '').strip()
        if query:
            tasks = tasks.filter(Q(title__icontains=query) | Q(description__icontains=query))

        category = self.request.GET.get('category', '')
        if category.isdigit():
            tasks = tasks.filter(category_id=int(category))
        elif category == 'none':
            tasks = tasks.filter(category__isnull=True)

        return tasks.sorted_for_list()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mine = Task.objects.owned_by(self.request.user)
        context.update(
            tab=self.tab,
            tabs=[(key, label, TABS[key][1](mine).count()) for key, (label, _) in TABS.items()],
            query=self.request.GET.get('q', '').strip(),
            category=self.request.GET.get('category', ''),
            categories=Category.objects.filter(owner=self.request.user).annotate(
                total=Count('tasks', filter=Q(tasks__completed=False)),
            ),
            no_tasks_at_all=not mine.exists(),
        )
        return context


class TaskDetailView(OwnedByUser, DetailView):
    model = Task
    template_name = 'tasks/task_detail.html'
    context_object_name = 'task'


class TaskFormMixin:
    """Общее для создания и редактирования задачи."""

    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_form.html'

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'owner': self.request.user}

    def get_success_url(self):
        return safe_back(self.request, reverse('tasks:list'))


class TaskCreateView(TaskFormMixin, LoginRequiredMixin, CreateView):
    def form_valid(self, form):
        # Владелец берётся из сессии, а не из присланных данных.
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Задача «{self.object}» создана.')
        return response

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'is_new': True}


class TaskUpdateView(TaskFormMixin, OwnedByUser, UpdateView):
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Изменения сохранены.')
        return response

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'is_new': False}


class TaskDeleteView(OwnedByUser, DeleteView):
    """GET показывает подтверждение, удаляет только POST."""

    model = Task
    template_name = 'tasks/task_confirm_delete.html'
    context_object_name = 'task'
    success_url = reverse_lazy('tasks:list')

    def form_valid(self, form):
        messages.success(self.request, f'Задача «{self.object}» удалена.')
        return super().form_valid(form)


class TaskToggleView(LoginRequiredMixin, View):
    """Отметить выполненной или вернуть в работу. Только POST."""

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, owner=request.user)
        task.completed = not task.completed
        task.save()
        if task.completed:
            messages.success(request, f'«{task}» - готово.')
        else:
            messages.info(request, f'«{task}» снова в работе.')
        return HttpResponseRedirect(safe_back(request, reverse('tasks:list')))


class CategoryListView(LoginRequiredMixin, CreateView):
    """Страница категорий: список с формой добавления на ней же."""

    form_class = CategoryForm
    template_name = 'tasks/category_list.html'
    success_url = reverse_lazy('tasks:categories')

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'owner': self.request.user}

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Категория добавлена.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        categories = Category.objects.filter(owner=self.request.user).annotate(total=Count('tasks'))
        return {**super().get_context_data(**kwargs), 'categories': categories}


class CategoryDeleteView(OwnedByUser, DeleteView):
    """Удаляет категорию. Задачи остаются, но становятся без категории."""

    model = Category
    template_name = 'tasks/category_confirm_delete.html'
    context_object_name = 'category'
    success_url = reverse_lazy('tasks:categories')

    def form_valid(self, form):
        messages.success(self.request, 'Категория удалена, задачи остались.')
        return super().form_valid(form)
