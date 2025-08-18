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
            flag_color = form.cleaned_data.get('flag_color')
            username = form.cleaned_data.get('username')
            
            # Store the flag color choice for character creation
            request.session['chosen_flag_color_id'] = flag_color.id
            
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
    """Mock API for PK player movement - returns success for testing"""
    import json
    from django.views.decorators.csrf import csrf_exempt
    from django.utils.decorators import method_decorator
    from django.views.decorators.http import require_http_methods
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        new_lat = float(data.get('lat'))
        new_lon = float(data.get('lon'))
        
        # Mock successful movement (since PK models are disabled)
        return JsonResponse({
            'success': True,
            'energy_used': 1,
            'remaining_energy': 95,
            'new_position': {
                'lat': new_lat,
                'lon': new_lon
            }
        })
        
    except (ValueError, KeyError) as e:
        return JsonResponse({
            'success': False,
            'error': 'Invalid coordinates'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


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
