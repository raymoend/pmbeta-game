"""
PMBeta - Parallel Kingdom URL Configuration
Routes for authentic PK gameplay experience
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import pk_views

# PK-specific URL patterns
pk_patterns = [
    # Core game views
    path('', pk_views.index, name='pk_index'),
    path('register/', pk_views.register, name='pk_register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html', success_url='/game/'), name='pk_login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='pk_logout'),
    path('game/', pk_views.pk_game, name='pk_game'),
    
    # Player API endpoints
    path('api/player/status/', pk_views.api_player_status, name='pk_api_player_status'),
    path('api/player/move/', pk_views.api_player_move, name='pk_api_player_move'),
    
    # Map and world data
    path('api/map/data/', pk_views.api_map_data, name='pk_api_map_data'),
    
    # Resource gathering
    path('api/resource/harvest/', pk_views.api_harvest_resource, name='pk_api_harvest_resource'),
    path('api/resources/nearby/', pk_views.api_resources_nearby, name='pk_api_resources_nearby'),
    path('api/resources/collect/<uuid:resource_id>/', pk_views.api_collect_resource, name='pk_api_collect_resource'),
    path('api/resources/check-spawn/', pk_views.api_check_resource_spawn, name='pk_api_check_resource_spawn'),
    
    # Territory management
    path('api/territory/place/', pk_views.api_place_territory, name='pk_api_place_territory'),
    path('api/territory/collect/', pk_views.api_collect_territory_resources, name='pk_api_collect_territory'),
    
    # Combat system
    path('api/combat/attack/', pk_views.api_attack_player, name='pk_api_attack_player'),
    
    # Trading system
    path('api/trade/create/', pk_views.api_create_trade, name='pk_api_create_trade'),
    
    # Messaging
    path('api/messages/', pk_views.api_get_messages, name='pk_api_get_messages'),
    
    # World generation (admin)
    path('api/admin/spawn/', pk_views.api_spawn_world_content, name='pk_api_spawn_world'),
]

urlpatterns = pk_patterns
