"""
Parallel Kingdom Style Flag System
Territory control flags with radius-based ownership, upkeep, and combat
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta, datetime
import math
import random

from .models import BaseModel, Character
from .building_models import FlagColor


class TerritoryFlag(BaseModel):
    """
    PK-style territory flag with circular control radius
    """
    STATUS_CHOICES = [
        ('constructing', 'Under Construction'),
        ('active', 'Active'),
        ('upgrading', 'Upgrading'),
        ('damaged', 'Damaged'),
        ('capturable', 'Capturable'),  # Destroyed, can be captured
        ('decayed', 'Decayed'),        # Abandoned, can be claimed by anyone
        ('destroyed', 'Destroyed'),    # Completely destroyed
    ]
    
    owner = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='territory_flags')
    
    # Location
    lat = models.FloatField(help_text="Flag latitude")
    lon = models.FloatField(help_text="Flag longitude")
    
    # Territory control
    level = models.IntegerField(default=1, help_text="Flag level (1-5)")
    radius_meters = models.IntegerField(default=200, help_text="Territory control radius in meters")
    
    # Status and health
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='constructing')
    current_hp = models.IntegerField(default=100)
    max_hp = models.IntegerField(default=100)
    
    # Visual customization  
    flag_color = models.ForeignKey(FlagColor, on_delete=models.SET_NULL, null=True, blank=True)
    custom_name = models.CharField(max_length=100, blank=True, help_text="Custom name for flag")
    
    # Economy
    base_revenue_per_hour = models.IntegerField(default=10, help_text="Base gold per hour")
    location_bonus_multiplier = models.FloatField(default=1.0, help_text="Location-based revenue multiplier")
    uncollected_revenue = models.IntegerField(default=0)
    total_revenue_generated = models.BigIntegerField(default=0)
    last_revenue_collection = models.DateTimeField(auto_now_add=True)
    
    # Upkeep system
    daily_upkeep_cost = models.IntegerField(default=50, help_text="Gold required per day")
    upkeep_due_at = models.DateTimeField(null=True, blank=True)
    upkeep_grace_period_hours = models.IntegerField(default=72, help_text="Hours before decay starts")
    last_upkeep_payment = models.DateTimeField(auto_now_add=True)
    
    # Construction and upgrade timing
    construction_started = models.DateTimeField(auto_now_add=True)
    construction_completed = models.DateTimeField(null=True, blank=True)
    construction_time_minutes = models.IntegerField(default=30)
    upgrade_started = models.DateTimeField(null=True, blank=True)
    upgrade_completed = models.DateTimeField(null=True, blank=True)
    
    # Combat
    last_attacked = models.DateTimeField(null=True, blank=True)
    capture_window_started = models.DateTimeField(null=True, blank=True)
    capture_window_minutes = models.IntegerField(default=30)
    
    class Meta:
        db_table = 'pk_territory_flags'
        unique_together = ['lat', 'lon']  # One flag per exact location
        
    def __str__(self):
        name = self.custom_name or f"Flag"
        return f"{self.owner.name}'s {name} (Level {self.level})"
    
    @property
    def display_name(self):
        return self.custom_name or f"Level {self.level} Flag"
    
    def get_level_stats(self, level=None):
        """Get stats for a given level (or current level)"""
        level = level or self.level
        
        # PK-style level progression
        level_data = {
            1: {'radius': 200, 'hp': 100, 'revenue_multiplier': 1.0, 'upkeep': 50},
            2: {'radius': 300, 'hp': 150, 'revenue_multiplier': 1.4, 'upkeep': 100},
            3: {'radius': 400, 'hp': 225, 'revenue_multiplier': 1.8, 'upkeep': 150},
            4: {'radius': 500, 'hp': 300, 'revenue_multiplier': 2.3, 'upkeep': 200},
            5: {'radius': 600, 'hp': 400, 'revenue_multiplier': 3.0, 'upkeep': 250},
        }
        
        return level_data.get(level, level_data[1])
    
    def get_upgrade_cost(self, to_level=None):
        """Get cost to upgrade to next level (or specified level)"""
        to_level = to_level or (self.level + 1)
        
        if to_level > 5 or to_level <= self.level:
            return None
            
        # PK-style upgrade costs (exponential scaling)
        costs = {
            2: {'gold': 500, 'wood': 25, 'stone': 15},
            3: {'gold': 1200, 'wood': 50, 'stone': 30},
            4: {'gold': 2500, 'wood': 100, 'stone': 60},
            5: {'gold': 5000, 'wood': 200, 'stone': 120},
        }
        
        return costs.get(to_level)
    
    def is_construction_complete(self):
        """Check if initial construction is complete"""
        if self.status != 'constructing':
            return True
            
        if not self.construction_started:
            return False
            
        elapsed = timezone.now() - self.construction_started
        required = timedelta(minutes=self.construction_time_minutes)
        
        if elapsed >= required:
            self.status = 'active'
            self.construction_completed = timezone.now()
            self.upkeep_due_at = timezone.now() + timedelta(days=1)
            self.save()
            return True
            
        return False
    
    def is_upgrade_complete(self):
        """Check if current upgrade is complete"""
        if self.status != 'upgrading' or not self.upgrade_started:
            return True
            
        elapsed = timezone.now() - self.upgrade_started
        # Upgrade time scales with level
        required = timedelta(minutes=self.construction_time_minutes * self.level)
        
        if elapsed >= required:
            # Apply level upgrade
            level_stats = self.get_level_stats(self.level)
            self.radius_meters = level_stats['radius']
            self.max_hp = level_stats['hp']
            self.current_hp = self.max_hp  # Full heal on upgrade
            self.daily_upkeep_cost = level_stats['upkeep']
            
            self.status = 'active'
            self.upgrade_completed = timezone.now()
            self.save()
            
            # Regenerate territory zone
            self.regenerate_territory_zone()
            
            return True
            
        return False
    
    def calculate_hourly_revenue(self):
        """Calculate current revenue per hour using PK formula"""
        if self.status != 'active':
            return 0
            
        level_stats = self.get_level_stats()
        
        # PK Revenue Formula: base_rate * level_multiplier * location_bonus * random_factor
        base_rate = self.base_revenue_per_hour
        level_multiplier = level_stats['revenue_multiplier']
        location_bonus = self.location_bonus_multiplier
        
        # Add some randomness (±20% variance)
        random_factor = random.uniform(0.8, 1.2)
        
        hourly_revenue = base_rate * level_multiplier * location_bonus * random_factor
        return max(1, int(hourly_revenue))
    
    def calculate_accumulated_revenue(self):
        """Calculate revenue accumulated since last collection"""
        if self.status != 'active':
            return 0
            
        time_since_collection = timezone.now() - self.last_revenue_collection
        hours_elapsed = time_since_collection.total_seconds() / 3600
        
        hourly_rate = self.calculate_hourly_revenue()
        return int(hourly_rate * hours_elapsed)
    
    def collect_revenue(self):
        """Collect accumulated revenue"""
        if self.status != 'active':
            return 0
            
        accumulated = self.calculate_accumulated_revenue()
        total_revenue = accumulated + self.uncollected_revenue
        
        if total_revenue > 0:
            # Add to owner's gold
            self.owner.gold += total_revenue
            self.owner.save()
            
            # Update flag tracking
            self.total_revenue_generated += total_revenue
            self.uncollected_revenue = 0
            self.last_revenue_collection = timezone.now()
            self.save()
            
            # Log collection
            FlagRevenueCollection.objects.create(
                flag=self,
                amount_collected=total_revenue,
                player_level=self.owner.level,
                flag_level=self.level
            )
            
        return total_revenue
    
    def pay_upkeep(self):
        """Pay daily upkeep to keep flag active"""
        if self.owner.gold < self.daily_upkeep_cost:
            return False, f"Need {self.daily_upkeep_cost} gold for upkeep"
            
        self.owner.gold -= self.daily_upkeep_cost
        self.owner.save()
        
        # Extend upkeep deadline
        self.last_upkeep_payment = timezone.now()
        self.upkeep_due_at = timezone.now() + timedelta(days=1)
        self.save()
        
        return True, f"Paid {self.daily_upkeep_cost} gold upkeep"
    
    def check_decay(self):
        """Check if flag should decay due to unpaid upkeep"""
        if self.status != 'active' or not self.upkeep_due_at:
            return
            
        now = timezone.now()
        
        if now > self.upkeep_due_at:
            # Calculate days overdue
            overdue_time = now - self.upkeep_due_at
            days_overdue = overdue_time.days
            
            if days_overdue <= 3:
                # Grace period - no penalty yet
                return
            elif days_overdue <= 7:
                # Decay phase - lose HP daily
                hp_loss = 10 * (days_overdue - 3)
                self.current_hp = max(0, self.max_hp - hp_loss)
                
                if self.current_hp <= 0:
                    self.status = 'decayed'
                    self.capture_window_started = now
                    
                self.save()
            else:
                # Completely abandoned
                self.status = 'decayed'
                self.current_hp = 0
                self.capture_window_started = now
                self.save()
    
    def can_attack(self, attacker):
        """Check if attacker can attack this flag - PK style unrestricted combat"""
        if self.owner == attacker:
            return False, "Cannot attack your own flag"
            
        if self.status not in ['active', 'damaged']:
            return False, f"Flag status is {self.status}"
            
        # Check if attacker is within territory radius
        distance = self.distance_to(attacker.lat, attacker.lon)
        if distance > self.radius_meters:
            return False, f"Must be within {self.radius_meters}m to attack"
        
        # PK-style: No protection for offline players or time-based restrictions
        # Flags can be attacked 24/7 regardless of owner online status
        return True, "Can attack"
    
    def apply_damage(self, attacker, damage_amount):
        """Apply damage to flag from attacker"""
        can_attack, message = self.can_attack(attacker)
        if not can_attack:
            return False, message
            
        # Apply damage
        self.current_hp = max(0, self.current_hp - damage_amount)
        self.last_attacked = timezone.now()
        
        if self.current_hp <= 0:
            # Flag destroyed - enter capturable state
            self.status = 'capturable'
            self.capture_window_started = timezone.now()
        else:
            self.status = 'damaged'
            
        self.save()
        
        # Log attack
        FlagCombatLog.objects.create(
            flag=self,
            attacker=attacker,
            action='attack',
            damage_dealt=damage_amount,
            flag_hp_after=self.current_hp
        )
        
        return True, f"Dealt {damage_amount} damage. Flag HP: {self.current_hp}/{self.max_hp}"
    
    def can_upgrade(self):
        """Check if flag can be upgraded"""
        if self.status != 'active':
            return False, "Flag must be active to upgrade"
        
        if self.level >= 5:
            return False, "Flag is already at maximum level"
        
        # Check if already upgrading
        if self.status == 'upgrading':
            return False, "Flag is already being upgraded"
        
        return True, "Can upgrade"
    
    def start_upgrade(self):
        """Start upgrading the flag to next level"""
        can_upgrade, message = self.can_upgrade()
        if not can_upgrade:
            return False, message
        
        upgrade_cost = self.get_upgrade_cost()
        if not upgrade_cost:
            return False, "No upgrade available"
        
        # Check resources
        if self.owner.gold < upgrade_cost['gold']:
            return False, f"Need {upgrade_cost['gold']} gold (have {self.owner.gold})"
        
        # Deduct resources
        self.owner.gold -= upgrade_cost['gold']
        self.owner.save()
        
        # Start upgrade
        self.level += 1
        self.status = 'upgrading'
        self.upgrade_started = timezone.now()
        self.save()
        
        # Apply new level stats immediately (instant upgrade for now)
        level_stats = self.get_level_stats()
        self.radius_meters = level_stats['radius']
        self.max_hp = level_stats['hp']
        self.current_hp = self.max_hp  # Full heal on upgrade
        self.daily_upkeep_cost = level_stats['upkeep']
        self.status = 'active'
        self.upgrade_completed = timezone.now()
        self.save()
        
        # Regenerate territory zone
        self.regenerate_territory_zone()
        
        return True, f"Upgraded to Level {self.level}!"
    
    def can_capture(self, player):
        """Check if player can capture this flag"""
        if self.status != 'capturable' and self.status != 'decayed':
            return False, "Flag is not capturable"
            
        if self.owner == player:
            return False, "Already own this flag"
            
        # Check capture window
        if self.capture_window_started:
            elapsed = timezone.now() - self.capture_window_started
            if elapsed > timedelta(minutes=self.capture_window_minutes):
                # Window expired - flag becomes available to original owner for repair
                return False, "Capture window expired"
                
        return True, "Can capture"
    
    def capture(self, new_owner):
        """Transfer flag ownership to new owner"""
        can_capture, message = self.can_capture(new_owner)
        if not can_capture:
            return False, message
            
        # Calculate loot (portion of stored revenue)
        loot_revenue = int(self.uncollected_revenue * 0.5)  # 50% of stored revenue
        
        # Transfer ownership
        old_owner = self.owner
        self.owner = new_owner
        
        # Reset to level 1 (PK behavior)
        self.level = 1
        level_stats = self.get_level_stats(1)
        self.radius_meters = level_stats['radius']
        self.max_hp = level_stats['hp']
        self.current_hp = self.max_hp
        self.daily_upkeep_cost = level_stats['upkeep']
        
        # Reset revenue and upkeep
        self.uncollected_revenue = 0
        self.last_revenue_collection = timezone.now()
        self.upkeep_due_at = timezone.now() + timedelta(days=1)
        self.last_upkeep_payment = timezone.now()
        
        # Clear capture state
        self.status = 'active'
        self.capture_window_started = None
        
        self.save()
        
        # Give loot to new owner
        if loot_revenue > 0:
            new_owner.gold += loot_revenue
            new_owner.save()
            
        # Log capture
        FlagCombatLog.objects.create(
            flag=self,
            attacker=new_owner,
            defender=old_owner,
            action='capture',
            loot_gained=loot_revenue
        )
        
        # Regenerate territory zone
        self.regenerate_territory_zone()
        
        return True, f"Captured flag! Gained {loot_revenue} gold loot."
    
    def repair(self, repair_amount):
        """Repair flag damage"""
        if self.status not in ['damaged', 'capturable']:
            return False, "Flag doesn't need repair"
            
        # Calculate repair cost (gold per HP)
        repair_cost_per_hp = 5
        total_cost = repair_amount * repair_cost_per_hp
        
        if self.owner.gold < total_cost:
            return False, f"Need {total_cost} gold to repair {repair_amount} HP"
            
        # Apply repair
        self.owner.gold -= total_cost
        self.owner.save()
        
        self.current_hp = min(self.max_hp, self.current_hp + repair_amount)
        
        if self.current_hp == self.max_hp:
            self.status = 'active'
            
        self.save()
        
        return True, f"Repaired {repair_amount} HP for {total_cost} gold"
    
    def distance_to(self, lat, lon):
        """Calculate distance to coordinates in meters"""
        # Haversine formula
        R = 6371000  # Earth radius in meters
        
        lat1, lon1 = math.radians(self.lat), math.radians(self.lon)
        lat2, lon2 = math.radians(lat), math.radians(lon)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def regenerate_territory_zone(self):
        """Regenerate the territory zone geometry"""
        # Remove old territory zone
        TerritoryZone.objects.filter(flag=self).delete()
        
        # Create new territory zone
        TerritoryZone.objects.create(
            flag=self,
            center_lat=self.lat,
            center_lon=self.lon,
            radius_meters=self.radius_meters
        )


class TerritoryZone(BaseModel):
    """
    Represents the circular territory controlled by a flag
    Used for fast spatial queries and collision detection
    """
    flag = models.OneToOneField(TerritoryFlag, on_delete=models.CASCADE, related_name='territory_zone')
    
    # Territory geometry
    center_lat = models.FloatField()
    center_lon = models.FloatField()
    radius_meters = models.IntegerField()
    
    # Bounding box for fast queries
    north_lat = models.FloatField()
    south_lat = models.FloatField() 
    east_lon = models.FloatField()
    west_lon = models.FloatField()
    
    class Meta:
        db_table = 'pk_territory_zones'
        
    def save(self, *args, **kwargs):
        # Calculate bounding box
        # Rough conversion: 1 degree ≈ 111km
        lat_offset = (self.radius_meters / 111000.0)
        lon_offset = (self.radius_meters / (111000.0 * math.cos(math.radians(self.center_lat))))
        
        self.north_lat = self.center_lat + lat_offset
        self.south_lat = self.center_lat - lat_offset
        self.east_lon = self.center_lon + lon_offset
        self.west_lon = self.center_lon - lon_offset
        
        super().save(*args, **kwargs)
        
    def contains_point(self, lat, lon):
        """Check if point is within territory"""
        # Quick bounding box check first
        if not (self.south_lat <= lat <= self.north_lat and 
                self.west_lon <= lon <= self.east_lon):
            return False
            
        # Precise distance check
        distance = self.distance_to(lat, lon)
        return distance <= self.radius_meters
    
    def overlaps_with(self, lat, lon, radius):
        """Check if another circle overlaps with this territory"""
        distance = self.distance_to(lat, lon)
        return distance < (self.radius_meters + radius)
    
    def distance_to(self, lat, lon):
        """Calculate distance to coordinates in meters"""
        R = 6371000  # Earth radius in meters
        
        lat1, lon1 = math.radians(self.center_lat), math.radians(self.center_lon)
        lat2, lon2 = math.radians(lat), math.radians(lon)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c


class FlagRevenueCollection(BaseModel):
    """Track flag revenue collections for analytics"""
    flag = models.ForeignKey(TerritoryFlag, on_delete=models.CASCADE, related_name='revenue_collections')
    amount_collected = models.IntegerField()
    player_level = models.IntegerField()
    flag_level = models.IntegerField()
    hours_since_last_collection = models.FloatField(default=0.0)
    
    class Meta:
        db_table = 'pk_flag_revenue_collections'
        
    def __str__(self):
        return f"Collection: {self.amount_collected} gold from {self.flag}"


class FlagCombatLog(BaseModel):
    """Track flag combat events for analytics and history"""
    ACTION_CHOICES = [
        ('attack', 'Attack'),
        ('capture', 'Capture'),
        ('repair', 'Repair'),
        ('destroy', 'Destroy'),
    ]
    
    flag = models.ForeignKey(TerritoryFlag, on_delete=models.CASCADE, related_name='combat_logs')
    attacker = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='flag_attacks')
    defender = models.ForeignKey(Character, on_delete=models.CASCADE, null=True, blank=True, related_name='flag_defenses')
    
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    damage_dealt = models.IntegerField(default=0)
    flag_hp_before = models.IntegerField(default=0)
    flag_hp_after = models.IntegerField(default=0)
    loot_gained = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'pk_flag_combat_logs'
        
    def __str__(self):
        return f"{self.attacker.name} {self.action} {self.flag} - {self.damage_dealt} damage"


class FlagUpkeepLog(BaseModel):
    """Track upkeep payments and decay events"""
    flag = models.ForeignKey(TerritoryFlag, on_delete=models.CASCADE, related_name='upkeep_logs')
    
    EVENT_CHOICES = [
        ('payment', 'Upkeep Paid'),
        ('missed', 'Upkeep Missed'),
        ('decay_start', 'Decay Started'),
        ('decay_progress', 'Decay Progressed'),
        ('abandoned', 'Flag Abandoned'),
    ]
    
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    amount_paid = models.IntegerField(default=0)
    days_overdue = models.IntegerField(default=0)
    hp_lost = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'pk_flag_upkeep_logs'
        
    def __str__(self):
        return f"{self.flag} - {self.event_type}"
