"""
Building System Views
API endpoints for building placement, management, and interaction
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
import json
import uuid

from .models import Character
from .building_models import BuildingType, FlagColor, PlayerBuilding, BuildingTemplate, BuildingAttack


@login_required
@require_http_methods(["GET"])
def api_building_types(request):
    """Get available building types for construction"""
    try:
        character = Character.objects.get(user=request.user)
        
        building_types = []
        for building_type in BuildingType.objects.filter(is_active=True):
            building_types.append({
                'id': str(building_type.id),
                'name': building_type.name,
                'description': building_type.description,
                'category': building_type.category,
                'cost': {
                    'gold': building_type.base_cost_gold,
                    'wood': building_type.base_cost_wood,
                    'stone': building_type.base_cost_stone,
                },
                'revenue_per_hour': building_type.base_revenue_per_hour,
                'max_revenue_per_hour': building_type.max_revenue_per_hour,
                'max_level': building_type.max_level,
                'construction_time_minutes': building_type.construction_time_minutes,
                'icon_name': building_type.icon_name,
                'can_afford': (
                    character.gold >= building_type.base_cost_gold and
                    character.inventory.filter(item_template__name='wood', quantity__gte=building_type.base_cost_wood).exists() and
                    character.inventory.filter(item_template__name='stone', quantity__gte=building_type.base_cost_stone).exists()
                )
            })
        
        return JsonResponse({
            'success': True,
            'building_types': building_types
        })
        
    except Character.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Character not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_repair_building(request, building_id):
    """Owner repairs a building to restore HP. Costs gold proportional to missing HP.
    Requires owner and proximity (~30m).
    """
    try:
        character = Character.objects.get(user=request.user)
        try:
            building = PlayerBuilding.objects.select_for_update().get(id=building_id, owner=character)
        except PlayerBuilding.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'building_not_found_or_not_owner'}, status=404)
        # Range check
        dist = character.distance_to(building.lat, building.lon)
        if dist > 30.0:
            return JsonResponse({'success': False, 'error': 'too_far'}, status=400)
        if building.current_hp >= building.max_hp and building.status == 'active':
            return JsonResponse({'success': False, 'error': 'already_full'}, status=400)
        missing = max(0, int(building.max_hp) - int(building.current_hp))
        # Cost: 1 gold per missing HP, min 10
        cost = max(10, missing)
        if character.gold < cost:
            return JsonResponse({'success': False, 'error': 'insufficient_gold', 'cost': cost, 'gold': character.gold}, status=400)
        character.gold -= cost
        character.save(update_fields=['gold'])
        building.current_hp = building.max_hp
        building.status = 'active'
        building.save(update_fields=['current_hp', 'status', 'updated_at'])
        _broadcast_building_event(building, 'repaired', extra={'cost': cost})
        return JsonResponse({'success': True, 'cost': cost, 'gold': character.gold, 'hp': {'current': building.current_hp, 'max': building.max_hp}})
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'character_not_found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'server_error', 'message': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_flag_colors(request):
    """Get available flag colors for player"""
    try:
        character = Character.objects.get(user=request.user)
        
        flag_colors = []
        for color in FlagColor.objects.filter(is_active=True):
            can_use = True
            if color.is_premium:
                can_use = (
                    character.level >= color.unlock_level and
                    character.gold >= color.unlock_cost
                )
            
            flag_colors.append({
                'id': str(color.id),
                'name': color.name,
                'hex_color': color.hex_color,
                'display_name': color.display_name,
                'is_premium': color.is_premium,
                'unlock_level': color.unlock_level,
                'unlock_cost': color.unlock_cost,
                'can_use': can_use
            })
        
        return JsonResponse({
            'success': True,
            'flag_colors': flag_colors
        })
        
    except Character.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Character not found'
        }, status=404)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_place_building(request):
    """Place a new building at specified coordinates"""
    try:
        character = Character.objects.get(user=request.user)
        
        data = json.loads(request.body)
        building_type_id = data.get('building_type_id')
        lat = float(data.get('lat'))
        lon = float(data.get('lon'))
        flag_color_id = data.get('flag_color_id')
        custom_name = data.get('custom_name', '').strip()
        
        # Validate inputs
        if not building_type_id or not lat or not lon:
            return JsonResponse({
                'success': False,
                'error': 'Missing required parameters'
            }, status=400)
        
        # Get building type
        try:
            building_type = BuildingType.objects.get(id=building_type_id, is_active=True)
        except BuildingType.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid building type'
            }, status=400)
        
        # Get flag color if provided
        flag_color = None
        if flag_color_id:
            try:
                flag_color = FlagColor.objects.get(id=flag_color_id, is_active=True)
                # Check if player can use this color
                if flag_color.is_premium:
                    if character.level < flag_color.unlock_level:
                        return JsonResponse({
                            'success': False,
                            'error': f'Requires level {flag_color.unlock_level} to use {flag_color.display_name}'
                        }, status=400)
            except FlagColor.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid flag color'
                }, status=400)
        
        # Check if location is already occupied
        if PlayerBuilding.objects.filter(lat=lat, lon=lon).exists():
            return JsonResponse({
                'success': False,
                'error': 'Location already occupied by another building'
            }, status=400)
        
        # Check distance from player (optional - prevent building too far away)
        distance = character.distance_to(lat, lon)
        max_building_distance = 1000  # 1km max distance
        if distance > max_building_distance:
            return JsonResponse({
                'success': False,
                'error': f'Cannot build more than {max_building_distance}m from your location'
            }, status=400)
        
        with transaction.atomic():
            # Check resources
            if character.gold < building_type.base_cost_gold:
                return JsonResponse({
                    'success': False,
                    'error': f'Need {building_type.base_cost_gold} gold (have {character.gold})'
                }, status=400)
            
            # Check wood
            try:
                wood_item = character.inventory.get(item_template__name='wood')
                if wood_item.quantity < building_type.base_cost_wood:
                    return JsonResponse({
                        'success': False,
                        'error': f'Need {building_type.base_cost_wood} wood (have {wood_item.quantity})'
                    }, status=400)
            except:
                return JsonResponse({
                    'success': False,
                    'error': f'Need {building_type.base_cost_wood} wood (have 0)'
                }, status=400)
            
            # Check stone
            try:
                stone_item = character.inventory.get(item_template__name='stone')
                if stone_item.quantity < building_type.base_cost_stone:
                    return JsonResponse({
                        'success': False,
                        'error': f'Need {building_type.base_cost_stone} stone (have {stone_item.quantity})'
                    }, status=400)
            except:
                return JsonResponse({
                    'success': False,
                    'error': f'Need {building_type.base_cost_stone} stone (have 0)'
                }, status=400)
            
            # Deduct resources
            character.gold -= building_type.base_cost_gold
            character.save()
            
            # Deduct wood
            wood_item.quantity -= building_type.base_cost_wood
            if wood_item.quantity <= 0:
                wood_item.delete()
            else:
                wood_item.save()
            
            # Deduct stone
            stone_item.quantity -= building_type.base_cost_stone
            if stone_item.quantity <= 0:
                stone_item.delete()
            else:
                stone_item.save()
            
            # Create building
            building = PlayerBuilding.objects.create(
                owner=character,
                building_type=building_type,
                lat=lat,
                lon=lon,
                flag_color=flag_color,
                custom_name=custom_name or building_type.name,
                status='constructing',
                level=1,
                current_hp=100,
                max_hp=100
            )
            
            return JsonResponse({
                'success': True,
                'message': f'{building_type.name} construction started!',
                'building': {
                    'id': str(building.id),
                    'name': building.custom_name or building.building_type.name,
                    'type': building.building_type.name,
                    'lat': building.lat,
                    'lon': building.lon,
                    'level': building.level,
                    'status': building.status,
                    'construction_time_minutes': building_type.construction_time_minutes,
                    'flag_color': {
                        'name': flag_color.display_name if flag_color else None,
                        'hex_color': flag_color.hex_color if flag_color else '#FFFFFF'
                    }
                }
            })
            
    except Character.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Character not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_nearby_buildings(request):
    """Get buildings near player location"""
    try:
        character = Character.objects.get(user=request.user)
        
        # Get radius from query params (default 1000m)
        radius_km = float(request.GET.get('radius', 1.0))
        radius_degrees = radius_km / 111.0  # Rough conversion
        
        # Find nearby buildings
        nearby_buildings = PlayerBuilding.objects.filter(
            lat__range=(character.lat - radius_degrees, character.lat + radius_degrees),
            lon__range=(character.lon - radius_degrees, character.lon + radius_degrees)
        ).select_related('owner', 'building_type', 'flag_color')
        
        buildings_data = []
        for building in nearby_buildings:
            # Check if construction is complete
            building.is_construction_complete()
            
            distance = character.distance_to(building.lat, building.lon)
            
            buildings_data.append({
                'id': str(building.id),
                'name': building.custom_name or building.building_type.name,
                'type': building.building_type.name,
                'category': building.building_type.category,
                'owner': building.owner.name,
                'is_own': building.owner == character,
                'lat': building.lat,
                'lon': building.lon,
                'level': building.level,
                'status': building.status,
                'distance_meters': round(distance),
                'revenue_per_hour': building.get_current_revenue_rate(),
                'flag_color': {
                    'name': building.flag_color.display_name if building.flag_color else None,
                    'hex_color': building.flag_color.hex_color if building.flag_color else '#FFFFFF'
                },
                'hp': {
                    'current': building.current_hp,
                    'max': building.max_hp
                }
            })
        
        return JsonResponse({
            'success': True,
            'buildings': buildings_data,
            'player_location': {
                'lat': character.lat,
                'lon': character.lon
            }
        })
        
    except Character.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Character not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def _broadcast_building_event(building, event: str, extra=None, radius_m: float = 800):
    try:
        from .utils.geo import tiles_within_radius
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        layer = get_channel_layer()
        payload = {
            'type': 'building_event',
            'event': event,
            'building': {
                'id': str(building.id),
                'name': building.custom_name or building.building_type.name,
                'type': building.building_type.name,
                'owner_id': building.owner.id if building.owner_id else None,
                'lat': building.lat,
                'lon': building.lon,
                'level': building.level,
                'status': building.status,
                'hp': {'current': building.current_hp, 'max': building.max_hp},
            },
        }
        if extra is not None:
            payload['extra'] = extra
        for g in tiles_within_radius(building.lat, building.lon, radius_m):
            async_to_sync(layer.group_send)(g, {'type': 'building.event', 'payload': payload})
    except Exception:
        pass


@login_required
@require_http_methods(["POST"])
def api_attack_building(request, building_id):
    """Attack a nearby building for PvP raiding.
    Rules:
    - Must be within interaction range (~30m).
    - Owner cannot attack own building.
    - Reduces HP; if HP reaches 0, building is destroyed and any uncollected revenue is stolen.
    - Creates a BuildingAttack record and broadcasts a building_event.
    """
    try:
        character = Character.objects.get(user=request.user)
        data = {}
        try:
            data = json.loads(request.body or '{}')
        except Exception:
            data = {}
        damage = int(data.get('damage', 0) or 0)
        if damage <= 0:
            # Simple damage model from character stats
            damage = max(10, int(character.strength) + int(character.level) // 2)
        # Find building
        try:
            building = PlayerBuilding.objects.select_for_update().get(id=building_id)
        except PlayerBuilding.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'building_not_found'}, status=404)
        # Prevent attacking own building
        if building.owner_id == character.id:
            return JsonResponse({'success': False, 'error': 'own_building_forbidden'}, status=403)
        # Range check (~30m)
        try:
            from .services.movement import ensure_interaction_range
            ensure_interaction_range(character, building.lat, building.lon)
        except Exception:
            # fallback precise distance check
            dist = character.distance_to(building.lat, building.lon)
            if dist > 30.0:
                return JsonResponse({'success': False, 'error': 'too_far'}, status=400)
        # Apply damage
        before = int(building.current_hp)
        after = max(0, before - max(1, int(damage)))
        building.current_hp = after
        building.last_attacked = timezone.now()
        if after <= 0:
            building.status = 'destroyed'
        elif building.status == 'active':
            building.status = 'damaged'
        building.save(update_fields=['current_hp', 'last_attacked', 'status', 'updated_at'])
        # Determine gold stolen if destroyed
        gold_stolen = 0
        if building.status == 'destroyed':
            # Steal uncollected revenue
            try:
                gold_stolen = max(0, int(building.uncollected_revenue or 0))
            except Exception:
                gold_stolen = 0
            building.uncollected_revenue = 0
            building.save(update_fields=['uncollected_revenue', 'updated_at'])
            # Give to attacker
            character.gold += gold_stolen
            character.save(update_fields=['gold'])
        # Record attack
        atk = BuildingAttack.objects.create(
            attacker=character,
            target_building=building,
            status='success' if building.status in ['damaged', 'destroyed'] else 'active',
            damage_dealt=(before - after),
            gold_stolen=gold_stolen,
            attack_power=int(damage),
            completed_at=timezone.now()
        )
        # Broadcast event
        extra = {'damage': before - after, 'gold_stolen': gold_stolen}
        _broadcast_building_event(building, 'under_attack' if building.status != 'destroyed' else 'destroyed', extra=extra)
        return JsonResponse({
            'success': True,
            'damage': before - after,
            'hp_after': after,
            'status': building.status,
            'gold_stolen': gold_stolen,
            'attacker_gold': character.gold,
            'attack_id': str(atk.id),
        })
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'character_not_found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'server_error', 'message': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_collect_revenue(request, building_id):
    """Collect revenue from a building"""
    try:
        character = Character.objects.get(user=request.user)
        
        # Get building
        try:
            building = PlayerBuilding.objects.get(id=building_id, owner=character)
        except PlayerBuilding.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Building not found or not owned by you'
            }, status=404)
        
        # Collect revenue
        revenue_collected = building.collect_revenue()
        
        # Broadcast collection event
        try:
            _broadcast_building_event(building, 'revenue_collected', extra={'amount': revenue_collected})
        except Exception:
            pass
        return JsonResponse({
            'success': True,
            'revenue_collected': revenue_collected,
            'message': f'Collected {revenue_collected} gold!' if revenue_collected > 0 else 'No revenue to collect',
            'building': {
                'id': str(building.id),
                'name': building.custom_name or building.building_type.name,
                'total_revenue_generated': building.total_revenue_generated,
                'current_revenue_rate': building.get_current_revenue_rate()
            },
            'player': {
                'gold': character.gold
            }
        })
        
    except Character.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Character not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
