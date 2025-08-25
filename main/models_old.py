"""
PMBeta Game Models
Location-based game models inspired by Parallel Kingdom
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.cache import caches
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import uuid
import math
import random
import time
import datetime
from pprint import pprint
class BaseModel(models.Model):
    """Base model with UUID and timestamps"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, verbose_name='ID')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class LivingEntity(BaseModel):
    """Base class for entities that exist at specific coordinates"""
    lat = models.FloatField(help_text="Latitude coordinate")
    lon = models.FloatField(help_text="Longitude coordinate") 
    hp = models.IntegerField(default=100, help_text="Hit points")

    class Meta:
        abstract = True

    @staticmethod
    def distance_between(lat1, lon1, lat2, lon2):
        """Calculate distance between two coordinates in meters (Haversine formula)"""
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


class Player(LivingEntity):
    """Player model with location-based functionality and mafia mechanics"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Player stats
    cash = models.BigIntegerField(default=10000, help_text="Liquid cash on hand")
    bank_money = models.BigIntegerField(default=0, help_text="Money in bank")
    level = models.IntegerField(default=1)
    experience = models.IntegerField(default=0)
    
    # Mafia-specific stats
    reputation = models.IntegerField(default=0, help_text="Street reputation")
    respect = models.IntegerField(default=0, help_text="Respect within organization")
    heat_level = models.FloatField(default=0.0, help_text="Law enforcement attention (0-100)")
    influence = models.IntegerField(default=1, help_text="Political/economic influence")
    
    # Combat stats
    strength = models.IntegerField(default=10)
    defense = models.IntegerField(default=10)
    speed = models.IntegerField(default=10)
    accuracy = models.IntegerField(default=10)
    
    # Status tracking
    is_jailed = models.BooleanField(default=False)
    jail_release_time = models.DateTimeField(null=True, blank=True)
    is_hospitalized = models.BooleanField(default=False)
    hospital_release_time = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    # Location data - center point for movement range
    center_lat = models.FloatField(help_text="Center latitude for movement range")
    center_lon = models.FloatField(help_text="Center longitude for movement range")
    
    # Player customization
    avatar = models.IntegerField(default=0, help_text="Avatar type")
    status = models.CharField(max_length=64, default="", blank=True)
    bio = models.CharField(max_length=256, default="", blank=True)
    
    def __str__(self):
        return f"{self.user.username} (Level {self.level})"
    
    def can_move_to(self, lat, lon):
        """Check if player can move to given coordinates (PK-style flag restriction)"""
        from .flag_models import TerritoryFlag
        
        # First check if target is within any flag radius
        accessible_flags = TerritoryFlag.objects.filter(
            status='active'
        )
        
        # Check if target position is within any flag radius
        for flag in accessible_flags:
            distance_to_flag = self.distance_between(flag.lat, flag.lon, lat, lon)
            
            # If within flag radius, movement is allowed
            if distance_to_flag <= flag.radius_meters:
                return True
        
        # Check if player is currently within a flag and trying to move within movement range
        # This allows movement within a smaller radius if already in a flag
        current_flag = None
        for flag in accessible_flags:
            current_distance = self.distance_between(flag.lat, flag.lon, self.lat, self.lon)
            if current_distance <= flag.radius_meters:
                current_flag = flag
                break
        
        # If currently in a flag, allow short-range movement within that flag
        if current_flag:
            distance_to_target = self.distance_between(self.lat, self.lon, lat, lon)
            # Allow small movements within the flag radius (50 meters max per move)
            if distance_to_target <= 50:
                target_distance_from_flag = self.distance_between(current_flag.lat, current_flag.lon, lat, lon)
                if target_distance_from_flag <= current_flag.radius_meters:
                    return True
        
        # If no flag access and not a small movement, deny
        return False
    
    def get_chunk_coords(self):
        """Get chunk coordinates for current position (P2K-style 0.01 degree chunks)"""
        granularity = settings.GAME_SETTINGS['CHUNK_GRANULARITY']
        chunk_x = int(self.lon * granularity)
        chunk_y = int(self.lat * granularity)
        return (chunk_x, chunk_y)
    
    @staticmethod
    def create_new_player(user, lat=None, lon=None):
        """Create a new player at default or specified location"""
        if lat is None:
            lat = settings.GAME_SETTINGS['DEFAULT_START_LAT']
        if lon is None:
            lon = settings.GAME_SETTINGS['DEFAULT_START_LON']
            
        return Player.objects.create(
            user=user,
            lat=lat,
            lon=lon,
            center_lat=lat,
            center_lon=lon,
        )


class Structure(BaseModel):
    """Base class for all structures in the world"""
    STRUCTURE_TYPES = [
        (1, 'Tree'),
        (2, 'Rock'),
        (3, 'Building'),
        (4, 'Flag'),
        (5, 'City'),
    ]
    
    structure_type = models.IntegerField(choices=STRUCTURE_TYPES)
    lat = models.FloatField(help_text="Latitude coordinate")
    lon = models.FloatField(help_text="Longitude coordinate")
    hp = models.IntegerField(default=100)
    
    # Optional metadata for different structure types
    metadata = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"{self.get_structure_type_display()} at ({self.lat:.4f}, {self.lon:.4f})"


class NatureStructure(Structure):
    """Structures that can be harvested (trees, rocks, etc.)"""
    last_harvest = models.DateTimeField(default=datetime.datetime.now)
    respawn_time = models.IntegerField(default=3600, help_text="Seconds until respawn")
    
    def can_harvest(self):
        """Check if structure can be harvested"""
        time_since_harvest = datetime.datetime.now() - self.last_harvest
        return time_since_harvest.total_seconds() >= self.respawn_time


class PlayerStructure(Structure):
    """Structures created by players"""
    creator = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='structures')
    level = models.IntegerField(default=1)
    
    def __str__(self):
        return f"{self.get_structure_type_display()} by {self.creator.user.username}"


class Item(BaseModel):
    """Base item model"""
    ITEM_TYPES = [
        (1, 'Wood'),
        (2, 'Stone'), 
        (3, 'Gold'),
        (4, 'Tool'),
        (5, 'Food'),
    ]
    
    item_type = models.IntegerField(choices=ITEM_TYPES)
    quantity = models.IntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)


class PlayerItem(Item):
    """Items in a player's inventory"""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='inventory')
    
    def __str__(self):
        return f"{self.quantity}x {self.get_item_type_display()} ({self.player.user.username})"


class GroundItem(Item):
    """Items dropped on the ground at specific coordinates"""
    lat = models.FloatField(help_text="Latitude coordinate")
    lon = models.FloatField(help_text="Longitude coordinate")
    expires_at = models.DateTimeField(help_text="When item despawns")
    
    def __str__(self):
        return f"{self.quantity}x {self.get_item_type_display()} on ground"


class GameEvent(BaseModel):
    """Track game events for real-time updates"""
    pass


# ===============================
# PARALLEL KINGDOM MODELS
# ===============================

