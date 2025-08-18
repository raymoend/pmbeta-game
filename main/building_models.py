"""
Building System - Like Parallel Kingdom Flags
Buildings that generate revenue over time with upgrades and customizable flag colors
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta
import random
import math

from .models import BaseModel, Character


class BuildingType(BaseModel):
    """Different types of buildings players can construct"""
    BUILDING_CATEGORIES = [
        ('economic', 'Economic'),     # Revenue generating
        ('military', 'Military'),     # Defense/attack
        ('utility', 'Utility'),       # Special functions
        ('decorative', 'Decorative'), # Cosmetic
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=500)
    category = models.CharField(max_length=20, choices=BUILDING_CATEGORIES)
    
    # Construction costs
    base_cost_gold = models.IntegerField(default=1000)
    base_cost_wood = models.IntegerField(default=50)
    base_cost_stone = models.IntegerField(default=25)
    
    # Revenue generation
    base_revenue_per_hour = models.IntegerField(default=10, help_text="Gold generated per hour at level 1")
    max_revenue_per_hour = models.IntegerField(default=2500, help_text="Max gold per hour at highest level")
    
    # Building properties
    max_level = models.IntegerField(default=10, help_text="Maximum upgrade level")
    construction_time_minutes = models.IntegerField(default=60, help_text="Time to build in minutes")
    
    # Visual appearance
    icon_name = models.CharField(max_length=50, default="building", help_text="Icon for map display")
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'pk_building_types'
    
    def __str__(self):
        return self.name
    
    def get_revenue_at_level(self, level):
        """Calculate revenue per hour at given level"""
        if level <= 0:
            return 0
        
        # Exponential growth curve that reaches max at max_level
        progress = min(level / self.max_level, 1.0)
        revenue = self.base_revenue_per_hour + (
            (self.max_revenue_per_hour - self.base_revenue_per_hour) * 
            (progress ** 1.5)  # Slightly curved growth
        )
        return min(int(revenue), self.max_revenue_per_hour)
    
    def get_upgrade_cost(self, current_level):
        """Calculate cost to upgrade to next level"""
        if current_level >= self.max_level:
            return None
        
        # Exponential cost increase
        multiplier = (1.5 ** current_level)
        return {
            'gold': int(self.base_cost_gold * multiplier),
            'wood': int(self.base_cost_wood * multiplier * 0.5),
            'stone': int(self.base_cost_stone * multiplier * 0.5),
        }


class FlagColor(BaseModel):
    """Available flag colors for players to choose"""
    name = models.CharField(max_length=50, unique=True)
    hex_color = models.CharField(max_length=7, help_text="Hex color code (e.g., #FF0000)")
    display_name = models.CharField(max_length=50, help_text="Display name for UI")
    
    # Color categories
    is_premium = models.BooleanField(default=False, help_text="Premium color requiring special unlock")
    unlock_level = models.IntegerField(default=1, help_text="Character level required to unlock")
    unlock_cost = models.IntegerField(default=0, help_text="Gold cost to unlock")
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'pk_flag_colors'
    
    def __str__(self):
        return self.display_name


class PlayerBuilding(BaseModel):
    """Individual building instances owned by players"""
    STATUS_CHOICES = [
        ('constructing', 'Under Construction'),
        ('active', 'Active'),
        ('damaged', 'Damaged'),
        ('destroyed', 'Destroyed'),
        ('upgrading', 'Upgrading'),
    ]
    
    owner = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='buildings')
    building_type = models.ForeignKey(BuildingType, on_delete=models.CASCADE)
    
    # Location
    lat = models.FloatField(help_text="Building latitude")
    lon = models.FloatField(help_text="Building longitude")
    
    # Building state
    level = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='constructing')
    
    # Flag customization
    flag_color = models.ForeignKey(FlagColor, on_delete=models.SET_NULL, null=True, blank=True)
    custom_name = models.CharField(max_length=100, blank=True, help_text="Custom name for building")
    
    # Revenue tracking
    last_collection = models.DateTimeField(auto_now_add=True)
    total_revenue_generated = models.BigIntegerField(default=0)
    uncollected_revenue = models.IntegerField(default=0)
    
    # Construction/upgrade timing
    construction_started = models.DateTimeField(auto_now_add=True)
    construction_completed = models.DateTimeField(null=True, blank=True)
    upgrade_started = models.DateTimeField(null=True, blank=True)
    upgrade_completed = models.DateTimeField(null=True, blank=True)
    
    # Damage system (for PvP/raids)
    current_hp = models.IntegerField(default=100)
    max_hp = models.IntegerField(default=100)
    last_attacked = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'pk_player_buildings'
        unique_together = ['lat', 'lon']  # One building per exact location
    
    def __str__(self):
        name = self.custom_name or f"{self.building_type.name}"
        return f"{self.owner.name}'s {name} (Level {self.level})"
    
    def is_construction_complete(self):
        """Check if initial construction is finished"""
        if self.status != 'constructing':
            return True
        
        if not self.construction_started:
            return False
        
        elapsed = timezone.now() - self.construction_started
        required = timedelta(minutes=self.building_type.construction_time_minutes)
        
        if elapsed >= required:
            self.status = 'active'
            self.construction_completed = timezone.now()
            self.save()
            return True
        
        return False
    
    def is_upgrade_complete(self):
        """Check if current upgrade is finished"""
        if self.status != 'upgrading' or not self.upgrade_started:
            return True
        
        elapsed = timezone.now() - self.upgrade_started
        required = timedelta(minutes=self.building_type.construction_time_minutes * self.level)
        
        if elapsed >= required:
            self.status = 'active'
            self.upgrade_completed = timezone.now()
            self.save()
            return True
        
        return False
    
    def can_collect_revenue(self):
        """Check if revenue can be collected"""
        return self.status == 'active' and self.is_construction_complete()
    
    def calculate_revenue(self):
        """Calculate accumulated revenue since last collection"""
        if not self.can_collect_revenue():
            return 0
        
        # Calculate time since last collection
        time_since_collection = timezone.now() - self.last_collection
        hours_elapsed = time_since_collection.total_seconds() / 3600
        
        # Get revenue rate for current level
        revenue_per_hour = self.building_type.get_revenue_at_level(self.level)
        
        # Calculate total revenue (with some randomness)
        base_revenue = int(revenue_per_hour * hours_elapsed)
        random_bonus = random.uniform(0.9, 1.1)  # ±10% variance
        total_revenue = int(base_revenue * random_bonus)
        
        return max(0, total_revenue)
    
    def collect_revenue(self):
        """Collect accumulated revenue"""
        if not self.can_collect_revenue():
            return 0
        
        revenue = self.calculate_revenue() + self.uncollected_revenue
        
        if revenue > 0:
            # Add to player's gold
            self.owner.gold += revenue
            self.owner.save()
            
            # Update building tracking
            self.total_revenue_generated += revenue
            self.uncollected_revenue = 0
            self.last_collection = timezone.now()
            self.save()
            
            # Create revenue collection event
            RevenueCollection.objects.create(
                building=self,
                amount_collected=revenue,
                player_level=self.owner.level
            )
        
        return revenue
    
    def can_upgrade(self):
        """Check if building can be upgraded"""
        if self.level >= self.building_type.max_level:
            return False, "Building is at maximum level"
        
        if self.status != 'active':
            return False, f"Building status is {self.status}"
        
        if not self.is_construction_complete():
            return False, "Building construction not complete"
        
        # Check upgrade costs
        costs = self.building_type.get_upgrade_cost(self.level)
        if not costs:
            return False, "No upgrade available"
        
        # Check if player has resources
        if self.owner.gold < costs['gold']:
            return False, f"Need {costs['gold']} gold"
        
        # Check inventory for materials (simplified - assumes items exist)
        try:
            wood_item = self.owner.inventory.get(item_template__name='wood')
            if wood_item.quantity < costs['wood']:
                return False, f"Need {costs['wood']} wood"
        except:
            return False, f"Need {costs['wood']} wood"
        
        try:
            stone_item = self.owner.inventory.get(item_template__name='stone')
            if stone_item.quantity < costs['stone']:
                return False, f"Need {costs['stone']} stone"
        except:
            return False, f"Need {costs['stone']} stone"
        
        return True, "Can upgrade"
    
    def start_upgrade(self):
        """Begin upgrade process"""
        can_upgrade, message = self.can_upgrade()
        if not can_upgrade:
            return False, message
        
        # Get upgrade costs
        costs = self.building_type.get_upgrade_cost(self.level)
        
        # Deduct resources
        self.owner.gold -= costs['gold']
        self.owner.save()
        
        # Deduct materials from inventory
        wood_item = self.owner.inventory.get(item_template__name='wood')
        wood_item.quantity -= costs['wood']
        if wood_item.quantity <= 0:
            wood_item.delete()
        else:
            wood_item.save()
        
        stone_item = self.owner.inventory.get(item_template__name='stone')
        stone_item.quantity -= costs['stone']
        if stone_item.quantity <= 0:
            stone_item.delete()
        else:
            stone_item.save()
        
        # Start upgrade
        self.status = 'upgrading'
        self.upgrade_started = timezone.now()
        self.level += 1
        
        # Increase building HP with level
        self.max_hp = 100 + (self.level * 25)
        self.current_hp = self.max_hp
        
        self.save()
        
        return True, f"Upgrade to level {self.level} started"
    
    def get_current_revenue_rate(self):
        """Get current revenue per hour"""
        if self.can_collect_revenue():
            return self.building_type.get_revenue_at_level(self.level)
        return 0
    
    def get_next_level_revenue(self):
        """Get revenue rate at next level"""
        if self.level < self.building_type.max_level:
            return self.building_type.get_revenue_at_level(self.level + 1)
        return self.get_current_revenue_rate()


class BuildingTemplate(BaseModel):
    """Predefined building templates for easy placement"""
    name = models.CharField(max_length=100)
    building_type = models.ForeignKey(BuildingType, on_delete=models.CASCADE)
    description = models.TextField(max_length=300)
    
    # Quick-build options
    is_starter = models.BooleanField(default=False, help_text="Available to new players")
    level_required = models.IntegerField(default=1)
    
    # Template costs (can override building type defaults)
    cost_gold = models.IntegerField(null=True, blank=True)
    cost_wood = models.IntegerField(null=True, blank=True)
    cost_stone = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'pk_building_templates'
    
    def __str__(self):
        return self.name
    
    def get_costs(self):
        """Get building costs (template override or building type default)"""
        return {
            'gold': self.cost_gold or self.building_type.base_cost_gold,
            'wood': self.cost_wood or self.building_type.base_cost_wood,
            'stone': self.cost_stone or self.building_type.base_cost_stone,
        }


class RevenueCollection(BaseModel):
    """Track revenue collections for analytics"""
    building = models.ForeignKey(PlayerBuilding, on_delete=models.CASCADE, related_name='collections')
    amount_collected = models.IntegerField()
    player_level = models.IntegerField()
    building_level = models.IntegerField()
    
    # Analytics
    hours_since_last_collection = models.FloatField(default=0.0)
    
    def save(self, *args, **kwargs):
        if not self.building_level:
            self.building_level = self.building.level
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'pk_revenue_collections'
    
    def __str__(self):
        return f"Collection: {self.amount_collected} gold from {self.building}"


class BuildingAttack(BaseModel):
    """Track attacks on buildings (for PvP raiding)"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('success', 'Successful'),
        ('failed', 'Failed'),
        ('abandoned', 'Abandoned'),
    ]
    
    attacker = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='building_attacks')
    target_building = models.ForeignKey(PlayerBuilding, on_delete=models.CASCADE, related_name='attacks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Attack details
    damage_dealt = models.IntegerField(default=0)
    gold_stolen = models.IntegerField(default=0)
    attack_power = models.IntegerField(help_text="Attacker's power at time of attack")
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'pk_building_attacks'
    
    def __str__(self):
        return f"{self.attacker.name} attacks {self.target_building.owner.name}'s {self.target_building.building_type.name}"
