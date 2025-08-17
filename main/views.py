"""
Views for PMBeta location-based game
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import (Player, Chunk, Structure, NatureStructure, Flag, FlagAttack, NPC, ResourceNode, 
                     CombatSession, CombatAction, Item, Weapon)
from django.conf import settings
from django.utils import timezone
import json
import random
from datetime import timedelta


def index(request):
    """Homepage - redirect to game if logged in, otherwise show welcome"""
    if request.user.is_authenticated:
        return redirect('game')
    
    return render(request, 'main/index.html')


def register(request):
    """User registration"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            
            # Create player for new user
            player = Player.create_new_player(user)
            
            # Log in the user
            login(request, user)
            return redirect('game')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


@login_required
def game(request):
    """Main game view"""
    # Get or create player
    player, created = Player.objects.get_or_create(
        user=request.user,
        defaults={
            'lat': settings.GAME_SETTINGS['DEFAULT_START_LAT'],
            'lon': settings.GAME_SETTINGS['DEFAULT_START_LON'],
            'center_lat': settings.GAME_SETTINGS['DEFAULT_START_LAT'],
            'center_lon': settings.GAME_SETTINGS['DEFAULT_START_LON'],
        }
    )
    
    if created:
        messages.success(request, 'Welcome to PMBeta! Click on the map to move around.')
    
    context = {
        'player': player,
        'game_settings': settings.GAME_SETTINGS,
    }
    
    return render(request, 'main/game.html', context)


@login_required
@require_http_methods(["GET"])
def api_world_data(request):
    """API endpoint to get world data for current player"""
    try:
        player = Player.objects.get(user=request.user)
        chunk = Chunk.from_coords(player.lat, player.lon)
        
        world_data = {
            'center': {
                'lat': player.center_lat,
                'lon': player.center_lon
            },
            'player': {
                'lat': player.lat,
                'lon': player.lon,
                'level': player.level,
                'cash': player.cash,
                'bank_money': player.bank_money,
                'reputation': player.reputation,
                'heat_level': player.heat_level,
                'hp': player.hp
            },
            'chunk': chunk.to_dict()
        }
        
        return JsonResponse({
            'success': True,
            'data': world_data
        })
        
    except Player.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Player not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_move_player(request):
    """API endpoint to move player (REST fallback for WebSocket)"""
    try:
        data = json.loads(request.body)
        target_lat = float(data.get('lat'))
        target_lon = float(data.get('lon'))
        
        player = Player.objects.get(user=request.user)
        
        # Validate movement - must stay within 800m of player's center (base)
        distance_from_center = player.distance_between(player.center_lat, player.center_lon, target_lat, target_lon)
        max_range = 800  # 800m radius from center
        
        if distance_from_center > max_range:
            return JsonResponse({
                'success': False,
                'error': f'Movement out of range ({int(distance_from_center)}m from base). Stay within {max_range}m of your base.'
            }, status=400)
        
        # Update position
        player.lat = target_lat
        player.lon = target_lon
        player.save(update_fields=['lat', 'lon'])
        
        return JsonResponse({
            'success': True,
            'data': {
                'lat': player.lat,
                'lon': player.lon
            }
        })
        
    except (ValueError, KeyError) as e:
        return JsonResponse({
            'success': False,
            'error': 'Invalid coordinates'
        }, status=400)
    except Player.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Player not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def player_profile(request):
    """Player profile page"""
    try:
        player = Player.objects.get(user=request.user)
        
        context = {
            'player': player,
            'inventory': player.inventory.all(),
            'structures': player.structures.all(),
        }
        
        return render(request, 'main/profile.html', context)
        
    except Player.DoesNotExist:
        messages.error(request, 'Player profile not found')
        return redirect('game')


