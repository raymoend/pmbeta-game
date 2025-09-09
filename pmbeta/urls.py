"""
PMBeta URL Configuration
Location-based web game URLs
"""
import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.http import JsonResponse
from django.contrib.auth import views as auth_views
from main import views  # Import for PK API endpoints
from main import views_resources  # Import for resource endpoints
from main import views_rpg
from django.views.generic import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage

# Simple healthcheck for Railway and production load balancers
def health(request):
    return JsonResponse({"status": "ok"}, status=200)

# Runtime debug endpoint: shows active settings and URL resolving state
# NOTE: Keep minimal and non-sensitive
from django.conf import settings
from django.urls import resolve, Resolver404

def runtime_debug(request):
    info = {
        "DJANGO_SETTINGS_MODULE": os.environ.get("DJANGO_SETTINGS_MODULE"),
        "ROOT_URLCONF": getattr(settings, "ROOT_URLCONF", None),
        "DEBUG": getattr(settings, "DEBUG", None),
        "ALLOWED_HOSTS": getattr(settings, "ALLOWED_HOSTS", []),
        "ASGI_APPLICATION": getattr(settings, "ASGI_APPLICATION", None),
        "WSGI_APPLICATION": getattr(settings, "WSGI_APPLICATION", None),
    }
    # Check resolving of common health routes
    checks = {}
    for p in ["/health/", "/health", "/healthz/", "/healthz", "/readyz/", "/readyz", "/livez/", "/livez"]:
        try:
            r = resolve(p)
            checks[p] = str(r)
        except Resolver404:
            checks[p] = "Resolver404"
        except Exception as e:
            checks[p] = f"error: {type(e).__name__}: {e}"
    info["resolve_checks"] = checks
    return JsonResponse(info, status=200)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Healthchecks (robust: accept with and without trailing slash)
    path('health/', health, name='health'),
    path('healthz/', health, name='healthz_root'),
    path('livez/', health, name='livez'),
    path('readyz/', health, name='readyz'),
    re_path(r'^(?:health|healthz|livez|readyz)/?$', health),
    path('debug/runtime/', runtime_debug, name='runtime_debug'),

    # Favicon at root path
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.svg'), permanent=True)),

    # Auth (logout via simple view allowing GET/POST for dev convenience)
    path('logout/', views_rpg.logout_view, name='logout'),

    # Game routes
    path('', include('main.urls_rpg')),  # Use new RPG system as default
    path('legacy/', include('main.urls')),  # Keep old system for reference
    path('', include('main.urls_crafting')),  # Crafting system endpoints

    # Flag API
    path('api/', include('main.flag_urls')),

    # Convenience alias for legacy stats endpoint at root
    path('api/stats/', views.api_game_stats, name='api_game_stats_root'),
    
    # PK Movement and Resource API (temporary - until PK models are fixed)
    path('api/player/move/', views.api_player_move, name='api_player_move_root'),
    path('api/resources/nearby/', views_resources.nearby_resources, name='api_nearby_resources_root'),
    path('api/resources/harvest/', views_resources.harvest_resource, name='api_harvest_resource_root'),
    path('api/resources/info/<uuid:resource_id>/', views_resources.resource_info, name='api_resource_info_root'),
    path('api/resources/collect/<uuid:resource_id>/', views.api_collect_resource, name='api_collect_resource_root'),
    path('api/resources/check-spawn/', views.api_check_resource_spawn, name='api_check_resource_spawn_root'),
    # Root alias for inventory berries (to avoid 404 then fallback)
    path('api/inventory/berries/', views_resources.use_berries, name='api_use_berries_root'),
    path('api/inventory/berries/tick/', views_resources.berries_tick, name='api_berries_tick_root'),
    # Generic consumable use alias for RPG UI
    path('api/inventory/use/', views_resources.use_item, name='api_use_item_root'),
    
    # path('pk/', include('main.pk_urls')),  # Disabled - missing PK models
]
