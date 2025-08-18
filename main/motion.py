"""
PMBeta Motion System
Handles smooth player movement with caching like P2K
"""
from django.core.cache import caches
from django.conf import settings
from .models import Player, Chunk
import time
import math


class EntityMotion:
    """
    Entity motion system with smooth interpolation and caching
    Based on P2K's motion system but updated for modern Django
    """
    cache = caches['default']
    
    def __init__(self, entity, lat=None, lon=None, target_lat=None, target_lon=None, start_time=None, end_time=None):
        self.entity = entity
        self.lat = lat or entity.lat
        self.lon = lon or entity.lon
        self.target_lat = target_lat or self.lat
        self.target_lon = target_lon or self.lon
        self.start_time = start_time or time.time()
        self.end_time = end_time or self.start_time
        self.is_moving = self.end_time > self.start_time
    
    def recenter(self):
        """Update current position based on movement progress"""
        now = time.time()
        
        if not self.is_moving or now >= self.end_time:
            # Movement complete
            self.lat = self.target_lat
            self.lon = self.target_lon
            self.start_time = now
            self.end_time = now
            self.is_moving = False
        else:
            # Calculate interpolated position
            progress = (now - self.start_time) / (self.end_time - self.start_time)
            self.lat = self.lat + (self.target_lat - self.lat) * progress
            self.lon = self.lon + (self.target_lon - self.lon) * progress
    
    def move(self, target_lat, target_lon):
        """Start movement to new coordinates"""
        self.recenter()  # Update current position
        
        # Calculate movement time based on distance and speed
        distance = self._calculate_distance(self.lat, self.lon, target_lat, target_lon)
        movement_speed = getattr(settings, 'MOVEMENT_SPEED', 220)  # meters per second (PK: 220 m/s)
        travel_time = max(1, distance / movement_speed)  # Minimum 1 second
        
        self.target_lat = target_lat
        self.target_lon = target_lon
        self.start_time = time.time()
        self.end_time = self.start_time + travel_time
        self.is_moving = True
    
    def cancel(self):
        """Cancel current movement"""
        self.recenter()
        self.target_lat = self.lat
        self.target_lon = self.lon
        self.end_time = self.start_time
        self.is_moving = False
    
    def save(self):
        """Save motion state to cache"""
        cache_key = f"motion.{self.entity.__class__.__name__.lower()}.{self.entity.id}"
        cache_data = {
            'lat': self.lat,
            'lon': self.lon,
            'target_lat': self.target_lat,
            'target_lon': self.target_lon,
            'start_time': self.start_time,
            'end_time': self.end_time,
        }
        self.cache.set(cache_key, cache_data, 3600)  # Cache for 1 hour
    
    def sync_to_db(self):
        """Sync current position to database"""
        self.recenter()
        self.entity.lat = self.lat
        self.entity.lon = self.lon
        self.entity.save(update_fields=['lat', 'lon'])
    
    def get_movement_data(self):
        """Get movement data for WebSocket broadcast"""
        return {
            'player_id': str(self.entity.id),
            'start': {
                'lat': self.lat,
                'lon': self.lon,
                'timestamp': self.start_time
            },
            'end': {
                'lat': self.target_lat,
                'lon': self.target_lon,
                'timestamp': self.end_time
            },
            'is_moving': self.is_moving
        }
    
    @classmethod
    def get_or_create(cls, entity):
        """Get motion object from cache or create new one"""
        cache_key = f"motion.{entity.__class__.__name__.lower()}.{entity.id}"
        cache_data = cls.cache.get(cache_key)
        
        if cache_data:
            return cls(
                entity,
                cache_data['lat'],
                cache_data['lon'],
                cache_data['target_lat'],
                cache_data['target_lon'],
                cache_data['start_time'],
                cache_data['end_time']
            )
        else:
            # Create new motion object
            motion = cls(entity)
            motion.save()
            return motion
    
    @staticmethod
    def _calculate_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between coordinates in meters"""
        R = 6371000  # Earth radius in meters
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c


class ChunkManager:
    """
    Chunk-based world management system
    Handles loading and caching of world chunks like P2K
    """
    
    @staticmethod
    def get_chunks_for_center(lat, lon, radius=800):
        """Get all chunks within radius of center point"""
        granularity = getattr(settings, 'CHUNK_GRANULARITY', 100)
        
        # Convert radius to degrees (approximate)
        lat_radius = radius / 111000  # ~111km per degree latitude
        lon_radius = radius / (111000 * math.cos(math.radians(lat)))
        
        # Get chunk bounds
        min_chunk_y = int((lat - lat_radius) * granularity)
        max_chunk_y = int((lat + lat_radius) * granularity)
        min_chunk_x = int((lon - lon_radius) * granularity)
        max_chunk_x = int((lon + lon_radius) * granularity)
        
        chunks = []
        for chunk_y in range(min_chunk_y, max_chunk_y + 1):
            for chunk_x in range(min_chunk_x, max_chunk_x + 1):
                chunks.append(Chunk(chunk_x, chunk_y))
        
        return chunks
    
    @staticmethod
    def load_chunk_data(chunks):
        """Load entity data for multiple chunks"""
        chunk_data = {
            'players': {},
            'structures': {},
            'items': {},
            'npcs': {},
            'flags': {}
        }
        
        for chunk in chunks:
            # Load players
            players = chunk.get_players()
            for player in players:
                motion = EntityMotion.get_or_create(player)
                motion.recenter()
                
                chunk_data['players'][str(player.id)] = {
                    'id': str(player.id),
                    'username': player.user.username,
                    'lat': motion.lat,
                    'lon': motion.lon,
                    'level': player.level,
                    'avatar': player.avatar,
                    'is_moving': motion.is_moving,
                }
            
            # Load structures
            structures = chunk.get_structures()
            for structure in structures:
                chunk_data['structures'][str(structure.id)] = {
                    'id': str(structure.id),
                    'type': structure.structure_type,
                    'lat': structure.lat,
                    'lon': structure.lon,
                    'hp': structure.hp,
                }
            
            # Load ground items
            items = chunk.get_items()
            for item in items:
                chunk_data['items'][str(item.id)] = {
                    'id': str(item.id),
                    'type': item.item_type,
                    'quantity': item.quantity,
                    'lat': item.lat,
                    'lon': item.lon,
                }
        
        return chunk_data
    
    @staticmethod
    def get_chunk_keys(chunks):
        """Get WebSocket channel keys for chunks"""
        return [f"chunk.{chunk.x}_{chunk.y}" for chunk in chunks]


class WorldUpdater:
    """
    Handles real-time world updates and WebSocket broadcasting
    """
    
    @staticmethod
    def broadcast_movement(player, motion, chunks):
        """Broadcast player movement to relevant chunks"""
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        movement_data = motion.get_movement_data()
        
        # Broadcast to all affected chunks
        for chunk in chunks:
            chunk_key = f"chunk.{chunk.x}_{chunk.y}"
            async_to_sync(channel_layer.group_send)(
                chunk_key,
                {
                    'type': 'player_moved',
                    'message': {
                        'type': 'player_moved',
                        'data': movement_data
                    }
                }
            )
    
    @staticmethod
    def broadcast_chunk_update(chunks, update_data):
        """Broadcast general chunk updates"""
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        
        for chunk in chunks:
            chunk_key = f"chunk.{chunk.x}_{chunk.y}"
            async_to_sync(channel_layer.group_send)(
                chunk_key,
                {
                    'type': 'world_update',
                    'message': {
                        'type': 'world_update',
                        'data': update_data
                    }
                }
            )
