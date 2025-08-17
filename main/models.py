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
    
    def add_item_to_inventory(self, item_name, quantity=1):
        """Add an item to character's inventory"""
        # Get or create the item template
        try:
            item_template = ItemTemplate.objects.get(name=item_name)
        except ItemTemplate.DoesNotExist:
            # Create basic resource item template if it doesn't exist
            item_template = self.create_resource_item_template(item_name)
        
        # Get or create inventory item
        inventory_item, created = InventoryItem.objects.get_or_create(
            character=self,
            item_template=item_template,
            defaults={'quantity': 0}
        )
        
        # Add quantity, respecting stack limit
        max_stack = item_template.max_stack_size
        inventory_item.quantity = min(inventory_item.quantity + quantity, max_stack)
        inventory_item.save()
        
        return inventory_item
    
    def create_resource_item_template(self, item_name):
        """Create a basic resource item template"""
        resource_templates = {
            'wood': {
                'description': 'Basic building material from trees',
                'item_type': 'material',
                'base_value': 2,
                'max_stack_size': 50
            },
            'stone': {
                'description': 'Sturdy stone for construction',
                'item_type': 'material',
                'base_value': 3,
                'max_stack_size': 50
            },
            'food': {
                'description': 'Basic sustenance for survival',
                'item_type': 'consumable',
                'base_value': 5,
                'max_stack_size': 20,
                'heal_amount': 10
            },
            'berries': {
                'description': 'Sweet berries that restore 25% health',
                'item_type': 'consumable',
                'base_value': 10,
                'max_stack_size': 10,
                'heal_percentage': 0.25  # 25% of max HP
            },
            'iron_ore': {
                'description': 'Raw iron ore for crafting',
                'item_type': 'material',
                'base_value': 8,
                'max_stack_size': 30
            },
            'gold_ore': {
                'description': 'Precious gold ore',
                'item_type': 'material',
                'base_value': 20,
                'max_stack_size': 20
            },
            'ancient_artifact': {
                'description': 'Mysterious artifact from ancient ruins',
                'item_type': 'misc',
                'rarity': 'rare',
                'base_value': 100,
                'max_stack_size': 5
            }
        }
        
        template_data = resource_templates.get(item_name, {
            'description': f'A {item_name.replace("_", " ")}',
            'item_type': 'misc',
            'base_value': 1,
            'max_stack_size': 10
        })
        
        return ItemTemplate.objects.create(
            name=item_name,
            **template_data
        )
    
    def use_item(self, item_name, quantity=1):
        """Use an item from inventory"""
        try:
            item_template = ItemTemplate.objects.get(name=item_name)
            inventory_item = InventoryItem.objects.get(
                character=self,
                item_template=item_template
            )
            
            if inventory_item.quantity < quantity:
                return False, "Not enough items"
            
            if item_template.item_type == 'consumable':
                # Use the item
                success, message = item_template.use_consumable(self)
                if success:
                    inventory_item.quantity -= quantity
                    if inventory_item.quantity <= 0:
                        inventory_item.delete()
                    else:
                        inventory_item.save()
                    return True, message
                else:
                    return False, message
            else:
                return False, "Item is not usable"
                
        except (ItemTemplate.DoesNotExist, InventoryItem.DoesNotExist):
            return False, "Item not found in inventory"
    
    def get_inventory_summary(self):
        """Get a summary of character's inventory"""
        inventory = {}
        for item in self.inventory.all():
            inventory[item.item_template.name] = {
                'quantity': item.quantity,
                'type': item.item_template.item_type,
                'value': item.item_template.base_value,
                'description': item.item_template.description
            }
        return inventory


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
    
    # For consumables
    heal_amount = models.IntegerField(default=0, help_text="HP healing amount")
    heal_percentage = models.FloatField(default=0.0, help_text="Percentage of max HP to heal (0.0-1.0)")
    mana_restore = models.IntegerField(default=0, help_text="Mana restoration amount")
    stamina_restore = models.IntegerField(default=0, help_text="Stamina restoration amount")
    
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
    
    def use_consumable(self, character):
        """Use this item as a consumable on a character"""
        if self.item_type != 'consumable':
            return False, "Item is not consumable"
        
        # Calculate healing effects
        total_heal = self.heal_amount
        if self.heal_percentage > 0:
            total_heal += int(character.max_hp * self.heal_percentage)
        
        # Apply effects
        if total_heal > 0:
            old_hp = character.current_hp
            character.heal(total_heal)
            actual_heal = character.current_hp - old_hp
        else:
            actual_heal = 0
        
        if self.mana_restore > 0:
            character.current_mana = min(character.max_mana, character.current_mana + self.mana_restore)
        
        if self.stamina_restore > 0:
            character.current_stamina = min(character.max_stamina, character.current_stamina + self.stamina_restore)
        
        character.save()
        
        return True, f"Healed {actual_heal} HP" if actual_heal > 0 else "Item used"


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
    
    def generate_loot_drops(self):
        """Generate loot drops from defeated monster"""
        loot = []
        monster_name = self.monster.template.name.lower()
        
        # Animal-type monsters drop berries more often
        animal_types = ['wolf', 'bear', 'deer', 'rabbit', 'boar', 'fox']
        is_animal = any(animal in monster_name for animal in animal_types)
        
        if is_animal:
            # Animals have higher chance to drop berries
            if random.random() < 0.6:  # 60% chance
                loot.append({
                    'name': 'berries',
                    'quantity': random.randint(1, 3)
                })
        
        # All monsters can drop basic loot
        if random.random() < 0.3:  # 30% chance for food
            loot.append({
                'name': 'food',
                'quantity': random.randint(1, 2)
            })
        
        # Higher level monsters drop better loot
        if self.monster.template.level >= 5:
            if random.random() < 0.2:  # 20% chance for rare materials
                rare_items = ['iron_ore', 'gold_ore', 'ancient_artifact']
                loot.append({
                    'name': random.choice(rare_items),
                    'quantity': 1
                })
        
        # Boss-type monsters (high level) drop guaranteed berries
        if self.monster.template.level >= 10:
            loot.append({
                'name': 'berries',
                'quantity': random.randint(2, 4)
            })
        
        return loot
    
    def end_combat(self, result):
        """End combat and apply results"""
        self.status = result
        self.ended_at = timezone.now()
        
        if result == 'victory':
            # Calculate rewards
            self.experience_gained = self.monster.template.base_experience + random.randint(0, 10)
            self.gold_gained = self.monster.template.base_gold + random.randint(0, 20)
            
            # Generate loot drops
            self.items_dropped = self.generate_loot_drops()
            
            # Give rewards to character
            self.character.gain_experience(self.experience_gained)
            self.character.gold += self.gold_gained
            self.character.current_hp = self.character_hp
            
            # Add dropped items to inventory
            for item_drop in self.items_dropped:
                self.character.add_item_to_inventory(item_drop['name'], item_drop['quantity'])
            
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
        ('resource_gathered', 'Resource Gathered'),
        ('loot_dropped', 'Loot Dropped'),
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


