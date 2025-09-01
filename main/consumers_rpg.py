"""
WebSocket consumers for real-time RPG game features
Handles real-time combat, trading, player movement, and chat
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class RPGGameConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time RPG game updates"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        try:
            # Get user from session
            user = self.scope["user"]
            if not user.is_authenticated:
                await self.close(code=4001)
                return

            # Resolve character for this user
            self.character = await self.get_character(user)
            if not self.character:
                await self.close(code=4002)
                return

            # Accept the socket
            await self.accept()

            # Join character-scoped group for push updates (inventory, character, resources)
            self.character_group = f"character_{self.character.id}"
            await self.channel_layer.group_add(self.character_group, self.channel_name)

            # Join a coarse location-scoped group for local events (movement, resources)
            try:
                lat_key = int(self.character.lat * 1000)
                lon_key = int(self.character.lon * 1000)
                self.location_group = f"location_{lat_key}_{lon_key}"
                await self.channel_layer.group_add(self.location_group, self.channel_name)
            except Exception:
                self.location_group = None

            # Join global chat group
            try:
                await self.channel_layer.group_add("global_chat", self.channel_name)
            except Exception:
                pass

            # Send a simple test message
            await self.send(text_data=json.dumps({
                'type': 'connection_test',
                'message': f'WebSocket connected for user {user.username}'
            }))

            logger.info(f"WebSocket connected for user: {user.username}")

        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            await self.close(code=4000)
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            if hasattr(self, 'character_group'):
                await self.channel_layer.group_discard(
                    self.character_group,
                    self.channel_name
                )
            
            if hasattr(self, 'location_group'):
                await self.channel_layer.group_discard(
                    self.location_group,
                    self.channel_name
                )
            
            await self.channel_layer.group_discard(
                "global_chat",
                self.channel_name
            )
            
            # Update character status to offline
            if hasattr(self, 'character'):
                await self.update_character_online_status(self.character.id, False)
                logger.info(f"WebSocket disconnected for character: {self.character.name}")
                
        except Exception as e:
            logger.error(f"WebSocket disconnect error: {e}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'player_movement':
                await self.handle_player_movement(data)
            elif message_type == 'combat_action':
                await self.handle_combat_action(data)
            elif message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'request_nearby_data':
                await self.send_nearby_data()
            elif message_type == 'ping':
                await self.send_pong()
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received in WebSocket")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    async def handle_player_movement(self, data):
        """Handle real-time player movement"""
        try:
            new_lat = float(data.get('lat'))
            new_lon = float(data.get('lon'))
            
            # Basic validation
            if not (-90 <= new_lat <= 90) or not (-180 <= new_lon <= 180):
                await self.send_error("Invalid coordinates")
                return
            
            # Update character position
            old_lat, old_lon = await self.update_character_position(self.character.id, new_lat, new_lon)
            
            # Check if we need to change location group
            new_location_group = f"location_{int(new_lat * 1000)}_{int(new_lon * 1000)}"
            if new_location_group != self.location_group:
                # Leave old location group
                await self.channel_layer.group_discard(
                    self.location_group,
                    self.channel_name
                )
                # Join new location group
                await self.channel_layer.group_add(
                    new_location_group,
                    self.channel_name
                )
                self.location_group = new_location_group
            
            # Broadcast movement to nearby players
            await self.channel_layer.group_send(
                self.location_group,
                {
                    'type': 'player_moved',
                    'character_id': str(self.character.id),
                    'character_name': self.character.name,
                    'lat': new_lat,
                    'lon': new_lon,
                }
            )
            
        except (ValueError, TypeError) as e:
            await self.send_error(f"Invalid movement data: {e}")
    
    async def handle_combat_action(self, data):
        """Handle real-time combat actions"""
        try:
            action_type = data.get('action')
            combat_id = data.get('combat_id')
            
            if not combat_id or not action_type:
                await self.send_error("Missing combat data")
                return
            
            # Process combat action
            result = await self.process_combat_action(combat_id, action_type)
            
            if result:
                # Send result back to sender
                await self.send(text_data=json.dumps({
                    'type': 'combat_result',
                    'data': result
                }))
                
        except Exception as e:
            logger.error(f"Combat action error: {e}")
            await self.send_error("Combat action failed")
    
    async def handle_chat_message(self, data):
        """Handle real-time chat messages"""
        try:
            message = data.get('message', '').strip()
            chat_type = data.get('chat_type', 'local')  # local, global
            
            if not message or len(message) > 500:
                await self.send_error("Invalid message")
                return
            
            chat_data = {
                'type': 'chat_message',
                'message': message,
                'character_name': self.character.name,
                'character_id': str(self.character.id),
                'chat_type': chat_type,
                'timestamp': self.get_current_timestamp()
            }
            
            if chat_type == 'local':
                # Send to nearby players
                await self.channel_layer.group_send(
                    self.location_group,
                    chat_data
                )
            elif chat_type == 'global':
                # Send to all online players
                await self.channel_layer.group_send(
                    "global_chat",
                    chat_data
                )
                
        except Exception as e:
            logger.error(f"Chat message error: {e}")
            await self.send_error("Chat failed")
    
    async def send_pong(self):
        """Respond to ping with pong"""
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': self.get_current_timestamp()
        }))
    
    async def send_error(self, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
    
    # WebSocket event handlers
    async def player_moved(self, event):
        """Send player movement update to client"""
        if str(self.character.id) != event['character_id']:  # Don't send to self
            await self.send(text_data=json.dumps({
                'type': 'player_movement',
                'character_id': event['character_id'],
                'character_name': event['character_name'],
                'lat': event['lat'],
                'lon': event['lon'],
            }))

    async def inventory_update(self, event):
        """Forward inventory update signal to client"""
        await self.send(text_data=json.dumps({'type': 'inventory_update'}))

    async def character_update(self, event):
        """Forward character update signal to client"""
        payload = {'type': 'character_update'}
        data = event.get('data') if isinstance(event, dict) else None
        if data is not None:
            payload['data'] = data
        await self.send(text_data=json.dumps(payload))

    async def resource_update(self, event):
        """Forward resource node update(s) to client"""
        try:
            if 'resource' in event:
                await self.send(text_data=json.dumps({'type': 'resource_update', 'resource': event['resource']}))
            elif 'resources' in event:
                await self.send(text_data=json.dumps({'type': 'resource_update', 'resources': event['resources']}))
        except Exception:
            pass
    
    async def chat_message(self, event):
        """Send chat message to client"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'character_name': event['character_name'],
            'character_id': event['character_id'],
            'chat_type': event['chat_type'],
            'timestamp': event['timestamp']
        }))
    
    async def notification(self, event):
        """Send notification to client"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'title': event.get('title', 'Notification'),
            'message': event['message'],
            'notification_type': event.get('notification_type', 'info')
        }))
    
    # Database helper methods
    @database_sync_to_async
    def get_character(self, user):
        """Get character for user"""
        try:
            from .models import Character
            return Character.objects.get(user=user)
        except:
            return None
    
    @database_sync_to_async
    def update_character_position(self, character_id, lat, lon):
        """Update character position in database"""
        try:
            from .models import Character
            character = Character.objects.get(id=character_id)
            old_lat, old_lon = character.lat, character.lon
            character.lat = lat
            character.lon = lon
            character.save(update_fields=['lat', 'lon'])
            return old_lat, old_lon
        except:
            return None, None
    
    @database_sync_to_async
    def update_character_online_status(self, character_id, is_online):
        """Update character online status"""
        try:
            from .models import Character
            character = Character.objects.get(id=character_id)
            character.is_online = is_online
            character.save(update_fields=['is_online', 'last_activity'])
            return True
        except:
            return False
    
    @database_sync_to_async
    def process_combat_action(self, combat_id, action_type):
        """Process combat action in database"""
        try:
            from .models import PvECombat
            import random
            
            # Get combat session
            combat = PvECombat.objects.get(id=combat_id, status='active')
            
            if action_type == 'attack':
                # Simple combat resolution
                player_damage = max(1, combat.character.strength - combat.monster.template.defense + random.randint(-3, 3))
                combat.monster_hp = max(0, combat.monster_hp - player_damage)
                
                message = f"You dealt {player_damage} damage!"
                
                if combat.monster_hp <= 0:
                    # Monster defeated
                    combat.status = 'victory'
                    combat.experience_gained = combat.monster.template.base_experience
                    combat.gold_gained = combat.monster.template.base_gold
                    combat.character.gain_experience(combat.experience_gained)
                    combat.character.gold += combat.gold_gained
                    combat.character.in_combat = False
                    combat.character.save()
                    combat.monster.die()
                    message += f" Monster defeated! Gained {combat.experience_gained} XP and {combat.gold_gained} gold!"
                else:
                    # Monster counter-attack
                    monster_damage = max(1, combat.monster.template.strength - combat.character.defense + random.randint(-2, 2))
                    combat.character_hp = max(0, combat.character_hp - monster_damage)
                    message += f" Monster hit you for {monster_damage} damage!"
                    
                    if combat.character_hp <= 0:
                        combat.status = 'defeat'
                        combat.character.current_hp = 1
                        combat.character.in_combat = False
                        combat.character.save()
                        message += " You were defeated!"
                
                combat.save()
                
                return {
                    'combat_id': str(combat.id),
                    'status': combat.status,
                    'character_hp': combat.character_hp,
                    'monster_hp': combat.monster_hp,
                    'message': message
                }
            
            elif action_type == 'flee':
                # Attempt to flee
                if random.random() < 0.7:  # 70% chance to flee successfully
                    combat.status = 'fled'
                    combat.character.in_combat = False
                    combat.character.save()
                    combat.monster.in_combat = False
                    combat.monster.current_target = None
                    combat.monster.save()
                    combat.save()
                    
                    return {
                        'combat_id': str(combat.id),
                        'status': 'fled',
                        'message': 'You successfully fled from combat!'
                    }
                else:
                    # Failed to flee, monster gets free attack
                    monster_damage = max(1, combat.monster.template.strength - combat.character.defense + random.randint(-1, 1))
                    combat.character_hp = max(0, combat.character_hp - monster_damage)
                    
                    if combat.character_hp <= 0:
                        combat.status = 'defeat'
                        combat.character.current_hp = 1
                        combat.character.in_combat = False
                        combat.character.save()
                    
                    combat.save()
                    
                    return {
                        'combat_id': str(combat.id),
                        'status': combat.status,
                        'character_hp': combat.character_hp,
                        'monster_hp': combat.monster_hp,
                        'message': f'Failed to flee! Monster hit you for {monster_damage} damage!'
                    }
                
        except Exception as e:
            logger.error(f"Combat processing error: {e}")
            return None
    
    async def send_character_status(self):
        """Send current character status to client"""
        character_data = await self.get_character_data(self.character.id)
        if character_data:
            await self.send(text_data=json.dumps({
                'type': 'character_status',
                'data': character_data
            }))
    
    async def send_nearby_data(self):
        """Send nearby players and monsters to client"""
        nearby_data = await self.get_nearby_data(self.character.id)
        if nearby_data:
            await self.send(text_data=json.dumps({
                'type': 'nearby_data',
                'data': nearby_data
            }))
    
    @database_sync_to_async
    def get_character_data(self, character_id):
        """Get character data for client"""
        try:
            from .models import Character
            character = Character.objects.get(id=character_id)
            return {
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
                'gold': character.gold,
                'in_combat': character.in_combat
            }
        except:
            return None
    
    @database_sync_to_async
    def get_nearby_data(self, character_id):
        """Get nearby players and monsters"""
        try:
            from .models import Character, Monster
            character = Character.objects.get(id=character_id)
            
            # Get nearby players (within 1km)
            lat_range = 0.01
            lon_range = 0.01
            
            nearby_players = Character.objects.filter(
                lat__gte=character.lat - lat_range,
                lat__lte=character.lat + lat_range,
                lon__gte=character.lon - lon_range,
                lon__lte=character.lon + lon_range,
                is_online=True
            ).exclude(id=character.id)[:20]
            
            # Get nearby monsters (within 500m)
            lat_range_monsters = 0.005
            lon_range_monsters = 0.005
            
            nearby_monsters = Monster.objects.filter(
                lat__gte=character.lat - lat_range_monsters,
                lat__lte=character.lat + lat_range_monsters,
                lon__gte=character.lon - lon_range_monsters,
                lon__lte=character.lon + lon_range_monsters,
                is_alive=True
            ).select_related('template')[:10]
            
            return {
                'players': [
                    {
                        'id': str(p.id),
                        'name': p.name,
                        'level': p.level,
                        'lat': p.lat,
                        'lon': p.lon
                    }
                    for p in nearby_players
                ],
                'monsters': [
                    {
                        'id': str(m.id),
                        'name': m.template.name,
                        'level': m.template.level,
                        'lat': m.lat,
                        'lon': m.lon,
                        'current_hp': m.current_hp,
                        'max_hp': m.max_hp
                    }
                    for m in nearby_monsters
                ]
            }
        except:
            return {'players': [], 'monsters': []}
    
    def get_current_timestamp(self):
        """Get current timestamp"""
        from django.utils import timezone
        return timezone.now().isoformat()
