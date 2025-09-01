"""
Location-Based RPG Views
API endpoints and views for the RPG game systems
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .forms import CombinedRegistrationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.db.models import Q, F
from datetime import timedelta
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
import random
import math

from .models import (
    Character, Monster, MonsterTemplate, ItemTemplate, InventoryItem,
    PvECombat, PvPCombat, Trade, TradeItem, Region, GameEvent, Skill,
    TerritoryFlag
)


# ===============================
# DEBUG VIEWS (TEMPORARY)
# ===============================

def debug_500_error(request):
    """Debug endpoint to diagnose 500 errors in production"""
    import traceback
    import sys
    from django.conf import settings
    from django.urls import reverse
    import os
    
    debug_info = {
        'status': 'debug_active',
        'django_version': sys.version,
        'settings_module': os.environ.get('DJANGO_SETTINGS_MODULE'),
        'debug_mode': settings.DEBUG,
        'allowed_hosts': settings.ALLOWED_HOSTS,
    }
    
    # Test database connection
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            debug_info['database'] = 'Connected'
    except Exception as e:
        debug_info['database'] = f'Error: {str(e)}'
    
    # Test URL reversal
    url_tests = {}
    test_urls = ['index', 'register', 'login', 'character_creation']
    for url_name in test_urls:
        try:
            resolved = reverse(url_name)
            url_tests[url_name] = f'OK: {resolved}'
        except Exception as e:
            url_tests[url_name] = f'ERROR: {str(e)}'
    
    debug_info['url_tests'] = url_tests
    
    # Test template rendering
    try:
        from django.template.loader import get_template
        template = get_template('main/index.html')
        debug_info['template'] = 'Template loads OK'
    except Exception as e:
        debug_info['template'] = f'Template error: {str(e)}'
    
    return JsonResponse(debug_info)


def health(request):
    """Simple healthcheck endpoint for load balancers."""
    return JsonResponse({"status": "ok"}, status=200)


# ===============================
# MAIN GAME VIEWS
# ===============================

def logout_view(request):
    """Log out user on GET or POST and redirect to login page (dev convenience)."""
    try:
        logout(request)
    finally:
        return redirect('login')


def register(request):
    """Unified user registration + character creation.
    Creates a user and their character in one step with class + flag color selection.
    """
    # If already authenticated, route based on whether a character exists
    if request.user.is_authenticated:
        if Character.objects.filter(user=request.user).exists():
            return redirect('rpg_game')
        return redirect('character_creation')

    def generate_unique_character_name(base: str) -> str:
        base = (base or '').strip()
        if not base:
            base = 'Adventurer'
        name = base
        max_len = 50
        # If base too long, trim to allow suffixes
        base_trim = base[:max_len]
        if not Character.objects.filter(name__iexact=name).exists():
            return name
        # Try deterministic numeric suffixes then random
        for i in range(2, 1000):
            suffix = f" {i}"
            candidate = (base_trim[: max(1, max_len - len(suffix))] + suffix).strip()
            if not Character.objects.filter(name__iexact=candidate).exists():
                return candidate
        import random
        for _ in range(20):
            suffix = f" {random.randint(1000, 9999)}"
            candidate = (base_trim[: max(1, max_len - len(suffix))] + suffix).strip()
            if not Character.objects.filter(name__iexact=candidate).exists():
                return candidate
        # Fallback to uuid short
        import uuid
        short = str(uuid.uuid4())[:8]
        candidate = (base_trim[: max(1, max_len - 9)] + '-' + short).strip()
        return candidate

    if request.method == 'POST':
        form = CombinedRegistrationForm(request.POST)
        if form.is_valid():
            # Create user
            user = form.save()
            # Prepare character fields
            desired_name = form.cleaned_data.get('character_name')
            class_type = form.cleaned_data.get('class_type')
            flag_color = form.cleaned_data.get('flag_color')
            unique_name = generate_unique_character_name(desired_name)

            # Starting location
            try:
                start_lat = settings.GAME_SETTINGS.get('DEFAULT_START_LAT', 41.0646633)
                start_lon = settings.GAME_SETTINGS.get('DEFAULT_START_LON', -80.6391736)
            except AttributeError:
                start_lat = 41.0646633
                start_lon = -80.6391736

            # Create character
            character = Character.objects.create(
                user=user,
                name=unique_name,
                lat=start_lat,
                lon=start_lon,
                class_type=class_type,
                flag_color=flag_color,
            )
            character.apply_class_base_stats()
            character.save()

            # Starter skills
            for skill_name, skill_type in [('Combat','combat'), ('Gathering','gathering')]:
                Skill.objects.create(character=character, name=skill_name, skill_type=skill_type, level=1)

            # Log user in and redirect to game
            login(request, user)
            if unique_name != (desired_name or '').strip():
                messages.info(request, f"Character name '{desired_name}' was taken. Assigned '{unique_name}'.")
            messages.success(request, f"Welcome to the world, {unique_name}! Account and character created.")
            return redirect('rpg_game')
    else:
        form = CombinedRegistrationForm()

    return render(request, 'registration/register.html', {
        'form': form,
        'class_info_json': json.dumps(Character.CLASS_INFO),
    })

def index(request):
    """Homepage - redirect to character creation or game"""
    if not request.user.is_authenticated:
        return render(request, 'main/index.html')
    
    try:
        character = Character.objects.get(user=request.user)
        return redirect('rpg_game')
    except Character.DoesNotExist:
        return redirect('character_creation')


@login_required
def character_creation(request):
    """Character creation page with class and flag color selection"""
    # If the user already has a character, go to game
    if Character.objects.filter(user=request.user).exists():
        return redirect('rpg_game')

    from .forms import CharacterCreationForm

    if request.method == 'POST':
        form = CharacterCreationForm(request.POST)
        if form.is_valid():
            character_name = form.cleaned_data['character_name']
            class_type = form.cleaned_data['class_type']
            flag_color = form.cleaned_data['flag_color']

            # Starting location
            try:
                start_lat = settings.GAME_SETTINGS.get('DEFAULT_START_LAT', 41.0646633)
                start_lon = settings.GAME_SETTINGS.get('DEFAULT_START_LON', -80.6391736)
            except AttributeError:
                start_lat = 41.0646633
                start_lon = -80.6391736

            # Create character
            character = Character.objects.create(
                user=request.user,
                name=character_name,
                lat=start_lat,
                lon=start_lon,
                class_type=class_type,
                flag_color=flag_color,
            )
            # Apply class base stats and derived
            character.apply_class_base_stats()
            character.save()

            # Create starting skills
            starting_skills = [
                ('Combat', 'combat'),
                ('Gathering', 'gathering'),
            ]
            for skill_name, skill_type in starting_skills:
                Skill.objects.create(
                    character=character,
                    name=skill_name,
                    skill_type=skill_type,
                    level=1
                )

            messages.success(request, f'Welcome to the world, {character_name}!')
            return redirect('rpg_game')
    else:
        form = CharacterCreationForm()

    return render(request, 'main/character_creation.html', { 'form': form, 'class_info_json': json.dumps(Character.CLASS_INFO) })


@login_required
def rpg_game(request):
    """Main RPG game view"""
    try:
        character = Character.objects.get(user=request.user)
    except Character.DoesNotExist:
        return redirect('character_creation')
    
    # Update character's online status and last activity
    character.is_online = True
    character.save(update_fields=['is_online', 'last_activity'])
    
    # Get game settings safely
    try:
        game_settings = settings.GAME_SETTINGS
    except AttributeError:
        # Fallback game settings
        game_settings = {
            'MAPBOX_ACCESS_TOKEN': 'pk.eyJ1IjoiamFsbGk5NiIsImEiOiJjbWU3eW9tZnUwOWJuMnJvcmJrN252OGloIn0.0OSOw3J1cDB45AIRS_mEbA',
            'MAPBOX_STYLE': 'mapbox://styles/mapbox/dark-v11',
            'ZOOM_LEVEL': 15
        }
    
    context = {
        'character': character,
        'game_settings': game_settings,
        'MAPBOX_ACCESS_TOKEN': game_settings.get('MAPBOX_ACCESS_TOKEN'),
        'MAPBOX_STYLE': game_settings.get('MAPBOX_STYLE', 'mapbox://styles/mapbox/streets-v12'),
    }
    
    return render(request, 'main/rpg_game.html', context)


# Territory manager view removed


# Territory debug view removed


@login_required
def pk_game(request):
    """Parallel Kingdom style game interface with tabbed navigation"""
    try:
        character = Character.objects.get(user=request.user)
    except Character.DoesNotExist:
        messages.error(request, 'Character not found. Please create a character first.')
        return redirect('character_creation')
    
    # Update character's online status
    character.is_online = True
    character.save(update_fields=['is_online', 'last_activity'])
    
    # Get game settings safely
    try:
        game_settings = settings.GAME_SETTINGS
    except AttributeError:
        # Fallback game settings
        game_settings = {
            'MAPBOX_ACCESS_TOKEN': 'pk.eyJ1IjoiamFsbGk5NiIsImEiOiJjbWU3eW9tZnUwOWJuMnJvcmJrN242OGloIn0.0OSOw3J1cDB45AIRS_mEbA',
            'MAPBOX_STYLE': 'mapbox://styles/mapbox/dark-v11',
            'ZOOM_LEVEL': 15
        }
    
    context = {
        'character': character,
        'MAPBOX_ACCESS_TOKEN': game_settings.get('MAPBOX_ACCESS_TOKEN'),
        'MAPBOX_STYLE': game_settings.get('MAPBOX_STYLE', 'mapbox://styles/mapbox/dark-v11'),
        'ZOOM_LEVEL': game_settings.get('ZOOM_LEVEL', 15),
    }
    
    return render(request, 'main/rpg_game.html', context)


@login_required
def building_game(request):
    """Building-focused game view with right-click placement"""
    try:
        character = Character.objects.get(user=request.user)
    except Character.DoesNotExist:
        return redirect('character_creation')
    
    # Update character's online status
    character.is_online = True
    character.save(update_fields=['is_online', 'last_activity'])
    
    context = {
        'character': character,
    }
    
    return render(request, 'pk/game_with_buildings.html', context)


def building_test(request):
    """Simple building test page that works without login"""
    return render(request, 'pk/building_test.html')


# ===============================
# CHARACTER API ENDPOINTS
# ===============================

@login_required
@require_http_methods(["POST"])
def api_character_relocate(request):
    """Relocate character to GPS coordinates"""
    try:
        character = Character.objects.get(user=request.user)
        
        # Parse request data
        data = json.loads(request.body)
        new_lat = float(data.get('lat', 0))
        new_lon = float(data.get('lon', 0))
        
        # Validate coordinates
        if not (-90 <= new_lat <= 90):
            return JsonResponse({
                'success': False,
                'error': 'Invalid latitude. Must be between -90 and 90.'
            }, status=400)
        
        if not (-180 <= new_lon <= 180):
            return JsonResponse({
                'success': False,
                'error': 'Invalid longitude. Must be between -180 and 180.'
            }, status=400)
        
        # Update character location
        old_lat, old_lon = character.lat, character.lon
        character.lat = new_lat
        character.lon = new_lon
        character.save()
        
        # Log the relocation event
        GameEvent.objects.create(
            character=character,
            event_type='player_teleport',
            title='GPS Relocation',
            message=f'Teleported from ({old_lat:.4f}, {old_lon:.4f}) to ({new_lat:.4f}, {new_lon:.4f})',
            data={'old_location': {'lat': old_lat, 'lon': old_lon}, 'new_location': {'lat': new_lat, 'lon': new_lon}}
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Character relocated successfully',
            'location': {
                'lat': character.lat,
                'lon': character.lon
            },
            'distance_moved': character.distance_between(old_lat, old_lon, new_lat, new_lon)
        })
        
    except Character.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Character not found'
        }, status=404)
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid request data: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_character_respawn(request):
    """Respawn character at provided real-life coordinates with full health.
    Body: { lat?: float, lon?: float }
    If coordinates are provided and valid, the character is moved there immediately (ignoring territory restrictions).
    Always restores HP to max. Does not restore gold; any defeat penalties remain.
    """
    try:
        character = Character.objects.get(user=request.user)
        data = {}
        try:
            data = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            data = {}
        new_lat = data.get('lat', None)
        new_lon = data.get('lon', None)
        moved = False
        old_lat, old_lon = character.lat, character.lon
        if new_lat is not None and new_lon is not None:
            try:
                new_lat_f = float(new_lat)
                new_lon_f = float(new_lon)
                if (-90 <= new_lat_f <= 90) and (-180 <= new_lon_f <= 180):
                    character.lat = new_lat_f
                    character.lon = new_lon_f
                    moved = True
            except (TypeError, ValueError):
                pass
        # Restore HP to full
        character.current_hp = character.max_hp
        character.in_combat = False
        character.save()
        # Log respawn event
        try:
            msg = 'Respawned with full health'
            if moved:
                msg += f" at ({character.lat:.6f}, {character.lon:.6f})"
            GameEvent.objects.create(
                character=character,
                event_type='respawn',
                title='Respawn',
                message=msg,
                data={'moved': moved, 'old_location': {'lat': old_lat, 'lon': old_lon}, 'new_location': {'lat': character.lat, 'lon': character.lon}}
            )
        except Exception:
            pass
        # Push character update via WebSocket so HUD refreshes
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'character_{character.id}',
                {'type': 'character_update'}
            )
        except Exception:
            pass
        return JsonResponse({
            'success': True,
            'message': 'Respawned successfully',
            'location': {'lat': character.lat, 'lon': character.lon},
            'moved': moved,
            'character': get_character_data(character)
        })
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)


@login_required
@require_http_methods(["GET"])
def api_character_status(request):
    """Get current character status and stats"""
    try:
        character = Character.objects.get(user=request.user)
        
        return JsonResponse({
            'success': True,
            'character': {
                'id': str(character.id),
                'name': character.name,
                'class_type': character.class_type,
                'level': character.level,
                'experience': character.experience,
                'experience_to_next': character.experience_needed_for_next_level(),
                'unspent_points': character.unspent_stat_points,
                'lat': character.lat,
                'lon': character.lon,
                'current_hp': character.current_hp,
                'max_hp': character.max_hp,
                'current_mana': character.current_mana,
                'max_mana': character.max_mana,
                'current_stamina': character.current_stamina,
                'max_stamina': character.max_stamina,
                'gold': character.gold,
                'strength': character.strength,
                'defense': character.defense,
                'vitality': character.vitality,
                'agility': character.agility,
                'intelligence': character.intelligence,
                'in_combat': character.in_combat,
                'pvp_enabled': character.pvp_enabled,
            }
        })
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)


@require_http_methods(["GET"])
def api_username_available(request):
    """AJAX: Check if a username is available (case-insensitive)."""
    username = (request.GET.get('username') or '').strip()
    available = bool(username) and not User.objects.filter(username__iexact=username).exists()
    return JsonResponse({'success': True, 'available': available})


@require_http_methods(["GET"])
def api_character_name_available(request):
    """AJAX: Check if a character name is available (case-insensitive)."""
    name = (request.GET.get('name') or '').strip()
    available = bool(name) and not Character.objects.filter(name__iexact=name).exists()
    # Provide a suggestion if not available
    suggestion = None
    if name and not available:
        try:
            def _gen(base: str) -> str:
                base = (base or 'Adventurer').strip()
                cand = base
                if not Character.objects.filter(name__iexact=cand).exists():
                    return cand
                for i in range(2, 50):
                    s = f" {i}"
                    c = (base[: max(1, 50 - len(s))] + s).strip()
                    if not Character.objects.filter(name__iexact=c).exists():
                        return c
                import random
                r = f" {random.randint(1000, 9999)}"
                return (base[: max(1, 50 - len(r))] + r).strip()
            suggestion = _gen(name)
        except Exception:
            suggestion = None
    return JsonResponse({'success': True, 'available': available, 'suggestion': suggestion})


@login_required
@require_http_methods(["GET"])
def api_nearby_players(request):
    """Get nearby players within range"""
    try:
        character = Character.objects.get(user=request.user)
        
        # Get players within 1km radius
        lat_range = 0.01  # ~1km
        lon_range = 0.01
        
        nearby_players = Character.objects.filter(
            lat__gte=character.lat - lat_range,
            lat__lte=character.lat + lat_range,
            lon__gte=character.lon - lon_range,
            lon__lte=character.lon + lon_range,
            is_online=True
        ).exclude(id=character.id).select_related('user')
        
        players_data = []
        for player in nearby_players:
            distance = character.distance_to(player.lat, player.lon)
            if distance <= 1000:  # 1km max
                players_data.append({
                    'id': str(player.id),
                    'name': player.name,
                    'level': player.level,
                    'lat': player.lat,
                    'lon': player.lon,
                    'distance': distance,
                    'in_combat': player.in_combat,
                    'pvp_enabled': player.pvp_enabled,
                })
        
        return JsonResponse({
            'success': True,
            'players': players_data
        })
        
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)


@login_required
@require_http_methods(["GET"])
def api_nearby_monsters(request):
    """Get nearby monsters within range"""
    try:
        character = Character.objects.get(user=request.user)
        
        # Get monsters within 500m radius
        lat_range = 0.005  # ~500m
        lon_range = 0.005
        
        nearby_monsters = Monster.objects.filter(
            lat__gte=character.lat - lat_range,
            lat__lte=character.lat + lat_range,
            lon__gte=character.lon - lon_range,
            lon__lte=character.lon + lon_range,
            is_alive=True
        ).select_related('template')
        
        monsters_data = []
        for monster in nearby_monsters:
            distance = character.distance_to(monster.lat, monster.lon)
            if distance <= 500:  # 500m max
                monsters_data.append({
                    'id': str(monster.id),
                    'name': monster.template.name,
                    'level': monster.template.level,
                    'lat': monster.lat,
                    'lon': monster.lon,
                    'current_hp': monster.current_hp,
                    'max_hp': monster.max_hp,
                    'distance': distance,
                    'is_aggressive': monster.template.is_aggressive,
                    'in_combat': monster.in_combat,
                })
        
        return JsonResponse({
            'success': True,
            'monsters': monsters_data
        })
        
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)


# ===============================
# COMBAT SYSTEM API
# ===============================

@login_required
@require_http_methods(["POST"])
def api_character_jump(request):
    """Instantly jump to one of your owned flags (center of its circle)."""
    try:
        data = json.loads(request.body)
        flag_id = data.get('flag_id')
        character = Character.objects.get(user=request.user)
        from .models import TerritoryFlag
        try:
            flag = TerritoryFlag.objects.get(id=flag_id)
        except TerritoryFlag.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Flag not found'}, status=404)
        # Allow jump if owner OR flag is public
        if flag.owner_id != request.user.id and getattr(flag, 'is_private', False):
            return JsonResponse({'success': False, 'error': 'Cannot jump: flag is private'}, status=403)
        # Teleport to slightly inside the circle center (use exact center)
        character.lat = flag.lat
        character.lon = flag.lon
        character.save(update_fields=['lat','lon'])
        return JsonResponse({'success': True, 'location': {'lat': character.lat, 'lon': character.lon}})
    except (Character.DoesNotExist, json.JSONDecodeError, KeyError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
@require_http_methods(["GET"])
def api_combat_state(request):
    """Return active PvE combat state if any (for resume on reload)."""
    try:
        character = Character.objects.get(user=request.user)
        combat = PvECombat.objects.filter(character=character, status='active').select_related('monster__template').first()
        if not combat:
            return JsonResponse({'success': True, 'active': False})
        return JsonResponse({'success': True, 'active': True, 'combat': get_combat_data(combat)})
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)

@login_required
@require_http_methods(["POST"])
def api_pve_combat_start(request):
    """Start PvE combat with a monster"""
    try:
        data = json.loads(request.body)
        monster_id = data.get('monster_id')
        
        character = Character.objects.get(user=request.user)
        monster = Monster.objects.get(id=monster_id, is_alive=True)
        
        # Check if character is already in combat
        if character.in_combat:
            return JsonResponse({
                'success': False,
                'error': 'Already in combat'
            }, status=400)
        
        # Check distance
        distance = character.distance_to(monster.lat, monster.lon)
        if distance > 50:  # 50m combat range
            return JsonResponse({
                'success': False,
                'error': f'Too far away (need to be within 50m, currently {int(distance)}m)'
            }, status=400)
        
        # Check if monster is already in combat
        if monster.in_combat:
            return JsonResponse({
                'success': False,
                'error': 'Monster is already in combat'
            }, status=400)
        
        # Start combat
        with transaction.atomic():
            combat = PvECombat.objects.create(
                character=character,
                monster=monster,
                character_hp=character.current_hp,
                monster_hp=monster.current_hp
            )
            
            # Set combat states
            character.in_combat = True
            character.save(update_fields=['in_combat'])
            
            monster.in_combat = True
            monster.current_target = character
            monster.save(update_fields=['in_combat', 'current_target'])
        
        return JsonResponse({
            'success': True,
            'combat': {
                'id': str(combat.id),
                'player_hp': combat.character_hp,
                'enemy_hp': combat.monster_hp,
                'enemy': {
                    'name': monster.template.name,
                    'level': monster.template.level,
                    'max_hp': monster.max_hp
                }
            }
        })
        
    except (Character.DoesNotExist, Monster.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Character or monster not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_combat_action(request):
    """Perform a combat action"""
    try:
        data = json.loads(request.body)
        combat_id = data.get('combat_id')
        action = data.get('action')  # 'attack', 'defend', 'flee'
        
        character = Character.objects.get(user=request.user)
        
        # Get active PvE combat
        combat = PvECombat.objects.get(
            id=combat_id,
            character=character,
            status='active'
        )
        
        # Simple stamina (energy) gating similar to PK: attack costs more than defend
        # Stamina disabled
        stamina_cost = 0
        
        if action == 'flee':
            # Handle flee attempt
            flee_success = random.random() < (character.agility / 50.0)  # Higher agility = better flee chance
            
            if flee_success:
                combat.status = 'fled'
                combat.ended_at = timezone.now()
                combat.save()
                
                # End combat states
                character.in_combat = False
                character.save(update_fields=['in_combat'])
                
                combat.monster.in_combat = False
                combat.monster.current_target = None
                combat.monster.save(update_fields=['in_combat', 'current_target'])
                
                return JsonResponse({
                    'success': True,
                    'combat_ended': True,
                    'message': 'Successfully fled from combat!',
                    'victory': False,
                    'fled': True,
                    'character': get_character_data(character)
                })
            else:
                # Failed to flee, monster gets free attack
                damage = max(1, combat.monster.template.strength - character.defense + random.randint(-2, 2))
                combat.character_hp = max(0, combat.character_hp - damage)
                combat.save()
                
                if combat.character_hp <= 0:
                    return handle_combat_defeat(combat, character)
                
                return JsonResponse({
                    'success': True,
                    'combat_ended': False,
                    'message': f'Failed to flee! Took {damage} damage.',
                    'combat': get_combat_data(combat)
                })
        
        elif action == 'attack':
            # Calculate damage
            player_damage = max(1, character.strength - combat.monster.template.defense + random.randint(-3, 3))
            combat.monster_hp = max(0, combat.monster_hp - player_damage)
            
            if combat.monster_hp <= 0:
                # Monster defeated
                return handle_combat_victory(combat, character)
            
            # Monster counter-attacks
            monster_damage = max(1, combat.monster.template.strength - character.defense + random.randint(-2, 2))
            combat.character_hp = max(0, combat.character_hp - monster_damage)
            
            if combat.character_hp <= 0:
                # Player defeated
                return handle_combat_defeat(combat, character)
            
            combat.save()
            
            return JsonResponse({
                'success': True,
                'combat_ended': False,
                'message': f'You dealt {player_damage} damage and took {monster_damage} damage.',
                'combat': get_combat_data(combat)
            })
        
        elif action == 'defend':
            # Defending reduces incoming damage
            monster_damage = max(1, (combat.monster.template.strength - character.defense * 1.5) + random.randint(-2, 1))
            combat.character_hp = max(0, combat.character_hp - monster_damage)
            
            if combat.character_hp <= 0:
                return handle_combat_defeat(combat, character)
            
            combat.save()
            
            return JsonResponse({
                'success': True,
                'combat_ended': False,
                'message': f'You defended and took only {monster_damage} damage.',
                'combat': get_combat_data(combat)
            })
        
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
        
    except (Character.DoesNotExist, PvECombat.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Combat not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def handle_combat_victory(combat, character):
    """Handle player victory in PvE combat, and advance any active FlagRun."""
    combat.status = 'victory'
    combat.ended_at = timezone.now()
    
    # Calculate rewards
    base_exp = combat.monster.template.base_experience
    base_gold = combat.monster.template.base_gold
    
    # Level difference bonus/penalty
    level_diff = combat.monster.template.level - character.level
    exp_multiplier = max(0.5, 1.0 + (level_diff * 0.1))
    gold_multiplier = max(0.5, 1.0 + (level_diff * 0.05))
    
    experience_gained = int(base_exp * exp_multiplier) + random.randint(0, 10)
    gold_gained = int(base_gold * gold_multiplier) + random.randint(0, 20)
    
    combat.experience_gained = experience_gained
    combat.gold_gained = gold_gained

    # Loot: centralized generator on the model (honors drop_pool and themed fallback)
    try:
        drops = combat.generate_loot_drops()
    except Exception:
        drops = []
    combat.items_dropped = drops

    # Give rewards and add dropped items to inventory immediately
    old_level = character.level
    character.gain_experience(experience_gained)
    character.gold += gold_gained
    # Add each dropped item to character inventory now so UI refresh sees it
    try:
        for d in drops:
            try:
                name = str(d.get('name') or '').strip()
                qty = int(d.get('quantity') or 0)
            except Exception:
                name, qty = '', 0
            if name and qty > 0:
                character.add_item_to_inventory(name, qty)
    except Exception:
        # Non-fatal: continue even if some items fail to add
        pass

    character.current_hp = combat.character_hp
    character.in_combat = False
    character.save()
    
    # Kill monster
    defeated_monster_id = str(combat.monster.id)
    combat.monster.die()
    
    combat.save()
    
    # Push live inventory and character updates via WebSocket (if WS connected)
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'character_{character.id}',
            {'type': 'inventory_update'}
        )
        async_to_sync(channel_layer.group_send)(
            f'character_{character.id}',
            {'type': 'character_update'}
        )
    except Exception:
        pass
    
    # Check for level up
    level_up_message = ""
    if character.level > old_level:
        level_up_message = f" Level up! You are now level {character.level}!"
    
    payload = {
        'success': True,
        'combat_ended': True,
        'victory': True,
        'message': f'Victory! Gained {experience_gained} XP and {gold_gained} gold.{level_up_message}',
        'character': get_character_data(character),
        'drops': combat.items_dropped,
        'experience_gained': experience_gained,
        'gold_gained': gold_gained,
    }
    return JsonResponse(payload)


def handle_combat_defeat(combat, character):
    """Handle player defeat in PvE combat"""
    combat.status = 'defeat'
    combat.ended_at = timezone.now()
    combat.save()
    
    # Player goes to 1 HP, loses some gold
    gold_lost = min(character.gold, character.gold // 10)  # Lose 10% of gold
    character.current_hp = 1
    character.gold -= gold_lost
    character.in_combat = False
    character.save()
    
    # Reset monster combat state
    combat.monster.in_combat = False
    combat.monster.current_target = None
    combat.monster.save(update_fields=['in_combat', 'current_target'])
    
    # Push character update via WebSocket
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'character_{character.id}',
            {'type': 'character_update'}
        )
    except Exception:
        pass
    
    return JsonResponse({
        'success': True,
        'combat_ended': True,
        'victory': False,
        'defeat': True,
        'message': f'Defeated! Lost {gold_lost} gold.',
        'character': get_character_data(character)
    })


def get_combat_data(combat):
    """Get combat data for frontend"""
    return {
        'id': str(combat.id),
        'player_hp': combat.character_hp,
        'enemy_hp': combat.monster_hp,
        'enemy': {
            'name': combat.monster.template.name,
            'level': combat.monster.template.level,
            'max_hp': combat.monster.max_hp
        }
    }


def get_character_data(character):
    """Get character data for frontend"""
    return {
        'id': str(character.id),
        'name': character.name,
        'level': character.level,
        'experience': character.experience,
        'experience_to_next': character.experience_needed_for_next_level(),
        'current_hp': character.current_hp,
        'max_hp': character.max_hp,
        'current_mana': character.current_mana,
        'max_mana': character.max_mana,
        'current_stamina': character.current_stamina,
        'max_stamina': character.max_stamina,
        'gold': character.gold,
        'strength': character.strength,
        'defense': character.defense,
        'vitality': character.vitality,
        'agility': character.agility,
        'intelligence': character.intelligence,
    }


# ===============================
# PVP SYSTEM API
# ===============================

@login_required
@require_http_methods(["POST"])
def api_pvp_challenge(request):
    """Send a PvP challenge to another player"""
    try:
        data = json.loads(request.body)
        target_player_id = data.get('player_id')
        
        challenger = Character.objects.get(user=request.user)
        defender = Character.objects.get(id=target_player_id)
        
        # Validation checks
        if challenger.id == defender.id:
            return JsonResponse({'success': False, 'error': 'Cannot challenge yourself'}, status=400)
        
        if challenger.in_combat or defender.in_combat:
            return JsonResponse({'success': False, 'error': 'One of the players is already in combat'}, status=400)
        
        if not defender.pvp_enabled:
            return JsonResponse({'success': False, 'error': 'Player has PvP disabled'}, status=400)
        
        # Check distance
        distance = challenger.distance_to(defender.lat, defender.lon)
        if distance > 100:  # 100m PvP range
            return JsonResponse({
                'success': False, 
                'error': f'Too far away (need to be within 100m, currently {int(distance)}m)'
            }, status=400)
        
        # Check for existing challenges
        existing_challenge = PvPCombat.objects.filter(
            Q(challenger=challenger, defender=defender) |
            Q(challenger=defender, defender=challenger),
            status__in=['challenge', 'accepted', 'active']
        ).exists()
        
        if existing_challenge:
            return JsonResponse({'success': False, 'error': 'Challenge already exists'}, status=400)
        
        # Create PvP challenge
        challenge = PvPCombat.objects.create(
            challenger=challenger,
            defender=defender,
            lat=challenger.lat,
            lon=challenger.lon,
            challenge_expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        return JsonResponse({
            'success': True,
            'challenge_id': str(challenge.id),
            'message': f'Challenge sent to {defender.name}!'
        })
        
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Player not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ===============================
# INVENTORY SYSTEM API
# ===============================

@login_required
@require_http_methods(["GET"])
def api_inventory(request):
    """Get character's inventory"""
    try:
        character = Character.objects.get(user=request.user)
        inventory_items = InventoryItem.objects.filter(character=character).select_related('item_template')
        
        inventory_data = []
        for item in inventory_items:
            inventory_data.append({
                'id': str(item.id),
                'item': {
                    'id': str(item.item_template.id),
                    'name': item.item_template.name,
                    'description': item.item_template.description,
                    'item_type': item.item_template.item_type,
                    'rarity': item.item_template.rarity,
                },
                'quantity': item.quantity,
                'is_equipped': item.is_equipped,
            })
        
        return JsonResponse({
            'success': True,
            'inventory': inventory_data
        })
        
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)


