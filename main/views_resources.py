"""
Resource Collection API Views
Handles resource harvesting, inventory management, and item usage for the RPG system
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
import json
import math
from datetime import timedelta
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import (
    Character, ResourceNode, ResourceHarvest, 
    InventoryItem, ItemTemplate, GameEvent
)


@csrf_exempt
@require_http_methods(["GET"])
@login_required
def nearby_resources(request):
    """Get resource nodes near the player's current location"""
    try:
        character = request.user.character
    except Character.DoesNotExist:
        return JsonResponse({'error': 'Character not found'}, status=404)
    
    # Get radius from query params (default 1000 meters)
    radius = float(request.GET.get('radius', 1000))
    
    # Calculate approximate lat/lon boundaries for efficiency
    lat_range = radius / 111000  # roughly 1 degree = 111km
    lon_range = radius / (111000 * math.cos(math.radians(character.lat)))
    
    # Query nearby resources
    nearby = ResourceNode.objects.filter(
        lat__range=[character.lat - lat_range, character.lat + lat_range],
        lon__range=[character.lon - lon_range, character.lon + lon_range]
    )
    
    resources = []
    for resource in nearby:
        # Calculate exact distance
        distance = character.distance_to(resource.lat, resource.lon)
        if distance <= radius:
            # Check if resource can respawn
            resource.respawn_if_ready()
            
            # Compute cooldown info for client-side timers
            ready_in = 0
            ready_at = None
            if resource.last_harvested:
                cooldown = int(resource.respawn_time) * 60
                elapsed = (timezone.now() - resource.last_harvested).total_seconds()
                remaining = int(max(0, cooldown - elapsed))
                ready_in = remaining
                if remaining > 0:
                    try:
                        ready_at = (resource.last_harvested + timedelta(seconds=cooldown)).isoformat()
                    except Exception:
                        ready_at = None

            resources.append({
                'id': str(resource.id),
                'type': resource.resource_type,
                'type_display': resource.get_resource_type_display(),
                'level': resource.level,
                'lat': resource.lat,
                'lon': resource.lon,
                'distance': round(distance, 1),
                'quantity': resource.quantity,
                'max_quantity': resource.max_quantity,
                'is_depleted': resource.is_depleted,
                'can_harvest': resource.can_harvest(),
                'respawn_time': resource.respawn_time,
                'last_harvested': resource.last_harvested.isoformat() if resource.last_harvested else None,
                'ready_in_seconds': ready_in,
                'ready_at': ready_at,
            })
    
    # Sort by distance
    resources.sort(key=lambda x: x['distance'])
    
    return JsonResponse({
        'success': True,
        'resources': resources,
        'character_location': {'lat': character.lat, 'lon': character.lon}
    })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def harvest_resource(request):
    """Harvest a resource node"""
    try:
        character = request.user.character
    except Character.DoesNotExist:
        return JsonResponse({'error': 'Character not found'}, status=404)
    
    data = json.loads(request.body)
    resource_id = data.get('resource_id')
    
    if not resource_id:
        return JsonResponse({'error': 'Resource ID required'}, status=400)
    
    resource = get_object_or_404(ResourceNode, id=resource_id)
    
    # Check if character can act
    if not character.can_act():
        return JsonResponse({'error': 'Character cannot act (in combat or no stamina)'}, status=400)

    # Check distance (must be within 50 meters)
    distance = character.distance_to(resource.lat, resource.lon)
    if distance > 50:
        return JsonResponse({'error': 'Too far from resource node'}, status=400)
    
    # Check if resource can be harvested
    if not resource.can_harvest():
        if resource.is_depleted:
            return JsonResponse({'error': 'Resource is depleted'}, status=400)
        else:
            return JsonResponse({'error': 'Resource not ready for harvest'}, status=400)
    
    # Perform harvest
    rewards = resource.harvest(character)
    
    if not rewards:
        return JsonResponse({'error': 'Failed to harvest resource'}, status=400)
    
    # Create harvest record
    harvest = ResourceHarvest.objects.create(
        resource=resource,
        character=character,
        status='completed',
        experience_gained=rewards.get('experience', 0),
        gold_gained=rewards.get('gold', 0),
        items_gained=rewards.get('items', []),
        completed_at=timezone.now()
    )
    
    # Add items to inventory
    items_received = []
    for item_data in rewards.get('items', []):
        if item_data['quantity'] > 0:  # Only add items with quantity > 0
            inventory_item = character.add_item_to_inventory(
                item_data['name'], 
                item_data['quantity']
            )
            items_received.append({
                'name': item_data['name'],
                'quantity': item_data['quantity'],
                'total_quantity': inventory_item.quantity
            })

    # Prepare updated resource payload for response and WS broadcast
    try:
        cooldown = int(resource.respawn_time) * 60
    except Exception:
        cooldown = 0
    ready_in = 0
    ready_at = None
    if resource.last_harvested and cooldown > 0:
        elapsed = (timezone.now() - resource.last_harvested).total_seconds()
        remaining = int(max(0, cooldown - elapsed))
        ready_in = remaining
        if remaining > 0:
            try:
                ready_at = (resource.last_harvested + timedelta(seconds=cooldown)).isoformat()
            except Exception:
                ready_at = None
    resource_payload = {
        'id': str(resource.id),
        'type': resource.resource_type,
        'type_display': resource.get_resource_type_display(),
        'level': resource.level,
        'lat': resource.lat,
        'lon': resource.lon,
        'quantity': resource.quantity,
        'max_quantity': resource.max_quantity,
        'is_depleted': resource.is_depleted,
        'can_harvest': resource.can_harvest(),
        'respawn_time': resource.respawn_time,
        'last_harvested': resource.last_harvested.isoformat() if resource.last_harvested else None,
        'ready_in_seconds': ready_in,
        'ready_at': ready_at,
    }
    
    # Create game event
    GameEvent.objects.create(
        character=character,
        event_type='resource_gathered',
        title='Resource Gathered',
        message=f"Harvested {resource.get_resource_type_display()} and gained {rewards.get('experience', 0)} XP",
        data={
            'resource_type': resource.resource_type,
            'experience': rewards.get('experience', 0),
            'gold': rewards.get('gold', 0),
            'items': items_received
        }
    )
    
    # Push live updates over WebSocket (inventory, character, and resource)
    try:
        channel_layer = get_channel_layer()
        # Character-scoped updates
        async_to_sync(channel_layer.group_send)(
            f'character_{character.id}',
            {'type': 'inventory_update'}
        )
        async_to_sync(channel_layer.group_send)(
            f'character_{character.id}',
            {'type': 'character_update'}
        )
        # Resource update for this player and nearby location group
        async_to_sync(channel_layer.group_send)(
            f'character_{character.id}',
            {'type': 'resource_update', 'resource': resource_payload}
        )
        try:
            # Broadcast to geo tile group so nearby players can see updates
            from .utils.geo import tile_for
            tile_group = tile_for(float(character.lat), float(character.lon))
            async_to_sync(channel_layer.group_send)(
                tile_group,
                {'type': 'resource_update', 'resource': resource_payload}
            )
        except Exception:
            pass
    except Exception:
        pass

    return JsonResponse({
        'success': True,
        'message': f'Successfully harvested {resource.get_resource_type_display()}',
        'rewards': {
            'experience': rewards.get('experience', 0),
            'gold': rewards.get('gold', 0),
            'items': items_received
        },
        'resource': resource_payload,
        'resource_status': {
            'quantity': resource.quantity,
            'is_depleted': resource.is_depleted
        }
    })


