"""
Настройки проекта «Планировщик».

Значения, различающиеся на компьютере разработчика и на сервере, приходят
из переменных окружения (см. .env.example и README.md). Разбор переменных -
в соседнем модуле env.py.
"""
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from . import env

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Основное ---------------------------------------------------------------

SECRET_KEY = env.text('DJANGO_SECRET_KEY', 'django-insecure-local-development-only')
DEBUG = env.flag('DJANGO_DEBUG', True)

if not DEBUG and SECRET_KEY.startswith('django-insecure'):
    raise ImproperlyConfigured('Задайте собственный DJANGO_SECRET_KEY перед запуском с DEBUG=False.')

ALLOWED_HOSTS = env.items('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env.items('DJANGO_CSRF_TRUSTED_ORIGINS')

# Хостинг сообщает внешнее имя сервиса сам - добавляем его в списки.
EXTERNAL_HOSTNAME = env.text('RENDER_EXTERNAL_HOSTNAME')
if EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS += [EXTERNAL_HOSTNAME]
    CSRF_TRUSTED_ORIGINS += ['https://' + EXTERNAL_HOSTNAME]

ROOT_URLCONF = 'task_manager.urls'
WSGI_APPLICATION = 'task_manager.wsgi.application'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Приложения и middleware ------------------------------------------------

INSTALLED_APPS = [
    # Мои приложения
    'tasks',
    'users',

    # Сторонние приложения
    'bootstrap4',

    # Приложения Django по умолчанию
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise отдаёт собранные статические файлы без отдельного веб-сервера.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# --- База данных ------------------------------------------------------------
# По умолчанию SQLite. Если задан DATABASE_URL, берётся он: так подключается
# внешний PostgreSQL, и данные переживают перезапуск контейнера.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': env.text('SQLITE_PATH') or BASE_DIR / 'db.sqlite3',
    },
}

if env.text('DATABASE_URL'):
    DATABASES['default'] = dj_database_url.config(conn_max_age=0, conn_health_checks=True)
    # Пулер соединений не поддерживает серверные курсоры.
    DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True

# --- Пользователи -----------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'tasks:list'
LOGOUT_REDIRECT_URL = 'tasks:index'

# --- Язык, время, статика ---------------------------------------------------

LANGUAGE_CODE = 'ru'
TIME_ZONE = env.text('DJANGO_TIME_ZONE', 'Europe/Moscow')
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage' if DEBUG
            else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),
    },
}

# --- Безопасность -----------------------------------------------------------
# HTTPS завершается на обратном прокси, он передаёт заголовок X-Forwarded-Proto.

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = env.flag('DJANGO_SECURE_SSL_REDIRECT', False)
SECURE_REDIRECT_EXEMPT = [r'^healthz/$']
SECURE_HSTS_SECONDS = env.number('DJANGO_HSTS_SECONDS', 0)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = not DEBUG
X_FRAME_OPTIONS = 'DENY'

# --- Журнал ошибок ----------------------------------------------------------
# Ошибки видны в выводе контейнера (docker compose logs).

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}
