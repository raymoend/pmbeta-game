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
    # Player classes and display labels
    CLASS_CHOICES = [
        ('cyber_warrior', 'Cyber Warrior'),
        ('neural_hacker', 'Neural Hacker'),
        ('mech_pilot', 'Mech Pilot'),
        ('bio_synth', 'Bio Synth'),
        ('quantum_rogue', 'Quantum Rogue'),
        ('void_sorcerer', 'Void Sorcerer'),
    ]

    # Class design: balanced base stats (sum=50) and descriptive notes
    CLASS_INFO = {
        'cyber_warrior': {
            'role': 'Tank / Melee Fighter',
            'description': 'Defensive frontline fighter using cybernetic armor and melee weaponry. Excels in defense and survivability.',
            'specials': [
                'Nano Shielding: Boost defense temporarily by spending energy.',
                'Overdrive Mode: Trade defense for temporary damage + speed boost.',
                'Magnetic Pull: Pulls enemies closer, hindering ranged attacks briefly.'
            ],
            'base_stats': {'vitality': 14, 'strength': 12, 'defense': 14, 'agility': 5, 'intelligence': 5}
        },
        'neural_hacker': {
            'role': 'Support / Utility',
            'description': 'Stealthy tech manipulator who hacks, disrupts enemies, and provides buffs/debuffs.',
            'specials': [
                'Overload: Disables enemy shields and drones in an area.',
                'EMP Blast: Temporarily disables enemy abilities or tech items.',
                'Data Steal: Steal resources or data to gain temporary boosts.',
                'Stealth Cloak: Temporarily invisible to sensors.'
            ],
            'base_stats': {'vitality': 9, 'strength': 6, 'defense': 8, 'agility': 11, 'intelligence': 16}
        },
        'mech_pilot': {
            'role': 'Ranged DPS / Tank Hybrid',
            'description': 'Operates advanced combat mechs or drones with strong ranged offense and solid armor.',
            'specials': [
                'Drone Strike: Call an AI drone to assist in combat.',
                'Overcharged Weaponry: Temporarily boosts ranged damage.',
                'Hover Mode: Avoid ground-based attacks briefly.',
                'Tactical Lock-On: Increased accuracy/damage on a target.'
            ],
            'base_stats': {'vitality': 11, 'strength': 9, 'defense': 13, 'agility': 7, 'intelligence': 10}
        },
        'bio_synth': {
            'role': 'Healer / Support',
            'description': 'Biotech specialist who heals, regenerates, and buffs allies using organic/synthetic enhancements.',
            'specials': [
                'Regeneration Field: Area heal over time.',
                'Vital Surge: Big single-target heal at energy cost.',
                'Biotic Shield: Temporary damage shield on allies.',
                'Nano Boost: Temporary strength/speed/damage boost to an ally.'
            ],
            'base_stats': {'vitality': 11, 'strength': 6, 'defense': 11, 'agility': 11, 'intelligence': 11}
        },
        'quantum_rogue': {
            'role': 'Stealth / DPS',
            'description': 'High-speed assassin manipulating time/space for stealth attacks and evasions.',
            'specials': [
                'Time Warp: Slow/speed time in an area to disorient foes.',
                'Phase Shift: Temporarily intangible to pass through obstacles.',
                'Critical Hack: Tech disruption to increase crit chance.',
                'Silent Strike: Attacks from stealth are stronger and quiet.'
            ],
            'base_stats': {'vitality': 7, 'strength': 12, 'defense': 7, 'agility': 16, 'intelligence': 8}
        },
        'void_sorcerer': {
            'role': 'Magic / Energy Manipulation',
            'description': 'Harnesses void and dark matter to control the battlefield with energy-based attacks.',
            'specials': [
                'Void Rift: Pull-in for crowd control.',
                'Energy Absorption: Convert incoming energy to health or power.',
                'Gravitational Crush: Damage and armor debuff.',
                'Black Hole Nova: AoE damage-over-time field.'
            ],
            'base_stats': {'vitality': 10, 'strength': 7, 'defense': 7, 'agility': 7, 'intelligence': 19}
        },
    }

    # Derived convenience mapping used by apply_class_base_stats
    CLASS_BASE_STATS = {k: v['base_stats'] for k, v in CLASS_INFO.items()}

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='character')
    
    # Character Info
    name = models.CharField(max_length=50, unique=True)
    
    # Location (GPS coordinates)
    lat = models.FloatField(help_text="Current latitude")
    lon = models.FloatField(help_text="Current longitude")
    # Movement center (set on first valid move) for enforcing movement radius
    move_center_lat = models.FloatField(null=True, blank=True, help_text="Movement center latitude")
    move_center_lon = models.FloatField(null=True, blank=True, help_text="Movement center longitude")
    
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

    # Unspent points to allocate on level-up
    unspent_stat_points = models.IntegerField(default=0)
    
    # Currency and Resources
    gold = models.BigIntegerField(default=1000, help_text="Primary currency")
    
    # Status
    is_online = models.BooleanField(default=False)
    last_activity = models.DateTimeField(auto_now=True)
    in_combat = models.BooleanField(default=False)
    
    # PvP Settings
    pvp_enabled = models.BooleanField(default=True, help_text="Can be attacked by other players")

    # Downed/respawn state (PK-style)
    downed_at = models.DateTimeField(null=True, blank=True)
    respawn_available_at = models.DateTimeField(null=True, blank=True)
    
    # Travel cooldowns
    last_jump_at = models.DateTimeField(null=True, blank=True)

    # Customization (chosen at registration only)
    class_type = models.CharField(max_length=32, choices=CLASS_CHOICES, default='cyber_warrior')
    flag_color = models.ForeignKey('main.FlagColor', on_delete=models.SET_NULL, null=True, blank=True, help_text="User's chosen flag color")
    
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
        """Level up and grant allocation points instead of auto-statting."""
        xp_needed = self.experience_needed_for_next_level()
        self.experience -= xp_needed
        self.level += 1

        # Grant unspent stat points (player allocates later via API/UI)
        self.unspent_stat_points += 5

        # Recalculate derived stats (HP baseline remains constant)
        self.recalculate_derived_stats()

        # Full restore on level up for QoL
        self.current_hp = self.max_hp
        self.current_mana = self.max_mana
        self.current_stamina = self.max_stamina
    
    def recalculate_derived_stats(self):
        """Recalculate derived stats.
        HP baseline is fixed at 100 for all classes; mana/stamina scale with INT/AGI and level.
        """
        # Fixed HP baseline for fairness across classes
        self.max_hp = 100
        # Mana and stamina still scale
        self.max_mana = 25 + (self.intelligence * 5) + (self.level * 2)
        self.max_stamina = 50 + (self.agility * 5) + (self.level * 3)
        # Clamp currents to new maxima if needed
        self.current_hp = min(self.current_hp or 0, self.max_hp)
        self.current_mana = min(self.current_mana or 0, self.max_mana)
        self.current_stamina = min(self.current_stamina or 0, self.max_stamina)

    def apply_class_base_stats(self):
        """Set core attributes based on selected class. Should be called on creation."""
        stats = self.CLASS_BASE_STATS.get(self.class_type)
        if not stats:
            return
        self.vitality = int(stats.get('vitality', self.vitality))
        self.strength = int(stats.get('strength', self.strength))
        self.defense = int(stats.get('defense', self.defense))
        self.agility = int(stats.get('agility', self.agility))
        self.intelligence = int(stats.get('intelligence', self.intelligence))
        # Derived stats and full restore; HP is fixed baseline
        self.recalculate_derived_stats()
        self.current_hp = self.max_hp
        self.current_mana = self.max_mana
        self.current_stamina = self.max_stamina
    
    def heal(self, amount):
        """Heal character"""
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        self.save()
    
    def can_act(self, stamina_cost=0, mana_cost=0):
        """Check if character can perform an action"""
        return (self.current_stamina >= stamina_cost and 
                self.current_mana >= mana_cost and 
                not self.in_combat)
    
    def allocate_stats(self, allocations: dict):
        """Allocate unspent points to attributes.
        allocations example: {'strength':2,'defense':1,'vitality':1,'agility':0,'intelligence':1}
        """
        valid = ['strength', 'defense', 'vitality', 'agility', 'intelligence']
        to_spend = sum(int(allocations.get(k, 0) or 0) for k in valid)
        if to_spend <= 0:
            return False, 'No points allocated'
        if to_spend > self.unspent_stat_points:
            return False, f'Not enough points (have {self.unspent_stat_points})'
        # Apply
        for k in valid:
            inc = int(allocations.get(k, 0) or 0)
            if inc:
                setattr(self, k, int(getattr(self, k)) + inc)
        self.unspent_stat_points -= to_spend
        # Recompute derived from new attributes
        self.recalculate_derived_stats()
        self.save()
        return True, 'Allocated'

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
            # Themed consumable replacement for legacy 'berries'
            'Energy Berries': {
                'description': 'Energetic berries that restore 25% health',
                'item_type': 'consumable',
                'base_value': 12,
                'max_stack_size': 10,
                'heal_percentage': 0.25
            },
            # Legacy support: keep old key usable for older inventories
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
    # Track agility penalty applied when equipping armor so we can reverse accurately on unequip
    agility_penalty_applied = models.IntegerField(default=0)
    
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
    # Optional structured drop pool for NPC death (list of {item, quantity})
    drop_pool = models.JSONField(default=list)
    
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

    # Real-time loop cadence
    last_turn_at = models.DateTimeField(null=True, blank=True)
    turn_interval_seconds = models.IntegerField(default=2)
    
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
        """Resolve a combat turn with server-driven pacing.
        - Enforces turn interval based on last_turn_at/turn_interval_seconds.
        - Includes weapon damage from equipped weapon.
        - Class perk: Void Sorcerer has 10% to deal 1.5x damage (Void Rift surge).
        - Stamina gating: consume stamina for attack and defend; if attack stamina is insufficient,
          the player skips their attack but the monster may still retaliate.
        Returns True if turn processed, False if throttled or inactive.
        """
        if self.status != 'active':
            return False
        now = timezone.now()
        try:
            interval = int(self.turn_interval_seconds or 2)
        except Exception:
            interval = 2
        if self.last_turn_at and (now - self.last_turn_at).total_seconds() < max(0, interval):
            return False  # Too soon

        did_attack = False
        # Character attacks first, but requires stamina
        try:
            from .services import stamina as stam
            atk_cost = int(stam.get_stamina_costs().get('ATTACK', 5))
            has_stamina = stam.consume_stamina(self.character, atk_cost)
        except Exception:
            has_stamina = True
        if has_stamina:
            did_attack = True
            # Base damage from stats
            base_damage = max(1, int(self.character.strength) - int(self.monster.template.defense) + random.randint(-3, 3))
            # Add weapon damage if equipped
            weapon_damage = 0
            try:
                from .models import InventoryItem  # local import to avoid cycles
            except Exception:
                InventoryItem = None
            if InventoryItem is not None:
                try:
                    weapon = InventoryItem.objects.select_related('item_template').filter(
                        character=self.character, is_equipped=True, item_template__item_type='weapon'
                    ).first()
                    if weapon and weapon.item_template:
                        weapon_damage = int(getattr(weapon.item_template, 'damage', 0) or 0)
                except Exception:
                    weapon_damage = 0
            total_damage = base_damage + max(0, weapon_damage)
            # Void Sorcerer perk: 10% surge to 1.5x
            try:
                if (self.character.class_type or '').lower() == 'void_sorcerer' and random.random() < 0.10:
                    total_damage = int(math.ceil(total_damage * 1.5))
            except Exception:
                pass
            total_damage = max(1, int(total_damage))
            self.monster_hp = max(0, int(self.monster_hp) - total_damage)

            if self.monster_hp <= 0:
                self.last_turn_at = now
                self.end_combat('victory')
                return True

        # Monster counter-attacks regardless of whether the player attacked
        retaliation = max(1, int(self.monster.template.strength) - int(self.character.defense) + random.randint(-3, 3))
        self.character_hp = max(0, int(self.character_hp) - retaliation)

        # Optional defend stamina cost (does not block damage if insufficient)
        try:
            from .services import stamina as stam
            def_cost = int(stam.get_stamina_costs().get('DEFEND', 2))
            stam.consume_stamina(self.character, def_cost)
        except Exception:
            pass

        if self.character_hp <= 0:
            self.last_turn_at = now
            self.end_combat('defeat')
            return True

        # Persist tick timestamp and HP
        self.last_turn_at = now
        self.save(update_fields=['character_hp', 'monster_hp', 'last_turn_at', 'updated_at'])
        return True
    
    def generate_loot_drops(self):
        """Generate loot drops from defeated monster.
        If the monster's template defines a drop_pool, honor optional per-entry probability `prob` (0.0-1.0).
        Otherwise use themed fallback heuristics (mafia–alien style).
        """
        loot = []
        try:
            pool = list(getattr(self.monster.template, 'drop_pool', []) or [])
        except Exception:
            pool = []
        if pool:
            for entry in pool:
                try:
                    item_name = entry.get('item') or entry.get('name')
                    qty = int(entry.get('quantity', 1))
                    prob = float(entry.get('prob', 0.5))
                except Exception:
                    item_name, qty, prob = None, 0, 0.0
                if not item_name or qty <= 0:
                    continue
                # Scale quantity by monster level (roughly +1 per 5 levels)
                try:
                    lvl = int(getattr(self.monster.template, 'level', 1) or 1)
                except Exception:
                    lvl = 1
                scaled_qty = max(1, int(round(qty * max(1.0, lvl / 5.0))))
                if random.random() < max(0.0, min(1.0, prob)):
                    loot.append({'name': item_name, 'quantity': scaled_qty})
            return loot

        # Themed fallback drops (mafia–alien). Skewed by level.
        commons = ['Energy Berries', 'Neon Wood', 'Plasma Stone', 'Mutant Herbs', 'Cyber Hide']
        rares = ['Quantum Ore', 'Stellar Gems', 'Void Essence']
        epics = ['Ancient Alien Relic', 'Nano-Fabric']
        p_common = 0.7
        p_rare = 0.2 if self.monster.template.level >= 4 else 0.1
        p_epic = 0.1 if self.monster.template.level >= 8 else 0.02
        if random.random() < p_common:
            loot.append({'name': random.choice(commons), 'quantity': random.randint(1, 3)})
        if random.random() < p_rare:
            loot.append({'name': random.choice(rares), 'quantity': 1})
        if random.random() < p_epic:
            loot.append({'name': random.choice(epics), 'quantity': 1})
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
            # Character loses; set to 1 HP and schedule respawn cooldown
            try:
                self.character.current_hp = 1
                self.character.downed_at = timezone.now()
                self.character.respawn_available_at = self.character.downed_at + timedelta(seconds=15)
            except Exception:
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
# FLAG/TERRITORY SYSTEM (PK-style minimal core)
# ===============================

