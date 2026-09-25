"""Маршруты приложения users."""
from django.urls import path

from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.SignInView.as_view(), name='login'),
    path('logout/', views.SignOutView.as_view(), name='logout'),
    path('register/', views.SignUpView.as_view(), name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/password/', views.PasswordView.as_view(), name='password_change'),
]
