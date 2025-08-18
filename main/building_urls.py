"""
URL patterns for building system
"""
from django.urls import path
from . import building_views

urlpatterns = [
    # Building API endpoints
    path('api/building-types/', building_views.api_building_types, name='api_building_types'),
    path('api/flag-colors/', building_views.api_flag_colors, name='api_flag_colors'),
    path('api/place-building/', building_views.api_place_building, name='api_place_building'),
    path('api/nearby-buildings/', building_views.api_nearby_buildings, name='api_nearby_buildings'),
    path('api/collect-revenue/<uuid:building_id>/', building_views.api_collect_revenue, name='api_collect_revenue'),
]