class PKPlayer(BaseModel):
    """Parallel Kingdom Player - core player model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pk_player')
    
    # Core PK Stats
    level = models.IntegerField(default=1)
    food = models.IntegerField(default=100, help_text="Food for actions")
    energy = models.IntegerField(default=100, help_text="Energy for movement/combat")
    gold = models.BigIntegerField(default=100, help_text="Primary currency")
    lumber = models.IntegerField(default=0)
    stone = models.IntegerField(default=0)
    ore = models.IntegerField(default=0)
    
    # PK Combat Stats
    might = models.IntegerField(default=10, help_text="Combat power")
    defense = models.IntegerField(default=10)
    health = models.IntegerField(default=100)
    max_health = models.IntegerField(default=100)
    
    # Location (GPS coordinates)
    lat = models.FloatField(help_text="Current latitude")
    lon = models.FloatField(help_text="Current longitude") 
    
    # PK Status
    is_online = models.BooleanField(default=False)
    last_activity = models.DateTimeField(auto_now=True)
    last_energy_regen = models.DateTimeField(auto_now_add=True)
    last_food_consumption = models.DateTimeField(auto_now_add=True)
    
    # Player customization
    avatar = models.IntegerField(default=0)
    status_message = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'pk_players'
        
    def __str__(self):
        return f"{self.user.username} (L{self.level})"
    
    @staticmethod
    def distance_between(lat1, lon1, lat2, lon2):
        """Calculate distance in meters using Haversine formula"""
        R = 6371000  # Earth radius in meters
        lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
        delta_lat, delta_lon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * 
             math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def regenerate_energy(self):
        """Regenerate energy based on time passed"""
        now = timezone.now()
        time_diff = now - self.last_energy_regen
        energy_to_add = int(time_diff.total_seconds() // 300)  # Every 5 minutes
        
        if energy_to_add > 0:
            self.energy = min(100, self.energy + energy_to_add)
            self.last_energy_regen = now
            return energy_to_add
        return 0
    
    def consume_food(self):
        """Consume food when online (PK mechanic)"""
        if not self.is_online:
            return False
            
        now = timezone.now()
        time_diff = now - self.last_food_consumption
        food_to_consume = int(time_diff.total_seconds() // 600)  # Every 10 minutes
        
        if food_to_consume > 0:
            self.food = max(0, self.food - food_to_consume)
            self.last_food_consumption = now
            return True
        return False
    
    def can_perform_action(self, energy_cost=1, food_cost=0):
        """Check if player has enough resources for action"""
        self.regenerate_energy()
        self.consume_food()
        return self.energy >= energy_cost and self.food >= food_cost


class PKTerritory(BaseModel):
    """Parallel Kingdom Territory/Flag system"""
    TERRITORY_TYPES = [
        ('flag', 'Flag'),
        ('outpost', 'Outpost'), 
        ('city', 'City'),
        ('castle', 'Castle'),
    ]
    
    owner = models.ForeignKey(PKPlayer, on_delete=models.CASCADE, related_name='territories')
    territory_type = models.CharField(max_length=10, choices=TERRITORY_TYPES, default='flag')
    name = models.CharField(max_length=50)
    
    # Location
    lat = models.FloatField()
    lon = models.FloatField()
    
    # Territory stats
    level = models.IntegerField(default=1)
    health = models.IntegerField(default=100)
    max_health = models.IntegerField(default=100)
    defense_bonus = models.IntegerField(default=0)
    
    # Resource generation (PK style)
    lumber_generation = models.IntegerField(default=1, help_text="Lumber per hour")
    stone_generation = models.IntegerField(default=1, help_text="Stone per hour") 
    ore_generation = models.IntegerField(default=0, help_text="Ore per hour")
    gold_generation = models.IntegerField(default=1, help_text="Gold per hour")
    
    # Territory control
    is_active = models.BooleanField(default=True)
    last_resource_collection = models.DateTimeField(auto_now_add=True)
    placed_at = models.DateTimeField(auto_now_add=True)
    
    # Protection (newly placed territories)
    protection_expires = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'pk_territories'
        verbose_name_plural = 'territories'
        
    def __str__(self):
        return f"{self.name} ({self.owner.user.username})"
    
    def is_protected(self):
        """Check if territory has newbie protection"""
        if not self.protection_expires:
            return False
        return timezone.now() < self.protection_expires
    
    def collect_resources(self):
        """Collect accumulated resources"""
        now = timezone.now()
        hours_passed = (now - self.last_resource_collection).total_seconds() / 3600
        
        if hours_passed >= 1:  # At least 1 hour passed
            multiplier = self.level
            collected = {
                'lumber': int(self.lumber_generation * multiplier * hours_passed),
                'stone': int(self.stone_generation * multiplier * hours_passed),
                'ore': int(self.ore_generation * multiplier * hours_passed),
                'gold': int(self.gold_generation * multiplier * hours_passed),
            }
            
            # Add to owner's resources
            self.owner.lumber += collected['lumber']
            self.owner.stone += collected['stone']
            self.owner.ore += collected['ore']
            self.owner.gold += collected['gold']
            
            self.owner.save()
            self.last_resource_collection = now
            self.save()
            
            return collected
        return {}


class PKResource(BaseModel):
    """Resource nodes spawned around the world (PK style)"""
    RESOURCE_TYPES = [
        ('tree', 'Tree'),
        ('rock', 'Rock'),
        ('mine', 'Mine'),
        ('ruins', 'Ancient Ruins'),
        ('chest', 'Treasure Chest'),
    ]
    
    resource_type = models.CharField(max_length=10, choices=RESOURCE_TYPES)
    
    # Location
    lat = models.FloatField()
    lon = models.FloatField()
    
    # Resource properties
    level = models.IntegerField(default=1, help_text="Resource difficulty/quality")
    health = models.IntegerField(default=100)
    max_health = models.IntegerField(default=100)
    
    # Yields
    lumber_yield = models.IntegerField(default=0)
    stone_yield = models.IntegerField(default=0)
    ore_yield = models.IntegerField(default=0)
    gold_yield = models.IntegerField(default=0)
    food_yield = models.IntegerField(default=0)
    
    # Status
    is_depleted = models.BooleanField(default=False)
    respawn_time = models.DateTimeField(null=True, blank=True)
    last_harvested = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'pk_resources'
        
    def __str__(self):
        return f"{self.get_resource_type_display()} L{self.level}"
    
    def can_harvest(self):
        """Check if resource can be harvested"""
        if self.is_depleted:
            return False
        return self.health > 0
    
    def harvest(self, player):
        """Harvest resource with player"""
        from datetime import timedelta
        
        if not self.can_harvest():
            return None
            
        # Calculate damage based on player might and resource level
        damage = max(1, player.might - self.level * 2)
        self.health -= damage
        
        # Calculate yields based on damage and resource type
        multiplier = damage / 10.0
        yields = {
            'lumber': int(self.lumber_yield * multiplier),
            'stone': int(self.stone_yield * multiplier), 
            'ore': int(self.ore_yield * multiplier),
            'gold': int(self.gold_yield * multiplier),
            'food': int(self.food_yield * multiplier),
        }
        
        if self.health <= 0:
            self.is_depleted = True
            self.respawn_time = timezone.now() + timedelta(hours=2)  # 2 hour respawn
            
        self.last_harvested = timezone.now()
        self.save()
        
        return yields


class PKCombat(BaseModel):
    """PK-style combat encounter"""
    COMBAT_TYPES = [
        ('pve', 'Player vs Environment'),
        ('pvp', 'Player vs Player'),
        ('siege', 'Territory Siege'),
    ]
    
    combat_type = models.CharField(max_length=10, choices=COMBAT_TYPES)
    attacker = models.ForeignKey(PKPlayer, on_delete=models.CASCADE, related_name='attacks_made')
    defender = models.ForeignKey(PKPlayer, on_delete=models.CASCADE, related_name='attacks_received', null=True, blank=True)
    target_territory = models.ForeignKey(PKTerritory, on_delete=models.CASCADE, null=True, blank=True)
    
    # Combat results
    attacker_might = models.IntegerField()
    defender_might = models.IntegerField()
    winner = models.CharField(max_length=10, choices=[('attacker', 'Attacker'), ('defender', 'Defender')])
    
    # Rewards/losses
    gold_transferred = models.IntegerField(default=0)
    lumber_transferred = models.IntegerField(default=0)
    stone_transferred = models.IntegerField(default=0)
    ore_transferred = models.IntegerField(default=0)
    
    # Combat location
    lat = models.FloatField()
    lon = models.FloatField()
    
    class Meta:
        db_table = 'pk_combat'
        
    def __str__(self):
        target = self.defender.user.username if self.defender else "NPC"
        return f"{self.attacker.user.username} vs {target}"


class PKGameEvent(BaseModel):
    """Game events for real-time updates"""
    EVENT_TYPES = [
        ('combat', 'Combat Event'),
        ('trade', 'Trade Event'),
        ('resource', 'Resource Event'),
        ('territory', 'Territory Event'),
        ('player', 'Player Event'),
        ('alliance', 'Alliance Event'),
    ]
    
    event_type = models.CharField(max_length=10, choices=EVENT_TYPES)
    player = models.ForeignKey(PKPlayer, on_delete=models.CASCADE, related_name='events', null=True, blank=True)
    
    # Event data
    title = models.CharField(max_length=100)
    description = models.TextField(max_length=500)
    event_data = models.JSONField(default=dict)
    
    # Event context
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    
    # Event status
    is_processed = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'pk_events'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} ({self.event_type})"


class PKTrade(BaseModel):
    """PK Trading system"""
    TRADE_TYPES = [
        ('player', 'Player to Player'),
        ('market', 'Market Trade'),
        ('caravan', 'Caravan Trade'),
    ]
    
    TRADE_STATUS = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    trade_type = models.CharField(max_length=10, choices=TRADE_TYPES)
    status = models.CharField(max_length=10, choices=TRADE_STATUS, default='pending')
    
    # Trade participants
    initiator = models.ForeignKey(PKPlayer, on_delete=models.CASCADE, related_name='trades_initiated')
    recipient = models.ForeignKey(PKPlayer, on_delete=models.CASCADE, related_name='trades_received', null=True, blank=True)
    
    # Trade items (what initiator offers)
    offer_gold = models.IntegerField(default=0)
    offer_lumber = models.IntegerField(default=0)
    offer_stone = models.IntegerField(default=0)
    offer_ore = models.IntegerField(default=0)
    offer_food = models.IntegerField(default=0)
    
    # Trade request (what initiator wants)
    request_gold = models.IntegerField(default=0)
    request_lumber = models.IntegerField(default=0)
    request_stone = models.IntegerField(default=0)
    request_ore = models.IntegerField(default=0)
    request_food = models.IntegerField(default=0)
    
    # Trade details
    expires_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'pk_trades'
        
    def __str__(self):
        return f"Trade: {self.initiator.user.username} -> {self.recipient.user.username if self.recipient else 'Market'}"


class PKMessage(BaseModel):
    """PK Messaging system"""
    MESSAGE_TYPES = [
        ('private', 'Private Message'),
        ('alliance', 'Alliance Message'),
        ('global', 'Global Chat'),
        ('system', 'System Message'),
    ]
    
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    sender = models.ForeignKey(PKPlayer, on_delete=models.CASCADE, related_name='messages_sent', null=True, blank=True)
    recipient = models.ForeignKey(PKPlayer, on_delete=models.CASCADE, related_name='messages_received', null=True, blank=True)
    
    subject = models.CharField(max_length=100, blank=True)
    content = models.TextField(max_length=1000)
    
    # Message status
    is_read = models.BooleanField(default=False)
    is_deleted_by_sender = models.BooleanField(default=False)
    is_deleted_by_recipient = models.BooleanField(default=False)
    
    # Location context (for location-based messages)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    
    class Meta:
        db_table = 'pk_messages'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Message from {self.sender.user.username if self.sender else 'System'}"


class PKAlliance(BaseModel):
    """PK Alliance/Guild system"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(max_length=500, blank=True)
    leader = models.ForeignKey(PKPlayer, on_delete=models.CASCADE, related_name='led_alliances')
    
    # Alliance stats
    total_might = models.IntegerField(default=0)
    member_count = models.IntegerField(default=1)
    territory_count = models.IntegerField(default=0)
    
    # Alliance settings
    is_recruiting = models.BooleanField(default=True)
    min_level = models.IntegerField(default=1)
    
    class Meta:
        db_table = 'pk_alliances'
        
    def __str__(self):
        return self.name