@csrf_exempt
@require_http_methods(["GET"])
@login_required
def character_inventory(request):
    """Get character's inventory"""
    try:
        character = request.user.character
    except Character.DoesNotExist:
        return JsonResponse({'error': 'Character not found'}, status=404)
    
    inventory = character.get_inventory_summary()
    
    return JsonResponse({
        'success': True,
        'inventory': inventory,
        'character': {
            'name': character.name,
            'level': character.level,
            'gold': character.gold,
            'current_hp': character.current_hp,
            'max_hp': character.max_hp
        }
    })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def use_item(request):
    """Use a consumable item"""
    try:
        character = request.user.character
    except Character.DoesNotExist:
        return JsonResponse({'error': 'Character not found'}, status=404)
    
    data = json.loads(request.body)
    item_name = data.get('item_name')
    quantity = data.get('quantity', 1)
    
    if not item_name:
        return JsonResponse({'error': 'Item name required'}, status=400)
    
    # Check if character can act
    if not character.can_act():
        return JsonResponse({'error': 'Character cannot act (in combat or no stamina)'}, status=400)
    
    # Use the item
    success, message = character.use_item(item_name, quantity)
    
    if not success:
        return JsonResponse({'error': message}, status=400)
    
    # Get updated character stats
    character.refresh_from_db()

    # Push updates: inventory may have changed and character stats changed
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
    
    return JsonResponse({
        'success': True,
        'message': message,
        'character_stats': {
            'current_hp': character.current_hp,
            'max_hp': character.max_hp,
            'current_mana': character.current_mana,
            'max_mana': character.max_mana,
            'current_stamina': character.current_stamina,
            'max_stamina': character.max_stamina
        }
    })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def use_berries(request):
    """Quick heal using Energy Berries (themed) with legacy fallback to 'berries'"""
    try:
        character = request.user.character
    except Character.DoesNotExist:
        return JsonResponse({'error': 'Character not found'}, status=404)
    
    # Check if character needs healing
    if character.current_hp >= character.max_hp:
        return JsonResponse({'error': 'Character is already at full health'}, status=400)
    
    # Check if character can act
    if not character.can_act():
        return JsonResponse({'error': 'Character cannot act (in combat or no stamina)'}, status=400)
    
    # Prefer Energy Berries; fallback to legacy 'berries'
    success, message = character.use_item('Energy Berries', 1)
    if not success:
        success, message = character.use_item('berries', 1)
    
    if not success:
        return JsonResponse({'error': message}, status=400)
    
    # Get updated character stats
    character.refresh_from_db()

    # Push updates after berries use
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
    
    return JsonResponse({
        'success': True,
        'message': message,
        'character_stats': {
            'current_hp': character.current_hp,
            'max_hp': character.max_hp,
            'hp_percentage': round((character.current_hp / character.max_hp) * 100, 1)
        }
    })


