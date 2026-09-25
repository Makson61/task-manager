from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):
    """Регистрация: имя пользователя, необязательная почта и пароль."""

    email = forms.EmailField(
        label='Электронная почта', required=False,
        help_text='Необязательно. Понадобится, если захотите восстановить доступ.',
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')
        labels = {'username': 'Имя пользователя'}
        help_texts = {'username': 'Латинские буквы, цифры и символы @/./+/-/_ - до 150 знаков.'}

    def clean_email(self):
        """Одна почта - один аккаунт (пустое поле не проверяется)."""
        email = self.cleaned_data.get('email', '').strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Пользователь с такой почтой уже зарегистрирован.')
        return email


class SignInForm(AuthenticationForm):
    """Форма входа с русскими подписями."""

    username = forms.CharField(label='Имя пользователя')
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Неверное имя пользователя или пароль.',
    }