class PKAllianceMember(BaseModel):
    """Alliance membership"""
    MEMBER_RANKS = [
        ('member', 'Member'),
        ('officer', 'Officer'), 
        ('leader', 'Leader'),
    ]
    
    alliance = models.ForeignKey(PKAlliance, on_delete=models.CASCADE, related_name='members')
    player = models.ForeignKey(PKPlayer, on_delete=models.CASCADE, related_name='alliance_memberships')
    rank = models.CharField(max_length=10, choices=MEMBER_RANKS, default='member')
    
    joined_at = models.DateTimeField(auto_now_add=True)
    contribution_points = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'pk_alliance_members'
        unique_together = ['alliance', 'player']
        
    def __str__(self):
        return f"{self.player.user.username} in {self.alliance.name}"


# Chunk system for efficient world management (like P2K)
class Chunk:
    """
    World chunk system for efficient querying
    Divides world into 0.01 degree chunks (approx 1km squares)
    """
    GRANULARITY = 100  # 0.01 degree chunks
    
    def __init__(self, chunk_x, chunk_y):
        self.x = chunk_x
        self.y = chunk_y
        self.lat_min = chunk_y / self.GRANULARITY
        self.lat_max = (chunk_y + 1) / self.GRANULARITY
        self.lon_min = chunk_x / self.GRANULARITY
        self.lon_max = (chunk_x + 1) / self.GRANULARITY
    
    def get_players(self):
        """Get all players in this chunk"""
        return Player.objects.filter(
            lat__gte=self.lat_min,
            lat__lt=self.lat_max,
            lon__gte=self.lon_min,
            lon__lt=self.lon_max
        )
    
    def get_structures(self):
        """Get all structures in this chunk"""
        return Structure.objects.filter(
            lat__gte=self.lat_min,
            lat__lt=self.lat_max,
            lon__gte=self.lon_min,
            lon__lt=self.lon_max
        )
    
    def get_items(self):
        """Get all ground items in this chunk"""
        return GroundItem.objects.filter(
            lat__gte=self.lat_min,
            lat__lt=self.lat_max,
            lon__gte=self.lon_min,
            lon__lt=self.lon_max
        )
    
    @staticmethod
    def from_coords(lat, lon):
        """Create chunk from lat/lon coordinates"""
        chunk_x = int(lon * Chunk.GRANULARITY)
        chunk_y = int(lat * Chunk.GRANULARITY)
        return Chunk(chunk_x, chunk_y)
    
    def to_dict(self):
        """Convert chunk data to dictionary for JSON serialization"""
        return {
            'chunk_x': self.x,
            'chunk_y': self.y,
            'bounds': {
                'lat_min': self.lat_min,
                'lat_max': self.lat_max,
                'lon_min': self.lon_min,
                'lon_max': self.lon_max,
            },
            'players': [
                {
                    'id': str(p.id),
                    'username': p.user.username,
                    'lat': p.lat,
                    'lon': p.lon,
                    'level': p.level,
                }
                for p in self.get_players()
            ],
            'structures': [
                {
                    'id': str(s.id),
                    'type': s.structure_type,
                    'lat': s.lat,
                    'lon': s.lon,
                }
                for s in self.get_structures()
            ],
            'items': [
                {
                    'id': str(i.id),
                    'type': i.item_type,
                    'quantity': i.quantity,
                    'lat': i.lat,
                    'lon': i.lon,
                }
                for i in self.get_items()
            ]
        }


