"""
Location-Based RPG Models
Core RPG systems for a Parallel Kingdom-style location-based game
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.cache import cache
from decimal import Decimal
import uuid
import math
import random
import json
from datetime import timedelta


class BaseModel(models.Model):
    """Base model with UUID and timestamps"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ===============================
# CORE CHARACTER SYSTEM
# ===============================

class Character(BaseModel):
    """Main character model with RPG progression"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='character')
    
    # Character Info
    name = models.CharField(max_length=50, unique=True)
    
    # Location (GPS coordinates)
    lat = models.FloatField(help_text="Current latitude")
    lon = models.FloatField(help_text="Current longitude")
    
    # Core RPG Stats
    level = models.IntegerField(default=1)
    experience = models.BigIntegerField(default=0)
    
    # Core Attributes
    strength = models.IntegerField(default=10, help_text="Physical power, affects damage")
    defense = models.IntegerField(default=10, help_text="Physical defense, reduces damage")
    vitality = models.IntegerField(default=10, help_text="Health and stamina")
    agility = models.IntegerField(default=10, help_text="Speed and dodge chance")
    intelligence = models.IntegerField(default=10, help_text="Magic power and mana")
    
    # Derived Stats
    max_hp = models.IntegerField(default=100)
    current_hp = models.IntegerField(default=100)
    max_mana = models.IntegerField(default=50)
    current_mana = models.IntegerField(default=50)
    max_stamina = models.IntegerField(default=100)
    current_stamina = models.IntegerField(default=100)
    
    # Currency and Resources
    gold = models.BigIntegerField(default=1000, help_text="Primary currency")
    
    # Status
    is_online = models.BooleanField(default=False)
    last_activity = models.DateTimeField(auto_now=True)
    in_combat = models.BooleanField(default=False)
    
    # PvP Settings
    pvp_enabled = models.BooleanField(default=True, help_text="Can be attacked by other players")
    
    class Meta:
        db_table = 'rpg_characters'
    
    def __str__(self):
        return f"{self.name} (Level {self.level})"
    
    @staticmethod
    def distance_between(lat1, lon1, lat2, lon2):
        """Calculate distance between two coordinates in meters"""
        R = 6371000  # Earth radius in meters
        lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
        delta_lat, delta_lon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * 
             math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def distance_to(self, lat, lon):
        """Calculate distance to given coordinates"""
        return self.distance_between(self.lat, self.lon, lat, lon)
    
    def gain_experience(self, amount):
        """Gain experience and handle level ups"""
        self.experience += amount
        
        while self.experience >= self.experience_needed_for_next_level():
            self.level_up()
        
        self.save()
    
    def experience_needed_for_next_level(self):
        """Calculate XP needed for next level"""
        return self.level * 1000
    
    def level_up(self):
        """Level up and increase stats"""
        xp_needed = self.experience_needed_for_next_level()
        self.experience -= xp_needed
        self.level += 1
        
        # Increase stats on level up
        self.strength += 2
        self.defense += 2
        self.vitality += 3
        self.agility += 2
        self.intelligence += 1
        
        # Recalculate derived stats
        self.recalculate_derived_stats()
        
        # Full heal on level up
        self.current_hp = self.max_hp
        self.current_mana = self.max_mana
        self.current_stamina = self.max_stamina
    
    def recalculate_derived_stats(self):
        """Recalculate HP, mana, stamina based on attributes"""
        self.max_hp = 50 + (self.vitality * 10) + (self.level * 5)
        self.max_mana = 25 + (self.intelligence * 5) + (self.level * 2)
        self.max_stamina = 50 + (self.agility * 5) + (self.level * 3)
    
    def heal(self, amount):
        """Heal character"""
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        self.save()
    
    def can_act(self, stamina_cost=0, mana_cost=0):
        """Check if character can perform an action"""
        return (self.current_stamina >= stamina_cost and 
                self.current_mana >= mana_cost and 
                not self.in_combat)


# ===============================
# SKILL SYSTEM
# ===============================

class Skill(BaseModel):
    """Character skills and abilities"""
    SKILL_TYPES = [
        ('combat', 'Combat'),
        ('magic', 'Magic'),
        ('crafting', 'Crafting'),
        ('gathering', 'Gathering'),
        ('social', 'Social'),
    ]
    
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='skills')
    skill_type = models.CharField(max_length=20, choices=SKILL_TYPES)
    name = models.CharField(max_length=50)
    level = models.IntegerField(default=1)
    experience = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'rpg_skills'
        unique_together = ['character', 'name']
    
    def __str__(self):
        return f"{self.character.name} - {self.name} (Level {self.level})"
    
    def gain_experience(self, amount):
        """Gain skill experience and level up if needed"""
        self.experience += amount
        
        while self.experience >= self.experience_needed_for_next_level():
            self.experience -= self.experience_needed_for_next_level()
            self.level += 1
        
        self.save()
    
    def experience_needed_for_next_level(self):
        """XP needed for next skill level"""
        return self.level * 100


# ===============================
# ITEM SYSTEM
# ===============================

class ItemTemplate(BaseModel):
    """Template for all items in the game"""
    ITEM_TYPES = [
        ('weapon', 'Weapon'),
        ('armor', 'Armor'),
        ('consumable', 'Consumable'),
        ('material', 'Material'),
        ('quest', 'Quest Item'),
        ('misc', 'Miscellaneous'),
    ]
    
    RARITY_TYPES = [
        ('common', 'Common'),
        ('uncommon', 'Uncommon'),
        ('rare', 'Rare'),
        ('epic', 'Epic'),
        ('legendary', 'Legendary'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=500)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES)
    rarity = models.CharField(max_length=20, choices=RARITY_TYPES, default='common')
    
    # Stats for equipment
    strength_bonus = models.IntegerField(default=0)
    defense_bonus = models.IntegerField(default=0)
    vitality_bonus = models.IntegerField(default=0)
    agility_bonus = models.IntegerField(default=0)
    intelligence_bonus = models.IntegerField(default=0)
    
    # For weapons
    damage = models.IntegerField(default=0)
    
    # Economic
    base_value = models.IntegerField(default=1, help_text="Base gold value")
    
    # Requirements
    level_required = models.IntegerField(default=1)
    
    # Stackability
    max_stack_size = models.IntegerField(default=1)
    
    class Meta:
        db_table = 'rpg_item_templates'
    
    def __str__(self):
        return f"{self.name} ({self.get_rarity_display()})"


class InventoryItem(BaseModel):
    """Items in character inventory"""
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='inventory')
    item_template = models.ForeignKey(ItemTemplate, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    is_equipped = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'rpg_inventory'
        unique_together = ['character', 'item_template']
    
    def __str__(self):
        return f"{self.character.name} - {self.item_template.name} x{self.quantity}"
    
    def can_equip(self):
        """Check if item can be equipped"""
        return (self.item_template.item_type in ['weapon', 'armor'] and 
                self.character.level >= self.item_template.level_required)


# ===============================
# MONSTER/NPC SYSTEM
# ===============================

class MonsterTemplate(BaseModel):
    """Template for monsters/NPCs"""
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=300)
    
    # Stats
    level = models.IntegerField(default=1)
    base_hp = models.IntegerField(default=50)
    strength = models.IntegerField(default=10)
    defense = models.IntegerField(default=8)
    agility = models.IntegerField(default=8)
    
    # Rewards
    base_experience = models.IntegerField(default=25)
    base_gold = models.IntegerField(default=10)
    
    # Behavior
    is_aggressive = models.BooleanField(default=True)
    respawn_time_minutes = models.IntegerField(default=30)
    
    class Meta:
        db_table = 'rpg_monster_templates'
    
    def __str__(self):
        return f"{self.name} (Level {self.level})"


class Monster(BaseModel):
    """Live monster instance"""
    template = models.ForeignKey(MonsterTemplate, on_delete=models.CASCADE)
    
    # Location
    lat = models.FloatField()
    lon = models.FloatField()
    
    # Current stats
    current_hp = models.IntegerField()
    max_hp = models.IntegerField()
    
    # Status
    is_alive = models.BooleanField(default=True)
    last_death = models.DateTimeField(null=True, blank=True)
    respawn_at = models.DateTimeField(null=True, blank=True)
    
    # Combat
    in_combat = models.BooleanField(default=False)
    current_target = models.ForeignKey(Character, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'rpg_monsters'
    
    def __str__(self):
        return f"{self.template.name} at ({self.lat:.4f}, {self.lon:.4f})"
    
    def can_respawn(self):
        """Check if monster can respawn"""
        if self.is_alive or not self.respawn_at:
            return False
        return timezone.now() >= self.respawn_at
    
    def respawn(self):
        """Respawn the monster"""
        self.is_alive = True
        self.current_hp = self.max_hp
        self.in_combat = False
        self.current_target = None
        self.respawn_at = None
        self.save()
    
    def die(self):
        """Handle monster death"""
        self.is_alive = False
        self.in_combat = False
        self.current_target = None
        self.last_death = timezone.now()
        self.respawn_at = timezone.now() + timedelta(minutes=self.template.respawn_time_minutes)
        self.save()


# ===============================
# COMBAT SYSTEM
# ===============================

class PvECombat(BaseModel):
    """Player vs Monster combat"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('victory', 'Player Victory'),
        ('defeat', 'Player Defeat'),
        ('fled', 'Player Fled'),
    ]
    
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='pve_combats')
    monster = models.ForeignKey(Monster, on_delete=models.CASCADE, related_name='combats')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Combat state
    character_hp = models.IntegerField()
    monster_hp = models.IntegerField()
    
    # Results
    experience_gained = models.IntegerField(default=0)
    gold_gained = models.IntegerField(default=0)
    items_dropped = models.JSONField(default=list)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'rpg_pve_combat'
    
    def __str__(self):
        return f"{self.character.name} vs {self.monster.template.name}"
    
    def resolve_turn(self):
        """Resolve a combat turn"""
        if self.status != 'active':
            return False
        
        # Character attacks first
        damage = max(1, self.character.strength - self.monster.template.defense + random.randint(-3, 3))
        self.monster_hp -= damage
        
        if self.monster_hp <= 0:
            self.end_combat('victory')
            return True
        
        # Monster counter-attacks
        damage = max(1, self.monster.template.strength - self.character.defense + random.randint(-3, 3))
        self.character_hp -= damage
        
        if self.character_hp <= 0:
            self.end_combat('defeat')
            return True
        
        self.save()
        return True
    
    def end_combat(self, result):
        """End combat and apply results"""
        self.status = result
        self.ended_at = timezone.now()
        
        if result == 'victory':
            # Calculate rewards
            self.experience_gained = self.monster.template.base_experience + random.randint(0, 10)
            self.gold_gained = self.monster.template.base_gold + random.randint(0, 20)
            
            # Give rewards to character
            self.character.gain_experience(self.experience_gained)
            self.character.gold += self.gold_gained
            self.character.current_hp = self.character_hp
            self.character.save()
            
            # Kill monster
            self.monster.die()
        
        elif result == 'defeat':
            # Character loses, goes to 1 HP
            self.character.current_hp = 1
            self.character.save()
        
        # End combat state
        self.character.in_combat = False
        self.character.save()
        
        self.monster.in_combat = False
        self.monster.current_target = None
        self.monster.save()
        
        self.save()


