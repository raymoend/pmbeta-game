"""
PMBeta - Parallel Kingdom Style Views/API
Complete API system for authentic PK gameplay
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.utils import timezone
from django.db import transaction
import json
import random
import math
from datetime import timedelta

from .models import (
    PKPlayer, PKTerritory, PKResource, PKCombat, PKTrade, 
    PKMessage, PKAlliance, PKAllianceMember, PKGameEvent
)


# ===============================
# CORE PK GAME VIEWS
# ===============================

def index(request):
    """Homepage - redirect to PK game if logged in"""
    if request.user.is_authenticated:
        return redirect('pk_game')
    
    return render(request, 'pk/index.html', {
        'title': 'PMBeta - Parallel Kingdom Clone'
    })


def register(request):
    """User registration for PK"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Welcome to PMBeta, {username}!')
            
            # Create PK player at random spawn location
            spawn_locations = [
                (40.7589, -73.9851),  # New York
                (51.5074, -0.1278),   # London  
                (35.6762, 139.6503),  # Tokyo
                (37.7749, -122.4194), # San Francisco
            ]
            lat, lon = random.choice(spawn_locations)
            
            pk_player = PKPlayer.objects.create(
                user=user,
                lat=lat,
                lon=lon
            )
            
            login(request, user)
            return redirect('pk_game')
    else:
        form = UserCreationForm()
    
    return render(request, 'pk/register.html', {'form': form})


@login_required
def pk_game(request):
    """Main Parallel Kingdom game interface"""
    try:
        player = PKPlayer.objects.get(user=request.user)
        player.is_online = True
        player.save()
    except PKPlayer.DoesNotExist:
        # Create player if doesn't exist
        spawn_locations = [
            (40.7589, -73.9851),  # New York
            (51.5074, -0.1278),   # London  
            (35.6762, 139.6503),  # Tokyo
            (37.7749, -122.4194), # San Francisco
        ]
        lat, lon = random.choice(spawn_locations)
        
        player = PKPlayer.objects.create(
            user=request.user,
            lat=lat,
            lon=lon,
            is_online=True
        )
    
    context = {
        'player': player,
        'pk_settings': {
            'MOVEMENT_COST': 1,  # Energy per movement
            'HARVEST_COST': 2,   # Energy per harvest
            'COMBAT_COST': 3,    # Energy per combat
            'MAX_ENERGY': 100,
            'MAX_FOOD': 500,
            'ENERGY_REGEN_MINUTES': 5,
            'FOOD_CONSUMPTION_MINUTES': 10,
        }
    }
    
    return render(request, 'pk/game.html', context)


# ===============================
# PK PLAYER API
# ===============================

@login_required
@require_http_methods(["GET"])
def api_player_status(request):
    """Get player's current status and resources"""
    try:
        player = PKPlayer.objects.get(user=request.user)
        player.regenerate_energy()
        player.consume_food()
        player.save()
        
        # Get alliance info if member
        alliance_info = None
        alliance_membership = player.alliance_memberships.first()
        if alliance_membership:
            alliance_info = {
                'name': alliance_membership.alliance.name,
                'rank': alliance_membership.rank,
                'member_count': alliance_membership.alliance.member_count
            }
        
        return JsonResponse({
            'success': True,
            'player': {
                'id': str(player.id),
                'username': player.user.username,
                'level': player.level,
                'food': player.food,
                'energy': player.energy,
                'gold': player.gold,
                'lumber': player.lumber,
                'stone': player.stone,
                'ore': player.ore,
                'might': player.might,
                'defense': player.defense,
                'health': player.health,
                'max_health': player.max_health,
                'lat': player.lat,
                'lon': player.lon,
                'is_online': player.is_online,
                'alliance': alliance_info,
                'avatar': player.avatar,
                'status_message': player.status_message,
            }
        })
        
    except PKPlayer.DoesNotExist:
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
def api_player_move(request):
    """Move player to new coordinates (PK style)"""
    try:
        data = json.loads(request.body)
        new_lat = float(data.get('lat'))
        new_lon = float(data.get('lon'))
        
        player = PKPlayer.objects.get(user=request.user)
        
        # Calculate distance and energy cost
        distance = player.distance_between(player.lat, player.lon, new_lat, new_lon)
        energy_cost = max(1, int(distance / 100))  # 1 energy per 100m
        
        # Check if player can move
        if not player.can_perform_action(energy_cost=energy_cost):
            return JsonResponse({
                'success': False,
                'error': f'Not enough energy (need {energy_cost}, have {player.energy})'
            }, status=400)
        
        # Update player position
        player.lat = new_lat
        player.lon = new_lon
        player.energy -= energy_cost
        player.save()
        
        return JsonResponse({
            'success': True,
            'energy_used': energy_cost,
            'remaining_energy': player.energy,
            'new_position': {
                'lat': player.lat,
                'lon': player.lon
            }
        })
        
    except (ValueError, KeyError):
        return JsonResponse({
            'success': False,
            'error': 'Invalid coordinates'
        }, status=400)
    except PKPlayer.DoesNotExist:
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
# PK MAP DATA API
# ===============================

