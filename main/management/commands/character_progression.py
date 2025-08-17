"""
Management command for character progression calculations and updates
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from main.models import Character, Skill
import math


class Command(BaseCommand):
    help = 'Manage character progression, levels, and skill calculations'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--calculate-levels',
            action='store_true',
            help='Calculate and update character levels based on experience'
        )
        parser.add_argument(
            '--recalculate-stats',
            action='store_true',
            help='Recalculate all character combat stats'
        )
        parser.add_argument(
            '--initialize-skills',
            action='store_true',
            help='Initialize missing character skills'
        )
        parser.add_argument(
            '--character-id',
            type=int,
            help='Process specific character ID only'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
    
    def handle(self, *args, **options):
        """Execute character progression tasks"""
        
        if not any([
            options['calculate_levels'], 
            options['recalculate_stats'], 
            options['initialize_skills']
        ]):
            self.stdout.write(
                self.style.WARNING('No progression tasks specified. Use --help for options.')
            )
            return
        
        # Get characters to process
        if options['character_id']:
            characters = Character.objects.filter(id=options['character_id'])
            if not characters.exists():
                self.stdout.write(
                    self.style.ERROR(f"Character with ID {options['character_id']} not found")
                )
                return
        else:
            characters = Character.objects.all()
        
        self.stdout.write(f"Processing {characters.count()} characters...")
        
        if options['calculate_levels']:
            self.calculate_levels(characters, options['dry_run'])
        
        if options['initialize_skills']:
            self.initialize_skills(characters, options['dry_run'])
        
        if options['recalculate_stats']:
            self.recalculate_stats(characters, options['dry_run'])
        
        self.stdout.write(
            self.style.SUCCESS('Character progression processing completed!')
        )
    
    def calculate_levels(self, characters, dry_run=False):
        """Calculate and update character levels based on experience"""
        self.stdout.write("Calculating character levels...")
        
        updated_count = 0
        
        for character in characters:
            old_level = character.level
            new_level = self.experience_to_level(character.experience)
            
            if new_level != old_level:
                if dry_run:
                    self.stdout.write(
                        f"Character {character.name} would level from {old_level} to {new_level}"
                    )
                else:
                    try:
                        with transaction.atomic():
                            # Calculate skill points gained
                            skill_points_gained = (new_level - old_level) * 2
                            
                            character.level = new_level
                            character.available_skill_points += skill_points_gained
                            character.save()
                            
                            self.stdout.write(
                                f"Character {character.name} leveled from {old_level} to {new_level} "
                                f"(+{skill_points_gained} skill points)"
                            )
                            updated_count += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Failed to update {character.name}: {e}")
                        )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Updated levels for {updated_count} characters")
            )
    
    def initialize_skills(self, characters, dry_run=False):
        """Initialize basic skills for characters"""
        self.stdout.write("Initializing character skills...")
        
        basic_skills = [
            ('Combat', 'combat'),
            ('Magic', 'magic'),
            ('Crafting', 'crafting'),
            ('Gathering', 'gathering'),
            ('Social', 'social')
        ]
        
        created_count = 0
        
        for character in characters:
            existing_skill_names = set(
                character.skills.values_list('name', flat=True)
            )
            
            for skill_name, skill_type in basic_skills:
                if skill_name not in existing_skill_names:
                    if dry_run:
                        self.stdout.write(
                            f"Would create {skill_name} skill for {character.name}"
                        )
                    else:
                        try:
                            Skill.objects.create(
                                character=character,
                                name=skill_name,
                                skill_type=skill_type,
                                level=1,
                                experience=0
                            )
                            created_count += 1
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Failed to create {skill_name} for {character.name}: {e}"
                                )
                            )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Created {created_count} character skills")
            )
    
    def recalculate_stats(self, characters, dry_run=False):
        """Recalculate character combat stats"""
        self.stdout.write("Recalculating character stats...")
        
        updated_count = 0
        
        for character in characters:
            if dry_run:
                self.stdout.write(f"Would recalculate stats for {character.name}")
            else:
                try:
                    with transaction.atomic():
                        # Calculate base stats
                        old_hp = character.current_health
                        old_max_hp = character.max_health
                        
                        # Base health calculation
                        character.max_health = self.calculate_max_health(character)
                        
                        # Maintain health percentage if possible
                        if old_max_hp > 0:
                            health_percentage = old_hp / old_max_hp
                            character.current_health = min(
                                int(character.max_health * health_percentage),
                                character.max_health
                            )
                        else:
                            character.current_health = character.max_health
                        
                        # Calculate combat stats
                        character.attack_power = self.calculate_attack_power(character)
                        character.defense = self.calculate_defense(character)
                        character.accuracy = self.calculate_accuracy(character)
                        character.evasion = self.calculate_evasion(character)
                        character.critical_chance = self.calculate_critical_chance(character)
                        
                        character.save()
                        
                        self.stdout.write(f"Updated stats for {character.name}")
                        updated_count += 1
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to update stats for {character.name}: {e}")
                    )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Updated stats for {updated_count} characters")
            )
    
    def experience_to_level(self, experience):
        """Convert experience points to character level"""
        # Exponential level curve: level = floor(sqrt(exp/100)) + 1
        if experience < 0:
            return 1
        return min(int(math.sqrt(experience / 100)) + 1, 100)  # Cap at level 100
    
    def calculate_max_health(self, character):
        """Calculate character's maximum health"""
        base_health = 100
        level_bonus = character.level * 10
        constitution_bonus = character.constitution * 5
        
        # Get health-related skill bonuses
        vitality_skill = character.skills.filter(name='Vitality').first()
        vitality_bonus = vitality_skill.level * 2 if vitality_skill else 0
        
        return base_health + level_bonus + constitution_bonus + vitality_bonus
    
    def calculate_attack_power(self, character):
        """Calculate character's attack power"""
        base_attack = 10
        level_bonus = character.level * 2
        strength_bonus = character.strength * 3
        
        # Get combat skill bonuses
        combat_skill = character.skills.filter(name='Combat').first()
        combat_bonus = combat_skill.level * 1.5 if combat_skill else 0
        
        return int(base_attack + level_bonus + strength_bonus + combat_bonus)
    
    def calculate_defense(self, character):
        """Calculate character's defense"""
        base_defense = 5
        level_bonus = character.level
        constitution_bonus = character.constitution * 2
        
        # Get defense skill bonuses
        defense_skill = character.skills.filter(name='Defense').first()
        defense_bonus = defense_skill.level if defense_skill else 0
        
        return int(base_defense + level_bonus + constitution_bonus + defense_bonus)
    
    def calculate_accuracy(self, character):
        """Calculate character's accuracy"""
        base_accuracy = 75
        dexterity_bonus = character.dexterity * 2
        
        # Get precision skill bonuses
        precision_skill = character.skills.filter(name='Precision').first()
        precision_bonus = precision_skill.level if precision_skill else 0
        
        return min(base_accuracy + dexterity_bonus + precision_bonus, 95)  # Cap at 95%
    
    def calculate_evasion(self, character):
        """Calculate character's evasion"""
        base_evasion = 10
        dexterity_bonus = character.dexterity
        
        # Get evasion skill bonuses
        evasion_skill = character.skills.filter(name='Evasion').first()
        evasion_bonus = evasion_skill.level if evasion_skill else 0
        
        return min(base_evasion + dexterity_bonus + evasion_bonus, 75)  # Cap at 75%
    
    def calculate_critical_chance(self, character):
        """Calculate character's critical hit chance"""
        base_crit = 5
        dexterity_bonus = character.dexterity * 0.5
        
        # Get critical skill bonuses
        critical_skill = character.skills.filter(name='Critical Strike').first()
        critical_bonus = critical_skill.level * 0.5 if critical_skill else 0
        
        return min(base_crit + dexterity_bonus + critical_bonus, 50)  # Cap at 50%