@login_required
@require_http_methods(["POST"])
def api_inventory_sell(request):
    """Quick-sell items from inventory by name and quantity.
    Body: { name: string, quantity: int }
    Sells at item_template.base_value per unit and removes from inventory.
    """
    try:
        character = Character.objects.get(user=request.user)
        data = json.loads(request.body or '{}')
        name = (data.get('name') or '').strip()
        qty = int(data.get('quantity') or 0)
        if not name or qty <= 0:
            return JsonResponse({'success': False, 'error': 'Invalid name or quantity'}, status=400)
        try:
            tpl = ItemTemplate.objects.get(name__iexact=name)
        except ItemTemplate.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Item not found'}, status=404)
        try:
            inv = InventoryItem.objects.get(character=character, item_template=tpl)
        except InventoryItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Item not in inventory'}, status=404)
        sell_qty = min(inv.quantity, qty)
        unit_value = int(getattr(tpl, 'base_value', 0) or 0)
        gold_gain = sell_qty * max(0, unit_value)
        # Update inventory
        inv.quantity -= sell_qty
        if inv.quantity <= 0:
            inv.delete()
        else:
            inv.save(update_fields=['quantity'])
        # Pay character
        character.gold += gold_gain
        character.save(update_fields=['gold'])
        # Push inventory update via WebSocket if connected
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(f'character_{character.id}', {'type': 'inventory_update'})
            async_to_sync(channel_layer.group_send)(f'character_{character.id}', {'type': 'character_update'})
        except Exception:
            pass
        return JsonResponse({'success': True, 'sold': sell_qty, 'gold_gained': gold_gain, 'gold': character.gold})
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


