"""
PMBeta URL Configuration
Location-based web game URLs
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls_rpg')),  # Use new RPG system as default
    path('legacy/', include('main.urls')),  # Keep old system for reference
    path('', include('main.urls_crafting')),  # Crafting system endpoints
    # path('pk/', include('main.pk_urls')),  # Disabled - will implement later
]
