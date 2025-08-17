"""
PMBeta URL Configuration
Location-based web game URLs
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),  # Use full Mapbox system as default
    path('pk/', include('main.pk_urls')),  # Keep PK system for reference
]
