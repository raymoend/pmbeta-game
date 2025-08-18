"""
URL patterns for Parallel Kingdom style territory flag system
"""
from django.urls import path
from . import flag_views

urlpatterns = [
    # Flag placement and management
    path('api/flags/colors/', flag_views.api_flag_colors, name='api_flag_colors'),
    path('api/flags/can-place/', flag_views.api_can_place_flag, name='api_can_place_flag'),
    path('api/flags/place/', flag_views.api_place_flag, name='api_place_flag'),
    path('api/flags/nearby/', flag_views.api_nearby_flags, name='api_nearby_flags'),
    
    # Flag operations
    path('api/flags/<uuid:flag_id>/collect-revenue/', flag_views.api_collect_flag_revenue, name='api_collect_flag_revenue'),
    path('api/flags/<uuid:flag_id>/pay-upkeep/', flag_views.api_pay_flag_upkeep, name='api_pay_flag_upkeep'),
    path('api/flags/<uuid:flag_id>/upgrade/', flag_views.api_upgrade_flag, name='api_upgrade_flag'),
    path('api/flags/<uuid:flag_id>/repair/', flag_views.api_repair_flag, name='api_repair_flag'),
    
    # PvP flag combat
    path('api/flags/<uuid:flag_id>/attack/', flag_views.api_attack_flag, name='api_attack_flag'),
    path('api/flags/<uuid:flag_id>/capture/', flag_views.api_capture_flag, name='api_capture_flag'),
    
    # Map data
    path('api/flags/territories/geojson/', flag_views.api_flag_territories_geojson, name='api_flag_territories_geojson'),
]
