"""
Legacy views for backward compatibility
The main RPG system views are in views_rpg.py
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse


def index(request):
    """Homepage - redirect to character creation or game"""
    if not request.user.is_authenticated:
        return render(request, 'main/index.html')
    
    # Redirect to RPG system
    return redirect('index')  # This will be handled by RPG URLs


def register(request):
    """User registration"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            
            # Log in the user
            login(request, user)
            return redirect('index')  # Will redirect to RPG character creation
    else:
        form = UserCreationForm()
    
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