# ===============================
# RESOURCE COLLECTION SYSTEM
# ===============================

class ResourceNode(BaseModel):
    """Resource nodes for harvesting (trees, mines, etc.)"""
    RESOURCE_TYPES = [
        ('tree', 'Tree'),  # Provides wood and berries
        ('iron_mine', 'Iron Mine'),  # Provides iron ore
        ('gold_mine', 'Gold Mine'),  # Provides gold ore
        ('stone_quarry', 'Stone Quarry'),  # Provides stone
        ('herb_patch', 'Herb Patch'),  # Provides herbs and berries
        ('ruins', 'Ancient Ruins'),  # Provides rare items
        ('cave', 'Cave'),  # Provides various minerals
        ('well', 'Water Well'),  # Provides water/food
        ('farm', 'Farm'),  # Provides food
        ('berry_bush', 'Berry Bush'),  # Provides berries for healing
    ]
    
    # Animal habitat mappings
    HABITAT_ANIMALS = {
        'tree': ['Forest Wolf'],
        'herb_patch': ['Forest Wolf', 'Rabbit'],
        'stone_quarry': ['Cave Bear'],
        'cave': ['Cave Bear'],
        'berry_bush': ['Rabbit'],
        'farm': ['Rabbit'],
        'well': ['Rabbit'],
    }
    
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    lat = models.FloatField(help_text="Resource latitude")
    lon = models.FloatField(help_text="Resource longitude")
    
    # Resource stats
    level = models.IntegerField(default=1, help_text="Resource level (1-10)")
    quantity = models.IntegerField(default=5, help_text="Current available quantity")
    max_quantity = models.IntegerField(default=5, help_text="Maximum quantity when full")
    
    # Harvesting mechanics
    last_harvested = models.DateTimeField(null=True, blank=True)
    harvest_count = models.IntegerField(default=0, help_text="Times harvested")
    respawn_time = models.IntegerField(default=60, help_text="Minutes to respawn")
    
    # Rewards
    base_experience = models.IntegerField(default=10)
    
    # Status
    is_depleted = models.BooleanField(default=False)
    created_by_system = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'rpg_resource_nodes'
        unique_together = ('lat', 'lon')  # One resource per location
        
    def __str__(self):
        return f"{self.get_resource_type_display()} (Level {self.level}) at ({self.lat:.4f}, {self.lon:.4f})"
    
    def can_harvest(self):
        """Check if resource can be harvested"""
        if self.is_depleted or self.quantity <= 0:
            return False
        
        if self.last_harvested:
            time_since_harvest = timezone.now() - self.last_harvested
            if time_since_harvest.total_seconds() < (self.respawn_time * 60):
                return False
        
        return True
    
    def get_harvest_rewards(self, character_level=1):
        """Calculate harvest rewards based on resource and character level"""
        level_multiplier = 1 + (self.level - 1) * 0.3
        character_multiplier = 1 + (character_level - 1) * 0.1
        
        # Base experience reward
        experience = int(self.base_experience * level_multiplier * character_multiplier)
        
        # Resource-specific rewards
        rewards = {
            'experience': experience,
            'items': []
        }
        
        # Determine what items to give based on resource type
        if self.resource_type == 'tree':
            rewards['items'] = [
                {'name': 'wood', 'quantity': random.randint(1, 3)},
                {'name': 'berries', 'quantity': random.randint(0, 2)}  # Sometimes berries
            ]
        elif self.resource_type == 'stone_quarry':
            rewards['items'] = [
                {'name': 'stone', 'quantity': random.randint(2, 4)}
            ]
        elif self.resource_type == 'farm' or self.resource_type == 'well':
            rewards['items'] = [
                {'name': 'food', 'quantity': random.randint(1, 3)}
            ]
        elif self.resource_type == 'berry_bush' or self.resource_type == 'herb_patch':
            rewards['items'] = [
                {'name': 'berries', 'quantity': random.randint(2, 5)}
            ]
        elif self.resource_type == 'gold_mine':
            rewards['items'] = [
                {'name': 'gold_ore', 'quantity': random.randint(1, 2)}
            ]
            rewards['gold'] = random.randint(10, 30)  # Direct gold reward
        elif self.resource_type == 'iron_mine':
            rewards['items'] = [
                {'name': 'iron_ore', 'quantity': random.randint(1, 3)}
            ]
        elif self.resource_type == 'cave':
            rewards['items'] = [
                {'name': 'stone', 'quantity': random.randint(1, 2)},
                {'name': 'iron_ore', 'quantity': random.randint(0, 1)}
            ]
        elif self.resource_type == 'ruins':
            rewards['items'] = [
                {'name': 'ancient_artifact', 'quantity': 1}
            ]
            rewards['gold'] = random.randint(50, 100)
        
        return rewards
    
    def harvest(self, character):
        """Harvest this resource node"""
        if not self.can_harvest():
            return None
        
        # Get rewards
        rewards = self.get_harvest_rewards(character.level)
        
        # Update resource state
        self.quantity -= 1
        self.harvest_count += 1
        self.last_harvested = timezone.now()
        
        if self.quantity <= 0:
            self.is_depleted = True
            # Set respawn time
            self.last_harvested = timezone.now()
        
        self.save()
        
        # Apply rewards to character
        if 'experience' in rewards:
            character.gain_experience(rewards['experience'])
        
        if 'gold' in rewards:
            character.gold += rewards['gold']
            character.save()
        
        return rewards
    
    def respawn_if_ready(self):
        """Check and respawn resource if ready"""
        if not self.is_depleted or not self.last_harvested:
            return False
        
        time_since_depletion = timezone.now() - self.last_harvested
        if time_since_depletion.total_seconds() >= (self.respawn_time * 60):
            self.quantity = self.max_quantity
            self.is_depleted = False
            self.save()
            return True
        
        return False