@login_required
@require_http_methods(["GET"])
def api_map_data(request):
    """Get map data around player's position (PK compatible)"""
    try:
        player = PKPlayer.objects.get(user=request.user)
        
        # Get radius from request (default 1km)
        radius = float(request.GET.get('radius', 0.01))  # ~1km in degrees
        
        # Get territories in area
        territories = PKTerritory.objects.filter(
            lat__gte=player.lat - radius,
            lat__lte=player.lat + radius,
            lon__gte=player.lon - radius,
            lon__lte=player.lon + radius,
            is_active=True
        ).select_related('owner')
        
        # Get resources in area
        resources = PKResource.objects.filter(
            lat__gte=player.lat - radius,
            lat__lte=player.lat + radius,
            lon__gte=player.lon - radius,
            lon__lte=player.lon + radius,
            is_depleted=False
        )
        
        # Get nearby players
        nearby_players = PKPlayer.objects.filter(
            lat__gte=player.lat - radius,
            lat__lte=player.lat + radius,
            lon__gte=player.lon - radius,
            lon__lte=player.lon + radius,
            is_online=True
        ).exclude(id=player.id)
        
        map_data = {
            'player_position': {
                'lat': player.lat,
                'lon': player.lon
            },
            'radius': radius,
            'territories': [
                {
                    'id': str(t.id),
                    'name': t.name,
                    'type': t.territory_type,
                    'owner': t.owner.user.username,
                    'level': t.level,
                    'lat': t.lat,
                    'lon': t.lon,
                    'health': t.health,
                    'max_health': t.max_health,
                    'is_protected': t.is_protected(),
                    'distance': int(player.distance_between(player.lat, player.lon, t.lat, t.lon))
                }
                for t in territories
            ],
            'resources': [
                {
                    'id': str(r.id),
                    'type': r.resource_type,
                    'level': r.level,
                    'lat': r.lat,
                    'lon': r.lon,
                    'health': r.health,
                    'max_health': r.max_health,
                    'yields': {
                        'lumber': r.lumber_yield,
                        'stone': r.stone_yield,
                        'ore': r.ore_yield,
                        'gold': r.gold_yield,
                        'food': r.food_yield
                    },
                    'distance': int(player.distance_between(player.lat, player.lon, r.lat, r.lon))
                }
                for r in resources
            ],
            'players': [
                {
                    'id': str(p.id),
                    'username': p.user.username,
                    'level': p.level,
                    'lat': p.lat,
                    'lon': p.lon,
                    'might': p.might,
                    'distance': int(player.distance_between(player.lat, player.lon, p.lat, p.lon))
                }
                for p in nearby_players
            ]
        }
        
        return JsonResponse({
            'success': True,
            'map_data': map_data
        })
        
    except PKPlayer.DoesNotExist:
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
# PK RESOURCE GATHERING API
# ===============================

@login_required
@require_http_methods(["POST"])
def api_harvest_resource(request):
    """Harvest a resource node (PK style)"""
    try:
        data = json.loads(request.body)
        resource_id = data.get('resource_id')
        
        player = PKPlayer.objects.get(user=request.user)
        resource = PKResource.objects.get(id=resource_id)
        
        # Check distance (must be within 50m)
        distance = player.distance_between(player.lat, player.lon, resource.lat, resource.lon)
        if distance > 50:
            return JsonResponse({
                'success': False,
                'error': f'Too far from resource (need to be within 50m, currently {int(distance)}m)'
            }, status=400)
        
        # Check energy cost
        energy_cost = 2
        if not player.can_perform_action(energy_cost=energy_cost):
            return JsonResponse({
                'success': False,
                'error': f'Not enough energy (need {energy_cost}, have {player.energy})'
            }, status=400)
        
        # Harvest the resource
        yields = resource.harvest(player)
        if not yields:
            return JsonResponse({
                'success': False,
                'error': 'Resource is depleted'
            }, status=400)
        
        # Apply yields to player
        player.lumber += yields['lumber']
        player.stone += yields['stone']
        player.ore += yields['ore']
        player.gold += yields['gold']
        player.food += yields['food']
        player.energy -= energy_cost
        player.save()
        
        # Create event
        PKGameEvent.objects.create(
            event_type='resource',
            player=player,
            title='Resource Harvested',
            description=f'Harvested {resource.get_resource_type_display()}',
            lat=resource.lat,
            lon=resource.lon,
            event_data=yields
        )
        
        return JsonResponse({
            'success': True,
            'yields': yields,
            'energy_used': energy_cost,
            'remaining_energy': player.energy,
            'resource': {
                'health': resource.health,
                'is_depleted': resource.is_depleted
            }
        })
        
    except PKResource.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Resource not found'
        }, status=404)
    except PKPlayer.DoesNotExist:
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
# PK TERRITORY API
# ===============================