# ===============================
# MAFIA-SPECIFIC MODELS
# ===============================

class Family(BaseModel):
    """Mafia family/crew organization"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=500, blank=True)
    boss = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='family_as_boss')
    
    # Family stats
    treasury = models.BigIntegerField(default=0, help_text="Family shared funds")
    reputation = models.IntegerField(default=0, help_text="Family reputation")
    territory_count = models.IntegerField(default=0, help_text="Number of controlled territories")
    heat_level = models.FloatField(default=0.0, help_text="Combined law enforcement attention")
    
    # Family settings
    is_recruiting = models.BooleanField(default=True)
    max_members = models.IntegerField(default=50)
    
    class Meta:
        verbose_name_plural = 'Families'
        
    def __str__(self):
        return f"{self.name} Family"
    
    def get_member_count(self):
        return self.memberships.count()
    
    def can_recruit(self):
        return self.is_recruiting and self.get_member_count() < self.max_members


class FamilyMembership(BaseModel):
    """Player membership in a family with hierarchy"""
    ROLES = [
        ('associate', 'Associate'),
        ('soldier', 'Soldier'),
        ('capo', 'Capo'),
        ('underboss', 'Underboss'),
        ('boss', 'Boss'),
    ]
    
    ROLE_HIERARCHY = {
        'associate': 1,
        'soldier': 2,
        'capo': 3,
        'underboss': 4,
        'boss': 5,
    }
    
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='memberships')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='family_membership')
    role = models.CharField(max_length=20, choices=ROLES, default='associate')
    joined_date = models.DateTimeField(auto_now_add=True)
    
    # Membership stats
    contributions = models.BigIntegerField(default=0, help_text="Total money contributed")
    respect_earned = models.IntegerField(default=0, help_text="Respect earned for family")
    
    class Meta:
        unique_together = ('family', 'player')
        
    def __str__(self):
        return f"{self.player.user.username} - {self.get_role_display()} in {self.family.name}"
    
    def get_role_level(self):
        return self.ROLE_HIERARCHY.get(self.role, 0)
    
    def can_promote_to(self, target_role):
        current_level = self.get_role_level()
        target_level = self.ROLE_HIERARCHY.get(target_role, 0)
        return current_level > target_level and target_level < 5  # Can't promote to boss


class Territory(BaseModel):
    """Geographic territory control system"""
    TERRITORY_TYPES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'), 
        ('industrial', 'Industrial'),
        ('downtown', 'Downtown'),
        ('port', 'Port/Docks'),
    ]
    
    name = models.CharField(max_length=100)
    territory_type = models.CharField(max_length=20, choices=TERRITORY_TYPES)
    
    # Geographic bounds (using chunk system)
    chunk_x = models.IntegerField(help_text="Chunk X coordinate")
    chunk_y = models.IntegerField(help_text="Chunk Y coordinate")
    
    # Control and ownership
    controlling_family = models.ForeignKey(Family, on_delete=models.SET_NULL, null=True, blank=True, related_name='controlled_territories')
    influence_level = models.FloatField(default=0.0, help_text="Control strength (0-100)")
    contested = models.BooleanField(default=False, help_text="Currently being contested")
    
    # Economic value
    income_per_hour = models.IntegerField(default=100, help_text="Base hourly income")
    population = models.IntegerField(default=1000, help_text="Territory population")
    
    class Meta:
        unique_together = ('chunk_x', 'chunk_y')
        verbose_name_plural = 'Territories'
        
    def __str__(self):
        return f"{self.name} ({self.get_territory_type_display()})"
    
    def get_actual_income(self):
        """Calculate actual income based on influence and type"""
        base_income = self.income_per_hour
        influence_multiplier = self.influence_level / 100.0
        return int(base_income * influence_multiplier)


class CriminalActivity(BaseModel):
    """Criminal activities/jobs that players can perform"""
    ACTIVITY_TYPES = [
        ('heist', 'Heist'),
        ('protection', 'Protection Racket'),
        ('drugs', 'Drug Trade'),
        ('robbery', 'Robbery'),
        ('smuggling', 'Smuggling'),
        ('assassination', 'Assassination'),
        ('extortion', 'Extortion'),
        ('money_laundering', 'Money Laundering'),
    ]
    
    DIFFICULTY_LEVELS = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ('extreme', 'Extreme'),
    ]
    
    name = models.CharField(max_length=100)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_LEVELS)
    description = models.TextField(max_length=500)
    
    # Requirements
    min_level = models.IntegerField(default=1)
    min_reputation = models.IntegerField(default=0)
    required_cash = models.IntegerField(default=0, help_text="Upfront cost")
    
    # Location requirements
    lat = models.FloatField(help_text="Activity location latitude")
    lon = models.FloatField(help_text="Activity location longitude")
    
    # Rewards and risks
    min_payout = models.IntegerField(default=100)
    max_payout = models.IntegerField(default=1000)
    heat_gain = models.FloatField(default=1.0, help_text="Heat gained on completion")
    success_chance = models.FloatField(default=0.8, help_text="Base success chance (0-1)")
    
    # Timing
    duration_minutes = models.IntegerField(default=60, help_text="Time to complete")
    cooldown_hours = models.IntegerField(default=24, help_text="Cooldown before repeating")
    
    # Status
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_difficulty_display()})"


class ActivityExecution(BaseModel):
    """Track player execution of criminal activities"""
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('busted', 'Busted by Police'),
    ]
    
    activity = models.ForeignKey(CriminalActivity, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='criminal_activities')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    
    # Execution details
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    payout = models.IntegerField(default=0)
    heat_gained = models.FloatField(default=0.0)
    reputation_gained = models.IntegerField(default=0)
    
    # Additional participants (for group activities)
    participants = models.ManyToManyField(Player, blank=True, related_name='participated_activities')
    
    def __str__(self):
        return f"{self.player.user.username} - {self.activity.name} ({self.status})"


class Business(BaseModel):
    """Legitimate businesses and illegal operations"""
    BUSINESS_TYPES = [
        ('restaurant', 'Restaurant'),
        ('club', 'Nightclub'),
        ('casino', 'Casino'),
        ('warehouse', 'Warehouse'),
        ('laundromat', 'Laundromat'),
        ('construction', 'Construction Company'),
        ('trucking', 'Trucking Company'),
        ('pawn_shop', 'Pawn Shop'),
    ]
    
    name = models.CharField(max_length=100)
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPES)
    owner = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='owned_businesses')
    
    # Location
    lat = models.FloatField(help_text="Business location latitude")
    lon = models.FloatField(help_text="Business location longitude")
    territory = models.ForeignKey(Territory, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Business stats
    level = models.IntegerField(default=1)
    legitimate_income = models.IntegerField(default=100, help_text="Hourly legitimate income")
    illegal_income = models.IntegerField(default=0, help_text="Hourly illegal income")
    upkeep_cost = models.IntegerField(default=50, help_text="Hourly operating costs")
    
    # Status
    is_operational = models.BooleanField(default=True)
    heat_generated = models.FloatField(default=0.1, help_text="Heat generated per hour")
    
    def __str__(self):
        return f"{self.name} ({self.get_business_type_display()})"
    
    def get_net_income(self):
        """Calculate net hourly income"""
        return (self.legitimate_income + self.illegal_income) - self.upkeep_cost


class Weapon(BaseModel):
    """Weapons and equipment for combat"""
    WEAPON_TYPES = [
        ('melee', 'Melee'),
        ('pistol', 'Pistol'),
        ('rifle', 'Rifle'),
        ('shotgun', 'Shotgun'),
        ('explosive', 'Explosive'),
        ('armor', 'Body Armor'),
        ('vehicle', 'Vehicle'),
    ]
    
    name = models.CharField(max_length=100)
    weapon_type = models.CharField(max_length=20, choices=WEAPON_TYPES)
    description = models.TextField(max_length=300)
    
    # Combat stats
    damage = models.IntegerField(default=10)
    accuracy = models.IntegerField(default=10)
    defense = models.IntegerField(default=0)  # For armor
    
    # Requirements and cost
    min_level = models.IntegerField(default=1)
    cost = models.IntegerField(default=1000)
    
    # Availability
    is_available = models.BooleanField(default=True)
    heat_to_purchase = models.FloatField(default=0.5, help_text="Heat gained when purchasing")
    
    def __str__(self):
        return f"{self.name} ({self.get_weapon_type_display()})"


class PlayerWeapon(BaseModel):
    """Player's weapon inventory"""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='weapons')
    weapon = models.ForeignKey(Weapon, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    condition = models.FloatField(default=100.0, help_text="Weapon condition (0-100)")
    
    def __str__(self):
        return f"{self.player.user.username} - {self.weapon.name} x{self.quantity}"


class Combat(BaseModel):
    """Combat encounters between players"""
    COMBAT_TYPES = [
        ('assault', 'Assault'),
        ('assassination', 'Assassination Attempt'),
        ('territory_war', 'Territory War'),
        ('family_war', 'Family War'),
        ('revenge', 'Revenge Attack'),
    ]
    
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('interrupted', 'Interrupted'),
    ]
    
    attacker = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='attacks_initiated')
    defender = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='attacks_received')
    combat_type = models.CharField(max_length=20, choices=COMBAT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    
    # Location
    lat = models.FloatField(help_text="Combat location latitude")
    lon = models.FloatField(help_text="Combat location longitude")
    
    # Results
    winner = models.ForeignKey(Player, on_delete=models.CASCADE, null=True, blank=True, related_name='combats_won')
    attacker_damage = models.IntegerField(default=0)
    defender_damage = models.IntegerField(default=0)
    
    # Consequences
    money_taken = models.IntegerField(default=0)
    respect_gained = models.IntegerField(default=0)
    heat_generated = models.FloatField(default=5.0)
    
    def __str__(self):
        return f"{self.attacker.user.username} vs {self.defender.user.username} ({self.get_combat_type_display()})"


class Flag(BaseModel):
    """Territory control flags - similar to Parallel Mafia flag system"""
    FLAG_TYPES = [
        ('territory', 'Territory Flag'),
        ('family', 'Family Flag'),
        ('outpost', 'Outpost'),
        ('stronghold', 'Stronghold'),
        ('watchtower', 'Watchtower'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('under_attack', 'Under Attack'),
        ('captured', 'Recently Captured'),
        ('abandoned', 'Abandoned'),
    ]
    
    name = models.CharField(max_length=100, help_text="Flag name/description")
    flag_type = models.CharField(max_length=20, choices=FLAG_TYPES, default='territory')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Location (precise coordinates)
    lat = models.FloatField(help_text="Flag latitude")
    lon = models.FloatField(help_text="Flag longitude")
    
    # Ownership and control
    owner = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='owned_flags')
    controlling_family = models.ForeignKey(Family, on_delete=models.SET_NULL, null=True, blank=True, related_name='controlled_flags')
    
    # Flag stats
    level = models.IntegerField(default=1, help_text="Flag level (1-10)")
    hp = models.IntegerField(default=1000, help_text="Flag hit points")
    max_hp = models.IntegerField(default=1000, help_text="Maximum hit points")
    defense_rating = models.IntegerField(default=50, help_text="Defense strength")
    
    # Economic benefits
    income_per_hour = models.IntegerField(default=500, help_text="Hourly income generated")
    influence_radius = models.IntegerField(default=100, help_text="Influence radius in meters")
    
    # Timing
    placed_at = models.DateTimeField(auto_now_add=True)
    last_attacked = models.DateTimeField(null=True, blank=True)
    invulnerable_until = models.DateTimeField(null=True, blank=True, help_text="Protection period after placement")
    
    # Costs and requirements
    placement_cost = models.IntegerField(default=50000, help_text="Cost to place this flag")
    upgrade_cost = models.IntegerField(default=10000, help_text="Cost to upgrade to next level")
    
    class Meta:
        unique_together = ('lat', 'lon')  # Only one flag per exact location
        
    def __str__(self):
        return f"{self.name} (Level {self.level}) - {self.owner.user.username}"
    
    def is_invulnerable(self):
        """Check if flag is in protection period"""
        if not self.invulnerable_until:
            return False
        from django.utils import timezone
        return timezone.now() < self.invulnerable_until
    
    def get_defense_strength(self):
        """Calculate total defense including upgrades and bonuses"""
        base_defense = self.defense_rating
        level_bonus = self.level * 10
        family_bonus = 20 if self.controlling_family else 0
        return base_defense + level_bonus + family_bonus
    
    def get_hourly_income(self):
        """Calculate actual hourly income with level multiplier"""
        base_income = self.income_per_hour
        level_multiplier = 1 + (self.level - 1) * 0.2  # 20% increase per level
        return int(base_income * level_multiplier)
    
    def can_be_attacked_by(self, player):
        """Check if flag can be attacked by given player"""
        if self.is_invulnerable():
            return False, "Flag is protected after recent placement"
        
        if self.owner == player:
            return False, "Cannot attack your own flag"
        
        if self.status == 'under_attack':
            return False, "Flag is already under attack"
        
        # Check distance (player must be within range)
        distance = player.distance_between(player.lat, player.lon, self.lat, self.lon)
        if distance > 200:  # 200m attack range
            return False, f"Too far away (need to be within 200m, currently {int(distance)}m)"
        
        return True, "Can attack"
    
    def calculate_upgrade_cost(self):
        """Calculate cost to upgrade to next level"""
        if self.level >= 10:
            return None  # Max level
        return self.upgrade_cost * (self.level ** 2)
    
    def spawn_npcs(self, num_npcs=None):
        """Spawn NPCs around this flag"""
        if num_npcs is None:
            # Spawn 1-3 NPCs based on flag level
            num_npcs = min(3, 1 + self.level // 3)
        
        import random
        import math
        from django.utils import timezone
        
        npcs_created = []
        
        for i in range(num_npcs):
            # Generate random position around flag (within 100m)
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(20, 100)  # 20-100m from flag
            
            # Convert to lat/lon offset (approximate)
            lat_offset = (distance * math.cos(angle)) / 111000  # ~111km per degree
            lon_offset = (distance * math.sin(angle)) / (111000 * math.cos(math.radians(self.lat)))
            
            npc_lat = self.lat + lat_offset
            npc_lon = self.lon + lon_offset
            
            # Choose random NPC type and stats based on flag level
            npc_types = ['bandit', 'thug', 'enforcer', 'dealer', 'bouncer']
            npc_type = random.choice(npc_types)
            npc_level = max(1, self.level + random.randint(-1, 2))
            
            # Generate NPC name
            first_names = ['Tony', 'Vinny', 'Joey', 'Sal', 'Rocco', 'Frankie', 'Nick', 'Bobby', 'Sammy', 'Lou']
            last_names = ['Knuckles', 'The Knife', 'Two-Times', 'Big Nose', 'The Bull', 'Scar', 'Iron Fist', 'Mad Dog', 'The Hammer', 'Cold Eyes']
            npc_name = f"{random.choice(first_names)} '{random.choice(last_names)}'"
            
            try:
                npc = NPC.objects.create(
                    npc_type=npc_type,
                    name=npc_name,
                    lat=npc_lat,
                    lon=npc_lon,
                    spawned_on_flag=self,
                    level=npc_level,
                    hp=50 + (npc_level * 25),
                    max_hp=50 + (npc_level * 25),
                    strength=8 + (npc_level * 3),
                    defense=8 + (npc_level * 2),
                    speed=5 + npc_level,
                    base_experience_reward=15 + (npc_level * 10),
                    base_gold_reward=50 + (npc_level * 25),
                    base_reputation_reward=3 + npc_level
                )
                npcs_created.append(npc)
            except Exception as e:
                # Skip if position conflicts (unique constraint on lat/lon)
                continue
        
        return npcs_created
    
    def respawn_dead_npcs(self):
        """Respawn NPCs that are ready to respawn"""
        dead_npcs = self.spawned_npcs.filter(is_alive=False)
        respawned = []
        
        for npc in dead_npcs:
            if npc.can_respawn():
                # Respawn the NPC
                npc.is_alive = True
                npc.hp = npc.max_hp
                npc.last_death = None
                npc.current_target = None
                npc.save()
                respawned.append(npc)
        
        return respawned


class FlagAttack(BaseModel):
    """Track attacks on flags"""
    STATUS_CHOICES = [
        ('preparing', 'Preparing Attack'),
        ('in_progress', 'Attack in Progress'),
        ('successful', 'Attack Successful'),
        ('failed', 'Attack Failed'),
        ('defended', 'Successfully Defended'),
    ]
    
    flag = models.ForeignKey(Flag, on_delete=models.CASCADE, related_name='attacks')
    attacker = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='flag_attacks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='preparing')
    
    # Attack details
    damage_dealt = models.IntegerField(default=0)
    attack_strength = models.IntegerField(default=100, help_text="Total attack power")
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=30, help_text="Attack duration")
    
    # Results
    attacker_casualties = models.IntegerField(default=0)
    defender_casualties = models.IntegerField(default=0)
    money_gained = models.IntegerField(default=0)
    reputation_gained = models.IntegerField(default=0)
    
    # Participants (for group attacks)
    supporting_players = models.ManyToManyField(Player, blank=True, related_name='supported_flag_attacks')
    
    def __str__(self):
        return f"{self.attacker.user.username} attacking {self.flag.name} ({self.status})"
    
    def calculate_success_chance(self):
        """Calculate probability of attack success"""
        attack_power = self.attack_strength
        defense_power = self.flag.get_defense_strength()
        
        # Base calculation
        power_ratio = attack_power / max(defense_power, 1)
        base_chance = min(0.95, max(0.05, power_ratio * 0.5))  # 5% to 95% range
        
        # Modifiers
        level_modifier = (self.attacker.level - self.flag.owner.level) * 0.02
        reputation_modifier = (self.attacker.reputation - self.flag.owner.reputation) * 0.001
        
        final_chance = base_chance + level_modifier + reputation_modifier
        return max(0.05, min(0.95, final_chance))


class FlagUpgrade(BaseModel):
    """Track flag upgrades and improvements"""
    UPGRADE_TYPES = [
        ('level', 'Level Increase'),
        ('defense', 'Defense Boost'),
        ('income', 'Income Boost'),
        ('range', 'Influence Range Increase'),
        ('special', 'Special Ability'),
    ]
    
    flag = models.ForeignKey(Flag, on_delete=models.CASCADE, related_name='upgrades')
    upgrade_type = models.CharField(max_length=20, choices=UPGRADE_TYPES)
    upgraded_by = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='flag_upgrades')
    
    # Upgrade details
    old_value = models.IntegerField(default=0)
    new_value = models.IntegerField(default=0)
    cost_paid = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.flag.name} - {self.get_upgrade_type_display()} by {self.upgraded_by.user.username}"