@login_required
@require_http_methods(["POST"])
def api_spawn_structures(request):
    """Admin endpoint to spawn test structures around player"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        player = Player.objects.get(user=request.user)
        
        # Spawn some test structures around the player
        structures_created = []
        
        for i in range(5):
            # Random position within 500m of player
            lat_offset = random.uniform(-0.005, 0.005)  # ~500m
            lon_offset = random.uniform(-0.005, 0.005)
            
            structure = NatureStructure.objects.create(
                structure_type=random.choice([1, 2]),  # Tree or Rock
                lat=player.lat + lat_offset,
                lon=player.lon + lon_offset,
                hp=100
            )
            
            structures_created.append({
                'id': str(structure.id),
                'type': structure.structure_type,
                'lat': structure.lat,
                'lon': structure.lon
            })
        
        return JsonResponse({
            'success': True,
            'structures_created': structures_created
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def api_game_stats(request):
    """Public API endpoint for game statistics"""
    try:
        stats = {
            'total_players': Player.objects.count(),
            'online_players': 0,  # TODO: Track online players
            'total_structures': Structure.objects.count(),
            'chunks_with_activity': 0,  # TODO: Calculate active chunks
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_place_flag(request):
    """API endpoint to place a new flag"""
    try:
        data = json.loads(request.body)
        target_lat = float(data.get('lat'))
        target_lon = float(data.get('lon'))
        flag_name = data.get('name', '').strip()
        flag_type = data.get('type', 'territory')
        
        player = Player.objects.get(user=request.user)
        
        # Validate flag name
        if not flag_name:
            return JsonResponse({
                'success': False,
                'error': 'Flag name is required'
            }, status=400)
        
        # Check if player can reach this location
        distance = player.distance_between(player.lat, player.lon, target_lat, target_lon)
        if distance > 50:  # Must be within 50m to place flag
            return JsonResponse({
                'success': False,
                'error': f'Too far away to place flag (need to be within 50m, currently {int(distance)}m)'
            }, status=400)
        
        # Check if location is already occupied by a flag
        existing_flag = Flag.objects.filter(
            lat__gte=target_lat - 0.0001,  # ~10m tolerance
            lat__lte=target_lat + 0.0001,
            lon__gte=target_lon - 0.0001,
            lon__lte=target_lon + 0.0001
        ).first()
        
        if existing_flag:
            return JsonResponse({
                'success': False,
                'error': 'Location already occupied by another flag'
            }, status=400)
        
        # Check cost and player funds
        placement_cost = 50000  # Base cost
        if player.cash < placement_cost:
            return JsonResponse({
                'success': False,
                'error': f'Not enough cash (need ${placement_cost:,}, have ${player.cash:,})'
            }, status=400)
        
        # Create the flag
        from django.utils import timezone
        from datetime import timedelta
        
        flag = Flag.objects.create(
            name=flag_name,
            flag_type=flag_type,
            lat=target_lat,
            lon=target_lon,
            owner=player,
            controlling_family=getattr(player, 'family_membership', None) and player.family_membership.family,
            placement_cost=placement_cost,
            invulnerable_until=timezone.now() + timedelta(hours=24)  # 24 hour protection
        )
        
        # Deduct cost from player
        player.cash -= placement_cost
        player.save(update_fields=['cash'])
        
        # Spawn NPCs around the flag
        spawned_npcs = flag.spawn_npcs()
        
        return JsonResponse({
            'success': True,
            'data': {
                'flag_id': str(flag.id),
                'name': flag.name,
                'lat': flag.lat,
                'lon': flag.lon,
                'level': flag.level,
                'hp': flag.hp,
                'max_hp': flag.max_hp,
                'income_per_hour': flag.get_hourly_income(),
                'invulnerable_until': flag.invulnerable_until.isoformat() if flag.invulnerable_until else None,
                'npcs_spawned': len(spawned_npcs)
            }
        })
        
    except (ValueError, KeyError) as e:
        return JsonResponse({
            'success': False,
            'error': 'Invalid request data'
        }, status=400)
    except Player.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Player not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_attack_flag(request):
    """API endpoint to attack a flag"""
    try:
        data = json.loads(request.body)
        flag_id = data.get('flag_id')
        
        player = Player.objects.get(user=request.user)
        flag = Flag.objects.get(id=flag_id)
        
        # Check if player can attack this flag
        can_attack, reason = flag.can_be_attacked_by(player)
        if not can_attack:
            return JsonResponse({
                'success': False,
                'error': reason
            }, status=400)
        
        # Calculate attack strength based on player stats
        attack_strength = player.strength + player.level * 5
        
        # Add weapon bonuses if player has weapons
        weapon_bonus = 0
        player_weapons = player.weapons.all()
        for pw in player_weapons[:3]:  # Max 3 weapons in combat
            weapon_bonus += pw.weapon.damage * (pw.condition / 100)
        
        total_attack_strength = int(attack_strength + weapon_bonus)
        
        # Create attack record
        attack = FlagAttack.objects.create(
            flag=flag,
            attacker=player,
            attack_strength=total_attack_strength
        )
        
        # Calculate success chance
        success_chance = attack.calculate_success_chance()
        
        # Simulate attack (for now, instant resolution)
        import random
        is_successful = random.random() < success_chance
        
        if is_successful:
            # Successful attack - transfer ownership
            flag.owner = player
            flag.controlling_family = getattr(player, 'family_membership', None) and player.family_membership.family
            flag.status = 'captured'
            flag.hp = max(1, flag.hp - total_attack_strength // 2)  # Damage the flag
            
            # Set new protection period
            from django.utils import timezone
            from datetime import timedelta
            flag.invulnerable_until = timezone.now() + timedelta(hours=6)  # 6 hour protection after capture
            flag.save()
            
            # Update attack record
            attack.status = 'successful'
            attack.damage_dealt = total_attack_strength // 2
            attack.reputation_gained = 50 + flag.level * 10
            attack.money_gained = flag.level * 1000
            
            # Reward attacker
            player.reputation += attack.reputation_gained
            player.cash += attack.money_gained
            player.save(update_fields=['reputation', 'cash'])
            
            result_message = f"Successfully captured {flag.name}!"
            
        else:
            # Failed attack
            attack.status = 'failed'
            attack.damage_dealt = total_attack_strength // 4  # Minimal damage on failure
            flag.hp = max(1, flag.hp - attack.damage_dealt)
            flag.save(update_fields=['hp'])
            
            result_message = f"Attack on {flag.name} failed!"
        
        attack.completed_at = timezone.now()
        attack.save()
        
        return JsonResponse({
            'success': True,
            'data': {
                'attack_successful': is_successful,
                'message': result_message,
                'damage_dealt': attack.damage_dealt,
                'reputation_gained': attack.reputation_gained,
                'money_gained': attack.money_gained,
                'flag': {
                    'id': str(flag.id),
                    'name': flag.name,
                    'owner': flag.owner.user.username,
                    'hp': flag.hp,
                    'max_hp': flag.max_hp,
                    'status': flag.status
                }
            }
        })
        
    except Flag.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Flag not found'
        }, status=404)
    except Player.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Player not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_get_flags(request):
    """API endpoint to get flags in player's area"""
    try:
        player = Player.objects.get(user=request.user)
        
        # Get flags within a reasonable radius (1km)
        lat_range = 0.01  # ~1km
        lon_range = 0.01  # ~1km
        
        flags = Flag.objects.filter(
            lat__gte=player.lat - lat_range,
            lat__lte=player.lat + lat_range,
            lon__gte=player.lon - lon_range,
            lon__lte=player.lon + lon_range
        ).select_related('owner', 'controlling_family')
        
        flag_data = []
        for flag in flags:
            distance = player.distance_between(player.lat, player.lon, flag.lat, flag.lon)
            can_attack, _ = flag.can_be_attacked_by(player)
            
            flag_data.append({
                'id': str(flag.id),
                'name': flag.name,
                'flag_type': flag.flag_type,
                'status': flag.status,
                'lat': flag.lat,
                'lon': flag.lon,
                'owner': flag.owner.user.username,
                'controlling_family': flag.controlling_family.name if flag.controlling_family else None,
                'level': flag.level,
                'hp': flag.hp,
                'max_hp': flag.max_hp,
                'defense_rating': flag.get_defense_strength(),
                'income_per_hour': flag.get_hourly_income(),
                'distance': int(distance),
                'can_attack': can_attack,
                'is_invulnerable': flag.is_invulnerable(),
                'is_owned_by_player': flag.owner == player
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'flags': flag_data,
                'player_location': {
                    'lat': player.lat,
                    'lon': player.lon
                }
            }
        })
        
    except Player.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Player not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def debug_player(request):
    """Debug endpoint to check player data"""
    try:
        player = Player.objects.get(user=request.user)
        debug_info = {
            'user': request.user.username,
            'player_id': str(player.id),
            'cash': player.cash,
            'bank_money': player.bank_money,
            'lat': player.lat,
            'lon': player.lon,
            'center_lat': player.center_lat,
            'center_lon': player.center_lon,
            'heat_level': player.heat_level,
            'reputation': player.reputation,
            'is_authenticated': request.user.is_authenticated,
        }
        
        return JsonResponse({
            'success': True,
            'debug': debug_info
        })
        
    except Player.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Player not found for user'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ===============================
