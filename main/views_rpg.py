"""
Location-Based RPG Views
API endpoints and views for the RPG game systems
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.db.models import Q, F
from datetime import timedelta
import json
import random
import math

from .models import (
    Character, Monster, MonsterTemplate, ItemTemplate, InventoryItem,
    PvECombat, PvPCombat, Trade, TradeItem, Region, GameEvent, Skill
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


# ===============================
# MAIN GAME VIEWS
# ===============================

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
    """Character creation page"""
    # Check if user already has a character
    if Character.objects.filter(user=request.user).exists():
        return redirect('rpg_game')
    
    if request.method == 'POST':
        character_name = request.POST.get('character_name', '').strip()
        
        if not character_name:
            messages.error(request, 'Character name is required')
            return render(request, 'main/character_creation.html')
        
        if Character.objects.filter(name=character_name).exists():
            messages.error(request, 'Character name already taken')
            return render(request, 'main/character_creation.html')
        
        # Get starting location (use user's IP geolocation in production)
        start_lat = settings.GAME_SETTINGS.get('DEFAULT_START_LAT', 41.0646633)
        start_lon = settings.GAME_SETTINGS.get('DEFAULT_START_LON', -80.6391736)
        
        # Create character
        character = Character.objects.create(
            user=request.user,
            name=character_name,
            lat=start_lat,
            lon=start_lon
        )
        
        # Calculate derived stats
        character.recalculate_derived_stats()
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
    
    return render(request, 'main/character_creation.html')


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
    
    context = {
        'character': character,
        'game_settings': settings.GAME_SETTINGS,
    }
    
    return render(request, 'main/rpg_game.html', context)


# ===============================
# CHARACTER API ENDPOINTS
# ===============================

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
                'level': character.level,
                'experience': character.experience,
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
    """Handle player victory in PvE combat"""
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
    
    # Give rewards
    old_level = character.level
    character.gain_experience(experience_gained)
    character.gold += gold_gained
    character.current_hp = combat.character_hp
    character.in_combat = False
    character.save()
    
    # Kill monster
    combat.monster.die()
    
    combat.save()
    
    # Check for level up
    level_up_message = ""
    if character.level > old_level:
        level_up_message = f" Level up! You are now level {character.level}!"
    
    return JsonResponse({
        'success': True,
        'combat_ended': True,
        'victory': True,
        'message': f'Victory! Gained {experience_gained} XP and {gold_gained} gold.{level_up_message}',
        'character': get_character_data(character)
    })


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
    
    return JsonResponse({
        'success': True,
        'combat_ended': True,
        'victory': False,
        'message': f'Defeated! Lost {gold_lost} gold. Rest to recover.',
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
    """Create basic monster templates"""
    monster_templates = [
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
        }
    ]
    
    for template_data in monster_templates:
        MonsterTemplate.objects.get_or_create(
            name=template_data['name'],
            defaults=template_data
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