class ResourceNode(BaseModel):
    """Resource nodes for harvesting (trees, mines, etc.) - Parallel Kingdom style"""
    RESOURCE_TYPES = [
        ('tree', 'Tree'),
        ('iron_mine', 'Iron Mine'),
        ('gold_mine', 'Gold Mine'),
        ('stone_quarry', 'Stone Quarry'),
        ('herb_patch', 'Herb Patch'),
        ('ruins', 'Ancient Ruins'),
        ('cave', 'Cave'),
        ('well', 'Water Well'),
    ]
    
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    lat = models.FloatField(help_text="Resource latitude")
    lon = models.FloatField(help_text="Resource longitude")
    
    # Resource stats
    hp = models.IntegerField(default=100, help_text="Resource hit points")
    max_hp = models.IntegerField(default=100, help_text="Maximum hit points")
    level = models.IntegerField(default=1, help_text="Resource level (1-5)")
    
    # Harvesting mechanics
    last_harvested = models.DateTimeField(null=True, blank=True)
    harvest_count = models.IntegerField(default=0, help_text="Times harvested")
    respawn_time = models.IntegerField(default=3600, help_text="Seconds to respawn")
    
    # Rewards
    base_experience = models.IntegerField(default=10)
    base_gold_reward = models.IntegerField(default=50)
    base_resource_amount = models.IntegerField(default=5)
    
    # Status
    is_depleted = models.BooleanField(default=False)
    created_by_system = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('lat', 'lon')  # One resource per location
        
    def __str__(self):
        return f"{self.get_resource_type_display()} (Level {self.level}) at ({self.lat:.4f}, {self.lon:.4f})"
    
    def can_harvest(self):
        """Check if resource can be harvested"""
        if self.is_depleted:
            return False
        
        if self.last_harvested:
            from django.utils import timezone
            time_since_harvest = timezone.now() - self.last_harvested
            if time_since_harvest.total_seconds() < self.respawn_time:
                return False
        
        return True
    
    def get_harvest_rewards(self, player_level=1):
        """Calculate harvest rewards based on resource and player level"""
        level_multiplier = 1 + (self.level - 1) * 0.5
        player_multiplier = 1 + (player_level - 1) * 0.1
        
        experience = int(self.base_experience * level_multiplier * player_multiplier)
        gold = int(self.base_gold_reward * level_multiplier * player_multiplier)
        resources = int(self.base_resource_amount * level_multiplier)
        
        return {
            'experience': experience,
            'gold': gold,
            'resources': resources,
            'resource_type': self.resource_type
        }


