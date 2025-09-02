"""
URL patterns for RPG game system
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import UserCreationForm
from django.views.generic import CreateView
from django.urls import reverse_lazy
from . import views_rpg

urlpatterns = [
    # Debug endpoint (temporary)
    path('debug/500/', views_rpg.debug_500_error, name='debug_500'),
    # Health endpoints (fallback for platforms expecting /health/ or /healthz/)
    path('health/', views_rpg.health, name='health_fallback'),
    path('healthz/', views_rpg.health, name='healthz'),
    
    # Main game views
    path('', views_rpg.index, name='index'),
    path('character-creation/', views_rpg.character_creation, name='character_creation'),
    path('game/', views_rpg.rpg_game, name='rpg_game'),
    path('buildings/', views_rpg.building_game, name='building_game'),
    path('building-test/', views_rpg.building_test, name='building_test'),
    # Territory system removed
    path('pk/', views_rpg.pk_game, name='pk_game'),
    
    
    # Authentication (keeping existing auth system)
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views_rpg.register, name='register'),
    
    # Character API endpoints
    path('api/rpg/character/status/', views_rpg.api_character_status, name='api_character_status'),
    path('api/rpg/character/relocate/', views_rpg.api_character_relocate, name='api_character_relocate'),
    path('api/rpg/character/respawn/', views_rpg.api_character_respawn, name='api_character_respawn'),
    path('api/rpg/nearby-players/', views_rpg.api_nearby_players, name='api_nearby_players'),
    path('api/rpg/nearby-monsters/', views_rpg.api_nearby_monsters, name='api_nearby_monsters'),
    
    # Availability checks
    path('api/rpg/availability/username/', views_rpg.api_username_available, name='api_username_available'),
    path('api/rpg/availability/character/', views_rpg.api_character_name_available, name='api_character_name_available'),
    
    # Combat API endpoints
    path('api/rpg/combat/pve/start/', views_rpg.api_pve_combat_start, name='api_pve_combat_start'),
    path('api/rpg/combat/action/', views_rpg.api_combat_action, name='api_combat_action'),
    path('api/rpg/combat/heal/', views_rpg.api_combat_heal, name='api_combat_heal'),
    path('api/rpg/combat/state/', views_rpg.api_combat_state, name='api_combat_state'),
    path('api/rpg/character/jump/', views_rpg.api_character_jump, name='api_character_jump'),
    
    # PvP API endpoints
    path('api/rpg/pvp/challenge/', views_rpg.api_pvp_challenge, name='api_pvp_challenge'),
    
    # Inventory API endpoints
    path('api/rpg/inventory/', views_rpg.api_inventory, name='api_inventory'),
    path('api/rpg/inventory/sell/', views_rpg.api_inventory_sell, name='api_inventory_sell'),
    path('api/rpg/inventory/equip/', views_rpg.api_inventory_equip, name='api_inventory_equip'),
    path('api/rpg/inventory/unequip/', views_rpg.api_inventory_unequip, name='api_inventory_unequip'),
    path('api/rpg/character/allocate/', views_rpg.api_allocate_stats, name='api_allocate_stats'),
    
    # Trading API endpoints
    path('api/rpg/trade/create/', views_rpg.api_trade_create, name='api_trade_create'),

    # Notifications (GameEvent) API
    path('api/rpg/events/', views_rpg.api_events_list, name='api_events_list'),
    path('api/rpg/events/mark-read/', views_rpg.api_events_mark_read, name='api_events_mark_read'),
    path('api/rpg/events/mark-all-read/', views_rpg.api_events_mark_all_read, name='api_events_mark_all_read'),

    # Flag/NPC endpoints (FlagRun deprecated)
    path('api/rpg/flag/npcs/<uuid:flag_id>/', views_rpg.api_flag_npcs, name='api_flag_npcs'),

    # Deprecated FlagRun endpoints (return 410 Gone)
    path('api/rpg/flag-run/start/', views_rpg.api_flag_run_start, name='api_flag_run_start'),
    path('api/rpg/flag-run/status/<uuid:run_id>/', views_rpg.api_flag_run_status, name='api_flag_run_status'),
    path('api/rpg/flag-run/abort/<uuid:run_id>/', views_rpg.api_flag_run_abort, name='api_flag_run_abort'),
    
    # Character movement endpoint
    path('api/rpg/character/move/', views_rpg.api_character_move, name='api_character_move'),
]

# Import building URLs
from . import building_views

# Add building API endpoints
building_patterns = [
    path('api/building-types/', building_views.api_building_types, name='api_building_types'),
    path('api/flag-colors/', building_views.api_flag_colors, name='api_flag_colors'),
    path('api/place-building/', building_views.api_place_building, name='api_place_building'),
    path('api/nearby-buildings/', building_views.api_nearby_buildings, name='api_nearby_buildings'),
    path('api/collect-revenue/<uuid:building_id>/', building_views.api_collect_revenue, name='api_collect_revenue'),
]

# Combine URL patterns
urlpatterns += building_patterns