# ===============================
# INVENTORY EQUIP/UNEQUIP
# ===============================

@login_required
@require_http_methods(["POST"])
def api_inventory_equip(request):
    """Equip a weapon or armor InventoryItem by ID.
    Body: { inventory_item_id: UUID }
    Only one weapon and one armor can be equipped at a time. Applies template stat bonuses.
    """
    try:
        from .models import InventoryItem
        character = Character.objects.get(user=request.user)
        data = json.loads(request.body or '{}')
        inv_id = data.get('inventory_item_id')
        if not inv_id:
            return JsonResponse({'success': False, 'error': 'inventory_item_id required'}, status=400)
        # Retrieve item and validate ownership
        try:
            inv = InventoryItem.objects.select_related('item_template', 'character').get(id=inv_id, character=character)
        except InventoryItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'item_not_found'}, status=404)
        tpl = inv.item_template
        item_type = (tpl.item_type or '').lower()
        if item_type not in ('weapon', 'armor'):
            return JsonResponse({'success': False, 'error': 'not_equipable'}, status=400)
        # Level requirement
        try:
            lvl_req = int(getattr(tpl, 'level_required', 1) or 1)
        except Exception:
            lvl_req = 1
        if int(character.level) < lvl_req:
            return JsonResponse({'success': False, 'error': f'level_required_{lvl_req}'}, status=400)
        # If already equipped, no-op success
        if inv.is_equipped:
            return JsonResponse({'success': True, 'message': 'already_equipped', 'character': get_character_data(character)})
        # Unequip currently equipped of same type (weapon or armor)
        from .models import InventoryItem as _Inv
        current_equipped = list(_Inv.objects.select_related('item_template').filter(character=character, is_equipped=True))
        to_unequip = [it for it in current_equipped if (getattr(it.item_template, 'item_type', '').lower() == item_type)]
        changed = False
        for it in to_unequip:
            # Reverse bonuses
            t = it.item_template
            try:
                character.strength = int(character.strength) - int(getattr(t, 'strength_bonus', 0) or 0)
                character.defense = int(character.defense) - int(getattr(t, 'defense_bonus', 0) or 0)
                character.vitality = int(character.vitality) - int(getattr(t, 'vitality_bonus', 0) or 0)
                character.agility = int(character.agility) - int(getattr(t, 'agility_bonus', 0) or 0)
                character.intelligence = int(character.intelligence) - int(getattr(t, 'intelligence_bonus', 0) or 0)
            except Exception:
                pass
            it.is_equipped = False
            it.save(update_fields=['is_equipped', 'updated_at'])
            changed = True
        # Apply new item bonuses
        try:
            character.strength = int(character.strength) + int(getattr(tpl, 'strength_bonus', 0) or 0)
            character.defense = int(character.defense) + int(getattr(tpl, 'defense_bonus', 0) or 0)
            character.vitality = int(character.vitality) + int(getattr(tpl, 'vitality_bonus', 0) or 0)
            character.agility = int(character.agility) + int(getattr(tpl, 'agility_bonus', 0) or 0)
            character.intelligence = int(character.intelligence) + int(getattr(tpl, 'intelligence_bonus', 0) or 0)
        except Exception:
            pass
        # Recompute derived stats and clamp
        try:
            character.recalculate_derived_stats()
        except Exception:
            pass
        character.save()
        inv.is_equipped = True
        inv.save(update_fields=['is_equipped', 'updated_at'])
        # Push WS updates
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(f'character_{character.id}', {'type': 'inventory_update'})
            async_to_sync(channel_layer.group_send)(f'character_{character.id}', {'type': 'character_update'})
        except Exception:
            pass
        return JsonResponse({'success': True, 'message': 'equipped', 'character': get_character_data(character)})
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'character_not_found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'internal_error', 'message': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_inventory_unequip(request):
    """Unequip an equipped InventoryItem by ID.
    Body: { inventory_item_id: UUID }
    Reverses stat bonuses if the item is equipped.
    """
    try:
        from .models import InventoryItem
        character = Character.objects.get(user=request.user)
        data = json.loads(request.body or '{}')
        inv_id = data.get('inventory_item_id')
        if not inv_id:
            return JsonResponse({'success': False, 'error': 'inventory_item_id required'}, status=400)
        try:
            inv = InventoryItem.objects.select_related('item_template', 'character').get(id=inv_id, character=character)
        except InventoryItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'item_not_found'}, status=404)
        if not inv.is_equipped:
            return JsonResponse({'success': True, 'message': 'already_unequipped', 'character': get_character_data(character)})
        tpl = inv.item_template
        item_type = (tpl.item_type or '').lower()
        if item_type not in ('weapon', 'armor'):
            return JsonResponse({'success': False, 'error': 'not_equipable'}, status=400)
        # Reverse bonuses
        try:
            character.strength = int(character.strength) - int(getattr(tpl, 'strength_bonus', 0) or 0)
            character.defense = int(character.defense) - int(getattr(tpl, 'defense_bonus', 0) or 0)
            character.vitality = int(character.vitality) - int(getattr(tpl, 'vitality_bonus', 0) or 0)
            character.agility = int(character.agility) - int(getattr(tpl, 'agility_bonus', 0) or 0)
            character.intelligence = int(character.intelligence) - int(getattr(tpl, 'intelligence_bonus', 0) or 0)
        except Exception:
            pass
        try:
            character.recalculate_derived_stats()
        except Exception:
            pass
        character.save()
        inv.is_equipped = False
        inv.save(update_fields=['is_equipped', 'updated_at'])
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(f'character_{character.id}', {'type': 'inventory_update'})
            async_to_sync(channel_layer.group_send)(f'character_{character.id}', {'type': 'character_update'})
        except Exception:
            pass
        return JsonResponse({'success': True, 'message': 'unequipped', 'character': get_character_data(character)})
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'character_not_found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'internal_error', 'message': str(e)}, status=500)

