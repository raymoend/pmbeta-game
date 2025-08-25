"""
Legacy views for backward compatibility
The main RPG system views are in views_rpg.py
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from .forms import CustomUserCreationForm
from django.contrib import messages
from django.http import JsonResponse
import json
from django.utils import timezone


def index(request):
    """Homepage - redirect to character creation or game"""
    if not request.user.is_authenticated:
        return render(request, 'main/index.html')
    
    # Redirect to RPG system
    return redirect('index')  # This will be handled by RPG URLs


def register(request):
    """User registration"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            
            # Flag color selection removed
            
            messages.success(request, f'Account created for {username}!')
            
            # Log in the user
            login(request, user)
            return redirect('index')  # Will redirect to RPG character creation
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


@login_required
def game(request):
    """Legacy game view - redirect to RPG game"""
    return redirect('rpg_game')


@login_required
def crafting(request):
    """Crafting workshop interface"""
    # Ensure user has a character
    try:
        character = request.user.character
    except:
        messages.error(request, 'You need to create a character first!')
        return redirect('index')
    
    return render(request, 'crafting.html', {
        'character': character,
        'title': 'Crafting Workshop'
    })


def api_game_stats(request):
    """Public API endpoint for game statistics"""
    return JsonResponse({
        'success': True,
        'stats': {
            'total_players': 0,
            'online_players': 0,
            'message': 'Using new RPG system'
        }
    })


def health_check(request):
    """Health check endpoint for Railway deployment debugging"""
    import sys
    import os
    from django.conf import settings
    from django.db import connections
    
    try:
        # Basic health check info
        health_info = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'django_version': __import__('django').VERSION,
            'python_version': sys.version,
            'settings_module': os.environ.get('DJANGO_SETTINGS_MODULE', 'Not set'),
            'debug': settings.DEBUG,
            'allowed_hosts': settings.ALLOWED_HOSTS,
        }
        
        # Test database connection
        try:
            db_conn = connections['default']
            db_conn.ensure_connection()
            health_info['database'] = 'connected'
            health_info['database_engine'] = settings.DATABASES['default']['ENGINE']
        except Exception as e:
            health_info['database'] = f'error: {str(e)}'
            health_info['status'] = 'unhealthy'
        
        # Check environment variables
        health_info['env_vars'] = {
            'SECRET_KEY': 'SET' if os.environ.get('SECRET_KEY') else 'NOT SET',
            'DATABASE_URL': 'SET' if os.environ.get('DATABASE_URL') else 'NOT SET',
            'RAILWAY_ENVIRONMENT': os.environ.get('RAILWAY_ENVIRONMENT', 'NOT SET'),
            'PORT': os.environ.get('PORT', 'NOT SET'),
        }
        
        return JsonResponse(health_info)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'error_type': type(e).__name__,
        }, status=500)


# ===============================
# PK MOVEMENT API (TEMPORARY)
# ===============================

@login_required
def api_player_move(request):
    """API for player movement with server-authoritative range checks"""
    import json
    from django.views.decorators.csrf import csrf_exempt
    from django.utils.decorators import method_decorator
    from django.views.decorators.http import require_http_methods
    from .models import Character
    # Movement enforcement service
    from .services import movement as movement_svc
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        new_lat = float(data.get('lat'))
        new_lon = float(data.get('lon'))
        
        # Get player's character
        try:
            character = Character.objects.get(user=request.user)
        except Character.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Character not found'
            }, status=404)
        
        # Enforce movement radius from move center (set center on first valid move)
        try:
            movement_svc.ensure_move_allowed(character, new_lat, new_lon)
        except movement_svc.MovementError as me:
            return JsonResponse({'success': False, 'error': me.code, 'message': str(me)}, status=400)
        
        # Calculate distance moved and energy cost
        distance = Character.distance_between(character.lat, character.lon, new_lat, new_lon)
        energy_cost = max(1, int(distance / 100))  # 1 energy per 100m
        
        # Check if character has enough energy/stamina
        if character.current_stamina < energy_cost:
            return JsonResponse({
                'success': False,
                'error': 'not_enough_stamina',
                'message': f'Need {energy_cost} stamina, have {character.current_stamina}'
            }, status=400)
        
        # Update character position and reduce stamina
        old_lat, old_lon = character.lat, character.lon
        character.lat = new_lat
        character.lon = new_lon
        character.current_stamina -= energy_cost
        character.save(update_fields=['lat', 'lon', 'current_stamina', 'updated_at'])
        
        territory_info = {'in_territory': False, 'bonuses': [], 'restrictions': []}
        
        return JsonResponse({
            'success': True,
            'energy_used': energy_cost,
            'remaining_energy': character.current_stamina,
            'new_position': {
                'lat': character.lat,
                'lon': character.lon
            },
            'territory_info': territory_info
        })
        
    except (ValueError, KeyError):
        return JsonResponse({
            'success': False,
            'error': 'invalid_coordinates'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'internal_error',
            'message': str(e)
        }, status=500)