@login_required
@require_http_methods(["POST"])
def api_place_territory(request):
    """Place a new territory/flag (PK style)"""
    try:
        data = json.loads(request.body)
        territory_name = data.get('name', '').strip()
        territory_type = data.get('type', 'flag')
        target_lat = float(data.get('lat'))
        target_lon = float(data.get('lon'))
        
        player = PKPlayer.objects.get(user=request.user)
        
        # Validate name
        if not territory_name:
            return JsonResponse({
                'success': False,
                'error': 'Territory name is required'
            }, status=400)
        
        # Check distance (must be within 25m)
        distance = player.distance_between(player.lat, player.lon, target_lat, target_lon)
        if distance > 25:
            return JsonResponse({
                'success': False,
                'error': f'Too far to place territory (need to be within 25m, currently {int(distance)}m)'
            }, status=400)
        
        # Check for existing territories nearby (50m minimum distance)
        nearby_territories = PKTerritory.objects.filter(
            lat__gte=target_lat - 0.0005,  # ~50m
            lat__lte=target_lat + 0.0005,
            lon__gte=target_lon - 0.0005,
            lon__lte=target_lon + 0.0005,
            is_active=True
        )
        
        if nearby_territories.exists():
            return JsonResponse({
                'success': False,
                'error': 'Too close to existing territory'
            }, status=400)
        
        # Check resource costs
        costs = {
            'flag': {'lumber': 10, 'stone': 5, 'gold': 50},
            'outpost': {'lumber': 25, 'stone': 15, 'gold': 200},
            'city': {'lumber': 100, 'stone': 50, 'gold': 1000},
        }
        
        cost = costs.get(territory_type, costs['flag'])
        
        if (player.lumber < cost['lumber'] or 
            player.stone < cost['stone'] or 
            player.gold < cost['gold']):
            return JsonResponse({
                'success': False,
                'error': f"Not enough resources (need {cost['lumber']} lumber, {cost['stone']} stone, {cost['gold']} gold)"
            }, status=400)
        
        # Create territory
        with transaction.atomic():
            territory = PKTerritory.objects.create(
                owner=player,
                territory_type=territory_type,
                name=territory_name,
                lat=target_lat,
                lon=target_lon,
                protection_expires=timezone.now() + timedelta(hours=24)  # 24h newbie protection
            )
            
            # Deduct resources
            player.lumber -= cost['lumber']
            player.stone -= cost['stone'] 
            player.gold -= cost['gold']
            player.save()
            
            # Create event
            PKGameEvent.objects.create(
                event_type='territory',
                player=player,
                title='Territory Placed',
                description=f'Placed {territory_type}: {territory_name}',
                lat=target_lat,
                lon=target_lon,
                event_data={'territory_id': str(territory.id)}
            )
        
        return JsonResponse({
            'success': True,
            'territory': {
                'id': str(territory.id),
                'name': territory.name,
                'type': territory.territory_type,
                'lat': territory.lat,
                'lon': territory.lon,
                'level': territory.level,
                'protection_expires': territory.protection_expires.isoformat()
            },
            'cost': cost
        })
        
    except (ValueError, KeyError):
        return JsonResponse({
            'success': False,
            'error': 'Invalid request data'
        }, status=400)
    except PKPlayer.DoesNotExist:
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
def api_collect_territory_resources(request):
    """Collect resources from player's territories"""
    try:
        data = json.loads(request.body)
        territory_id = data.get('territory_id')
        
        player = PKPlayer.objects.get(user=request.user)
        territory = PKTerritory.objects.get(id=territory_id, owner=player)
        
        # Check distance (must be within 50m)
        distance = player.distance_between(player.lat, player.lon, territory.lat, territory.lon)
        if distance > 50:
            return JsonResponse({
                'success': False,
                'error': f'Too far from territory (need to be within 50m, currently {int(distance)}m)'
            }, status=400)
        
        # Collect resources
        collected = territory.collect_resources()
        
        if not collected:
            return JsonResponse({
                'success': False,
                'error': 'No resources available to collect (need at least 1 hour since last collection)'
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'collected': collected,
            'player_resources': {
                'lumber': player.lumber,
                'stone': player.stone,
                'ore': player.ore,
                'gold': player.gold
            }
        })
        
    except PKTerritory.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Territory not found or not owned by player'
        }, status=404)
    except PKPlayer.DoesNotExist:
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
# PK COMBAT API
# ===============================

