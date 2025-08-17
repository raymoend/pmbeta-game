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
    
    # Main game views
    path('', views_rpg.index, name='index'),
    path('character-creation/', views_rpg.character_creation, name='character_creation'),
    path('game/', views_rpg.rpg_game, name='rpg_game'),
    
    
    # Authentication (keeping existing auth system)
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', CreateView.as_view(
        form_class=UserCreationForm,
        template_name='registration/register.html',
        success_url=reverse_lazy('character_creation')
    ), name='register'),
    
    # Character API endpoints
    path('api/rpg/character/status/', views_rpg.api_character_status, name='api_character_status'),
    path('api/rpg/nearby-players/', views_rpg.api_nearby_players, name='api_nearby_players'),
    path('api/rpg/nearby-monsters/', views_rpg.api_nearby_monsters, name='api_nearby_monsters'),
    
    # Combat API endpoints
    path('api/rpg/combat/pve/start/', views_rpg.api_pve_combat_start, name='api_pve_combat_start'),
    path('api/rpg/combat/action/', views_rpg.api_combat_action, name='api_combat_action'),
    
    # PvP API endpoints
    path('api/rpg/pvp/challenge/', views_rpg.api_pvp_challenge, name='api_pvp_challenge'),
    
    # Inventory API endpoints
    path('api/rpg/inventory/', views_rpg.api_inventory, name='api_inventory'),
    
    # Trading API endpoints
    path('api/rpg/trade/create/', views_rpg.api_trade_create, name='api_trade_create'),
]