@csrf_exempt
@require_http_methods(["GET"])
@login_required
def harvest_history(request):
    """Get character's recent harvest history"""
    try:
        character = request.user.character
    except Character.DoesNotExist:
        return JsonResponse({'error': 'Character not found'}, status=404)
    
    # Get recent harvests (last 20)
    harvests = ResourceHarvest.objects.filter(
        character=character
    ).order_by('-created_at')[:20]
    
    harvest_history = []
    for harvest in harvests:
        harvest_history.append({
            'id': str(harvest.id),
            'resource_type': harvest.resource.get_resource_type_display(),
            'status': harvest.get_status_display(),
            'experience_gained': harvest.experience_gained,
            'gold_gained': harvest.gold_gained,
            'items_gained': harvest.items_gained,
            'created_at': harvest.created_at.isoformat(),
            'completed_at': harvest.completed_at.isoformat() if harvest.completed_at else None
        })
    
    return JsonResponse({
        'success': True,
        'harvest_history': harvest_history
    })


@csrf_exempt
@require_http_methods(["GET"])
@login_required
def resource_info(request, resource_id):
    """Get detailed information about a specific resource node"""
    try:
        character = request.user.character
    except Character.DoesNotExist:
        return JsonResponse({'error': 'Character not found'}, status=404)
    
    resource = get_object_or_404(ResourceNode, id=resource_id)
    
    # Calculate distance
    distance = character.distance_to(resource.lat, resource.lon)
    
    # Check if resource can respawn
    resource.respawn_if_ready()
    
    # Get potential rewards
    rewards = resource.get_harvest_rewards(character.level)

    # Cooldown info for timers
    ready_in = 0
    ready_at = None
    if resource.last_harvested:
        cooldown = int(resource.respawn_time) * 60
        elapsed = (timezone.now() - resource.last_harvested).total_seconds()
        remaining = int(max(0, cooldown - elapsed))
        ready_in = remaining
        if remaining > 0:
            try:
                ready_at = (resource.last_harvested + timedelta(seconds=cooldown)).isoformat()
            except Exception:
                ready_at = None
    
    return JsonResponse({
        'success': True,
        'resource': {
            'id': str(resource.id),
            'type': resource.resource_type,
            'type_display': resource.get_resource_type_display(),
            'level': resource.level,
            'lat': resource.lat,
            'lon': resource.lon,
            'distance': round(distance, 1),
            'quantity': resource.quantity,
            'max_quantity': resource.max_quantity,
            'is_depleted': resource.is_depleted,
            'can_harvest': resource.can_harvest(),
            'respawn_time': resource.respawn_time,
            'harvest_count': resource.harvest_count,
            'base_experience': resource.base_experience,
            'potential_rewards': rewards,
            'last_harvested': resource.last_harvested.isoformat() if resource.last_harvested else None,
            'ready_in_seconds': ready_in,
            'ready_at': ready_at,
        }
    })
