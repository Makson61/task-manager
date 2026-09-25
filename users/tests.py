"""Тесты регистрации, входа, выхода, профиля и служебных команд."""
import os
from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse


class SignUpTests(TestCase):
    def test_new_user_is_created_and_logged_in(self):
        response = self.client.post(reverse('users:register'), {
            'username': 'newbie', 'email': 'newbie@example.com',
            'password1': 'Kofe-Chai-9731', 'password2': 'Kofe-Chai-9731',
        }, follow=True)
        self.assertEqual(response.context['user'].username, 'newbie')
        self.assertEqual(User.objects.get(username='newbie').email, 'newbie@example.com')

    def test_email_is_optional(self):
        self.client.post(reverse('users:register'), {
            'username': 'noemail', 'password1': 'Kofe-Chai-9731', 'password2': 'Kofe-Chai-9731',
        })
        self.assertEqual(User.objects.get(username='noemail').email, '')

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user('first', email='taken@example.com')
        response = self.client.post(reverse('users:register'), {
            'username': 'second', 'email': 'TAKEN@example.com',
            'password1': 'Kofe-Chai-9731', 'password2': 'Kofe-Chai-9731',
        })
        self.assertIn('email', response.context['form'].errors)
        self.assertFalse(User.objects.filter(username='second').exists())

    def test_mismatched_passwords_show_error(self):
        response = self.client.post(reverse('users:register'), {
            'username': 'newbie', 'password1': 'Kofe-Chai-9731', 'password2': 'other-pass-3197',
        })
        self.assertTrue(response.context['form'].errors)
        self.assertFalse(User.objects.filter(username='newbie').exists())

    def test_logged_in_user_is_redirected_away(self):
        self.client.force_login(User.objects.create_user('someone'))
        self.assertEqual(self.client.get(reverse('users:register')).status_code, 302)


class SignInOutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('dmitry', password='pass-12345')

    def test_login_follows_next(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'dmitry', 'password': 'pass-12345', 'next': '/tasks/',
        })
        self.assertRedirects(response, '/tasks/')

    def test_login_ignores_outside_next(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'dmitry', 'password': 'pass-12345', 'next': 'https://evil.example/',
        })
        self.assertNotIn('evil', response['Location'])

    def test_wrong_password_shows_error(self):
        response = self.client.post(reverse('users:login'), {'username': 'dmitry', 'password': 'nope'})
        self.assertContains(response, 'Неверное имя пользователя или пароль.')

    def test_logout_by_get_is_not_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('users:logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_logout_by_post_ends_session(self):
        self.client.force_login(self.user)
        self.client.post(reverse('users:logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse('users:logout')).status_code, 403)

    def test_profile_requires_login(self):
        url = reverse('users:profile')
        self.assertRedirects(self.client.get(url), f"{reverse('users:login')}?next={url}")
        self.client.force_login(self.user)
        self.assertContains(self.client.get(url), 'dmitry')


class CommandTests(TestCase):
    def test_ensure_admin_creates_and_updates(self):
        env = {'DJANGO_SUPERUSER_USERNAME': 'boss', 'DJANGO_SUPERUSER_PASSWORD': 'Adm1n-pass!'}
        with mock.patch.dict(os.environ, env):
            call_command('ensure_admin', stdout=StringIO())
            call_command('ensure_admin', stdout=StringIO())
        boss = User.objects.get(username='boss')
        self.assertTrue(boss.is_superuser and boss.is_staff)
        self.assertTrue(boss.check_password('Adm1n-pass!'))

    def test_ensure_admin_without_variables_does_nothing(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            call_command('ensure_admin', stdout=StringIO())
        self.assertFalse(User.objects.exists())

    def test_demo_data_is_safe_to_repeat(self):
        with mock.patch.dict(os.environ, {'DEMO_PASSWORD': 'Demo-pass-1'}):
            call_command('demo_data', stdout=StringIO())
            call_command('demo_data', stdout=StringIO())
        self.assertEqual(User.objects.filter(username__in=['dmitry', 'olga']).count(), 2)
        self.assertTrue(self.client.login(username='olga', password='Demo-pass-1'))

    def test_prestart_does_everything_at_once(self):
        env = {'DJANGO_SUPERUSER_USERNAME': 'boss', 'DJANGO_SUPERUSER_PASSWORD': 'Adm1n-pass!',
               'DEMO_DATA': 'True', 'DEMO_PASSWORD': 'Demo-pass-1'}
        with mock.patch.dict(os.environ, env):
            call_command('prestart', stdout=StringIO())
        self.assertTrue(User.objects.get(username='boss').is_superuser)
        self.assertTrue(User.objects.filter(username='dmitry').exists())
