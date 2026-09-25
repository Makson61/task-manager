"""Тесты планировщика задач.

Обязательные проверки из задания: авторизация, фильтрация по владельцу,
назначение владельца, запрет изменения и удаления чужой задачи, 404 для
отсутствующего идентификатора, переключение состояния, невозможность
удалить задачу запросом GET.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Category, Task


class PlannerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dmitry = User.objects.create_user('dmitry', password='pass-12345')
        cls.olga = User.objects.create_user('olga', password='pass-12345')
        cls.task = Task.objects.create(owner=cls.dmitry, title='Задача Дмитрия')
        cls.foreign = Task.objects.create(owner=cls.olga, title='Задача Ольги')

    def link(self, name, *args):
        return reverse(f'tasks:{name}', args=args)


class AuthTests(PlannerTestCase):
    def test_guest_is_sent_to_login(self):
        """Обязательный: страницы с данными требуют входа."""
        pages = [self.link('list'), self.link('new'), self.link('detail', self.task.pk),
                 self.link('edit', self.task.pk), self.link('delete', self.task.pk),
                 self.link('categories')]
        for url in pages:
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), f"{reverse('users:login')}?next={url}")

    def test_guest_cannot_toggle(self):
        self.client.post(self.link('toggle', self.task.pk))
        self.task.refresh_from_db()
        self.assertFalse(self.task.completed)

    def test_home_is_open(self):
        self.assertContains(self.client.get(self.link('index')), 'Регистрация')


class OwnershipTests(PlannerTestCase):
    def setUp(self):
        self.client.force_login(self.dmitry)

    def test_list_contains_only_own_tasks(self):
        """Обязательный: в списке только задачи владельца."""
        response = self.client.get(self.link('list'))
        titles = [task.title for task in response.context['tasks']]
        self.assertEqual(titles, ['Задача Дмитрия'])

    def test_owner_is_taken_from_session(self):
        """Обязательный: владелец назначается сам, подмена в POST не проходит."""
        self.client.post(self.link('new'), {
            'title': 'Новая', 'priority': 'normal', 'owner': self.olga.pk,
        })
        self.assertEqual(Task.objects.get(title='Новая').owner, self.dmitry)

    def test_foreign_task_is_404(self):
        """Обязательный: чужую задачу нельзя открыть, изменить, удалить и переключить."""
        cases = [
            ('get', self.link('detail', self.foreign.pk)),
            ('get', self.link('edit', self.foreign.pk)),
            ('post', self.link('edit', self.foreign.pk)),
            ('get', self.link('delete', self.foreign.pk)),
            ('post', self.link('delete', self.foreign.pk)),
            ('post', self.link('toggle', self.foreign.pk)),
        ]
        for method, url in cases:
            with self.subTest(url=url, method=method):
                response = getattr(self.client, method)(url, {'title': 'взлом', 'priority': 'low'})
                self.assertEqual(response.status_code, 404)

        self.foreign.refresh_from_db()
        self.assertEqual(self.foreign.title, 'Задача Ольги')
        self.assertFalse(self.foreign.completed)

    def test_missing_id_is_404(self):
        """Обязательный: несуществующий идентификатор даёт 404, а не 500."""
        for name in ('detail', 'edit', 'delete'):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(self.link(name, 99999)).status_code, 404)
        self.assertEqual(self.client.post(self.link('toggle', 99999)).status_code, 404)

    def test_foreign_category_cannot_be_used(self):
        foreign_category = Category.objects.create(owner=self.olga, name='Работа')
        self.client.post(self.link('new'), {
            'title': 'С чужой категорией', 'priority': 'normal', 'category': foreign_category.pk,
        })
        self.assertFalse(Task.objects.filter(title='С чужой категорией').exists())


class ActionTests(PlannerTestCase):
    def setUp(self):
        self.client.force_login(self.dmitry)

    def test_toggle_marks_done_and_back(self):
        """Обязательный: состояние переключается в обе стороны."""
        self.client.post(self.link('toggle', self.task.pk))
        self.task.refresh_from_db()
        self.assertTrue(self.task.completed)
        self.assertIsNotNone(self.task.completed_at)

        self.client.post(self.link('toggle', self.task.pk))
        self.task.refresh_from_db()
        self.assertFalse(self.task.completed)
        self.assertIsNone(self.task.completed_at)

    def test_toggle_by_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.link('toggle', self.task.pk)).status_code, 405)
        self.task.refresh_from_db()
        self.assertFalse(self.task.completed)

    def test_toggle_ignores_outside_next(self):
        response = self.client.post(self.link('toggle', self.task.pk), {'next': 'https://evil.example/'})
        self.assertRedirects(response, self.link('list'))

    def test_delete_by_get_only_asks(self):
        """Обязательный: удаление запросом GET не выполняется."""
        response = self.client.get(self.link('delete', self.task.pk))
        self.assertContains(response, 'Да, удалить')
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

    def test_delete_by_post_removes_task(self):
        self.client.post(self.link('delete', self.task.pk))
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())

    def test_edit_saves_due_date_and_priority(self):
        self.client.post(self.link('edit', self.task.pk), {
            'title': 'Задача Дмитрия', 'priority': 'high', 'due_date': '2030-05-01T10:30',
        })
        self.task.refresh_from_db()
        self.assertEqual(self.task.priority, 'high')
        self.assertEqual(timezone.localtime(self.task.due_date).strftime('%d.%m.%Y %H:%M'), '01.05.2030 10:30')

    def test_wrong_due_date_shows_form_error(self):
        response = self.client.post(self.link('new'), {
            'title': 'Кривая дата', 'priority': 'normal', 'due_date': '31-31-2030',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('due_date', response.context['form'].errors)
        self.assertFalse(Task.objects.filter(title='Кривая дата').exists())

    def test_empty_title_shows_form_error(self):
        response = self.client.post(self.link('new'), {'title': '', 'priority': 'normal'})
        self.assertIn('title', response.context['form'].errors)


class ListLogicTests(PlannerTestCase):
    def setUp(self):
        self.client.force_login(self.olga)
        Task.objects.owned_by(self.olga).delete()
        now = timezone.now()
        self.study = Category.objects.create(owner=self.olga, name='Учёба')
        self.done = self.add('Выполненная высокая', priority='high', completed=True)
        self.low_soon = self.add('Низкая скоро', priority='low', due_date=now + timedelta(hours=3))
        self.high_no_due = self.add('Высокая без срока', priority='high')
        self.high_late = self.add('Высокая поздняя', priority='high', due_date=now + timedelta(days=8))
        self.high_soon = self.add('Высокая ранняя', priority='high', due_date=now + timedelta(days=1),
                                  category=self.study)
        self.overdue = self.add('Просроченная', priority='normal', due_date=now - timedelta(days=2))

    def add(self, title, **fields):
        return Task.objects.create(owner=self.olga, title=title, **fields)

    def titles(self, **params):
        response = self.client.get(reverse('tasks:list'), params)
        return [task.title for task in response.context['tasks']]

    def test_order_matches_the_rules(self):
        self.assertEqual(self.titles(tab='all'), [
            'Высокая ранняя', 'Высокая поздняя', 'Высокая без срока',
            'Просроченная', 'Низкая скоро', 'Выполненная высокая',
        ])

    def test_tabs(self):
        self.assertEqual(self.titles(tab='overdue'), ['Просроченная'])
        self.assertEqual(self.titles(tab='done'), ['Выполненная высокая'])
        self.assertEqual(len(self.titles(tab='open')), 5)
        self.assertEqual(len(self.titles(tab='непонятно')), 5)

    def test_search_works_with_russian_case(self):
        self.assertEqual(self.titles(tab='all', q='ПРОСРОЧ'), ['Просроченная'])

    def test_filter_by_category(self):
        self.assertEqual(self.titles(tab='all', category=str(self.study.pk)), ['Высокая ранняя'])
        self.assertEqual(len(self.titles(tab='all', category='none')), 5)

    def test_states(self):
        self.assertEqual(self.overdue.state, 'overdue')
        self.assertEqual(self.low_soon.state, 'soon')
        self.assertEqual(self.high_no_due.state, 'open')
        self.assertEqual(self.done.state, 'done')

    def test_overdue_is_visible_in_list(self):
        response = self.client.get(reverse('tasks:list'), {'tab': 'all'})
        self.assertContains(response, 'просрочена')
        self.assertContains(response, 'скоро срок')

    def test_pagination(self):
        for number in range(12):
            self.add(f'Ещё задача {number}')
        response = self.client.get(reverse('tasks:list'), {'tab': 'all', 'page': 2})
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertEqual(len(response.context['tasks']), 8)


class CategoryTests(PlannerTestCase):
    def setUp(self):
        self.client.force_login(self.dmitry)

    def test_create_category(self):
        self.client.post(self.link('categories'), {'name': 'Дом'})
        self.assertTrue(Category.objects.filter(owner=self.dmitry, name='Дом').exists())

    def test_duplicate_category_is_rejected(self):
        Category.objects.create(owner=self.dmitry, name='Дом')
        response = self.client.post(self.link('categories'), {'name': 'дом'})
        self.assertIn('name', response.context['form'].errors)
        self.assertEqual(Category.objects.filter(owner=self.dmitry).count(), 1)

    def test_delete_category_keeps_tasks(self):
        category = Category.objects.create(owner=self.dmitry, name='Дом')
        self.task.category = category
        self.task.save()
        self.client.post(self.link('category_delete', category.pk))
        self.task.refresh_from_db()
        self.assertIsNone(self.task.category)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

    def test_foreign_category_cannot_be_deleted(self):
        foreign = Category.objects.create(owner=self.olga, name='Работа')
        self.assertEqual(self.client.post(self.link('category_delete', foreign.pk)).status_code, 404)
        self.assertTrue(Category.objects.filter(pk=foreign.pk).exists())


class ModelTests(TestCase):
    def test_defaults(self):
        user = User.objects.create_user('someone')
        task = Task.objects.create(owner=user, title='Купить хлеб')
        self.assertEqual(str(task), 'Купить хлеб')
        self.assertEqual(task.priority, Task.Priority.NORMAL)
        self.assertFalse(task.completed)
        self.assertIsNone(task.completed_at)