# ===============================
# TRADING SYSTEM API
# ===============================

@login_required
@require_http_methods(["POST"])
def api_trade_create(request):
    """Create a trade offer"""
    try:
        data = json.loads(request.body)
        target_player_id = data.get('target_player_id')
        offered_gold = data.get('offered_gold', 0)
        requested_gold = data.get('requested_gold', 0)
        
        initiator = Character.objects.get(user=request.user)
        recipient = Character.objects.get(id=target_player_id)
        
        # Validation
        if initiator.gold < offered_gold:
            return JsonResponse({'success': False, 'error': 'Not enough gold'}, status=400)
        
        # Check distance
        distance = initiator.distance_to(recipient.lat, recipient.lon)
        if distance > 100:  # 100m trade range
            return JsonResponse({
                'success': False, 
                'error': f'Too far away (need to be within 100m, currently {int(distance)}m)'
            }, status=400)
        
        # Create trade
        trade = Trade.objects.create(
            initiator=initiator,
            recipient=recipient,
            initiator_gold=offered_gold,
            recipient_gold=requested_gold,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        return JsonResponse({
            'success': True,
            'trade_id': str(trade.id),
            'message': f'Trade offer sent to {recipient.name}!'
        })
        
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Player not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_allocate_stats(request):
    """Allocate unspent stat points to attributes.
    Body: { strength, defense, vitality, agility, intelligence }
    """
    try:
        character = Character.objects.get(user=request.user)
        data = json.loads(request.body or '{}')
        allocations = {k: int(data.get(k, 0) or 0) for k in ['strength','defense','vitality','agility','intelligence']}
        ok, msg = character.allocate_stats(allocations)
        if not ok:
            return JsonResponse({'success': False, 'error': msg, 'unspent': character.unspent_stat_points}, status=400)
        # Push character update via WebSocket so HUDs refresh stats
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'character_{character.id}',
                {'type': 'character_update'}
            )
        except Exception:
            pass
        return JsonResponse({'success': True, 'message': 'Stats allocated', 'unspent': character.unspent_stat_points, 'character': {
            'strength': character.strength,
            'defense': character.defense,
            'vitality': character.vitality,
            'agility': character.agility,
            'intelligence': character.intelligence,
            'max_mana': character.max_mana,
            'max_stamina': character.max_stamina,
        }})
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


