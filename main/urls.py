"""
Legacy URL patterns for main app
The main RPG system URLs are in urls_rpg.py
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Main pages
    path('', views.index, name='legacy_index'),
    path('game/', views.game, name='legacy_game'),
    
    # Authentication
    path('register/', views.register, name='legacy_register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='legacy_login'),
    path('logout/', auth_views.LogoutView.as_view(), name='legacy_logout'),
    
    # API endpoints that exist
    path('api/stats/', views.api_game_stats, name='api_game_stats'),
]