class NPC(BaseModel):
    """NPCs for PvE combat - Parallel Kingdom style"""
    NPC_TYPES = [
        ('bandit', 'Bandit'),
        ('thug', 'Street Thug'),
        ('enforcer', 'Rival Enforcer'),
        ('boss', 'Crime Boss'),
        ('cop', 'Corrupt Cop'),
        ('rival_soldier', 'Rival Soldier'),
        ('bouncer', 'Club Bouncer'),
        ('dealer', 'Drug Dealer'),
        ('hitman', 'Hitman'),
        ('informant', 'Informant'),
    ]
    
    npc_type = models.CharField(max_length=20, choices=NPC_TYPES)
    name = models.CharField(max_length=100, help_text="NPC display name")
    lat = models.FloatField(help_text="NPC latitude")
    lon = models.FloatField(help_text="NPC longitude")
    
    # Flag association - NPCs spawn on flags
    spawned_on_flag = models.ForeignKey(
        'Flag', 
        on_delete=models.CASCADE, 
        related_name='spawned_npcs',
        null=True, 
        blank=True,
        help_text="Flag this NPC is defending (null for legacy NPCs)"
    )
    
    # Combat stats
    level = models.IntegerField(default=1)
    hp = models.IntegerField(default=100)
    max_hp = models.IntegerField(default=100)
    strength = models.IntegerField(default=10)
    defense = models.IntegerField(default=10)
    speed = models.IntegerField(default=10)
    
    # AI and behavior
    aggression = models.FloatField(default=0.5, help_text="How likely to attack players (0-1)")
    wander_radius = models.IntegerField(default=50, help_text="Meters NPC can move from spawn")
    respawn_time = models.IntegerField(default=300, help_text="Seconds to respawn after death (5 minutes)")
    
    # Rewards
    base_experience_reward = models.IntegerField(default=25)
    base_gold_reward = models.IntegerField(default=100)
    base_reputation_reward = models.IntegerField(default=5)
    
    # Status
    is_alive = models.BooleanField(default=True)
    last_death = models.DateTimeField(null=True, blank=True)
    current_target = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='targeted_by_npcs')
    
    class Meta:
        unique_together = ('lat', 'lon')  # One NPC per location
        
    def __str__(self):
        return f"{self.name} ({self.get_npc_type_display()}) Level {self.level}"
    
    def can_respawn(self):
        """Check if NPC can respawn"""
        if self.is_alive:
            return False
            
        if self.last_death:
            from django.utils import timezone
            time_since_death = timezone.now() - self.last_death
            return time_since_death.total_seconds() >= self.respawn_time
        
        return True
    
    def get_combat_power(self):
        """Calculate total combat power"""
        return self.strength + self.defense + self.speed + (self.level * 5)
    
    def get_kill_rewards(self, player_level=1):
        """Calculate rewards for defeating this NPC"""
        level_multiplier = 1 + (self.level - 1) * 0.3
        player_multiplier = 1 + max(0, (player_level - self.level)) * 0.1
        
        experience = int(self.base_experience_reward * level_multiplier * player_multiplier)
        gold = int(self.base_gold_reward * level_multiplier * player_multiplier)
        reputation = int(self.base_reputation_reward * level_multiplier)
        
        return {
            'experience': experience,
            'gold': gold,
            'reputation': reputation
        }