@login_required
@require_http_methods(["POST"])
def api_character_move(request):
    """Handle character movement via tap-to-move"""
    try:
        character = Character.objects.get(user=request.user)
        
        data = json.loads(request.body)
        target_lat = float(data.get('lat', 0))
        target_lon = float(data.get('lon', 0))
        
        # Validate coordinates
        if not (-90 <= target_lat <= 90) or not (-180 <= target_lon <= 180):
            return JsonResponse({'success': False, 'error': 'Invalid coordinates'}, status=400)
        
        # Calculate distance using Haversine formula
        import math
        
        def calculate_distance(lat1, lon1, lat2, lon2):
            R = 6371000  # Earth's radius in meters
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            delta_lat = math.radians(lat2 - lat1)
            delta_lon = math.radians(lon2 - lon1)
            
            a = (math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
                 math.cos(lat1_rad) * math.cos(lat2_rad) *
                 math.sin(delta_lon / 2) * math.sin(delta_lon / 2))
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return R * c
        
        # Calculate movement distance for logging
        distance = calculate_distance(
            character.lat, character.lon,
            target_lat, target_lon
        )

        # Allow movement during combat with leash-follow behavior handled below.
        # Movement restriction: only block entering private territories owned by others
        from .models import TerritoryFlag
        from .services.territory import point_in_flag
        try:
            private_flags = TerritoryFlag.objects.filter(status=getattr(TerritoryFlag.Status, 'ACTIVE', 'ACTIVE'), is_private=True).only('lat','lon','level','owner_id','status','is_private')
            for f in private_flags:
                try:
                    if f.owner_id != request.user.id and point_in_flag(target_lat, target_lon, f):
                        return JsonResponse({'success': False, 'error': 'This territory is private. Movement blocked.'}, status=403)
                except Exception:
                    continue
        except Exception:
            # If flag lookup fails, default to allowing movement
            pass

        # Update character position
        character.lat = target_lat
        character.lon = target_lon
        character.save(update_fields=['lat', 'lon'])
        
        # If moving during active PvE combat, make the NPC follow within a leash range (~one territory radius)
        combat_following = False
        combat_ended_flag = False
        fled = False
        leash_remaining_m = None
        try:
            if character.in_combat:
                # Find active combat session
                combat = PvECombat.objects.filter(character=character, status='active').select_related('monster__template').first()
                if combat and combat.monster and combat.monster.is_alive:
                    from .services.movement import haversine_m
                    from .services.territory import point_in_flag, flag_radius_for_level, flag_radius_for_flag
                    # Determine leash anchor and radius (cache per combat)
                    anchor_key = f"combat_anchor:{combat.id}"
                    anchor = cache.get(anchor_key)
                    if not anchor:
                        anchor_lat = float(getattr(combat.monster, 'lat', character.lat))
                        anchor_lon = float(getattr(combat.monster, 'lon', character.lon))
                        # Default radius ~ one territory circle
                        try:
                            gs = getattr(settings, 'GAME_SETTINGS', {})
                        except Exception:
                            gs = {}
                        default_r = int(gs.get('FLAG_RADIUS_M') or gs.get('FLAG_RADIUS') or 600)
                        radius_m = default_r
                        # If anchor is inside a flag, use that flag's radius
                        try:
                            nearby_flags = TerritoryFlag.objects.filter(
                                lat__gte=anchor_lat - 0.05,
                                lat__lte=anchor_lat + 0.05,
                                lon__gte=anchor_lon - 0.05,
                                lon__lte=anchor_lon + 0.05,
                                status=getattr(TerritoryFlag.Status, 'ACTIVE', 'active'),
                            )
                            for f in nearby_flags:
                                try:
                                    if point_in_flag(anchor_lat, anchor_lon, f):
                                        radius_m = int(flag_radius_for_flag(f))
                                        break
                                except Exception:
                                    continue
                        except Exception:
                            pass
                        anchor = {'lat': anchor_lat, 'lon': anchor_lon, 'radius_m': int(radius_m)}
                        cache.set(anchor_key, anchor, 3600)
                    # Check distance from leash anchor to new target
                    dist_from_anchor = float(haversine_m(target_lat, target_lon, anchor['lat'], anchor['lon']))
                    leash_remaining_m = max(0, int(anchor['radius_m'] - dist_from_anchor))
                    if dist_from_anchor > float(anchor['radius_m']):
                        # Out of leash: end combat as fled and release the monster
                        with transaction.atomic():
                            combat.status = 'fled'
                            combat.ended_at = timezone.now()
                            combat.save(update_fields=['status', 'ended_at'])
                            character.in_combat = False
                            character.save(update_fields=['in_combat'])
                            try:
                                # Return monster to leash anchor and clear combat state
                                m = combat.monster
                                m.in_combat = False
                                m.current_target = None
                                m.lat = anchor['lat']
                                m.lon = anchor['lon']
                                m.save(update_fields=['in_combat', 'current_target', 'lat', 'lon'])
                            except Exception:
                                pass
                        combat_ended_flag = True
                        fled = True
                        combat_following = False
                        # Clear cached anchor since combat ended
                        try:
                            cache.delete(anchor_key)
                        except Exception:
                            pass
                    else:
                        # Within leash: move the monster to follow the player
                        try:
                            m = combat.monster
                            m.lat = target_lat
                            m.lon = target_lon
                            m.save(update_fields=['lat', 'lon'])
                            combat_following = True
                        except Exception:
                            combat_following = False
        except Exception:
            # Non-fatal: do not block movement on combat follow errors
            pass
        
        # Ensure persistent NPC presence inside nearest territory circle (PK-style)
        try:
            from .models import TerritoryFlag, Monster, MonsterTemplate, ResourceNode
            from .services.territory import flag_radius_for_level, point_in_flag, spawn_monsters_in_flag
            inside_flag = False
            nearest_flag = None
            min_d = 1e12
            ring_r = 0.0
            for f in TerritoryFlag.objects.filter(status=getattr(TerritoryFlag.Status, 'ACTIVE', 'ACTIVE')):
                r = flag_radius_for_level(getattr(f, 'level', 1))
                d = character.distance_to(f.lat, f.lon)
                if d <= r and d < min_d:
                    inside_flag = True
                    nearest_flag = f
                    min_d = d
                    ring_r = r
            if inside_flag and nearest_flag:
                gs = getattr(settings, 'GAME_SETTINGS', {})
                MIN_ALIVE = int(gs.get('MIN_FLAG_NPCS', 3))
                # Ensure NPCs inside flag
                alive = [m for m in Monster.objects.filter(is_alive=True) if point_in_flag(m.lat, m.lon, nearest_flag)]
                deficit = max(0, int(MIN_ALIVE) - len(alive))
                if deficit > 0:
                    spawn_monsters_in_flag(nearest_flag, count=deficit)
                # Ensure basic resources inside flag (berries), like PK
                try:
                    nodes = [rn for rn in ResourceNode.objects.filter(resource_type='berry_bush') if point_in_flag(rn.lat, rn.lon, nearest_flag)]
                    if len(nodes) < 2:
                        need = 2 - len(nodes)
                        for _ in range(need):
                            # Sample point in circle near flag center
                            rr = ring_r * 0.6
                            import random, math
                            ang = random.random() * 2*math.pi
                            dist = rr * (random.random() ** 0.5)
                            lat_off = dist / 111320.0
                            lon_off = dist / (111320.0 * max(1e-6, math.cos(nearest_flag.lat * math.pi/180.0)))
                            ResourceNode.objects.create(
                                resource_type='berry_bush',
                                lat=nearest_flag.lat + lat_off * math.sin(ang),
                                lon=nearest_flag.lon + lon_off * math.cos(ang),
                                level=max(1, getattr(nearest_flag, 'level', 1)),
                                quantity=5,
                                max_quantity=5,
                                respawn_time=45,
                            )
                except Exception:
                    pass
            else:
                # Outside any flag: ensure a baseline of wild NPCs around player
                gs = getattr(settings, 'GAME_SETTINGS', {})
                WILD_MIN = int(gs.get('WILD_MIN_NPCS', 5))
                WILD_R = int(gs.get('WILD_SPAWN_RADIUS_M', 120))
                # Bounding box filter (approx)
                lat_eps = WILD_R / 111320.0
                lon_eps = WILD_R / (111320.0 * max(1e-6, math.cos(math.radians(character.lat))))
                nearby = Monster.objects.filter(
                    is_alive=True,
                    lat__gte=character.lat - lat_eps,
                    lat__lte=character.lat + lat_eps,
                    lon__gte=character.lon - lon_eps,
                    lon__lte=character.lon + lon_eps,
                )
                if nearby.count() < WILD_MIN:
                    to_spawn = WILD_MIN - nearby.count()
                    # Choose a suitable template (default to Forest Wolf)
                    tmpl = MonsterTemplate.objects.filter(level__gte=max(1, int(character.level)-1), level__lte=int(character.level)+1).order_by('?').first()
                    if not tmpl:
                        tmpl = MonsterTemplate.objects.create(
                            name='Forest Wolf', description='A wild wolf roaming the forest', level=max(1, int(character.level)),
                            base_hp=40, strength=12, defense=6, agility=14,
                            base_experience=30, base_gold=15, is_aggressive=True,
                            respawn_time_minutes=30
                        )
                    import random
                    for _ in range(to_spawn):
                        ang = random.random() * 2*math.pi
                        dist = random.uniform(10.0, float(WILD_R))
                        lat_off = dist / 111320.0
                        lon_off = dist / (111320.0 * max(1e-6, math.cos(math.radians(character.lat))))
                        Monster.objects.create(
                            template=tmpl,
                            lat=character.lat + lat_off * math.sin(ang),
                            lon=character.lon + lon_off * math.cos(ang),
                            current_hp=tmpl.base_hp,
                            max_hp=tmpl.base_hp,
                            is_alive=True,
                        )
        except Exception:
            # Never block movement on spawn/resource errors
            pass

        # Auto-aggro: if not in combat, check for aggressive monster within 30m and start PvE
        if not character.in_combat:
            nearby_aggressive = Monster.objects.filter(
                lat__gte=character.lat - 0.0003,
                lat__lte=character.lat + 0.0003,
                lon__gte=character.lon - 0.0003,
                lon__lte=character.lon + 0.0003,
                is_alive=True,
                in_combat=False,
                template__is_aggressive=True,
            ).select_related('template').first()
            if nearby_aggressive:
                # Verify actual distance <= 30m
                dcheck = character.distance_to(nearby_aggressive.lat, nearby_aggressive.lon)
                if dcheck <= 30:
                    with transaction.atomic():
                        combat = PvECombat.objects.create(
                            character=character,
                            monster=nearby_aggressive,
                            character_hp=character.current_hp,
                            monster_hp=nearby_aggressive.current_hp
                        )
                        character.in_combat = True
                        character.save(update_fields=['in_combat'])
                        nearby_aggressive.in_combat = True
                        nearby_aggressive.current_target = character
                        nearby_aggressive.save(update_fields=['in_combat', 'current_target'])
                    return JsonResponse({
                        'success': True,
                        'lat': character.lat,
                        'lon': character.lon,
                        'distance': distance,
                        'combat_started': True,
                        'combat_ended': False,
                        'fled': False,
                        'combat': get_combat_data(combat)
                    })
        
        return JsonResponse({
            'success': True,
            'lat': character.lat,
            'lon': character.lon,
            'distance': distance,
            'combat_started': False,
            'combat_ended': combat_ended_flag,
            'fled': fled,
            'leash_remaining_m': leash_remaining_m
        })
        
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid coordinate values'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ===============================
# TERRITORY NPC LISTING (persistent NPCs in flags)
# ===============================

