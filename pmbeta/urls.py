"""
PMBeta URL Configuration
Location-based web game URLs
"""
from django.contrib import admin
from django.urls import path, include
from main import views  # Import for PK API endpoints
from main import views_resources  # Import for resource endpoints

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls_rpg')),  # Use new RPG system as default
    path('legacy/', include('main.urls')),  # Keep old system for reference
    path('', include('main.urls_crafting')),  # Crafting system endpoints
    path('', include('main.flag_urls')),  # PK-style territory flag system
    
    # PK Movement and Resource API (temporary - until PK models are fixed)
    path('api/player/move/', views.api_player_move, name='api_player_move_root'),
    path('api/resources/nearby/', views_resources.nearby_resources, name='api_nearby_resources_root'),
    path('api/resources/collect/<uuid:resource_id>/', views.api_collect_resource, name='api_collect_resource_root'),
    path('api/resources/check-spawn/', views.api_check_resource_spawn, name='api_check_resource_spawn_root'),
    
    # path('pk/', include('main.pk_urls')),  # Disabled - missing PK models
]
