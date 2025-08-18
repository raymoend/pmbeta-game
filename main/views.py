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