@login_required
@require_http_methods(["POST"])
def api_attack_player(request):
    """Attack another player (PK PvP combat)"""
    try:
        data = json.loads(request.body)
        target_player_id = data.get('target_player_id')
        
        attacker = PKPlayer.objects.get(user=request.user)
        defender = PKPlayer.objects.get(id=target_player_id)
        
        # Check distance (must be within 100m)
        distance = attacker.distance_between(attacker.lat, attacker.lon, defender.lat, defender.lon)
        if distance > 100:
            return JsonResponse({
                'success': False,
                'error': f'Too far to attack (need to be within 100m, currently {int(distance)}m)'
            }, status=400)
        
        # Check energy cost
        energy_cost = 3
        if not attacker.can_perform_action(energy_cost=energy_cost):
            return JsonResponse({
                'success': False,
                'error': f'Not enough energy (need {energy_cost}, have {attacker.energy})'
            }, status=400)
        
        # Calculate combat results (simplified PK-style)
        attacker_power = attacker.might + random.randint(-5, 5)
        defender_power = defender.defense + random.randint(-5, 5)
        
        is_victory = attacker_power > defender_power
        
        # Calculate rewards/losses
        if is_victory:
            # Attacker wins - steals resources
            gold_stolen = min(defender.gold, max(10, defender.gold // 20))  # 5% of gold, min 10
            lumber_stolen = min(defender.lumber, defender.lumber // 10)    # 10% of lumber
            stone_stolen = min(defender.stone, defender.stone // 10)       # 10% of stone
            
            attacker.gold += gold_stolen
            attacker.lumber += lumber_stolen
            attacker.stone += stone_stolen
            
            defender.gold -= gold_stolen
            defender.lumber -= lumber_stolen
            defender.stone -= stone_stolen
            
            result_msg = f"Victory! Stole {gold_stolen} gold, {lumber_stolen} lumber, {stone_stolen} stone"
        else:
            # Attacker loses
            gold_stolen = lumber_stolen = stone_stolen = 0
            result_msg = "Defeat! No resources gained"
        
        # Update players
        attacker.energy -= energy_cost
        attacker.save()
        defender.save()
        
        # Record combat
        combat = PKCombat.objects.create(
            combat_type='pvp',
            attacker=attacker,
            defender=defender,
            attacker_might=attacker_power,
            defender_might=defender_power,
            winner='attacker' if is_victory else 'defender',
            gold_transferred=gold_stolen,
            lumber_transferred=lumber_stolen,
            stone_transferred=stone_stolen,
            lat=attacker.lat,
            lon=attacker.lon
        )
        
        # Create events
        PKGameEvent.objects.create(
            event_type='combat',
            player=attacker,
            title='Combat Result',
            description=result_msg,
            lat=attacker.lat,
            lon=attacker.lon,
            event_data={'combat_id': str(combat.id), 'victory': is_victory}
        )
        
        return JsonResponse({
            'success': True,
            'victory': is_victory,
            'message': result_msg,
            'combat_results': {
                'attacker_power': attacker_power,
                'defender_power': defender_power,
                'gold_transferred': gold_stolen,
                'lumber_transferred': lumber_stolen,
                'stone_transferred': stone_stolen
            },
            'remaining_energy': attacker.energy
        })
        
    except PKPlayer.DoesNotExist:
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
# PK TRADING API
# ===============================

@login_required
@require_http_methods(["POST"])
def api_create_trade(request):
    """Create a trade offer (PK trading system)"""
    try:
        data = json.loads(request.body)
        
        player = PKPlayer.objects.get(user=request.user)
        recipient_username = data.get('recipient_username')
        
        # Trade offer (what player gives)
        offer = {
            'gold': int(data.get('offer_gold', 0)),
            'lumber': int(data.get('offer_lumber', 0)),
            'stone': int(data.get('offer_stone', 0)),
            'ore': int(data.get('offer_ore', 0)),
            'food': int(data.get('offer_food', 0)),
        }
        
        # Trade request (what player wants)
        request_items = {
            'gold': int(data.get('request_gold', 0)),
            'lumber': int(data.get('request_lumber', 0)),
            'stone': int(data.get('request_stone', 0)),
            'ore': int(data.get('request_ore', 0)),
            'food': int(data.get('request_food', 0)),
        }
        
        # Find recipient
        try:
            recipient = PKPlayer.objects.get(user__username=recipient_username)
        except PKPlayer.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Recipient player not found'
            }, status=404)
        
        # Check if player has offered resources
        if (player.gold < offer['gold'] or 
            player.lumber < offer['lumber'] or
            player.stone < offer['stone'] or
            player.ore < offer['ore'] or
            player.food < offer['food']):
            return JsonResponse({
                'success': False,
                'error': 'Not enough resources to make this offer'
            }, status=400)
        
        # Create trade
        trade = PKTrade.objects.create(
            trade_type='player',
            initiator=player,
            recipient=recipient,
            offer_gold=offer['gold'],
            offer_lumber=offer['lumber'],
            offer_stone=offer['stone'],
            offer_ore=offer['ore'],
            offer_food=offer['food'],
            request_gold=request_items['gold'],
            request_lumber=request_items['lumber'],
            request_stone=request_items['stone'],
            request_ore=request_items['ore'],
            request_food=request_items['food'],
            expires_at=timezone.now() + timedelta(days=3)  # 3 day expiry
        )
        
        # Create notification for recipient
        PKMessage.objects.create(
            message_type='system',
            recipient=recipient,
            subject='New Trade Offer',
            content=f'{player.user.username} has sent you a trade offer!'
        )
        
        return JsonResponse({
            'success': True,
            'trade_id': str(trade.id),
            'expires_at': trade.expires_at.isoformat()
        })
        
    except PKPlayer.DoesNotExist:
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
# PK MESSAGING API
# ===============================

@login_required
@require_http_methods(["GET"])
def api_get_messages(request):
    """Get player's messages"""
    try:
        player = PKPlayer.objects.get(user=request.user)
        
        messages = PKMessage.objects.filter(
            recipient=player,
            is_deleted_by_recipient=False
        )[:50]  # Last 50 messages
        
        message_data = []
        for msg in messages:
            message_data.append({
                'id': str(msg.id),
                'type': msg.message_type,
                'sender': msg.sender.user.username if msg.sender else 'System',
                'subject': msg.subject,
                'content': msg.content,
                'is_read': msg.is_read,
                'created_at': msg.created_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'messages': message_data
        })
        
    except PKPlayer.DoesNotExist:
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
# PK WORLD GENERATION
# ===============================

@login_required  
@require_http_methods(["POST"])
def api_spawn_world_content(request):
    """Spawn resources around player (admin/dev function)"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Admin access required'}, status=403)
    
    try:
        data = json.loads(request.body)
        center_lat = float(data.get('lat'))
        center_lon = float(data.get('lon'))
        spawn_count = int(data.get('count', 20))
        
        resources_created = []
        
        for _ in range(spawn_count):
            # Random position within 2km radius
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, 0.02)  # ~2km in degrees
            
            resource_lat = center_lat + distance * math.cos(angle)
            resource_lon = center_lon + distance * math.sin(angle)
            
            # Random resource type
            resource_types = ['tree', 'rock', 'mine', 'ruins']
            resource_type = random.choice(resource_types)
            
            # Set yields based on type
            yields = {
                'tree': {'lumber_yield': 25, 'stone_yield': 0, 'ore_yield': 0, 'gold_yield': 5, 'food_yield': 0},
                'rock': {'lumber_yield': 0, 'stone_yield': 20, 'ore_yield': 5, 'gold_yield': 2, 'food_yield': 0},
                'mine': {'lumber_yield': 0, 'stone_yield': 5, 'ore_yield': 15, 'gold_yield': 10, 'food_yield': 0},
                'ruins': {'lumber_yield': 10, 'stone_yield': 10, 'ore_yield': 10, 'gold_yield': 50, 'food_yield': 20}
            }
            
            resource = PKResource.objects.create(
                resource_type=resource_type,
                lat=resource_lat,
                lon=resource_lon,
                level=random.randint(1, 5),
                **yields[resource_type]
            )
            
            resources_created.append({
                'type': resource_type,
                'lat': resource_lat,
                'lon': resource_lon,
                'level': resource.level
            })
        
        return JsonResponse({
            'success': True,
            'resources_created': len(resources_created),
            'resources': resources_created
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