class PvPCombat(BaseModel):
    """Player vs Player combat"""
    STATUS_CHOICES = [
        ('challenge', 'Challenge Sent'),
        ('accepted', 'Challenge Accepted'),
        ('active', 'Combat Active'),
        ('victory', 'Combat Ended - Victory'),
        ('declined', 'Challenge Declined'),
        ('expired', 'Challenge Expired'),
    ]
    
    challenger = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='pvp_challenges_sent')
    defender = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='pvp_challenges_received')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='challenge')
    winner = models.ForeignKey(Character, on_delete=models.CASCADE, null=True, blank=True, related_name='pvp_wins')
    
    # Combat state
    challenger_hp = models.IntegerField(default=0)
    defender_hp = models.IntegerField(default=0)
    
    # Location where combat initiated
    lat = models.FloatField()
    lon = models.FloatField()
    
    # Stakes and rewards
    gold_wagered = models.IntegerField(default=0)
    winner_takes_gold = models.IntegerField(default=0)
    
    # Timing
    challenge_expires_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'rpg_pvp_combat'
    
    def __str__(self):
        return f"{self.challenger.name} vs {self.defender.name}"
    
    def can_accept(self):
        """Check if challenge can be accepted"""
        return (self.status == 'challenge' and 
                timezone.now() < self.challenge_expires_at and
                not self.defender.in_combat)
    
    def accept_challenge(self):
        """Accept PvP challenge"""
        if not self.can_accept():
            return False
        
        self.status = 'accepted'
        self.challenger_hp = self.challenger.current_hp
        self.defender_hp = self.defender.current_hp
        
        # Set both players in combat
        self.challenger.in_combat = True
        self.defender.in_combat = True
        self.challenger.save()
        self.defender.save()
        
        self.save()
        return True