@login_required
@require_http_methods(["GET"])
def api_flag_npcs(request, flag_id):
    """List alive NPCs inside a specific flag's territory."""
    try:
        flag = TerritoryFlag.objects.get(id=flag_id)
        from .services.territory import point_in_flag, flag_radius_for_flag
        alive = [m for m in Monster.objects.filter(is_alive=True) if point_in_flag(m.lat, m.lon, flag)]
        monsters = [{
            'id': str(m.id),
            'name': m.template.name,
            'lat': m.lat,
            'lon': m.lon,
            'current_hp': m.current_hp,
            'max_hp': m.max_hp,
        } for m in alive]
        return JsonResponse({'success': True, 'flag_id': str(flag.id), 'radius_m': flag_radius_for_flag(flag), 'monsters': monsters})
    except TerritoryFlag.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'flag_not_found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'internal_error', 'message': str(e)}, status=500)


# ===============================
# FLAG RUN (Territory NPC waves) API
# ===============================

@login_required
@require_http_methods(["POST"])
def api_flag_run_start(request):
    """Deprecated: FlagRun feature removed. NPCs are now persistent within territories."""
    return JsonResponse({'success': False, 'error': 'feature_removed', 'message': 'Flag runs have been removed; NPCs are now persistent within territories.'}, status=410)


