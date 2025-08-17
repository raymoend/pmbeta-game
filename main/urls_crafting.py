"""
URL patterns for crafting system API endpoints and pages
"""
from django.urls import path
from . import views_crafting, views

urlpatterns = [
    # Crafting Page
    path('crafting/', views.crafting, name='crafting'),
    
    # Crafting System API Endpoints
    path('api/crafting/recipes/', views_crafting.available_recipes, name='api_available_recipes'),
    path('api/crafting/start/', views_crafting.start_crafting, name='api_start_crafting'),
    path('api/crafting/history/', views_crafting.crafting_history, name='api_crafting_history'),
    path('api/crafting/recipe/<uuid:recipe_id>/', views_crafting.recipe_details, name='api_recipe_details'),
    path('api/crafting/stats/', views_crafting.crafting_stats, name='api_crafting_stats'),
]
