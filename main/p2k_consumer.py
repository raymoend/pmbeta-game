"""
P2K-Style WebSocket Consumer
Implements chunk-based world loading and smooth movement like Parallel Kingdom
"""
import json
import uuid
import time
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from .models import Player, GameEvent, Flag, NPC, ResourceNode
from .motion import EntityMotion, ChunkManager, WorldUpdater
from django.conf import settings


class P2KGameConsumer(AsyncWebsocketConsumer):
    """
    P2K-inspired WebSocket consumer with chunk-based world management
    Features:
    - Chunk-based entity loading (like P2K)
    - Smooth motion interpolation
    - Real-time multiplayer updates
    - Mafia game mechanics
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.player = None
        self.user = None
        self.current_chunks = []
        self.chunk_groups = []
        self.motion = None
    
    async def connect(self):
        """Handle WebSocket connection - P2K style"""
        # Get user from scope
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Get or create player
        self.player = await self.get_or_create_player()
        if not self.player:
            await self.close()
            return
        
        # Initialize motion system
        self.motion = await sync_to_async(EntityMotion.get_or_create)(self.player)
        
        # Accept connection
        await self.accept()
        
        # Load initial world data around player
        await self.send_initial_world()
        
        print(f"P2K Player {self.user.username} connected")
    
    async def disconnect(self, close_code):
        """Handle disconnection - clean up chunk subscriptions"""
        if self.chunk_groups:
            for group in self.chunk_groups:
                await self.channel_layer.group_discard(group, self.channel_name)
        
        # Sync motion to database
        if self.motion:
            await sync_to_async(self.motion.sync_to_db)()
        
        print(f"P2K Player {self.user.username} disconnected")
    
    async def receive(self, text_data):
        """Handle incoming messages"""
        try:
            data = json.loads(text_data)
            tag = data.get('tag')
            message_data = data.get('data', {})
            
            if tag == 'move':
                await self.handle_move(message_data)
            elif tag == 'recentre':
                await self.handle_recentre()
            elif tag == 'chat':
                await self.handle_chat(message_data)
            elif tag == 'attack_flag':
                await self.handle_attack_flag(message_data)
            elif tag == 'attack_npc':
                await self.handle_attack_npc(message_data)
            elif tag == 'harvest_resource':
                await self.handle_harvest_resource(message_data)
            else:
                await self.send_error(f"Unknown tag: {tag}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON")
        except Exception as e:
            print(f"P2K Consumer error: {e}")
            await self.send_error("Internal error")
    
    async def handle_move(self, data):
        """Handle movement request - P2K style"""
        try:
            target = data.get('target', {})
            target_lat = float(target['lat'])
            target_lon = float(target['lon'])
            
            # Check if movement is valid
            if not await sync_to_async(self.player.can_move_to)(target_lat, target_lon):
                await self.send_error("Movement out of range")
                return
            
            # Update motion
            await sync_to_async(self.motion.move)(target_lat, target_lon)
            await sync_to_async(self.motion.save)()
            
            # Get movement data for broadcast
            movement_data = await sync_to_async(self.motion.get_movement_data)()
            event_id = str(uuid.uuid4())
            
            # Broadcast to all chunks player is visible in
            for group in self.chunk_groups:
                await self.channel_layer.group_send(group, {
                    'type': 'player_movement',
                    'event_id': event_id,
                    'data': movement_data
                })
            
            print(f"P2K Move: {self.user.username} to {target_lat:.6f}, {target_lon:.6f}")
            
        except (ValueError, KeyError) as e:
            await self.send_error("Invalid movement data")
        except Exception as e:
            print(f"Move error: {e}")
            await self.send_error("Movement failed")
    
    async def handle_recentre(self):
        """Handle recentre request - reset movement and update chunks"""
        try:
            # Cancel current movement and recenter
            await sync_to_async(self.motion.recenter)()
            await sync_to_async(self.motion.cancel)()
            
            # Update player position in database
            await sync_to_async(self.motion.sync_to_db)()
            
            # Update center position for movement range
            await self.update_player_center()
            
            # Reload world around new center
            await self.send_initial_world()
            
        except Exception as e:
            print(f"Recentre error: {e}")
            await self.send_error("Recentre failed")
    
    async def handle_chat(self, data):
        """Handle chat message"""
        try:
            message = data.get('message', '').strip()
            if not message or len(message) > 200:
                return
            
            # Broadcast to nearby players
            for group in self.chunk_groups:
                await self.channel_layer.group_send(group, {
                    'type': 'chat_message',
                    'data': {
                        'player_id': str(self.player.id),
                        'username': self.user.username,
                        'message': message,
                        'timestamp': time.time()
                    }
                })
                
        except Exception as e:
            print(f"Chat error: {e}")
    
    async def handle_attack_flag(self, data):
        """Handle flag attack"""
        try:
            flag_id = data.get('flag_id')
            if not flag_id:
                await self.send_error("No flag specified")
                return
            
            # TODO: Implement flag attack logic
            await self.send_error("Flag attacks not yet implemented")
            
        except Exception as e:
            print(f"Flag attack error: {e}")
            await self.send_error("Attack failed")
    
    async def handle_attack_npc(self, data):
        """Handle NPC attack"""
        try:
            npc_id = data.get('npc_id')
            if not npc_id:
                await self.send_error("No NPC specified")
                return
            
            # TODO: Implement NPC combat
            await self.send_error("NPC combat not yet implemented")
            
        except Exception as e:
            print(f"NPC attack error: {e}")
            await self.send_error("Combat failed")
    
    async def handle_harvest_resource(self, data):
        """Handle resource harvesting"""
        try:
            resource_id = data.get('resource_id')
            if not resource_id:
                await self.send_error("No resource specified")
                return
            
            # TODO: Implement resource harvesting
            await self.send_error("Harvesting not yet implemented")
            
        except Exception as e:
            print(f"Harvest error: {e}")
            await self.send_error("Harvest failed")
    
    async def send_initial_world(self):
        """Send initial world load - P2K style"""
        try:
            # Get chunks around player's center
            chunks = await sync_to_async(ChunkManager.get_chunks_for_center)(
                self.player.center_lat, 
                self.player.center_lon
            )
            
            # Update chunk subscriptions
            await self.update_chunk_subscriptions(chunks)
            
            # Load chunk data
            chunk_data = await sync_to_async(ChunkManager.load_chunk_data)(chunks)
            
            # Add flags, NPCs, and resources
            await self.add_special_entities(chunk_data)
            
            # Send world load message
            await self.send(text_data=json.dumps({
                'tag': 'load',
                'data': {
                    'centre': {
                        'lat': self.player.center_lat,
                        'lon': self.player.center_lon
                    },
                    'pos': {
                        'lat': self.player.lat,
                        'lon': self.player.lon
                    },
                    'entities': chunk_data
                }
            }))
            
        except Exception as e:
            print(f"World load error: {e}")
    
    async def update_chunk_subscriptions(self, chunks):
        """Update WebSocket group subscriptions for chunks"""
        # Leave old chunk groups
        for group in self.chunk_groups:
            await self.channel_layer.group_discard(group, self.channel_name)
        
        # Join new chunk groups
        self.current_chunks = chunks
        self.chunk_groups = []
        
        for chunk in chunks:
            group_name = f"chunk.{chunk.x}_{chunk.y}"
            self.chunk_groups.append(group_name)
            await self.channel_layer.group_add(group_name, self.channel_name)
    
    async def add_special_entities(self, chunk_data):
        """Add flags, NPCs, and resources to chunk data"""
        try:
            # Add flags
            chunk_data['flags'] = {}
            flags = await self.get_nearby_flags()
            for flag in flags:
                chunk_data['flags'][str(flag.id)] = {
                    'id': str(flag.id),
                    'name': flag.name,
                    'owner': flag.owner.user.username,
                    'level': flag.level,
                    'lat': flag.lat,
                    'lon': flag.lon,
                    'hp': flag.hp,
                    'max_hp': flag.max_hp,
                    'flag_type': flag.flag_type,
                    'is_owned_by_player': flag.owner_id == self.player.id
                }
            
            # Add NPCs
            chunk_data['npcs'] = {}
            npcs = await self.get_nearby_npcs()
            for npc in npcs:
                chunk_data['npcs'][str(npc.id)] = {
                    'id': str(npc.id),
                    'name': npc.name,
                    'npc_type': npc.npc_type,
                    'level': npc.level,
                    'lat': npc.lat,
                    'lon': npc.lon,
                    'hp': npc.hp,
                    'max_hp': npc.max_hp,
                    'is_alive': npc.is_alive
                }
            
            # Add resources
            chunk_data['resources'] = {}
            resources = await self.get_nearby_resources()
            for resource in resources:
                chunk_data['resources'][str(resource.id)] = {
                    'id': str(resource.id),
                    'resource_type': resource.resource_type,
                    'level': resource.level,
                    'lat': resource.lat,
                    'lon': resource.lon,
                    'can_harvest': await sync_to_async(resource.can_harvest)()
                }
                
        except Exception as e:
            print(f"Special entities error: {e}")
    
    async def send_error(self, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'tag': 'error',
            'message': message
        }))
    
    # Group message handlers
    async def player_movement(self, event):
        """Handle player movement broadcast"""
        await self.send(text_data=json.dumps({
            'tag': 'move',
            'id': event.get('event_id'),
            'data': event['data']
        }))
    
    async def chat_message(self, event):
        """Handle chat message broadcast"""
        await self.send(text_data=json.dumps({
            'tag': 'chat',
            'data': event['data']
        }))
    
    async def world_update(self, event):
        """Handle world update broadcast"""
        await self.send(text_data=json.dumps({
            'tag': 'update',
            'data': event['data']
        }))
    
    # Database operations
    @database_sync_to_async
    def get_or_create_player(self):
        """Get or create player for current user"""
        try:
            return Player.objects.get(user=self.user)
        except Player.DoesNotExist:
            # Create new player with default settings from settings.py
            return Player.create_new_player(
                self.user,
                settings.GAME_SETTINGS.get('DEFAULT_START_LAT', 41.0646633),
                settings.GAME_SETTINGS.get('DEFAULT_START_LON', -80.6391736)
            )
    
    @database_sync_to_async
    def update_player_center(self):
        """Update player's center position"""
        self.player.center_lat = self.motion.lat
        self.player.center_lon = self.motion.lon
        self.player.save(update_fields=['center_lat', 'center_lon'])
    
    @database_sync_to_async
    def get_nearby_flags(self):
        """Get flags near player"""
        # Get flags within view range (roughly 1km radius)
        return list(Flag.objects.filter(
            lat__gte=self.player.center_lat - 0.01,
            lat__lte=self.player.center_lat + 0.01,
            lon__gte=self.player.center_lon - 0.01,
            lon__lte=self.player.center_lon + 0.01
        ).select_related('owner__user'))
    
    @database_sync_to_async
    def get_nearby_npcs(self):
        """Get NPCs near player"""
        return list(NPC.objects.filter(
            lat__gte=self.player.center_lat - 0.01,
            lat__lte=self.player.center_lat + 0.01,
            lon__gte=self.player.center_lon - 0.01,
            lon__lte=self.player.center_lon + 0.01
        ))
    
    @database_sync_to_async
    def get_nearby_resources(self):
        """Get resource nodes near player"""
        return list(ResourceNode.objects.filter(
            lat__gte=self.player.center_lat - 0.01,
            lat__lte=self.player.center_lat + 0.01,
            lon__gte=self.player.center_lon - 0.01,
            lon__lte=self.player.center_lon + 0.01
        ))
