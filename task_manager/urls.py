"""Корневые маршруты проекта «Планировщик»."""
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

admin.site.site_header = 'Планировщик задач: администрирование'
admin.site.site_title = 'Планировщик задач'
admin.site.index_title = 'Данные сайта'


def healthz(_request):
    """Проверка живости для Docker и хостинга: не трогает базу данных."""
    return HttpResponse('ok', content_type='text/plain')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('healthz/', healthz, name='healthz'),
    path('', include('tasks.urls')),
]