class ResourceHarvest(BaseModel):
    """Track resource harvesting by characters"""
    STATUS_CHOICES = [
        ('in_progress', 'Harvesting'),
        ('completed', 'Completed'),
        ('interrupted', 'Interrupted'),
        ('failed', 'Failed'),
    ]
    
    resource = models.ForeignKey(ResourceNode, on_delete=models.CASCADE, related_name='harvests')
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='resource_harvests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    
    # Results
    experience_gained = models.IntegerField(default=0)
    gold_gained = models.IntegerField(default=0)
    items_gained = models.JSONField(default=list)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=5, help_text="Time to complete harvest")
    
    class Meta:
        db_table = 'rpg_resource_harvests'
    
    def __str__(self):
        return f"{self.character.name} harvesting {self.resource.get_resource_type_display()} ({self.status})"


# ===============================
# CRAFTING SYSTEM
# ===============================

class CraftingRecipe(BaseModel):
    """Crafting recipes that combine resources into items"""
    RECIPE_CATEGORIES = [
        ('tools', 'Tools'),
        ('weapons', 'Weapons'),
        ('armor', 'Armor'),
        ('consumables', 'Consumables'),
        ('materials', 'Materials'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=500)
    category = models.CharField(max_length=20, choices=RECIPE_CATEGORIES)
    
    # Output item
    result_item = models.ForeignKey(ItemTemplate, on_delete=models.CASCADE, related_name='crafting_recipes')
    result_quantity = models.IntegerField(default=1)
    
    # Requirements
    required_level = models.IntegerField(default=1, help_text="Character level required")
    required_skill_level = models.IntegerField(default=1, help_text="Crafting skill level required")
    
    # Crafting mechanics
    base_success_rate = models.FloatField(default=0.8, help_text="Base success rate (0.0-1.0)")
    craft_time_seconds = models.IntegerField(default=10, help_text="Time to complete crafting")
    experience_reward = models.IntegerField(default=25, help_text="Crafting XP gained")
    
    # Status
    is_discoverable = models.BooleanField(default=True, help_text="Can players discover this recipe")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'rpg_crafting_recipes'
    
    def __str__(self):
        return f"{self.name} -> {self.result_item.name}"
    
    def get_required_materials(self):
        """Get all required materials for this recipe"""
        return self.required_materials.all()
    
    def can_craft(self, character):
        """Check if character can craft this recipe"""
        # Check level requirement
        if character.level < self.required_level:
            return False, f"Requires character level {self.required_level}"
        
        # Check crafting skill (if exists)
        try:
            crafting_skill = character.skills.get(name='Crafting')
            if crafting_skill.level < self.required_skill_level:
                return False, f"Requires Crafting skill level {self.required_skill_level}"
        except Skill.DoesNotExist:
            if self.required_skill_level > 1:
                return False, "Requires Crafting skill"
        
        # Check required materials
        for material in self.get_required_materials():
            try:
                inventory_item = character.inventory.get(item_template__name=material.material_name)
                if inventory_item.quantity < material.quantity_required:
                    return False, f"Need {material.quantity_required} {material.material_name}, have {inventory_item.quantity}"
            except InventoryItem.DoesNotExist:
                return False, f"Need {material.quantity_required} {material.material_name}, have 0"
        
        return True, "Can craft"
    
    def calculate_success_rate(self, character):
        """Calculate success rate based on character skills"""
        success_rate = self.base_success_rate
        
        # Skill bonus
        try:
            crafting_skill = character.skills.get(name='Crafting')
            skill_bonus = (crafting_skill.level - self.required_skill_level) * 0.05  # 5% per level above requirement
            success_rate += skill_bonus
        except Skill.DoesNotExist:
            pass
        
        # Level bonus
        level_bonus = (character.level - self.required_level) * 0.02  # 2% per level above requirement
        success_rate += level_bonus
        
        return min(0.95, max(0.1, success_rate))  # Clamp between 10% and 95%


class CraftingRecipeMaterial(BaseModel):
    """Required materials for crafting recipes"""
    recipe = models.ForeignKey(CraftingRecipe, on_delete=models.CASCADE, related_name='required_materials')
    material_name = models.CharField(max_length=100, help_text="Name of required item")
    quantity_required = models.IntegerField(default=1)
    is_consumed = models.BooleanField(default=True, help_text="Is this material consumed during crafting")
    
    class Meta:
        db_table = 'rpg_crafting_materials'
        unique_together = ['recipe', 'material_name']
    
    def __str__(self):
        return f"{self.recipe.name} requires {self.quantity_required}x {self.material_name}"


class CraftingAttempt(BaseModel):
    """Track crafting attempts by characters"""
    STATUS_CHOICES = [
        ('in_progress', 'Crafting'),
        ('success', 'Success'),
        ('failure', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='crafting_attempts')
    recipe = models.ForeignKey(CraftingRecipe, on_delete=models.CASCADE, related_name='attempts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    
    # Results
    success_rate_used = models.FloatField(help_text="Success rate at time of crafting")
    items_created = models.JSONField(default=list, help_text="Items successfully created")
    experience_gained = models.IntegerField(default=0)
    materials_consumed = models.JSONField(default=list, help_text="Materials used in attempt")
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'rpg_crafting_attempts'
    
    def __str__(self):
        return f"{self.character.name} crafting {self.recipe.name} ({self.status})"
