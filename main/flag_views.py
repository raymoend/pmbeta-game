"""
Parallel Kingdom Style Flag System API Views
Territory control flags with radius-based ownership, upkeep, and combat
"""
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import json
import math

from .models import Character
from .flag_models import TerritoryFlag, TerritoryZone, FlagRevenueCollection, FlagCombatLog
from .building_models import FlagColor


def can_place_flag_at_location(character, lat, lon, radius=200):
    """
    Check if a flag can be placed at the given location
    Implements PK territory overlap rules - flags must be outside existing territory radius
    """
    from django.conf import settings
    
    # Check if location is within reasonable distance of player
    distance_to_player = character.distance_to(lat, lon)
    max_placement_distance = 1000  # 1km max like PK
    
    if distance_to_player > max_placement_distance:
        return False, f"Cannot place flag more than {max_placement_distance}m from your location"
    
    # Get minimum distance between flags from settings
    min_distance = settings.GAME_SETTINGS.get('FLAG_PLACEMENT_MIN_DISTANCE', 400)
    
    # Check all existing flags for distance conflicts (including own flags)
    # In PK style, you cannot place overlapping flags even if they're your own
    existing_flags = TerritoryFlag.objects.filter(
        status__in=['active', 'constructing', 'upgrading', 'damaged']
    )  # Check against ALL flags, including own
    
    for existing_flag in existing_flags:
        distance_to_flag = existing_flag.distance_to(lat, lon)
        required_distance = existing_flag.radius_meters + radius  # Sum of both radii
        
        if distance_to_flag < required_distance:
            return False, f"Too close to {existing_flag.owner.name}'s {existing_flag.display_name}. Need {required_distance}m distance (currently {int(distance_to_flag)}m)"
    
    return True, "Location is available"


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
@require_http_methods(["POST"])
def api_can_place_flag(request):
    """Check if flag can be placed at location"""
    try:
        character = Character.objects.get(user=request.user)
        data = json.loads(request.body)
        
        lat = float(data.get('lat'))
        lon = float(data.get('lon'))
        
        can_place, message = can_place_flag_at_location(character, lat, lon)
        
        return JsonResponse({
            'success': True,
            'can_place': can_place,
            'message': message
        })
        
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_place_flag(request):
    """Place a new territory flag"""
    try:
        character = Character.objects.get(user=request.user)
        
        data = json.loads(request.body)
        lat = float(data.get('lat'))
        lon = float(data.get('lon'))
        custom_name = data.get('custom_name', '').strip()
        
        # Use character's chosen flag color
        flag_color = character.flag_color
        
        # Validate inputs
        if not lat or not lon:
            return JsonResponse({
                'success': False,
                'error': 'Missing required coordinates'
            }, status=400)
        
        # Check placement rules
        can_place, message = can_place_flag_at_location(character, lat, lon)
        if not can_place:
            return JsonResponse({
                'success': False,
                'error': message
            }, status=400)
        
        # Use default red color if character doesn't have a flag color set
        if not flag_color:
            try:
                flag_color = FlagColor.objects.filter(
                    hex_color='#ff0000',  # Red color
                    is_active=True
                ).first()
            except:
                pass
        
        with transaction.atomic():
            # Check resources (PK-style flag costs)
            flag_cost_gold = 500  # Base cost for flag
            flag_cost_wood = 20
            flag_cost_stone = 10
            
            if character.gold < flag_cost_gold:
                return JsonResponse({
                    'success': False,
                    'error': f'Need {flag_cost_gold} gold (have {character.gold})'
                }, status=400)
            
            # Check wood
            try:
                wood_item = character.inventory.get(item_template__name='wood')
                if wood_item.quantity < flag_cost_wood:
                    return JsonResponse({
                        'success': False,
                        'error': f'Need {flag_cost_wood} wood (have {wood_item.quantity})'
                    }, status=400)
            except:
                return JsonResponse({
                    'success': False,
                    'error': f'Need {flag_cost_wood} wood (have 0)'
                }, status=400)
            
            # Check stone
            try:
                stone_item = character.inventory.get(item_template__name='stone')
                if stone_item.quantity < flag_cost_stone:
                    return JsonResponse({
                        'success': False,
                        'error': f'Need {flag_cost_stone} stone (have {stone_item.quantity})'
                    }, status=400)
            except:
                return JsonResponse({
                    'success': False,
                    'error': f'Need {flag_cost_stone} stone (have 0)'
                }, status=400)
            
            # Deduct resources
            character.gold -= flag_cost_gold
            character.save()
            
            wood_item.quantity -= flag_cost_wood
            if wood_item.quantity <= 0:
                wood_item.delete()
            else:
                wood_item.save()
            
            stone_item.quantity -= flag_cost_stone
            if stone_item.quantity <= 0:
                stone_item.delete()
            else:
                stone_item.save()
            
            # Create flag - instant placement
            flag = TerritoryFlag.objects.create(
                owner=character,
                lat=lat,
                lon=lon,
                flag_color=flag_color,
                custom_name=custom_name or "Territory Flag",
                level=1,
                radius_meters=200,  # Level 1 radius
                current_hp=100,
                max_hp=100,
                daily_upkeep_cost=50,
                status='active',  # Instant activation
                construction_time_minutes=0  # No construction time
            )
            
            # Create territory zone
            flag.regenerate_territory_zone()
            
            return JsonResponse({
                'success': True,
                'message': 'Territory flag placed successfully! Your territory is now active.',
                'flag': {
                    'id': str(flag.id),
                    'name': flag.display_name,
                    'lat': flag.lat,
                    'lon': flag.lon,
                    'level': flag.level,
                    'status': flag.status,
                    'radius_meters': flag.radius_meters,
                    'construction_time_minutes': flag.construction_time_minutes,
                    'flag_color': {
                        'name': flag_color.display_name if flag_color else None,
                        'hex_color': flag_color.hex_color if flag_color else '#FFFFFF'
                    }
                }
            })
            
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_nearby_flags(request):
    """Get territory flags near player location"""
    try:
        character = Character.objects.get(user=request.user)
        
        # Get radius from query params (default 2km)
        radius_km = float(request.GET.get('radius', 2.0))
        radius_degrees = radius_km / 111.0  # Rough conversion
        
        # Find nearby flags - simplified query
        nearby_flags = TerritoryFlag.objects.filter(
            lat__range=(character.lat - radius_degrees, character.lat + radius_degrees),
            lon__range=(character.lon - radius_degrees, character.lon + radius_degrees)
        ).select_related('owner', 'flag_color').exclude(
            status='destroyed'
        )
        
        flags_data = []
        for flag in nearby_flags:
            try:
                distance = character.distance_to(flag.lat, flag.lon)
                
                flag_data = {
                    'id': str(flag.id),
                    'name': flag.custom_name or f"Flag {flag.id}",
                    'owner': flag.owner.name,
                    'is_mine': flag.owner == character,
                    'lat': flag.lat,
                    'lon': flag.lon,
                    'level': flag.level,
                    'status': flag.status,
                    'distance_meters': round(distance),
                    'radius_meters': flag.radius_meters,
                    'flag_color': {
                        'name': flag.flag_color.display_name if flag.flag_color else 'Default',
                        'hex_color': flag.flag_color.hex_color if flag.flag_color else '#FF4444'
                    }
                }
                
                flags_data.append(flag_data)
            except Exception as flag_error:
                # Skip this flag if there's an error processing it
                print(f"Error processing flag {flag.id}: {flag_error}")
                continue
        
        return JsonResponse({
            'success': True,
            'flags': flags_data
        })
        
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)
    except Exception as e:
        import traceback
        print(f"API Error: {e}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_collect_flag_revenue(request, flag_id):
    """Collect revenue from a territory flag"""
    try:
        character = Character.objects.get(user=request.user)
        
        # Get flag
        try:
            flag = TerritoryFlag.objects.get(id=flag_id, owner=character)
        except TerritoryFlag.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Flag not found or not owned by you'
            }, status=404)
        
        # Collect revenue
        revenue_collected = flag.collect_revenue()
        
        return JsonResponse({
            'success': True,
            'message': f'Collected {revenue_collected} gold revenue',
            'revenue_collected': revenue_collected,
            'new_gold_total': character.gold
        })
        
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_pay_flag_upkeep(request, flag_id):
    """Pay upkeep for a territory flag"""
    try:
        character = Character.objects.get(user=request.user)
        
        # Get flag
        try:
            flag = TerritoryFlag.objects.get(id=flag_id, owner=character)
        except TerritoryFlag.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Flag not found or not owned by you'
            }, status=404)
        
        # Pay upkeep
        success, message = flag.pay_upkeep()
        
        if success:
            return JsonResponse({
                'success': True,
                'message': message,
                'new_gold_total': character.gold,
                'upkeep_due_at': flag.upkeep_due_at.isoformat()
            })
        else:
            return JsonResponse({
                'success': False,
                'error': message
            }, status=400)
        
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_upgrade_flag(request, flag_id):
    """Upgrade a territory flag"""
    try:
        character = Character.objects.get(user=request.user)
        
        # Get flag
        try:
            flag = TerritoryFlag.objects.get(id=flag_id, owner=character)
        except TerritoryFlag.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Flag not found or not owned by you'
            }, status=404)
        
        # Check if can upgrade
        can_upgrade, message = flag.can_upgrade()
        if not can_upgrade:
            return JsonResponse({
                'success': False,
                'error': message
            }, status=400)
        
        # Get upgrade cost
        upgrade_cost = flag.get_upgrade_cost()
        if not upgrade_cost:
            return JsonResponse({
                'success': False,
                'error': 'No upgrade available'
            }, status=400)
        
        with transaction.atomic():
            # Check resources
            if character.gold < upgrade_cost['gold']:
                return JsonResponse({
                    'success': False,
                    'error': f'Need {upgrade_cost["gold"]} gold (have {character.gold})'
                }, status=400)
            
            # Check materials
            try:
                wood_item = character.inventory.get(item_template__name='wood')
                if wood_item.quantity < upgrade_cost['wood']:
                    return JsonResponse({
                        'success': False,
                        'error': f'Need {upgrade_cost["wood"]} wood (have {wood_item.quantity})'
                    }, status=400)
            except:
                return JsonResponse({
                    'success': False,
                    'error': f'Need {upgrade_cost["wood"]} wood (have 0)'
                }, status=400)
            
            try:
                stone_item = character.inventory.get(item_template__name='stone')
                if stone_item.quantity < upgrade_cost['stone']:
                    return JsonResponse({
                        'success': False,
                        'error': f'Need {upgrade_cost["stone"]} stone (have {stone_item.quantity})'
                    }, status=400)
            except:
                return JsonResponse({
                    'success': False,
                    'error': f'Need {upgrade_cost["stone"]} stone (have 0)'
                }, status=400)
            
            # Start upgrade
            success, message = flag.start_upgrade()
            
            if success:
                return JsonResponse({
                    'success': True,
                    'message': message,
                    'new_level': flag.level,
                    'new_gold_total': character.gold
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': message
                }, status=400)
        
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_attack_flag(request, flag_id):
    """Attack an enemy territory flag - PK style unrestricted combat (24/7 attacks allowed)"""
    try:
        character = Character.objects.get(user=request.user)
        
        data = json.loads(request.body)
        damage_amount = int(data.get('damage', 20))  # Default attack damage
        
        # Get flag
        try:
            flag = TerritoryFlag.objects.get(id=flag_id)
        except TerritoryFlag.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Flag not found'
            }, status=404)
        
        # Apply damage
        success, message = flag.apply_damage(character, damage_amount)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': message,
                'flag': {
                    'id': str(flag.id),
                    'current_hp': flag.current_hp,
                    'max_hp': flag.max_hp,
                    'status': flag.status,
                    'can_capture': flag.can_capture(character)[0]
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': message
            }, status=400)
        
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_capture_flag(request, flag_id):
    """Capture an enemy territory flag"""
    try:
        character = Character.objects.get(user=request.user)
        
        # Get flag
        try:
            flag = TerritoryFlag.objects.get(id=flag_id)
        except TerritoryFlag.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Flag not found'
            }, status=404)
        
        # Capture flag
        success, message = flag.capture(character)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': message,
                'flag': {
                    'id': str(flag.id),
                    'owner': flag.owner.name,
                    'level': flag.level,
                    'current_hp': flag.current_hp,
                    'max_hp': flag.max_hp,
                    'status': flag.status,
                    'radius_meters': flag.radius_meters
                },
                'new_gold_total': character.gold
            })
        else:
            return JsonResponse({
                'success': False,
                'error': message
            }, status=400)
        
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_repair_flag(request, flag_id):
    """Repair damage to a territory flag"""
    try:
        character = Character.objects.get(user=request.user)
        
        data = json.loads(request.body)
        repair_amount = int(data.get('repair_amount', 20))  # Default repair amount
        
        # Get flag
        try:
            flag = TerritoryFlag.objects.get(id=flag_id, owner=character)
        except TerritoryFlag.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Flag not found or not owned by you'
            }, status=404)
        
        # Repair flag
        success, message = flag.repair(repair_amount)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': message,
                'flag': {
                    'current_hp': flag.current_hp,
                    'max_hp': flag.max_hp,
                    'status': flag.status
                },
                'new_gold_total': character.gold
            })
        else:
            return JsonResponse({
                'success': False,
                'error': message
            }, status=400)
        
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_flag_territories_geojson(request):
    """Get territory boundaries as GeoJSON for map rendering"""
    try:
        character = Character.objects.get(user=request.user)
        
        # Get radius for search
        radius_km = float(request.GET.get('radius', 5.0))  # Default 5km
        radius_degrees = radius_km / 111.0
        
        # Find nearby territory zones
        nearby_zones = TerritoryZone.objects.filter(
            center_lat__range=(character.lat - radius_degrees, character.lat + radius_degrees),
            center_lon__range=(character.lon - radius_degrees, character.lon + radius_degrees)
        ).select_related('flag', 'flag__owner', 'flag__flag_color')
        
        features = []
        for zone in nearby_zones:
            if zone.flag.status == 'destroyed':
                continue
                
            # Create GeoJSON feature for circular territory
            # Approximate circle with polygon
            points = []
            center_lat = zone.center_lat
            center_lon = zone.center_lon
            radius_deg = zone.radius_meters / 111000.0  # Convert meters to degrees
            
            # Create circle with 16 points
            for i in range(16):
                angle = (i * 2 * math.pi) / 16
                lat = center_lat + radius_deg * math.cos(angle)
                lon = center_lon + radius_deg * math.sin(angle) / math.cos(math.radians(center_lat))
                points.append([lon, lat])  # GeoJSON uses [lon, lat]
            points.append(points[0])  # Close the polygon
            
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Polygon',
                    'coordinates': [points]
                },
                'properties': {
                    'flag_id': str(zone.flag.id),
                    'owner': zone.flag.owner.name,
                    'name': zone.flag.display_name,
                    'level': zone.flag.level,
                    'status': zone.flag.status,
                    'radius_meters': zone.radius_meters,
                    'is_own': zone.flag.owner == character,
                    'flag_color': zone.flag.flag_color.hex_color if zone.flag.flag_color else '#FFFFFF'
                }
            }
            
            features.append(feature)
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        return JsonResponse({
            'success': True,
            'geojson': geojson
        })
        
    except Character.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Character not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