# NPC API ENDPOINTS
# ===============================

@login_required
@require_http_methods(["GET"])
def api_get_npcs(request):
    """API endpoint to get ALL NPCs (PMBeta professional format)"""
    try:
        player = Player.objects.get(user=request.user)
        
        # Get ALL alive NPCs - let the frontend handle distance filtering for display
        # This ensures all 210 NPCs are available for rendering
        npcs = NPC.objects.filter(
            is_alive=True
        ).select_related('spawned_on_flag')
        
        print(f"DEBUG: Found {npcs.count()} alive NPCs for {player.user.username}")
        
        npc_data = []
        for npc in npcs:
            distance = player.distance_between(player.lat, player.lon, npc.lat, npc.lon)
            
            npc_data.append({
                'id': str(npc.id),
                'name': npc.name,
                'npc_type': npc.npc_type,
                'level': npc.level,
                'lat': npc.lat,
                'lon': npc.lon,
                'current_hp': npc.hp,  # Field is 'hp' not 'current_hp'
                'max_hp': npc.max_hp,
                'attack_power': npc.strength,  # Field is 'strength' not 'attack_power'
                'defense_rating': npc.defense,  # Field is 'defense' not 'defense_rating'
                'money_reward': npc.base_gold_reward,  # Field is 'base_gold_reward'
                'xp_reward': npc.base_experience_reward,  # Field is 'base_experience_reward'
                'is_alive': npc.is_alive,  # Field is boolean, not method
                'distance': int(distance),
                'respawn_time': npc.respawn_time,
                'last_death': npc.last_death.isoformat() if npc.last_death else None
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'npcs': npc_data,
                'player_location': {
                    'lat': player.lat,
                    'lon': player.lon
                }
            }
        })
        
    except Player.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Player not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_attack_npc(request):
    """API endpoint to attack an NPC"""
    try:
        data = json.loads(request.body)
        npc_id = data.get('npc_id')
        
        player = Player.objects.get(user=request.user)
        npc = NPC.objects.get(id=npc_id)
        
        # Check if NPC is alive
        if not npc.is_alive:
            return JsonResponse({
                'success': False,
                'error': 'NPC is already dead'
            }, status=400)
        
        # Check distance - must be within 50m
        distance = player.distance_between(player.lat, player.lon, npc.lat, npc.lon)
        if distance > 50:
            return JsonResponse({
                'success': False,
                'error': f'Too far from NPC (need to be within 50m, currently {int(distance)}m)'
            }, status=400)
        
        # Combat calculation
        player_attack = player.strength + player.level * 2 + random.randint(1, 20)
        npc_defense = npc.defense + random.randint(1, 10)  # Use 'defense' not 'defense_rating'
        
        damage_dealt = max(1, player_attack - npc_defense)
        npc.hp = max(0, npc.hp - damage_dealt)  # Use 'hp' not 'current_hp'
        
        victory = npc.hp <= 0
        
        if victory:
            # NPC defeated
            npc.last_death = timezone.now()
            npc.hp = 0
            npc.is_alive = False  # Set boolean field
            
            # Calculate rewards based on NPC level and type
            money_gained = npc.base_gold_reward + random.randint(0, npc.level * 100)
            xp_gained = npc.base_experience_reward + npc.level * 10
            reputation_gained = max(1, npc.level // 2)
            
            # Give rewards to player
            player.cash += money_gained
            player.experience += xp_gained
            player.reputation += reputation_gained
            
            # Level up check (simple XP system)
            xp_needed = player.level * 1000
            if player.experience >= xp_needed:
                player.level += 1
                player.experience -= xp_needed
                # Increase stats on level up
                player.strength += 2
                player.hp = min(100, player.hp + 10)  # Restore some HP on level up
            
            player.save()
            
            result_message = f"Defeated {npc.name}! Gained ${money_gained:,}, {xp_gained} XP, and {reputation_gained} reputation."
            
        else:
            # NPC still alive, counter-attack
            npc_attack = npc.strength + random.randint(1, 15)  # Use 'strength' not 'attack_power'
            player_defense = player.strength // 2 + random.randint(1, 10)
            
            damage_received = max(1, npc_attack - player_defense)
            player.hp = max(1, player.hp - damage_received)  # Player can't die for now
            player.save(update_fields=['hp'])
            
            result_message = f"Attacked {npc.name} for {damage_dealt} damage. {npc.name} counter-attacked for {damage_received} damage!"
            money_gained = 0
            xp_gained = 0
            reputation_gained = 0
        
        npc.save()
        
        return JsonResponse({
            'success': True,
            'data': {
                'victory': victory,
                'message': result_message,
                'damage_dealt': damage_dealt,
                'money_gained': money_gained,
                'xp_gained': xp_gained,
                'reputation_gained': reputation_gained,
                'player_hp': player.hp,
                'npc': {
                    'id': str(npc.id),
                    'name': npc.name,
                    'current_hp': npc.hp,  # Use 'hp' for current_hp
                    'max_hp': npc.max_hp,
                    'is_alive': npc.is_alive  # Use boolean field
                }
            }
        })
        
    except NPC.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'NPC not found'
        }, status=404)
    except Player.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Player not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ===============================
