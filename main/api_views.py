"""
Enhanced RPG API Views
Integrates all systems: combat, quests, MapBox, WebSocket notifications
"""
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from django.db import transaction
from django.core.paginator import Paginator

from .models import Character, Monster, PvECombat, PvPCombat, Trade, Skill
from .quest_system import quest_manager, QuestType, QuestDifficulty
from .mapbox_integration import game_world, GeoLocation
from .combat_engine import CombatEngine, CombatStats, DamageType
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


class RPGAPIView(View):
    """Base class for RPG API views with common functionality"""
    
    @method_decorator(csrf_exempt)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        try:
            # Get character for user
            self.character = Character.objects.get(user=request.user)
        except Character.DoesNotExist:
            return JsonResponse({
                'error': 'No character found for user',
                'redirect': '/character/create'
            }, status=404)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_json_data(self, request):
        """Parse JSON data from request"""
        try:
            if request.content_type == 'application/json':
                return json.loads(request.body)
            return {}
        except json.JSONDecodeError:
            return {}
    
    def send_websocket_update(self, event_type, data):
        """Send real-time update via WebSocket"""
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'character_{self.character.id}',
                {
                    'type': event_type,
                    'data': data
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send WebSocket update: {e}")


class GameStatusView(RPGAPIView):
    """Get comprehensive game status for character"""
    
    def get(self, request):
        # Get character location
        char_location = GeoLocation(self.character.lat, self.character.lon)
        
        # Get map data
        map_data = game_world.create_map_data(char_location)
        
        # Get nearby monsters (from actual database)
        nearby_monsters = Monster.objects.filter(
            lat__range=(self.character.lat - 0.01, self.character.lat + 0.01),
            lon__range=(self.character.lon - 0.01, self.character.lon + 0.01),
            is_alive=True
        ).values('id', 'name', 'level', 'lat', 'lon', 'current_hp', 'max_hp')
        
        # Get active combat
        active_combat = PvECombat.objects.filter(
            character=self.character,
            status='active'
        ).select_related('monster').first()
        
        # Get active trades
        active_trades = Trade.objects.filter(
            responder=self.character,
            status='pending'
        ).select_related('requester').values(
            'id', 'requester__name', 'offered_items', 'requested_items', 'created_at'
        )
        
        # Get available quests
        available_quests = quest_manager.get_available_quests(self.character.level)
        
        return JsonResponse({
            'character': {
                'id': str(self.character.id),
                'name': self.character.name,
                'level': self.character.level,
                'experience': self.character.experience,
                'location': {
                    'lat': self.character.lat,
                    'lon': self.character.lon
                },
                'health': {
                    'current': self.character.current_hp,
                    'max': self.character.max_hp
                },
                'stats': {
                    'strength': self.character.strength,
                    'defense': self.character.defense,
                    'vitality': self.character.vitality,
                    'agility': self.character.agility,
                    'intelligence': self.character.intelligence
                },
                'gold': self.character.gold,
                'in_combat': active_combat is not None
            },
            'map_data': map_data,
            'nearby_monsters': list(nearby_monsters),
            'active_combat': {
                'id': str(active_combat.id),
                'monster': {
                    'name': active_combat.monster.name,
                    'level': active_combat.monster.level,
                    'hp': active_combat.monster.current_hp,
                    'max_hp': active_combat.monster.max_hp
                },
                'turn': active_combat.status
            } if active_combat else None,
            'pending_trades': list(active_trades),
            'available_quests': [quest.to_dict() for quest in available_quests],
            'timestamp': timezone.now().isoformat()
        })


class MoveCharacterView(RPGAPIView):
    """Move character to new location"""
    
    def post(self, request):
        data = self.get_json_data(request)
        
        try:
            target_lat = float(data.get('latitude'))
            target_lon = float(data.get('longitude'))
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Invalid coordinates'}, status=400)
        
        # Create location objects
        current_location = GeoLocation(self.character.lat, self.character.lon, timestamp=timezone.now())
        target_location = GeoLocation(target_lat, target_lon, timestamp=timezone.now())
        
        # Validate movement
        if not game_world.validate_movement(current_location, target_location):
            return JsonResponse({'error': 'Invalid movement'}, status=400)
        
        # Update character position
        with transaction.atomic():
            self.character.lat = target_lat
            self.character.lon = target_lon
            self.character.save(update_fields=['lat', 'lon'])
        
        # Send WebSocket update
        self.send_websocket_update('character_moved', {
            'character_id': str(self.character.id),
            'character_name': self.character.name,
            'new_position': {
                'lat': target_lat,
                'lon': target_lon
            },
            'timestamp': timezone.now().isoformat()
        })
        
        # Get location info
        location_info = game_world.mapbox.reverse_geocode(target_location)
        
        return JsonResponse({
            'success': True,
            'new_position': {
                'lat': target_lat,
                'lon': target_lon
            },
            'location_info': location_info,
            'distance_moved': current_location.distance_to(target_location)
        })


class AttackMonsterView(RPGAPIView):
    """Attack a monster (PvE combat)"""
    
    def post(self, request):
        data = self.get_json_data(request)
        
        try:
            monster_id = data.get('monster_id')
            monster = Monster.objects.get(id=monster_id, is_alive=True)
        except (Monster.DoesNotExist, TypeError):
            return JsonResponse({'error': 'Monster not found'}, status=404)
        
        # Check if monster is nearby
        distance = self.character.distance_to(monster.lat, monster.lon)
        if distance > 100:  # 100 meters max attack range
            return JsonResponse({'error': 'Monster too far away'}, status=400)
        
        # Check if already in combat
        existing_combat = PvECombat.objects.filter(
            character=self.character,
            status='active'
        ).first()
        
        if existing_combat and existing_combat.monster != monster:
            return JsonResponse({'error': 'Already in combat with another monster'}, status=400)
        
        with transaction.atomic():
            # Create or get combat session
            if existing_combat:
                combat = existing_combat
            else:
                combat = PvECombat.objects.create(
                    character=self.character,
                    monster=monster
                )
            
            # Execute attack using combat engine
            try:
                result = combat.execute_character_attack()
                
                # Send real-time update
                self.send_websocket_update('combat_update', {
                    'combat_id': str(combat.id),
                    'result': result,
                    'character_hp': self.character.current_hp,
                    'monster_hp': monster.current_hp,
                    'monster_alive': monster.is_alive
                })
                
                return JsonResponse({
                    'success': True,
                    'combat_id': str(combat.id),
                    'attack_result': result,
                    'character_hp': self.character.current_hp,
                    'monster_hp': monster.current_hp,
                    'monster_defeated': not monster.is_alive
                })
                
            except Exception as e:
                logger.error(f"Combat error: {e}")
                return JsonResponse({'error': 'Combat failed'}, status=500)


class FleeFromCombatView(RPGAPIView):
    """Attempt to flee from combat"""
    
    def post(self, request):
        data = self.get_json_data(request)
        
        try:
            combat_id = data.get('combat_id')
            combat = PvECombat.objects.get(
                id=combat_id,
                character=self.character,
                status='active'
            )
        except (PvECombat.DoesNotExist, TypeError):
            return JsonResponse({'error': 'Combat session not found'}, status=404)
        
        with transaction.atomic():
            try:
                result = combat.attempt_flee()
                
                self.send_websocket_update('combat_update', {
                    'combat_id': str(combat.id),
                    'flee_result': result,
                    'status': combat.status
                })
                
                return JsonResponse({
                    'success': True,
                    'flee_result': result,
                    'combat_ended': combat.status != 'active'
                })
                
            except Exception as e:
                logger.error(f"Flee error: {e}")
                return JsonResponse({'error': 'Failed to flee'}, status=500)


class GetQuestsView(RPGAPIView):
    """Get available and active quests"""
    
    def get(self, request):
        # Get available quests
        available_quests = quest_manager.get_available_quests(self.character.level)
        
        # Get character location for location-specific quests
        char_location = GeoLocation(self.character.lat, self.character.lon)
        current_region = game_world.find_region_for_location(char_location)
        
        return JsonResponse({
            'available_quests': [quest.to_dict() for quest in available_quests],
            'current_region': current_region.name if current_region else None,
            'character_level': self.character.level
        })


class StartQuestView(RPGAPIView):
    """Start a specific quest"""
    
    def post(self, request):
        data = self.get_json_data(request)
        
        quest_type = data.get('quest_type')
        difficulty = data.get('difficulty', 'normal')
        
        try:
            # Generate quest
            quest_type_enum = QuestType(quest_type) if quest_type else None
            difficulty_enum = QuestDifficulty(difficulty)
            
            quest = quest_manager.generator.generate_quest(
                self.character.level,
                quest_type=quest_type_enum,
                difficulty=difficulty_enum
            )
            
            if not quest:
                return JsonResponse({'error': 'Failed to generate quest'}, status=500)
            
            # Check if character can start quest
            if not quest_manager.start_quest(self.character, quest):
                return JsonResponse({'error': 'Cannot start quest'}, status=400)
            
            # In a full implementation, you'd save the quest to database here
            
            return JsonResponse({
                'success': True,
                'quest': quest.to_dict()
            })
            
        except ValueError as e:
            return JsonResponse({'error': f'Invalid quest parameters: {e}'}, status=400)


class CreateTradeView(RPGAPIView):
    """Create a trade offer"""
    
    def post(self, request):
        data = self.get_json_data(request)
        
        try:
            target_character_id = data.get('target_character_id')
            target_character = Character.objects.get(id=target_character_id)
        except (Character.DoesNotExist, TypeError):
            return JsonResponse({'error': 'Target character not found'}, status=404)
        
        if target_character == self.character:
            return JsonResponse({'error': 'Cannot trade with yourself'}, status=400)
        
        # Check if characters are nearby (within 50 meters)
        distance = self.character.distance_to(target_character.lat, target_character.lon)
        if distance > 50:
            return JsonResponse({'error': 'Characters too far apart'}, status=400)
        
        offered_items = data.get('offered_items', [])
        requested_items = data.get('requested_items', [])
        gold_offered = data.get('gold_offered', 0)
        gold_requested = data.get('gold_requested', 0)
        
        with transaction.atomic():
            trade = Trade.objects.create(
                requester=self.character,
                responder=target_character,
                offered_items=offered_items,
                requested_items=requested_items,
                gold_offered=gold_offered,
                gold_requested=gold_requested
            )
        
        # Send real-time notification to target
        self.send_websocket_update('trade_request_received', {
            'trade_id': str(trade.id),
            'requester': self.character.name,
            'offered_items': offered_items,
            'requested_items': requested_items,
            'gold_offered': gold_offered,
            'gold_requested': gold_requested
        })
        
        return JsonResponse({
            'success': True,
            'trade_id': str(trade.id),
            'message': f'Trade offer sent to {target_character.name}'
        })


class RespondToTradeView(RPGAPIView):
    """Respond to a trade offer"""
    
    def post(self, request):
        data = self.get_json_data(request)
        
        try:
            trade_id = data.get('trade_id')
            response = data.get('response')  # 'accept' or 'decline'
            
            if response not in ['accept', 'decline']:
                return JsonResponse({'error': 'Invalid response'}, status=400)
            
            trade = Trade.objects.get(
                id=trade_id,
                responder=self.character,
                status='pending'
            )
        except (Trade.DoesNotExist, TypeError):
            return JsonResponse({'error': 'Trade not found'}, status=404)
        
        with transaction.atomic():
            if response == 'accept':
                # Execute trade (simplified - would need full item validation)
                trade.status = 'completed'
                
                # Transfer gold
                if trade.gold_offered > 0:
                    trade.requester.gold -= trade.gold_offered
                    self.character.gold += trade.gold_offered
                    trade.requester.save(update_fields=['gold'])
                
                if trade.gold_requested > 0:
                    self.character.gold -= trade.gold_requested
                    trade.requester.gold += trade.gold_requested
                    trade.requester.save(update_fields=['gold'])
                
                self.character.save(update_fields=['gold'])
                
                result = {'success': True, 'message': 'Trade completed'}
            else:
                trade.status = 'declined'
                result = {'success': True, 'message': 'Trade declined'}
            
            trade.save()
        
        # Notify trade initiator
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'character_{trade.requester.id}',
                {
                    'type': 'trade_response',
                    'data': {
                        'trade_id': str(trade.id),
                        'response': response,
                        'responder': self.character.name
                    }
                }
            )
        except Exception as e:
            logger.warning(f"Failed to notify trade requester: {e}")
        
        return JsonResponse(result)