class CombatSession(BaseModel):
    """Active combat session between player and NPC with turn-based mechanics"""
    SESSION_STATUS = [
        ('active', 'Combat Active'),
        ('player_turn', 'Player Turn'),
        ('npc_turn', 'NPC Turn'),
        ('player_victory', 'Player Victory'),
        ('npc_victory', 'NPC Victory'),
        ('player_fled', 'Player Fled'),
        ('expired', 'Session Expired'),
    ]
    
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='combat_sessions')
    npc = models.ForeignKey(NPC, on_delete=models.CASCADE, related_name='combat_sessions')
    status = models.CharField(max_length=20, choices=SESSION_STATUS, default='player_turn')
    
    # Combat state
    turn_number = models.IntegerField(default=1)
    player_hp = models.IntegerField(help_text="Player HP at start of combat")
    npc_hp = models.IntegerField(help_text="NPC HP at start of combat")
    player_current_hp = models.IntegerField(help_text="Player's current HP")
    npc_current_hp = models.IntegerField(help_text="NPC's current HP")
    
    # Combat modifiers and effects
    player_attack_bonus = models.IntegerField(default=0)
    player_defense_bonus = models.IntegerField(default=0)
    npc_attack_bonus = models.IntegerField(default=0)
    npc_defense_bonus = models.IntegerField(default=0)
    
    # Status effects (JSON field for flexibility)
    player_effects = models.JSONField(default=dict, help_text="Active status effects on player")
    npc_effects = models.JSONField(default=dict, help_text="Active status effects on NPC")
    
    # Session management
    expires_at = models.DateTimeField(help_text="When session expires if inactive")
    last_action = models.DateTimeField(auto_now=True)
    
    # Final results (populated when combat ends)
    total_damage_to_npc = models.IntegerField(default=0)
    total_damage_to_player = models.IntegerField(default=0)
    experience_gained = models.IntegerField(default=0)
    gold_gained = models.IntegerField(default=0)
    reputation_gained = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('player', 'npc')  # One combat per player-npc pair
    
    def __str__(self):
        return f"{self.player.user.username} vs {self.npc.name} (Turn {self.turn_number})"
    
    def is_player_turn(self):
        return self.status == 'player_turn'
    
    def is_npc_turn(self):
        return self.status == 'npc_turn'
    
    def is_active(self):
        return self.status in ['player_turn', 'npc_turn', 'active']
    
    def is_complete(self):
        return self.status in ['player_victory', 'npc_victory', 'player_fled', 'expired']
    
    def get_player_effective_stats(self):
        """Get player's effective combat stats with bonuses"""
        base_attack = self.player.strength
        base_defense = self.player.defense
        base_speed = self.player.speed
        base_accuracy = self.player.accuracy
        
        # Apply equipment bonuses (if implemented)
        # Apply status effect bonuses
        for effect_name, effect_data in self.player_effects.items():
            if effect_data.get('attack_bonus'):
                base_attack += effect_data['attack_bonus']
            if effect_data.get('defense_bonus'):
                base_defense += effect_data['defense_bonus']
        
        return {
            'attack': base_attack + self.player_attack_bonus,
            'defense': base_defense + self.player_defense_bonus,
            'speed': base_speed,
            'accuracy': base_accuracy,
            'level': self.player.level
        }
    
    def get_npc_effective_stats(self):
        """Get NPC's effective combat stats with bonuses"""
        base_attack = self.npc.strength
        base_defense = self.npc.defense
        base_speed = self.npc.speed
        
        # Apply status effect bonuses
        for effect_name, effect_data in self.npc_effects.items():
            if effect_data.get('attack_bonus'):
                base_attack += effect_data['attack_bonus']
            if effect_data.get('defense_bonus'):
                base_defense += effect_data['defense_bonus']
        
        return {
            'attack': base_attack + self.npc_attack_bonus,
            'defense': base_defense + self.npc_defense_bonus,
            'speed': base_speed,
            'accuracy': 80,  # Base NPC accuracy
            'level': self.npc.level
        }
    
    def calculate_damage(self, attacker_stats, defender_stats, action_type='attack'):
        """Calculate damage dealt in an attack"""
        import random
        
        base_damage = attacker_stats['attack']
        defense = defender_stats['defense']
        level_modifier = attacker_stats['level'] * 2
        
        # Action type modifiers
        if action_type == 'heavy_attack':
            base_damage = int(base_damage * 1.5)
        elif action_type == 'quick_attack':
            base_damage = int(base_damage * 0.8)
        
        # Calculate raw damage
        raw_damage = base_damage + level_modifier + random.randint(-5, 10)
        
        # Apply defense
        damage_reduction = defense * 0.5
        final_damage = max(1, int(raw_damage - damage_reduction))
        
        # Critical hit chance (10% base + accuracy bonus)
        crit_chance = 0.1 + (attacker_stats['accuracy'] - 50) * 0.002
        is_critical = random.random() < crit_chance
        
        if is_critical:
            final_damage = int(final_damage * 1.8)
        
        return {
            'damage': final_damage,
            'is_critical': is_critical,
            'raw_damage': raw_damage,
            'damage_reduction': damage_reduction
        }
    
    def calculate_accuracy(self, attacker_stats, defender_stats, action_type='attack'):
        """Calculate hit chance for an attack"""
        base_accuracy = attacker_stats['accuracy']
        defender_speed = defender_stats['speed']
        
        # Action type modifiers
        if action_type == 'heavy_attack':
            base_accuracy -= 15  # Heavy attacks are less accurate
        elif action_type == 'quick_attack':
            base_accuracy += 10  # Quick attacks are more accurate
        
        # Calculate hit chance (40% to 95% range)
        hit_chance = 0.4 + (base_accuracy - defender_speed) * 0.01
        return max(0.4, min(0.95, hit_chance))
    
    def apply_status_effect(self, target, effect_name, effect_data, duration_turns=3):
        """Apply a status effect to player or NPC"""
        if target == 'player':
            effects = self.player_effects.copy()
        else:
            effects = self.npc_effects.copy()
        
        effects[effect_name] = {
            **effect_data,
            'duration': duration_turns,
            'applied_turn': self.turn_number
        }
        
        if target == 'player':
            self.player_effects = effects
        else:
            self.npc_effects = effects
    
    def process_turn_end_effects(self):
        """Process status effects at end of turn"""
        # Process player effects
        player_effects = self.player_effects.copy()
        for effect_name in list(player_effects.keys()):
            effect = player_effects[effect_name]
            effect['duration'] -= 1
            
            # Apply damage over time effects
            if effect.get('poison_damage'):
                self.player_current_hp -= effect['poison_damage']
                self.player_current_hp = max(0, self.player_current_hp)
            
            # Remove expired effects
            if effect['duration'] <= 0:
                del player_effects[effect_name]
        
        self.player_effects = player_effects
        
        # Process NPC effects
        npc_effects = self.npc_effects.copy()
        for effect_name in list(npc_effects.keys()):
            effect = npc_effects[effect_name]
            effect['duration'] -= 1
            
            # Apply damage over time effects
            if effect.get('poison_damage'):
                self.npc_current_hp -= effect['poison_damage']
                self.npc_current_hp = max(0, self.npc_current_hp)
            
            # Remove expired effects
            if effect['duration'] <= 0:
                del npc_effects[effect_name]
        
        self.npc_effects = npc_effects