class TerritoryFlag(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        UNDER_ATTACK = 'under_attack', 'Under Attack'
        CAPTURABLE = 'capturable', 'Capturable'
        DESTROYED = 'destroyed', 'Destroyed'

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flags')
    name = models.CharField(max_length=64, blank=True, default='')
    lat = models.FloatField(db_index=True)
    lon = models.FloatField(db_index=True)
    # Hex occupancy (axial coordinates); optional for legacy flags
    hex_q = models.IntegerField(null=True, blank=True, db_index=True)
    hex_r = models.IntegerField(null=True, blank=True, db_index=True)
    level = models.PositiveSmallIntegerField(default=1)
    hp_current = models.PositiveIntegerField(default=100)
    hp_max = models.PositiveIntegerField(default=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    # Privacy: when true, only owner can jump to this flag
    is_private = models.BooleanField(default=False)

    uncollected_balance = models.BigIntegerField(default=0)
    income_per_hour = models.IntegerField(default=10)
    upkeep_per_day = models.IntegerField(default=5)

    last_income_at = models.DateTimeField(auto_now_add=True)
    last_upkeep_at = models.DateTimeField(auto_now_add=True)
    capture_window_ends_at = models.DateTimeField(null=True, blank=True)
    protection_ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'rpg_territory_flags'
        indexes = [
            models.Index(fields=['lat', 'lon']),
        ]
        unique_together = (
            ('hex_q', 'hex_r'),
        )

    def __str__(self):
        return f"Flag {self.name or str(self.id)[:8]} L{self.level} ({self.lat:.4f},{self.lon:.4f})"


class FlagAttack(BaseModel):
    flag = models.ForeignKey(TerritoryFlag, on_delete=models.CASCADE, related_name='attacks')
    attacker = models.ForeignKey(User, on_delete=models.CASCADE)
    damage = models.IntegerField(default=0)
    lat = models.FloatField()
    lon = models.FloatField()

    class Meta:
        db_table = 'rpg_flag_attacks'


class FlagLedger(BaseModel):
    class EntryType(models.TextChoices):
        INCOME = 'income', 'Income'
        UPKEEP = 'upkeep', 'Upkeep'
        COLLECT = 'collect', 'Collect'
        ADJUST = 'adjust', 'Adjust'

    flag = models.ForeignKey(TerritoryFlag, on_delete=models.CASCADE, related_name='ledger')
    entry_type = models.CharField(max_length=16, choices=EntryType.choices)
    amount = models.BigIntegerField(default=0)
    notes = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        db_table = 'rpg_flag_ledger'


class FlagRun(BaseModel):
    """Per-player per-flag run: defeat N NPCs inside the flag radius to clear it.
    New runs can be started again even after clearing.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cleared', 'Cleared'),
        ('abandoned', 'Abandoned'),
    ]

    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='flag_runs')
    flag = models.ForeignKey(TerritoryFlag, on_delete=models.CASCADE, related_name='runs')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='active')

    # Goals and progress
    target_count = models.PositiveIntegerField(default=5)
    defeated_count = models.PositiveIntegerField(default=0)

    # Track live monsters spawned for this run so we can update progress on defeat
    active_monster_ids = models.JSONField(default=list)

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    cleared_at = models.DateTimeField(null=True, blank=True)
    last_progress_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rpg_flag_runs'
        indexes = [
            models.Index(fields=['character', 'flag', 'status']),
        ]

    def __str__(self):
        return f"Run {str(self.id)[:8]} {self.character.name} @ {self.flag.name or str(self.flag.id)[:6]} ({self.status})"

    @property
    def remaining(self) -> int:
        return max(0, int(self.target_count) - int(self.defeated_count))


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
        ('tree', 'Neon Tree'),  # Neon wood + Energy Berries
        ('iron_mine', 'Plasma Mine'),  # Plasma Stone + Quantum Ore
        ('gold_mine', 'Stellar Crystal Vein'),  # Stellar Gems + Void Essence
        ('stone_quarry', 'Alloy Quarry'),  # Themed stone equivalent
        ('herb_patch', 'Mutant Herb Cluster'),  # Mutant Herbs + Energy Berries
        ('ruins', 'Ancient Alien Ruins'),  # Rare items
        ('cave', 'Void-Touched Cave'),  # Various minerals/essence
        ('well', 'Hydration Nexus'),  # Food/water analogue
        ('farm', 'Biofarm'),  # Food analogue
        ('berry_bush', 'Energy Berry Bush'),  # Energy Berries for healing
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
    # Optional structured drop pool for harvest (list of {item, quantity})
    drop_pool = models.JSONField(default=list)
    
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
        """Calculate harvest rewards based on resource and character level.
        Themed: if drop_pool present, honor entry prob; else themed by resource type.
        """
        level_multiplier = 1 + (self.level - 1) * 0.3
        character_multiplier = 1 + (character_level - 1) * 0.1
        experience = int(self.base_experience * level_multiplier * character_multiplier)
        rewards = { 'experience': experience, 'items': [] }

        pool = list(getattr(self, 'drop_pool', []) or [])
        if pool:
            items = []
            for entry in pool:
                try:
                    name = entry.get('item') or entry.get('name')
                    qty = int(entry.get('quantity', 1))
                    prob = float(entry.get('prob', 0.5))
                except Exception:
                    name, qty, prob = None, 0, 0.0
                if not name or qty <= 0:
                    continue
                if random.random() < max(0.0, min(1.0, prob)):
                    items.append({'name': name, 'quantity': qty})
            rewards['items'] = items
            return rewards

        # Themed resource-specific rewards
        rt = self.resource_type
        if rt == 'tree':  # Neon Tree
            rewards['items'] = [
                {'name': 'Neon Wood', 'quantity': random.randint(1, 3)},
                {'name': 'Energy Berries', 'quantity': random.randint(0, 2)}
            ]
        elif rt == 'stone_quarry':  # Alloy Quarry
            rewards['items'] = [ {'name': 'Plasma Stone', 'quantity': random.randint(2, 4)} ]
        elif rt in ('farm','well'):
            rewards['items'] = [ {'name': 'food', 'quantity': random.randint(1, 3)} ]
        elif rt in ('berry_bush','herb_patch'):
            if rt == 'berry_bush':
                rewards['items'] = [ {'name': 'Energy Berries', 'quantity': random.randint(2, 5)} ]
            else:
                rewards['items'] = [ {'name': 'Mutant Herbs', 'quantity': random.randint(2, 5)} ]
        elif rt == 'gold_mine':  # Stellar Crystal Vein
            rewards['items'] = [ {'name': 'Stellar Gems', 'quantity': random.randint(1, 2)}, {'name': 'Void Essence', 'quantity': random.randint(0, 1)} ]
            rewards['gold'] = random.randint(10, 30)
        elif rt == 'iron_mine':  # Plasma Mine
            rewards['items'] = [ {'name': 'Plasma Stone', 'quantity': random.randint(1, 3)}, {'name': 'Quantum Ore', 'quantity': random.randint(0, 2)} ]
        elif rt == 'cave':  # Void-Touched Cave
            tmp = [ {'name': 'Plasma Stone', 'quantity': random.randint(1, 2)}, {'name': 'Quantum Ore', 'quantity': random.randint(0, 1)} ]
            if random.random() < 0.1:
                tmp.append({'name': 'Void Essence', 'quantity': 1})
            rewards['items'] = [i for i in tmp if i['quantity'] > 0]
        elif rt == 'ruins':  # Ancient Alien Ruins
            rewards['items'] = [ {'name': 'Ancient Alien Relic', 'quantity': 1} ]
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


class HealingClaim(BaseModel):
    """Exclusive healing claim on a ResourceNode within proximity.
    Grants 5 HP/sec up to 30 seconds while the claimant remains within 5 meters.
    """
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='healing_claims')
    resource = models.ForeignKey(ResourceNode, on_delete=models.CASCADE, related_name='healing_claims')
    active = models.BooleanField(default=True)

    started_at = models.DateTimeField(auto_now_add=True)
    last_tick_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'rpg_healing_claims'
        indexes = [
            models.Index(fields=['resource', 'active']),
            models.Index(fields=['character', 'active']),
        ]

    def __str__(self):
        return f"HealClaim {str(self.id)[:8]} {self.character.name} @ {self.resource.get_resource_type_display()} ({'active' if self.active else 'ended'})"


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


# Import building models to register them with Django
from .building_models import FlagColor
# Flag system models removed
