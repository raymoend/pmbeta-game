"""
WebSocket consumers for real-time RPG game functionality
Handles character movement, combat, trading, and chat
"""
import json
import asyncio
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class RPGGameConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time RPG game updates
    Handles character interactions, combat, and trading
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Get user from session
        self.user = self.scope["user"]
        
        if isinstance(self.user, AnonymousUser) or self.user.is_anonymous:
            # Reject connection for anonymous users
            await self.close()
            return
        
        # Get character for user
        self.character = await self.get_character()
        if not self.character:
            await self.close()
            return
        
        # Join personal group for character-specific messages
        self.character_group_name = f'character_{self.character.id}'
        await self.channel_layer.group_add(
            self.character_group_name,
            self.channel_name
        )
        
        # Join location-based group
        self.location_group_name = f'location_{int(self.character.lat * 1000)}_{int(self.character.lon * 1000)}'
        await self.channel_layer.group_add(
            self.location_group_name,
            self.channel_name
        )
        
        # Join global game room
        self.global_group_name = 'global_game'
        await self.channel_layer.group_add(
            self.global_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial game data
        await self.send_initial_data()
        
        print(f"Character {self.character.name} ({self.user.username}) connected to RPG game")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave all groups
        if hasattr(self, 'character_group_name'):
            await self.channel_layer.group_discard(
                self.character_group_name,
                self.channel_name
            )
        
        if hasattr(self, 'location_group_name'):
            await self.channel_layer.group_discard(
                self.location_group_name,
                self.channel_name
            )
        
        if hasattr(self, 'global_group_name'):
            await self.channel_layer.group_discard(
                self.global_group_name,
                self.channel_name
            )
        
        print(f"Character {self.character.name if hasattr(self, 'character') else 'Unknown'} disconnected")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            message_data = data.get('data', {})
            
            # Route message to appropriate handler
            if message_type == 'move':
                await self.handle_move(message_data)
            elif message_type == 'chat':
                await self.handle_chat(message_data)
            elif message_type == 'get_game_data':
                await self.send_initial_data()
            elif message_type == 'attack':
                await self.handle_attack(message_data)
            elif message_type == 'flee':
                await self.handle_flee(message_data)
            elif message_type == 'use_skill':
                await self.handle_use_skill(message_data)
            elif message_type == 'trade_request':
                await self.handle_trade_request(message_data)
            elif message_type == 'trade_respond':
                await self.handle_trade_respond(message_data)
            elif message_type == 'get_inventory':
                await self.send_inventory()
            elif message_type == 'get_character_stats':
                await self.send_character_stats()
            else:
                await self.send_error(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            print(f"WebSocket error: {e}")
            await self.send_error("Internal server error")
    
    async def handle_move(self, data):
        """Handle character movement request"""
        try:
            target = data.get('target', {})
            target_lat = float(target.get('lat'))
            target_lon = float(target.get('lon'))
            
            # Validate movement (basic range check)
            if not await self.can_move_to(target_lat, target_lon):
                await self.send_error("Movement out of range")
                return
            
            # Get current position
            old_lat = self.character.lat
            old_lon = self.character.lon
            old_location_group = f'location_{int(old_lat * 1000)}_{int(old_lon * 1000)}'
            
            # Update character position
            await self.update_character_position(target_lat, target_lon)
            
            # Update location group
            new_location_group = f'location_{int(target_lat * 1000)}_{int(target_lon * 1000)}'
            if old_location_group != new_location_group:
                # Leave old location group
                await self.channel_layer.group_discard(
                    self.location_group_name,
                    self.channel_name
                )
                # Join new location group
                self.location_group_name = new_location_group
                await self.channel_layer.group_add(
                    self.location_group_name,
                    self.channel_name
                )
            
            # Broadcast movement to location groups
            movement_data = {
                'character_id': str(self.character.id),
                'character_name': self.character.name,
                'old_position': {
                    'lat': old_lat,
                    'lon': old_lon
                },
                'new_position': {
                    'lat': target_lat,
                    'lon': target_lon
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # Send to both old and new location groups
            await self.channel_layer.group_send(
                old_location_group,
                {
                    'type': 'character_moved',
                    'data': movement_data
                }
            )
            
            if old_location_group != new_location_group:
                await self.channel_layer.group_send(
                    new_location_group,
                    {
                        'type': 'character_moved',
                        'data': movement_data
                    }
                )
            
            print(f"Character {self.character.name} moved to {target_lat:.6f}, {target_lon:.6f}")
            
        except (ValueError, KeyError) as e:
            await self.send_error("Invalid movement data")
        except Exception as e:
            print(f"Move error: {e}")
            await self.send_error("Movement failed")
    
    async def handle_chat(self, data):
        """Handle chat message"""
        try:
            message = data.get('message', '').strip()
            channel = data.get('channel', 'global')  # global, location, or private
            
            if not message or len(message) > 200:
                await self.send_error("Invalid message")
                return
            
            chat_data = {
                'character_name': self.character.name,
                'message': message,
                'channel': channel,
                'timestamp': datetime.now().isoformat()
            }
            
            # Send to appropriate channel
            if channel == 'global':
                group_name = self.global_group_name
            elif channel == 'location':
                group_name = self.location_group_name
            else:
                await self.send_error("Invalid chat channel")
                return
            
            await self.channel_layer.group_send(
                group_name,
                {
                    'type': 'chat_message',
                    'data': chat_data
                }
            )
            
        except Exception as e:
            print(f"Chat error: {e}")
            await self.send_error("Chat failed")
    
    async def handle_attack(self, data):
        """Handle combat attack action"""
        try:
            target_type = data.get('target_type')  # 'monster' or 'character'
            target_id = data.get('target_id')
            
            if not target_type or not target_id:
                await self.send_error("Invalid attack target")
                return
            
            if target_type == 'monster':
                result = await self.attack_monster(target_id)
            elif target_type == 'character':
                result = await self.attack_character(target_id)
            else:
                await self.send_error("Invalid target type")
                return
            
            if result:
                # Send combat update to relevant groups
                await self.send_combat_update(result)
            
        except Exception as e:
            print(f"Attack error: {e}")
            await self.send_error("Attack failed")
    
    async def handle_flee(self, data):
        """Handle flee from combat"""
        try:
            combat_id = data.get('combat_id')
            if not combat_id:
                await self.send_error("No combat session specified")
                return
            
            result = await self.flee_combat(combat_id)
            if result:
                await self.send_combat_update(result)
            
        except Exception as e:
            print(f"Flee error: {e}")
            await self.send_error("Flee failed")
    
    async def handle_use_skill(self, data):
        """Handle skill usage"""
        try:
            skill_id = data.get('skill_id')
            target_id = data.get('target_id')
            
            if not skill_id:
                await self.send_error("No skill specified")
                return
            
            result = await self.use_skill(skill_id, target_id)
            if result:
                await self.send_skill_result(result)
            
        except Exception as e:
            print(f"Skill error: {e}")
            await self.send_error("Skill failed")
    
    async def handle_trade_request(self, data):
        """Handle trade request to another character"""
        try:
            target_character_id = data.get('target_character_id')
            offered_items = data.get('offered_items', [])
            requested_items = data.get('requested_items', [])
            
            if not target_character_id:
                await self.send_error("No target character specified")
                return
            
            trade = await self.create_trade_request(
                target_character_id, offered_items, requested_items
            )
            
            if trade:
                # Notify target character
                await self.channel_layer.group_send(
                    f'character_{target_character_id}',
                    {
                        'type': 'trade_request_received',
                        'data': {
                            'trade_id': str(trade.id),
                            'requester': self.character.name,
                            'offered_items': offered_items,
                            'requested_items': requested_items
                        }
                    }
                )
            
        except Exception as e:
            print(f"Trade request error: {e}")
            await self.send_error("Trade request failed")
    
    async def handle_trade_respond(self, data):
        """Handle response to trade request"""
        try:
            trade_id = data.get('trade_id')
            response = data.get('response')  # 'accept' or 'decline'
            
            if not trade_id or response not in ['accept', 'decline']:
                await self.send_error("Invalid trade response")
                return
            
            result = await self.respond_to_trade(trade_id, response)
            if result:
                await self.send_trade_result(result)
            
        except Exception as e:
            print(f"Trade response error: {e}")
            await self.send_error("Trade response failed")
    
    async def send_initial_data(self):
        """Send initial game data to character"""
        try:
            game_data = await self.get_game_data()
            
            await self.send(text_data=json.dumps({
                'type': 'initial_data',
                'data': game_data
            }))
            
        except Exception as e:
            print(f"Initial data error: {e}")
    
    async def send_inventory(self):
        """Send character inventory data"""
        try:
            inventory = await self.get_inventory_data()
            
            await self.send(text_data=json.dumps({
                'type': 'inventory',
                'data': inventory
            }))
            
        except Exception as e:
            print(f"Inventory error: {e}")
    
    async def send_character_stats(self):
        """Send character statistics"""
        try:
            stats = await self.get_character_stats_data()
            
            await self.send(text_data=json.dumps({
                'type': 'character_stats',
                'data': stats
            }))
            
        except Exception as e:
            print(f"Character stats error: {e}")
    
    async def send_combat_update(self, combat_data):
        """Send combat update to relevant parties"""
        await self.send(text_data=json.dumps({
            'type': 'combat_update',
            'data': combat_data
        }))
    
    async def send_skill_result(self, skill_data):
        """Send skill usage result"""
        await self.send(text_data=json.dumps({
            'type': 'skill_result',
            'data': skill_data
        }))
    
    async def send_trade_result(self, trade_data):
        """Send trade result to both parties"""
        await self.send(text_data=json.dumps({
            'type': 'trade_result',
            'data': trade_data
        }))
    
    async def send_error(self, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
    
    # WebSocket message handlers (called from group_send)
    async def character_moved(self, event):
        """Handle character moved event"""
        await self.send(text_data=json.dumps({
            'type': 'character_moved',
            'data': event['data']
        }))
    
    async def trade_request_received(self, event):
        """Handle trade request received event"""
        await self.send(text_data=json.dumps({
            'type': 'trade_request',
            'data': event['data']
        }))
    
    async def chat_message(self, event):
        """Handle chat message event"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'data': event['data']
        }))
    
    async def world_changed(self, event):
        """Handle world change event"""
        await self.send(text_data=json.dumps({
            'type': 'world_update',
            'data': event['data']
        }))
    
    # Database operations (async)
    @database_sync_to_async
    def get_character(self):
        """Get character object for current user"""
        from .models import Character
        try:
            return Character.objects.get(user=self.user)
        except Character.DoesNotExist:
            return None
    
    @database_sync_to_async
    def can_move_to(self, lat, lon):
        """Check if character can move to specified coordinates"""
        # Basic validation - could add more complex checks
        import math
        distance = math.sqrt(
            (lat - self.character.lat) ** 2 + 
            (lon - self.character.lon) ** 2
        )
        return distance <= 0.01  # Max movement range
    
    @database_sync_to_async
    def update_character_position(self, lat, lon):
        """Update character's position in database"""
        self.character.lat = lat
        self.character.lon = lon
        self.character.save(update_fields=['lat', 'lon'])
    
    @database_sync_to_async
    def get_game_data(self):
        """Get initial game data for character"""
        from .models import Monster, Character
        
        # Get nearby characters
        nearby_characters = Character.objects.filter(
            lat__range=(self.character.lat - 0.01, self.character.lat + 0.01),
            lon__range=(self.character.lon - 0.01, self.character.lon + 0.01)
        ).exclude(id=self.character.id)
        
        characters_data = []
        for char in nearby_characters:
            characters_data.append({
                'id': str(char.id),
                'name': char.name,
                'level': char.level,
                'latitude': char.lat,
                'longitude': char.lon,
                'current_health': char.current_hp,
                'max_health': char.max_hp
            })
        
        # Get nearby monsters
        nearby_monsters = Monster.objects.filter(
            lat__range=(self.character.lat - 0.01, self.character.lat + 0.01),
            lon__range=(self.character.lon - 0.01, self.character.lon + 0.01),
            is_alive=True
        )
        
        monsters_data = []
        for monster in nearby_monsters:
            monsters_data.append({
                'id': str(monster.id),
                'name': monster.name,
                'level': monster.level,
                'latitude': monster.lat,
                'longitude': monster.lon,
                'current_health': monster.current_hp,
                'max_health': monster.max_hp,
                'monster_type': monster.monster_type
            })
        
        return {
            'character': {
                'id': str(self.character.id),
                'name': self.character.name,
                'level': self.character.level,
                'latitude': self.character.lat,
                'longitude': self.character.lon,
                'current_health': self.character.current_hp,
                'max_health': self.character.max_hp,
                'experience': self.character.experience,
                'gold': self.character.gold
            },
            'nearby_characters': characters_data,
            'nearby_monsters': monsters_data
        }
    
    @database_sync_to_async
    def get_inventory_data(self):
        """Get character inventory data"""
        inventory_items = self.character.inventory.all()
        items_data = []
        
        for item in inventory_items:
            items_data.append({
                'id': str(item.id),
                'item_type': item.item_type,
                'quantity': item.quantity,
                'durability': item.durability,
                'max_durability': item.max_durability,
                'is_equipped': item.is_equipped
            })
        
        return {
            'items': items_data,
            'capacity': 50,  # Could be dynamic based on character stats
            'weight': sum(item.quantity for item in inventory_items)
        }
    
    @database_sync_to_async
    def get_character_stats_data(self):
        """Get character statistics data"""
        skills_data = []
        for skill in self.character.skills.all():
            skills_data.append({
                'skill_name': skill.name,
                'level': skill.level,
                'experience': skill.experience,
                'skill_type': skill.skill_type
            })
        
        return {
            'basic_stats': {
                'strength': self.character.strength,
                'defense': self.character.defense,
                'vitality': self.character.vitality,
                'agility': self.character.agility,
                'intelligence': self.character.intelligence
            },
            'derived_stats': {
                'max_hp': self.character.max_hp,
                'current_hp': self.character.current_hp,
                'max_mana': self.character.max_mana,
                'current_mana': self.character.current_mana,
                'max_stamina': self.character.max_stamina,
                'current_stamina': self.character.current_stamina
            },
            'skills': skills_data,
            'gold': self.character.gold
        }
    
    @database_sync_to_async
    def attack_monster(self, monster_id):
        """Handle attack on monster"""
        from .models import Monster, PvECombat
        try:
            monster = Monster.objects.get(id=monster_id, is_alive=True)
            
            # Check if already in combat with this monster
            existing_combat = PvECombat.objects.filter(
                character=self.character,
                monster=monster,
                status='active'
            ).first()
            
            if existing_combat:
                combat_session = existing_combat
            else:
                # Create new combat session
                combat_session = PvECombat.objects.create(
                    character=self.character,
                    monster=monster
                )
            
            # Execute attack
            result = combat_session.execute_character_attack()
            
            return {
                'combat_id': str(combat_session.id),
                'attack_result': result,
                'character_health': self.character.current_health,
                'monster_health': monster.current_health,
                'monster_alive': monster.is_alive
            }
            
        except Monster.DoesNotExist:
            return None
    
    @database_sync_to_async
    def attack_character(self, character_id):
        """Handle attack on another character (PvP)"""
        from .models import Character, PvPCombat
        try:
            target_character = Character.objects.get(id=character_id)
            
            if target_character == self.character:
                return None  # Can't attack self
            
            # Create PvP challenge
            combat_session = PvPCombat.objects.create(
                challenger=self.character,
                defender=target_character
            )
            
            return {
                'combat_id': str(combat_session.id),
                'type': 'pvp_challenge',
                'target_character': target_character.name,
                'message': 'PvP challenge sent'
            }
            
        except Character.DoesNotExist:
            return None
    
    @database_sync_to_async
    def flee_combat(self, combat_id):
        """Handle fleeing from combat"""
        from .models import PvECombat, PvPCombat
        from django.db.models import Q
        try:
            # Try PvE combat first
            try:
                combat = PvECombat.objects.get(id=combat_id, character=self.character, status='active')
                combat.status = 'fled'
                combat.save()
                return {'type': 'pve_flee', 'success': True}
            except PvECombat.DoesNotExist:
                pass
            
            # Try PvP combat
            try:
                combat = PvPCombat.objects.filter(
                    id=combat_id, 
                    status='active'
                ).filter(
                    Q(challenger=self.character) | Q(defender=self.character)
                ).first()
                
                if combat:
                    combat.status = 'fled'
                    combat.save()
                    return {'type': 'pvp_flee', 'success': True}
            except:
                pass
            
            return None
        except Exception:
            return None
    
    @database_sync_to_async
    def use_skill(self, skill_id, target_id=None):
        """Handle skill usage"""
        from .models import Skill
        try:
            skill = Skill.objects.get(
                character=self.character,
                id=skill_id
            )
            
            # Basic skill usage logic - could be expanded
            return {
                'skill_name': skill.name,
                'level': skill.level,
                'success': True,
                'message': f'Used {skill.name}'
            }
            
        except Skill.DoesNotExist:
            return None
    
    @database_sync_to_async
    def create_trade_request(self, target_character_id, offered_items, requested_items):
        """Create a trade request"""
        from .models import Trade, Character
        try:
            target_character = Character.objects.get(id=target_character_id)
            
            trade = Trade.objects.create(
                requester=self.character,
                responder=target_character,
                offered_items=offered_items,
                requested_items=requested_items
            )
            
            return trade
            
        except Character.DoesNotExist:
            return None
    
    @database_sync_to_async
    def respond_to_trade(self, trade_id, response):
        """Respond to a trade request"""
        from .models import Trade
        try:
            trade = Trade.objects.get(
                id=trade_id,
                responder=self.character,
                status='pending'
            )
            
            if response == 'accept':
                # Execute trade logic here
                trade.status = 'accepted'
                result = {'success': True, 'message': 'Trade accepted'}
            else:
                trade.status = 'declined'
                result = {'success': False, 'message': 'Trade declined'}
            
            trade.save()
            return result
            
        except Trade.DoesNotExist:
            return None