class CombatAction(BaseModel):
    """Individual combat actions within a session"""
    ACTION_TYPES = [
        ('attack', 'Basic Attack'),
        ('heavy_attack', 'Heavy Attack'),
        ('quick_attack', 'Quick Attack'),
        ('defend', 'Defend'),
        ('special_ability', 'Special Ability'),
        ('use_item', 'Use Item'),
        ('flee', 'Attempt to Flee'),
    ]
    
    session = models.ForeignKey(CombatSession, on_delete=models.CASCADE, related_name='actions')
    actor = models.CharField(max_length=10, choices=[('player', 'Player'), ('npc', 'NPC')])
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    turn_number = models.IntegerField()
    
    # Action details
    target = models.CharField(max_length=10, choices=[('player', 'Player'), ('npc', 'NPC')])
    damage_dealt = models.IntegerField(default=0)
    healing_done = models.IntegerField(default=0)
    was_critical = models.BooleanField(default=False)
    was_miss = models.BooleanField(default=False)
    
    # Status effects applied
    effects_applied = models.JSONField(default=dict, blank=True)
    
    # Action description for combat log
    description = models.TextField(max_length=500, blank=True)
    
    class Meta:
        ordering = ['turn_number', 'created_at']
    
    def __str__(self):
        return f"{self.actor} {self.action_type} (Turn {self.turn_number})"


class NPCCombat(BaseModel):
    """Legacy combat tracking - kept for backward compatibility"""
    STATUS_CHOICES = [
        ('initiated', 'Combat Initiated'),
        ('in_progress', 'In Progress'),
        ('player_won', 'Player Victory'),
        ('npc_won', 'NPC Victory'),
        ('fled', 'Player Fled'),
    ]
    
    npc = models.ForeignKey(NPC, on_delete=models.CASCADE, related_name='combat_encounters')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='npc_combats')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    
    # Link to new combat session if available
    combat_session = models.OneToOneField(CombatSession, on_delete=models.CASCADE, null=True, blank=True, related_name='legacy_combat')
    
    # Combat results
    player_damage_dealt = models.IntegerField(default=0)
    npc_damage_dealt = models.IntegerField(default=0)
    experience_gained = models.IntegerField(default=0)
    gold_gained = models.IntegerField(default=0)
    reputation_gained = models.IntegerField(default=0)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.player.user.username} vs {self.npc.name} ({self.status})"


class ResourceHarvest(BaseModel):
    """Track resource harvesting by players"""
    STATUS_CHOICES = [
        ('in_progress', 'Harvesting'),
        ('completed', 'Completed'),
        ('interrupted', 'Interrupted'),
        ('failed', 'Failed'),
    ]
    
    resource = models.ForeignKey(ResourceNode, on_delete=models.CASCADE, related_name='harvests')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='resource_harvests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    
    # Results
    experience_gained = models.IntegerField(default=0)
    gold_gained = models.IntegerField(default=0)
    resources_gained = models.IntegerField(default=0)
    resource_type = models.CharField(max_length=20, blank=True)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=30, help_text="Time to complete harvest")
    
    def __str__(self):
        return f"{self.player.user.username} harvesting {self.resource.get_resource_type_display()} ({self.status})"


class LawEnforcementEvent(BaseModel):
    """Police investigations and enforcement actions"""
    EVENT_TYPES = [
        ('investigation', 'Investigation Started'),
        ('raid', 'Police Raid'),
        ('arrest', 'Arrest'),
        ('surveillance', 'Under Surveillance'),
        ('witness_protection', 'Witness in Protection'),
    ]
    
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    target_player = models.ForeignKey(Player, on_delete=models.CASCADE, null=True, blank=True, related_name='law_enforcement_events')
    target_family = models.ForeignKey(Family, on_delete=models.CASCADE, null=True, blank=True, related_name='law_enforcement_events')
    target_business = models.ForeignKey(Business, on_delete=models.CASCADE, null=True, blank=True, related_name='law_enforcement_events')
    
    description = models.TextField(max_length=500)
    severity = models.IntegerField(default=1, help_text="Severity level 1-10")
    
    # Status
    is_active = models.BooleanField(default=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        target = self.target_player or self.target_family or self.target_business or "Unknown"
        return f"{self.get_event_type_display()} - {target}"
