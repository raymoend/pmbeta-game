"""
URL patterns for main app
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('game/', views.game, name='game'),
    path('profile/', views.player_profile, name='profile'),
    
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # API endpoints
    path('api/world/', views.api_world_data, name='api_world_data'),
    path('api/move/', views.api_move_player, name='api_move_player'),
    path('api/stats/', views.api_game_stats, name='api_game_stats'),
    
    # Flag system API endpoints
    path('api/flags/', views.api_get_flags, name='api_get_flags'),
    path('api/flags/place/', views.api_place_flag, name='api_place_flag'),
    path('api/flags/attack/', views.api_attack_flag, name='api_attack_flag'),
    
    # NPC system API endpoints
    path('api/npcs/', views.api_get_npcs, name='api_get_npcs'),
    path('api/npcs/attack/', views.api_attack_npc, name='api_attack_npc'),
    
    # Resource system API endpoints
    path('api/resources/', views.api_get_resources, name='api_get_resources'),
    path('api/resources/harvest/', views.api_harvest_resource, name='api_harvest_resource'),
    
    # PK Echoes compatible endpoints
    path('api/mapdata/', views.api_map_data, name='api_map_data'),
    path('api/nearbyplayers/', views.api_nearby_players, name='api_nearby_players'),
    path('api/territories/', views.api_territories, name='api_territories'),
    
    # Admin/debugging
    path('api/spawn-structures/', views.api_spawn_structures, name='api_spawn_structures'),
    path('debug/player/', views.debug_player, name='debug_player'),
    path('debug/login/', views.debug_login_status, name='debug_login_status'),
    path('debug/autologin/', views.debug_auto_login, name='debug_auto_login'),
]