# ===============================
# TRADING SYSTEM
# ===============================

class Trade(BaseModel):
    """Player-to-player trading"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    initiator = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='trades_initiated')
    recipient = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='trades_received')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Offer from initiator
    initiator_gold = models.IntegerField(default=0)
    
    # Request for recipient  
    recipient_gold = models.IntegerField(default=0)
    
    # Timing
    expires_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'rpg_trades'
    
    def __str__(self):
        return f"Trade: {self.initiator.name} -> {self.recipient.name}"
    
    def can_accept(self):
        """Check if trade can be accepted"""
        return (self.status == 'pending' and 
                timezone.now() < self.expires_at and
                self.recipient.gold >= self.recipient_gold)
    
    def accept_trade(self):
        """Accept and execute the trade"""
        if not self.can_accept():
            return False
        
        # Transfer gold
        self.initiator.gold += self.recipient_gold
        self.recipient.gold += self.initiator_gold
        
        self.initiator.gold -= self.initiator_gold
        self.recipient.gold -= self.recipient_gold
        
        self.initiator.save()
        self.recipient.save()
        
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        return True


class TradeItem(BaseModel):
    """Items included in a trade"""
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, related_name='items')
    from_character = models.ForeignKey(Character, on_delete=models.CASCADE)
    item_template = models.ForeignKey(ItemTemplate, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    
    class Meta:
        db_table = 'rpg_trade_items'
    
    def __str__(self):
        return f"{self.item_template.name} x{self.quantity}"


# ===============================
# WORLD SYSTEM
# ===============================

class Region(BaseModel):
    """Game world regions for monster spawning"""
    name = models.CharField(max_length=100)
    
    # Geographic bounds
    lat_min = models.FloatField()
    lat_max = models.FloatField()
    lon_min = models.FloatField()
    lon_max = models.FloatField()
    
    # Region properties
    monster_level_min = models.IntegerField(default=1)
    monster_level_max = models.IntegerField(default=10)
    spawn_rate = models.FloatField(default=1.0, help_text="Spawn rate multiplier")
    
    # PvP settings
    pvp_enabled = models.BooleanField(default=True)
    is_safe_zone = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'rpg_regions'
    
    def __str__(self):
        return self.name
    
    def contains_point(self, lat, lon):
        """Check if coordinates are within this region"""
        return (self.lat_min <= lat <= self.lat_max and 
                self.lon_min <= lon <= self.lon_max)
    
    def get_recommended_level(self):
        """Get recommended character level for this region"""
        return (self.monster_level_min + self.monster_level_max) // 2


# ===============================
# EVENTS AND NOTIFICATIONS
# ===============================

class GameEvent(BaseModel):
    """Game events for real-time notifications"""
    EVENT_TYPES = [
        ('combat', 'Combat Event'),
        ('trade', 'Trade Event'), 
        ('level_up', 'Level Up'),
        ('item_found', 'Item Found'),
        ('player_nearby', 'Player Nearby'),
    ]
    
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    title = models.CharField(max_length=100)
    message = models.TextField(max_length=300)
    data = models.JSONField(default=dict)
    
    # Status
    is_read = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'rpg_events'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.character.name} - {self.title}"