class GetMapDataView(RPGAPIView):
    """Get map data for current location"""
    
    def get(self, request):
        zoom = int(request.GET.get('zoom', 15))
        
        char_location = GeoLocation(self.character.lat, self.character.lon)
        map_data = game_world.create_map_data(char_location, zoom)
        
        return JsonResponse(map_data)


class ListTerritoriesView(RPGAPIView):
    """List all territory flags within a reasonable radius of the player."""

    def get(self, request):
        from .models import TerritoryFlag
        try:
            lat, lon = float(self.character.lat), float(self.character.lon)
        except Exception:
            lat, lon = 0.0, 0.0
        # Simple radius filter (~10km box; DB index friendly). Refine as needed.
        flags_qs = TerritoryFlag.objects.all()
        nearby = flags_qs.filter(
            lat__range=(lat - 0.1, lat + 0.1),
            lon__range=(lon - 0.1, lon + 0.1),
        )
        def as_dict(f):
            return {
                'id': str(getattr(f, 'id', '')),
                'name': getattr(f, 'name', 'Flag'),
                'position': {'x': float(getattr(f, 'lon', 0.0)), 'y': float(getattr(f, 'lat', 0.0))},
                'flagType': getattr(f, 'flag_type', 'basic_flag') or 'basic_flag',
                'accessType': getattr(f, 'access_type', 'public') or 'public',
                'accessCost': getattr(f, 'access_cost', 0) or 0,
                'ownerId': getattr(f, 'owner_id', None),
                'level': getattr(f, 'level', 1) or 1,
            }
        return JsonResponse({
            'success': True,
            'territories': [as_dict(f) for f in nearby]
        })