@login_required
@require_http_methods(["GET"])
def api_flag_run_status(request, run_id):
    """Deprecated: FlagRun feature removed. NPCs are now persistent within territories."""
    return JsonResponse({'success': False, 'error': 'feature_removed', 'message': 'Flag runs have been removed; NPCs are now persistent within territories.'}, status=410)


@login_required
@require_http_methods(["POST"])
def api_flag_run_abort(request, run_id):
    """Deprecated: FlagRun feature removed."""
    return JsonResponse({'success': False, 'error': 'feature_removed', 'message': 'Flag runs have been removed; NPCs are now persistent within territories.'}, status=410)


# ===============================
# UTILITY FUNCTIONS
# ===============================

def spawn_random_monsters():
    """Spawn random monsters around the world (called by management command)"""
    regions = Region.objects.all()
    monster_templates = MonsterTemplate.objects.all()
    
    for region in regions:
        # Calculate how many monsters this region should have
        area = (region.lat_max - region.lat_min) * (region.lon_max - region.lon_min)
        target_monsters = max(1, int(area * 1000 * region.spawn_rate))  # Monsters per square km
        
        current_monsters = Monster.objects.filter(
            lat__gte=region.lat_min,
            lat__lte=region.lat_max,
            lon__gte=region.lon_min,
            lon__lte=region.lon_max,
            is_alive=True
        ).count()
        
        monsters_to_spawn = max(0, target_monsters - current_monsters)
        
        for _ in range(monsters_to_spawn):
            # Random location within region
            lat = random.uniform(region.lat_min, region.lat_max)
            lon = random.uniform(region.lon_min, region.lon_max)
            
            # Choose random monster template appropriate for region
            suitable_templates = monster_templates.filter(
                level__gte=region.monster_level_min,
                level__lte=region.monster_level_max
            )
            
            if suitable_templates:
                template = random.choice(suitable_templates)
                
                Monster.objects.create(
                    template=template,
                    lat=lat,
                    lon=lon,
                    current_hp=template.base_hp,
                    max_hp=template.base_hp
                )


def respawn_dead_monsters():
    """Respawn monsters that are ready to respawn"""
    dead_monsters = Monster.objects.filter(is_alive=False, respawn_at__lte=timezone.now())
    
    for monster in dead_monsters:
        if monster.can_respawn():
            monster.respawn()


