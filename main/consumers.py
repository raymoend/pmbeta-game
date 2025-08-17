"""
WebSocket consumers for real-time game functionality
Handles player movement, world updates, and chat
P2K-inspired chunk-based system with motion interpolation
"""
import json
import asyncio
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class GameConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time game updates
    Similar to P2K's real-time system
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Get user from session
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            # Reject connection for anonymous users
            await self.close()
            return
        
        # Get or create player
        self.player = await self.get_player()
        if not self.player:
            await self.close()
            return
        
        # Join game room (for now, one global room)
        self.room_group_name = 'game_world'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial world data
        await self.send_world_update()
        
        print(f"Player {self.user.username} connected to game")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        
        print(f"Player {self.user.username} disconnected")
    
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
            elif message_type == 'get_world':
                await self.send_world_update()
            elif message_type == 'harvest':
                await self.handle_harvest(message_data)
            else:
                await self.send_error(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            print(f"WebSocket error: {e}")
            await self.send_error("Internal server error")
    
    async def handle_move(self, data):
        """Handle player movement request"""
        try:
            target = data.get('target', {})
            target_lat = float(target.get('lat'))
            target_lon = float(target.get('lon'))
            
            # Validate movement (check range)
            if not await self.can_move_to(target_lat, target_lon):
                await self.send_error("Movement out of range")
                return
            
            # Get current position
            old_lat = self.player.lat
            old_lon = self.player.lon
            
            # Update player position
            await self.update_player_position(target_lat, target_lon)
            
            # Create movement event
            await self.create_game_event('move', {
                'player_id': str(self.player.id),
                'start': {
                    'lat': old_lat,
                    'lon': old_lon,
                    'timestamp': datetime.now().timestamp()
                },
                'end': {
                    'lat': target_lat,
                    'lon': target_lon,
                    'timestamp': datetime.now().timestamp()
                }
            })
            
            # Broadcast movement to all players
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'player_moved',
                    'data': {
                        'player_id': str(self.player.id),
                        'username': self.user.username,
                        'start': {
                            'lat': old_lat,
                            'lon': old_lon,
                            'timestamp': datetime.now().timestamp()
                        },
                        'end': {
                            'lat': target_lat,
                            'lon': target_lon,
                            'timestamp': datetime.now().timestamp()
                        }
                    }
                }
            )
            
            print(f"Player {self.user.username} moved to {target_lat:.6f}, {target_lon:.6f}")
            
        except (ValueError, KeyError) as e:
            await self.send_error("Invalid movement data")
        except Exception as e:
            print(f"Move error: {e}")
            await self.send_error("Movement failed")
    
    async def handle_chat(self, data):
        """Handle chat message"""
        try:
            message = data.get('message', '').strip()
            if not message or len(message) > 200:
                await self.send_error("Invalid message")
                return
            
            # Broadcast chat message to all players
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'data': {
                        'username': self.user.username,
                        'message': message,
                        'timestamp': datetime.now().isoformat()
                    }
                }
            )
            
        except Exception as e:
            print(f"Chat error: {e}")
            await self.send_error("Chat failed")
    
    async def handle_harvest(self, data):
        """Handle resource harvesting"""
        try:
            structure_id = data.get('structure_id')
            if not structure_id:
                await self.send_error("No structure specified")
                return
            
            # TODO: Implement harvesting logic
            await self.send_error("Harvesting not yet implemented")
            
        except Exception as e:
            print(f"Harvest error: {e}")
            await self.send_error("Harvest failed")
    
    async def send_world_update(self):
        """Send current world state to player"""
        try:
            # Get chunk data for player's current location
            from .models import Chunk
            chunk = Chunk.from_coords(self.player.lat, self.player.lon)
            world_data = await self.get_chunk_data(chunk)
            
            await self.send(text_data=json.dumps({
                'type': 'world_update',
                'data': world_data
            }))
            
        except Exception as e:
            print(f"World update error: {e}")
    
    async def send_error(self, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
    
    # WebSocket message handlers (called from group_send)
    async def player_moved(self, event):
        """Handle player moved event"""
        await self.send(text_data=json.dumps({
            'type': 'player_moved',
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
    def get_player(self):
        """Get player object for current user"""
        from .models import Player
        try:
            return Player.objects.get(user=self.user)
        except Player.DoesNotExist:
            # Create new player if doesn't exist
            return Player.create_new_player(self.user)
    
    @database_sync_to_async
    def can_move_to(self, lat, lon):
        """Check if player can move to specified coordinates"""
        return self.player.can_move_to(lat, lon)
    
    @database_sync_to_async
    def update_player_position(self, lat, lon):
        """Update player's position in database"""
        self.player.lat = lat
        self.player.lon = lon
        self.player.save(update_fields=['lat', 'lon'])
    
    @database_sync_to_async
    def create_game_event(self, event_type, event_data):
        """Create a game event record"""
        from .models import GameEvent
        return GameEvent.objects.create(
            event_type=event_type,
            player=self.player,
            data=event_data
        )
    
    @database_sync_to_async
    def get_chunk_data(self, chunk):
        """Get all data for a specific chunk"""
        # Get players in chunk
        players = {}
        for player in chunk.get_players():
            players[str(player.id)] = {
                'id': str(player.id),
                'username': player.user.username,
                'lat': player.lat,
                'lon': player.lon,
                'level': player.level,
                'avatar': player.avatar
            }
        
        # Get structures in chunk
        structures = {}
        for structure in chunk.get_structures():
            structures[str(structure.id)] = {
                'id': str(structure.id),
                'type': structure.structure_type,
                'type_name': structure.get_structure_type_display(),
                'lat': structure.lat,
                'lon': structure.lon,
                'hp': structure.hp
            }
        
        # Get ground items in chunk
        items = {}
        for item in chunk.get_items():
            items[str(item.id)] = {
                'id': str(item.id),
                'type': item.item_type,
                'type_name': item.get_item_type_display(),
                'quantity': item.quantity,
                'lat': item.lat,
                'lon': item.lon
            }
        
        return {
            'chunk': {
                'x': chunk.x,
                'y': chunk.y
            },
            'players': players,
            'structures': structures,
            'items': items,
            'center': {
                'lat': self.player.center_lat,
                'lon': self.player.center_lon
            }
        }