class TravelToTerritoryView(RPGAPIView):
    """Teleport the player to a territory flag center (server-authoritative)."""

    def post(self, request):
        data = self.get_json_data(request)
        territory_id = data.get('territory_id')
        if not territory_id:
            return JsonResponse({'error': 'territory_id is required'}, status=400)
        from .models import TerritoryFlag
        try:
            flag = TerritoryFlag.objects.get(id=territory_id)
        except TerritoryFlag.DoesNotExist:
            return JsonResponse({'error': 'Territory not found'}, status=404)
        # Access checks could be added here (ownership, public/private, fees)
        with transaction.atomic():
            self.character.lat = float(getattr(flag, 'lat', 0.0))
            self.character.lon = float(getattr(flag, 'lon', 0.0))
            # Optionally set move center to flag for movement enforcement
            if hasattr(self.character, 'move_center_lat') and hasattr(self.character, 'move_center_lon'):
                self.character.move_center_lat = self.character.lat
                self.character.move_center_lon = self.character.lon
            self.character.save(update_fields=['lat', 'lon'] + ([
                'move_center_lat', 'move_center_lon'] if hasattr(self.character, 'move_center_lat') else []))
        self.send_websocket_update('character_moved', {
            'character_id': str(self.character.id),
            'character_name': self.character.name,
            'new_position': {'lat': self.character.lat, 'lon': self.character.lon},
            'timestamp': timezone.now().isoformat()
        })
        return JsonResponse({
            'success': True,
            'new_position': {'lat': self.character.lat, 'lon': self.character.lon},
            'territory': {
                'id': str(getattr(flag, 'id', '')),
                'name': getattr(flag, 'name', 'Flag'),
                'position': {'x': float(getattr(flag, 'lon', 0.0)), 'y': float(getattr(flag, 'lat', 0.0))},
                'flagType': getattr(flag, 'flag_type', 'basic_flag') or 'basic_flag',
            }
        })