def can_move_to_location(character, lat, lon):
    """Check if character can move to given coordinates - REMOVED flag restrictions"""
    # Territory system removed - allow all movement
    return True, "Movement allowed"


def get_territory_info(character, lat, lon):
    """Get territory influence information - REMOVED"""
    # Territory system removed - return empty data
    return {
        'in_territory': False,
        'owner_name': None,
        'flag_name': None,
        'flag_id': None,
        'is_friendly': False,
        'bonuses': [],
        'restrictions': [],
        'is_contested': False,
        'influence_count': 0,
        'all_influences': []
    }


@login_required 
def api_collect_resource(request, resource_id):
    """Mock API for PK resource collection - returns success for testing"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        # Mock successful resource collection
        return JsonResponse({
            'success': True,
            'items_gained': '5 lumber, 2 stone',
            'yields': {
                'lumber': 5,
                'stone': 2,
                'ore': 0,
                'gold': 1,
                'food': 0
            },
            'energy_used': 2,
            'remaining_energy': 93
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def api_check_resource_spawn(request):
    """Mock API for PK resource spawning - returns empty for testing"""
    try:
        return JsonResponse({
            'success': True,
            'spawned': []  # No new resources spawned for now
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# Flag system views - PR2/PR3 JSON endpoints (place/list/attack/capture)
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .services import flags as flag_svc


@login_required
@csrf_exempt
@require_http_methods(["POST"]) 
def api_flags_place(request):
    try:
        data = json.loads(request.body)
        lat = float(data.get('lat'))
        lon = float(data.get('lon'))
        name = data.get('name')
        flag = flag_svc.place_flag(request.user, lat, lon, name)
        return JsonResponse({
            'success': True,
            'flag': {
                'id': str(flag.id),
                'name': flag.name,
                'lat': flag.lat,
                'lon': flag.lon,
                'level': flag.level,
                'status': flag.status,
                'hp_current': flag.hp_current,
                'hp_max': flag.hp_max,
            }
        }, status=201)
    except flag_svc.FlagError as fe:
        return JsonResponse({'success': False, 'error': fe.code, 'message': str(fe)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'internal_error', 'message': str(e)}, status=500)


@login_required
@require_http_methods(["GET"]) 
def api_flags_nearby(request):
    try:
        lat = float(request.GET.get('lat'))
        lon = float(request.GET.get('lon'))
        radius = float(request.GET.get('radius_m', 2000))
        flags = flag_svc.list_flags_near(lat, lon, radius)
        return JsonResponse({'success': True, 'flags': flags})
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'invalid_coordinates'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'internal_error', 'message': str(e)}, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"]) 
def api_flags_attack(request, flag_id):
    try:
        data = json.loads(request.body or '{}')
        lat = float(data.get('lat'))
        lon = float(data.get('lon'))
        damage = int(data.get('damage', 50))
        result = flag_svc.attack_flag(request.user, flag_id, lat, lon, damage)
        return JsonResponse({'success': True, 'result': result})
    except flag_svc.FlagError as fe:
        return JsonResponse({'success': False, 'error': fe.code, 'message': str(fe)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'internal_error', 'message': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"]) 
def api_flags_capture(request, flag_id):
    try:
        data = json.loads(request.body or '{}')
        lat = float(data.get('lat'))
        lon = float(data.get('lon'))
        result = flag_svc.capture_flag(request.user, flag_id, lat, lon)
        return JsonResponse({'success': True, 'result': result})
    except flag_svc.FlagError as fe:
        return JsonResponse({'success': False, 'error': fe.code, 'message': str(fe)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'internal_error', 'message': str(e)}, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"]) 
def api_flags_collect(request, flag_id):
    try:
        result = flag_svc.collect_revenue(request.user, flag_id)
        return JsonResponse({'success': True, 'result': result})
    except flag_svc.FlagError as fe:
        return JsonResponse({'success': False, 'error': fe.code, 'message': str(fe)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'internal_error', 'message': str(e)}, status=500)

# Flag system views removed


@login_required
def java_style_client(request):
    """
    Java-style flag client - matches the JavaFX implementation
    Simple HTML/Canvas client that calls the same APIs as the Java example
    """
    return render(request, 'java_style_client.html')