# RESOURCE API ENDPOINTS
# ===============================

@login_required
@require_http_methods(["GET"])
def api_get_resources(request):
    """API endpoint to get resource nodes in player's area"""
    try:
        player = Player.objects.get(user=request.user)
        
        # Get resources within a reasonable radius (1km)
        lat_range = 0.01  # ~1km
        lon_range = 0.01  # ~1km
        
        resources = ResourceNode.objects.filter(
            lat__gte=player.lat - lat_range,
            lat__lte=player.lat + lat_range,
            lon__gte=player.lon - lon_range,
            lon__lte=player.lon + lon_range
        )
        
        resource_data = []
        for resource in resources:
            distance = player.distance_between(player.lat, player.lon, resource.lat, resource.lon)
            
            resource_data.append({
                'id': str(resource.id),
                'resource_type': resource.resource_type,
                'level': resource.level,
                'lat': resource.lat,
                'lon': resource.lon,
                'quantity': resource.base_resource_amount,  # Use base amount as current quantity
                'max_quantity': resource.base_resource_amount * 2,  # Max is twice base
                'can_harvest': resource.can_harvest(),
                'distance': int(distance),
                'respawn_time': resource.respawn_time,
                'last_harvest': resource.last_harvested.isoformat() if resource.last_harvested else None
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'resources': resource_data,
                'player_location': {
                    'lat': player.lat,
                    'lon': player.lon
                }
            }
        })
        
    except Player.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Player not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_harvest_resource(request):
    """API endpoint to harvest a resource node"""
    try:
        data = json.loads(request.body)
        resource_id = data.get('resource_id')
        
        player = Player.objects.get(user=request.user)
        resource = ResourceNode.objects.get(id=resource_id)
        
        # Check if resource can be harvested
        if not resource.can_harvest():
            return JsonResponse({
                'success': False,
                'error': 'Resource is depleted and not ready for harvest'
            }, status=400)
        
        # Check distance - must be within 50m
        distance = player.distance_between(player.lat, player.lon, resource.lat, resource.lon)
        if distance > 50:
            return JsonResponse({
                'success': False,
                'error': f'Too far from resource (need to be within 50m, currently {int(distance)}m)'
            }, status=400)
        
        # Harvest calculation based on resource type and player level
        harvest_amount = min(resource.quantity, 1 + random.randint(0, player.level // 5))
        
        # Calculate rewards based on resource type
        resource_rewards = {
            'tree': {'money': 100, 'xp': 25},
            'iron_mine': {'money': 250, 'xp': 40},
            'gold_mine': {'money': 500, 'xp': 50},
            'stone_quarry': {'money': 150, 'xp': 30},
            'herb_patch': {'money': 75, 'xp': 35},
            'ruins': {'money': 400, 'xp': 60},
            'cave': {'money': 300, 'xp': 45},
            'well': {'money': 50, 'xp': 20}
        }
        
        base_rewards = resource_rewards.get(resource.resource_type, {'money': 100, 'xp': 25})
        money_gained = base_rewards['money'] * harvest_amount * resource.level
        xp_gained = base_rewards['xp'] * harvest_amount * resource.level
        
        # Apply harvest
        resource.quantity = max(0, resource.quantity - harvest_amount)
        if resource.quantity == 0:
            resource.last_harvest = timezone.now()
        
        # Give rewards to player
        player.cash += money_gained
        player.experience += xp_gained
        
        # Level up check
        xp_needed = player.level * 1000
        if player.experience >= xp_needed:
            player.level += 1
            player.experience -= xp_needed
            player.strength += 2
            player.hp = min(100, player.hp + 10)
        
        player.save()
        resource.save()
        
        result_message = f"Harvested {harvest_amount} {resource.resource_type.replace('_', ' ')}! Gained ${money_gained:,} and {xp_gained} XP."
        
        return JsonResponse({
            'success': True,
            'data': {
                'resources_gained': harvest_amount,
                'message': result_message,
                'money_gained': money_gained,
                'xp_gained': xp_gained,
                'resource': {
                    'id': str(resource.id),
                    'resource_type': resource.resource_type,
                    'quantity': resource.quantity,
                    'max_quantity': resource.max_quantity,
                    'can_harvest': resource.can_harvest()
                }
            }
        })
        
    except ResourceNode.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Resource node not found'
        }, status=404)
    except Player.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Player not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ===============================
