"""Вход, выход, регистрация, профиль и смена пароля.

Все страницы - классовые представления Django, поэтому логика входа,
проверки формы и перенаправлений не дублируется вручную.
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, resolve_url
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from .forms import SignInForm, SignUpForm


class SignInView(auth_views.LoginView):
    """Вход. Уже вошедшего пользователя сразу отправляем на рабочую страницу."""

    form_class = SignInForm
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'С возвращением, {form.get_user().username}!')
        return response


class SignOutView(auth_views.LogoutView):
    """Выход. LogoutView в Django 5 принимает только POST, GET получает 405."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.info(request, 'Вы вышли из аккаунта.')
        return response


class SignUpView(CreateView):
    """Регистрация с автоматическим входом сразу после создания аккаунта."""

    form_class = SignUpForm
    template_name = 'users/register.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        login(self.request, self.object)
        messages.success(self.request, f'Аккаунт создан. Добро пожаловать, {self.object.username}!')
        return redirect(self.get_success_url())

    def get_success_url(self):
        # LOGIN_REDIRECT_URL задан именем маршрута, поэтому его нужно развернуть
        # в настоящий адрес: в заголовок Location имя класть нельзя.
        return resolve_url(settings.LOGIN_REDIRECT_URL)


class ProfileView(LoginRequiredMixin, TemplateView):
    """Страница аккаунта: имя, почта, дата регистрации."""

    template_name = 'users/profile.html'


class PasswordView(LoginRequiredMixin, auth_views.PasswordChangeView):
    template_name = 'registration/password_change_form.html'
    success_url = reverse_lazy('users:profile')

    def form_valid(self, form):
        messages.success(self.request, 'Пароль изменён.')
        return super().form_valid(form)