def create_starter_items():
    """Create basic item templates (called once during setup)"""
    starter_items = [
        # Weapons
        {
            'name': 'Rusty Sword',
            'description': 'A basic iron sword, worn but functional',
            'item_type': 'weapon',
            'rarity': 'common',
            'damage': 5,
            'level_required': 1,
            'base_value': 50
        },
        {
            'name': 'Iron Sword',
            'description': 'A well-crafted iron sword',
            'item_type': 'weapon',
            'rarity': 'common',
            'damage': 12,
            'level_required': 5,
            'base_value': 200
        },
        
        # Armor
        {
            'name': 'Leather Vest',
            'description': 'Basic leather protection',
            'item_type': 'armor',
            'rarity': 'common',
            'defense_bonus': 3,
            'level_required': 1,
            'base_value': 75
        },
        {
            'name': 'Chain Mail',
            'description': 'Interlocked metal rings provide good protection',
            'item_type': 'armor',
            'rarity': 'uncommon',
            'defense_bonus': 8,
            'vitality_bonus': 2,
            'level_required': 8,
            'base_value': 300
        },
        
        # Consumables
        {
            'name': 'Health Potion',
            'description': 'Restores 50 HP',
            'item_type': 'consumable',
            'rarity': 'common',
            'base_value': 25,
            'max_stack_size': 10
        },
        {
            'name': 'Mana Potion',
            'description': 'Restores 30 MP',
            'item_type': 'consumable',
            'rarity': 'common',
            'base_value': 20,
            'max_stack_size': 10
        }
    ]
    
    for item_data in starter_items:
        ItemTemplate.objects.get_or_create(
            name=item_data['name'],
            defaults=item_data
        )


def create_monster_templates():
    """Create basic and themed monster templates"""
    monster_templates = [
        # Classic set
        {
            'name': 'Forest Wolf',
            'description': 'A wild wolf roaming the forest',
            'level': 2,
            'base_hp': 40,
            'strength': 12,
            'defense': 6,
            'agility': 14,
            'base_experience': 30,
            'base_gold': 15,
            'is_aggressive': True,
            'respawn_time_minutes': 30
        },
        {
            'name': 'Goblin Scout',
            'description': 'A sneaky goblin carrying a rusty dagger',
            'level': 3,
            'base_hp': 50,
            'strength': 10,
            'defense': 8,
            'agility': 12,
            'base_experience': 40,
            'base_gold': 25,
            'is_aggressive': True,
            'respawn_time_minutes': 45
        },
        {
            'name': 'Cave Bear',
            'description': 'A massive bear with thick fur and sharp claws',
            'level': 8,
            'base_hp': 120,
            'strength': 20,
            'defense': 15,
            'agility': 6,
            'base_experience': 100,
            'base_gold': 60,
            'is_aggressive': True,
            'respawn_time_minutes': 60
        },
        {
            'name': 'Rabbit',
            'description': 'A harmless woodland creature',
            'level': 1,
            'base_hp': 15,
            'strength': 3,
            'defense': 2,
            'agility': 18,
            'base_experience': 10,
            'base_gold': 5,
            'is_aggressive': False,
            'respawn_time_minutes': 15
        },
        # Themed mafia–alien set
        {
            'name': 'Mafia Enforcer',
            'description': 'A hardened enforcer from the family',
            'level': 4,
            'base_hp': 80,
            'strength': 16,
            'defense': 10,
            'agility': 10,
            'base_experience': 60,
            'base_gold': 45,
            'is_aggressive': True,
            'respawn_time_minutes': 35,
            'drop_pool': [
                {'item': 'Energy Berries', 'quantity': 1, 'prob': 0.5},
                {'item': 'Neon Wood', 'quantity': 1, 'prob': 0.3},
                {'item': 'Quantum Ore', 'quantity': 1, 'prob': 0.15}
            ]
        },
        {
            'name': 'Yakuza Blade',
            'description': 'A swift blade adept',
            'level': 5,
            'base_hp': 75,
            'strength': 18,
            'defense': 8,
            'agility': 16,
            'base_experience': 75,
            'base_gold': 55,
            'is_aggressive': True,
            'respawn_time_minutes': 40,
            'drop_pool': [
                {'item': 'Mutant Herbs', 'quantity': 1, 'prob': 0.4},
                {'item': 'Plasma Stone', 'quantity': 1, 'prob': 0.25}
            ]
        },
        {
            'name': 'Cartel Sicario',
            'description': 'A ruthless assassin',
            'level': 6,
            'base_hp': 90,
            'strength': 20,
            'defense': 12,
            'agility': 14,
            'base_experience': 90,
            'base_gold': 70,
            'is_aggressive': True,
            'respawn_time_minutes': 45,
            'drop_pool': [
                {'item': 'Plasma Stone', 'quantity': 1, 'prob': 0.35},
                {'item': 'Stellar Gems', 'quantity': 1, 'prob': 0.15}
            ]
        },
        {
            'name': 'Void Cultist',
            'description': 'A fanatic channeling void energies',
            'level': 7,
            'base_hp': 95,
            'strength': 14,
            'defense': 10,
            'agility': 10,
            'base_experience': 110,
            'base_gold': 80,
            'is_aggressive': True,
            'respawn_time_minutes': 50,
            'drop_pool': [
                {'item': 'Void Essence', 'quantity': 1, 'prob': 0.25},
                {'item': 'Stellar Gems', 'quantity': 1, 'prob': 0.2}
            ]
        },
        {
            'name': 'Drone Marauder',
            'description': 'A rogue combat drone',
            'level': 3,
            'base_hp': 55,
            'strength': 12,
            'defense': 9,
            'agility': 12,
            'base_experience': 45,
            'base_gold': 25,
            'is_aggressive': True,
            'respawn_time_minutes': 25,
            'drop_pool': [
                {'item': 'Nano-Fabric', 'quantity': 1, 'prob': 0.1},
                {'item': 'Plasma Stone', 'quantity': 1, 'prob': 0.35}
            ]
        },
        {
            'name': 'Alien Stalker',
            'description': 'Stealthy extraterrestrial predator',
            'level': 8,
            'base_hp': 110,
            'strength': 22,
            'defense': 12,
            'agility': 18,
            'base_experience': 130,
            'base_gold': 90,
            'is_aggressive': True,
            'respawn_time_minutes': 55,
            'drop_pool': [
                {'item': 'Ancient Alien Relic', 'quantity': 1, 'prob': 0.08},
                {'item': 'Void Essence', 'quantity': 1, 'prob': 0.2}
            ]
        }
    ]
    
    for template_data in monster_templates:
        # Allow drop_pool passthrough if provided
        defaults = {k: v for k, v in template_data.items() if k != 'name'}
        MonsterTemplate.objects.get_or_create(
            name=template_data['name'],
            defaults=defaults
        )


def create_basic_regions():
    """Create basic world regions"""
    # Cleveland area regions
    regions = [
        {
            'name': 'Downtown Cleveland',
            'lat_min': 41.490,
            'lat_max': 41.510,
            'lon_min': -81.700,
            'lon_max': -81.680,
            'monster_level_min': 1,
            'monster_level_max': 5,
            'spawn_rate': 0.5,
            'pvp_enabled': True,
            'is_safe_zone': False
        },
        {
            'name': 'Cleveland Forest',
            'lat_min': 41.450,
            'lat_max': 41.490,
            'lon_min': -81.750,
            'lon_max': -81.700,
            'monster_level_min': 3,
            'monster_level_max': 10,
            'spawn_rate': 1.5,
            'pvp_enabled': True,
            'is_safe_zone': False
        },
        {
            'name': 'Safe Harbor',
            'lat_min': 41.510,
            'lat_max': 41.520,
            'lon_min': -81.690,
            'lon_max': -81.680,
            'monster_level_min': 1,
            'monster_level_max': 1,
            'spawn_rate': 0.1,
            'pvp_enabled': False,
            'is_safe_zone': True
        }
    ]
    
    for region_data in regions:
        Region.objects.get_or_create(
            name=region_data['name'],
            defaults=region_data
        )