class GetInventoryView(RPGAPIView):
    """Get character inventory"""
    
    def get(self, request):
        inventory_items = self.character.inventory.all().select_related('item_template')
        
        items = []
        for item in inventory_items:
            items.append({
                'id': str(item.id),
                'name': item.item_template.name,
                'type': item.item_template.item_type,
                'rarity': item.item_template.rarity,
                'quantity': item.quantity,
                'is_equipped': item.is_equipped,
                'durability': item.durability,
                'max_durability': item.max_durability,
                'value': item.item_template.base_value
            })
        
        return JsonResponse({
            'items': items,
            'total_weight': sum(item.quantity for item in inventory_items),
            'max_capacity': 50,  # Could be dynamic
            'gold': self.character.gold
        })


class GetSkillsView(RPGAPIView):
    """Get character skills"""
    
    def get(self, request):
        skills = self.character.skills.all()
        
        skills_data = []
        for skill in skills:
            skills_data.append({
                'id': str(skill.id),
                'name': skill.name,
                'type': skill.skill_type,
                'level': skill.level,
                'experience': skill.experience,
                'experience_needed': skill.experience_needed_for_next_level()
            })
        
        return JsonResponse({
            'skills': skills_data,
            'available_skill_points': getattr(self.character, 'available_skill_points', 0)
        })


# URL mappings would go in urls.py
RPG_API_URLS = [
    ('game-status/', GameStatusView.as_view(), 'game_status'),
    ('move/', MoveCharacterView.as_view(), 'move_character'),
    ('attack/', AttackMonsterView.as_view(), 'attack_monster'),
    ('flee/', FleeFromCombatView.as_view(), 'flee_combat'),
    ('quests/', GetQuestsView.as_view(), 'get_quests'),
    ('quest/start/', StartQuestView.as_view(), 'start_quest'),
    ('trade/create/', CreateTradeView.as_view(), 'create_trade'),
    ('trade/respond/', RespondToTradeView.as_view(), 'respond_trade'),
    ('map/', GetMapDataView.as_view(), 'get_map'),
    ('inventory/', GetInventoryView.as_view(), 'get_inventory'),
    ('skills/', GetSkillsView.as_view(), 'get_skills'),
    ('territories/', ListTerritoriesView.as_view(), 'list_territories'),
    ('territory/travel/', TravelToTerritoryView.as_view(), 'travel_territory'),
]
