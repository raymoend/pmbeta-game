"""
Legacy URL patterns for main app
The main RPG system URLs are in urls_rpg.py
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import views_resources

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
    
    # Health check for debugging
    path('health/', views.health_check, name='health_check'),
    
    # Crafting interface
    path('crafting/', views.crafting, name='crafting'),
    
    # Resource Collection API
    path('api/resources/nearby/', views_resources.nearby_resources, name='api_nearby_resources'),
    path('api/resources/harvest/', views_resources.harvest_resource, name='api_harvest_resource'),
    path('api/resources/info/<uuid:resource_id>/', views_resources.resource_info, name='api_resource_info'),
    path('api/inventory/', views_resources.character_inventory, name='api_character_inventory'),
    path('api/inventory/use/', views_resources.use_item, name='api_use_item'),
    path('api/inventory/berries/', views_resources.use_berries, name='api_use_berries'),
    path('api/harvest-history/', views_resources.harvest_history, name='api_harvest_history'),
    
    # PK Movement API (temporary - until PK models are fixed)
    path('api/player/move/', views.api_player_move, name='api_player_move'),
    path('api/resources/collect/<uuid:resource_id>/', views.api_collect_resource, name='api_collect_resource'),
    path('api/resources/check-spawn/', views.api_check_resource_spawn, name='api_check_resource_spawn'),
]