# DEBUG ENDPOINTS
# ===============================

@require_http_methods(["GET"])
def debug_login_status(request):
    """Debug endpoint to check login status"""
    debug_info = {
        'is_authenticated': request.user.is_authenticated,
        'username': request.user.username if request.user.is_authenticated else None,
        'session_key': request.session.session_key,
        'csrf_token': request.META.get('CSRF_COOKIE'),
        'user_agent': request.META.get('HTTP_USER_AGENT'),
        'remote_addr': request.META.get('REMOTE_ADDR'),
    }
    
    return JsonResponse({
        'success': True,
        'debug': debug_info
    })


@require_http_methods(["GET"])
def debug_auto_login(request):
    """TEMPORARY: Auto-login for testing purposes"""
    from django.contrib.auth import login
    from django.contrib.auth.models import User
    
    try:
        # Auto-login as testuser for testing
        user = User.objects.get(username='testuser')
        login(request, user)
        return redirect('/game/')
    except User.DoesNotExist:
        return JsonResponse({
            'error': 'Test user not found. Available users: ' + ', '.join([u.username for u in User.objects.all()])
        })


# ===============================
# PK ECHOES COMPATIBLE ENDPOINTS
# ===============================

@login_required
@require_http_methods(["GET"])
def api_map_data(request):
    """PK Echoes compatible map data endpoint"""
    try:
        player = Player.objects.get(user=request.user)
        
        # Get position and radius from query params (PK Echoes format)
        lat = float(request.GET.get('lat', player.lat))
        lon = float(request.GET.get('lon', player.lon))
        radius = float(request.GET.get('radius', 0.0045))  # Default ~500m
        
        # Get flags (territories) in the area
        flags = Flag.objects.filter(
            lat__gte=lat - radius,
            lat__lte=lat + radius,
            lon__gte=lon - radius,
            lon__lte=lon + radius
        ).select_related('owner')
        
        # Get NPCs in the area (flag-based only)
        npcs = NPC.objects.filter(
            spawned_on_flag__in=flags,
            is_alive=True
        ).select_related('spawned_on_flag')
        
        # Get resources in the area
        resources = ResourceNode.objects.filter(
            lat__gte=lat - radius,
            lat__lte=lat + radius,
            lon__gte=lon - radius,
            lon__lte=lon + radius
        )
        
        # Format data in PK Echoes expected structure
        map_data = {
            'territories': [
                {
                    'id': str(flag.id),
                    'name': flag.name,
                    'type': flag.flag_type,
                    'lat': flag.lat,
                    'lon': flag.lon,
                    'owner': flag.owner.user.username,
                    'level': flag.level,
                    'hp': flag.hp,
                    'maxHp': flag.max_hp,
                    'status': flag.status,
                    'isInvulnerable': flag.is_invulnerable(),
                    'placedAt': flag.placed_at.isoformat(),
                }
                for flag in flags
            ],
            'npcs': [
                {
                    'id': str(npc.id),
                    'name': npc.name,
                    'type': npc.npc_type,
                    'lat': npc.lat,
                    'lon': npc.lon,
                    'level': npc.level,
                    'hp': npc.hp,
                    'maxHp': npc.max_hp,
                    'isAlive': npc.is_alive,
                    'territoryId': str(npc.spawned_on_flag.id),
                    'lastDeath': npc.last_death.isoformat() if npc.last_death else None,
                }
                for npc in npcs
            ],
            'resources': [
                {
                    'id': str(res.id),
                    'type': res.resource_type,
                    'lat': res.lat,
                    'lon': res.lon,
                    'level': res.level,
                    'canHarvest': res.can_harvest(),
                }
                for res in resources
            ],
            'playerPosition': {
                'lat': player.lat,
                'lon': player.lon
            },
            'loadRadius': radius
        }
        
        return JsonResponse({
            'success': True,
            'data': map_data
        })
        
    except Player.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Player not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_nearby_players(request):
    """PK Echoes compatible nearby players endpoint"""
    try:
        player = Player.objects.get(user=request.user)
        
        # Get other players within 1km radius
        lat_range = 0.01  # ~1km
        lon_range = 0.01
        
        nearby_players = Player.objects.filter(
            lat__gte=player.lat - lat_range,
            lat__lte=player.lat + lat_range,
            lon__gte=player.lon - lon_range,
            lon__lte=player.lon + lon_range
        ).exclude(id=player.id).select_related('user')
        
        players_data = [
            {
                'id': str(p.id),
                'username': p.user.username,
                'lat': p.lat,
                'lon': p.lon,
                'level': p.level,
                'hp': p.hp,
                'reputation': p.reputation,
                'lastActivity': p.last_activity.isoformat(),
            }
            for p in nearby_players
        ]
        
        return JsonResponse(players_data, safe=False)
        
    except Player.DoesNotExist:
        return JsonResponse([], safe=False)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_territories(request):
    """PK Echoes compatible territories endpoint (persistent active territory)"""
    try:
        player = Player.objects.get(user=request.user)
        
        # Get player's owned flags/territories
        territories = Flag.objects.filter(owner=player).order_by('-placed_at')
        
        territories_data = [
            {
                'id': str(flag.id),
                'name': flag.name,
                'type': flag.flag_type,
                'lat': flag.lat,
                'lon': flag.lon,
                'level': flag.level,
                'hp': flag.hp,
                'maxHp': flag.max_hp,
                'status': flag.status,
                'incomePerHour': flag.get_hourly_income(),
                'defenseRating': flag.get_defense_strength(),
                'placedAt': flag.placed_at.isoformat(),
                'npcCount': flag.spawned_npcs.filter(is_alive=True).count(),
            }
            for flag in territories
        ]
        
        # Return the most recent territory as "active" (PK Echoes pattern)
        active_territory = territories_data[0] if territories_data else None
        
        return JsonResponse({
            'activeTerritory': active_territory,
            'allTerritories': territories_data
        })
        
    except Player.DoesNotExist:
        return JsonResponse({
            'activeTerritory': None,
            'allTerritories': []
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


# ===============================
# PVE COMBAT API ENDPOINTS
# ===============================

@login_required
@require_http_methods(["POST"])
def api_combat_start(request):
    """Start a PvE combat session with an NPC"""
    try:
        import json
        from .combat_engine import CombatEngine
        
        player = Player.objects.get(user=request.user)
        data = json.loads(request.body)
        npc_id = data.get('npc_id')
        
        if not npc_id:
            return JsonResponse({
                'success': False,
                'error': 'NPC ID is required'
            }, status=400)
        
        try:
            npc = NPC.objects.get(id=npc_id, is_alive=True)
        except NPC.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'NPC not found or already defeated'
            }, status=404)
        
        # Check if player is close enough to the NPC
        distance = abs(player.lat - npc.lat) + abs(player.lon - npc.lon)
        if distance > 0.001:  # ~100m
            return JsonResponse({
                'success': False,
                'error': 'You are too far from the NPC'
            }, status=400)
        
        # Check for existing combat session
        existing_combat = CombatSession.objects.filter(
            player=player,
            is_active=True
        ).first()
        
        if existing_combat:
            return JsonResponse({
                'success': False,
                'error': 'You are already in combat'
            }, status=400)
        
        # Create new combat session
        from datetime import timedelta
        combat_session = CombatSession.objects.create(
            player=player,
            npc=npc,
            player_hp=player.hp,
            npc_hp=npc.hp,
            player_current_hp=player.hp,
            npc_current_hp=npc.hp,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Initialize combat engine
        combat_engine = CombatEngine(combat_session)
        combat_data = combat_engine.get_combat_state()
        
        return JsonResponse({
            'success': True,
            'combat_session_id': str(combat_session.id),
            'combat_data': combat_data
        })
        
    except Player.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Player not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_combat_action(request):
    """Execute a combat action (attack, defend, use item, flee)"""
    try:
        import json
        from .combat_engine import CombatEngine
        
        player = Player.objects.get(user=request.user)
        data = json.loads(request.body)
        
        combat_session_id = data.get('combat_session_id')
        action_type = data.get('action_type')  # 'attack', 'defend', 'item', 'flee'
        weapon_id = data.get('weapon_id')  # For attack actions
        item_id = data.get('item_id')  # For item actions
        
        if not combat_session_id or not action_type:
            return JsonResponse({
                'success': False,
                'error': 'Combat session ID and action type are required'
            }, status=400)
        
        try:
            combat_session = CombatSession.objects.get(
                id=combat_session_id,
                player=player,
                is_active=True
            )
        except CombatSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Combat session not found or not active'
            }, status=404)
        
        # Initialize combat engine
        combat_engine = CombatEngine(combat_session)
        
        # Execute the requested action
        if action_type == 'attack':
            weapon = None
            if weapon_id:
                try:
                    weapon = Weapon.objects.get(id=weapon_id, owner=player)
                except Weapon.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'Weapon not found or not owned by player'
                    }, status=400)
            
            result = combat_engine.player_attack(weapon)
            
        elif action_type == 'defend':
            result = combat_engine.player_defend()
            
        elif action_type == 'item':
            if not item_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Item ID is required for item actions'
                }, status=400)
            
            try:
                item = Item.objects.get(id=item_id, owner=player)
            except Item.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Item not found or not owned by player'
                }, status=400)
            
            result = combat_engine.use_item(item)
            
        elif action_type == 'flee':
            result = combat_engine.attempt_flee()
            
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid action type'
            }, status=400)
        
        # Get updated combat state
        combat_data = combat_engine.get_combat_state()
        
        return JsonResponse({
            'success': True,
            'action_result': result,
            'combat_data': combat_data
        })
        
    except Player.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Player not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_combat_status(request):
    """Get the current combat session status and state"""
    try:
        player = Player.objects.get(user=request.user)
        
        # Get active combat session
        combat_session = CombatSession.objects.filter(
            player=player,
            is_active=True
        ).first()
        
        if not combat_session:
            return JsonResponse({
                'success': True,
                'in_combat': False,
                'combat_data': None
            })
        
        # Initialize combat engine and get state
        from .combat_engine import CombatEngine
        combat_engine = CombatEngine(combat_session)
        combat_data = combat_engine.get_combat_state()
        
        return JsonResponse({
            'success': True,
            'in_combat': True,
            'combat_session_id': str(combat_session.id),
            'combat_data': combat_data
        })
        
    except Player.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Player not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
