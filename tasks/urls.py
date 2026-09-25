"""Схемы URL приложения tasks."""
from django.urls import path

from . import views

app_name = 'tasks'

urlpatterns = [
    path('', views.HomeView.as_view(), name='index'),
    path('tasks/', views.TaskListView.as_view(), name='list'),
    path('tasks/new/', views.TaskCreateView.as_view(), name='new'),
    path('tasks/<int:pk>/', views.TaskDetailView.as_view(), name='detail'),
    path('tasks/<int:pk>/edit/', views.TaskUpdateView.as_view(), name='edit'),
    path('tasks/<int:pk>/delete/', views.TaskDeleteView.as_view(), name='delete'),
    path('tasks/<int:pk>/toggle/', views.TaskToggleView.as_view(), name='toggle'),
    path('categories/', views.CategoryListView.as_view(), name='categories'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
]
