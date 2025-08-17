"""
Management command to spawn NPCs around the world for PM-style gameplay
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import NPC
import random
from decimal import Decimal


class Command(BaseCommand):
    help = 'Spawn NPCs around the world for PM-style gameplay'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Number of NPCs to spawn (default: 50)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing NPCs before spawning new ones'
        )
        parser.add_argument(
            '--area-lat',
            type=float,
            default=40.7128,  # NYC default
            help='Central latitude for spawn area'
        )
        parser.add_argument(
            '--area-lon',
            type=float,
            default=-74.0060,  # NYC default
            help='Central longitude for spawn area'
        )
        parser.add_argument(
            '--radius',
            type=float,
            default=0.1,  # ~10km radius
            help='Spawn radius in decimal degrees (~0.01 = 1km)'
        )

    def handle(self, *args, **options):
        count = options['count']
        clear_existing = options['clear']
        center_lat = options['area_lat']
        center_lon = options['area_lon']
        radius = options['radius']

        if clear_existing:
            deleted_count = NPC.objects.all().delete()[0]
            self.stdout.write(
                self.style.WARNING(f'Deleted {deleted_count} existing NPCs')
            )

        # NPC types with their characteristics
        npc_types = {
            'bandit': {
                'names': ['Scarface Jake', 'Mad Dog Mike', 'Vicious Vince', 'Brutal Bruno', 'Crazy Carl'],
                'level_range': (1, 15),
                'base_hp': 50,
                'base_attack': 15,
                'base_defense': 8,
                'base_money': 200,
                'base_xp': 50
            },
            'soldier': {
                'names': ['Sergeant Stone', 'Captain Kane', 'Major Martinez', 'Colonel Cross', 'General Garcia'],
                'level_range': (8, 25),
                'base_hp': 80,
                'base_attack': 25,
                'base_defense': 20,
                'base_money': 500,
                'base_xp': 100
            },
            'mercenary': {
                'names': ['Blade Walker', 'Steel Simmons', 'Iron Irving', 'Chrome Charlie', 'Titanium Tony'],
                'level_range': (12, 30),
                'base_hp': 100,
                'base_attack': 35,
                'base_defense': 25,
                'base_money': 800,
                'base_xp': 150
            },
            'guard': {
                'names': ['Watchman Will', 'Guardian Gary', 'Protector Pete', 'Defender Dan', 'Shield Shaw'],
                'level_range': (5, 20),
                'base_hp': 70,
                'base_attack': 20,
                'base_defense': 30,
                'base_money': 350,
                'base_xp': 75
            },
            'assassin': {
                'names': ['Shadow Sam', 'Phantom Phil', 'Ghost George', 'Wraith Walter', 'Specter Steve'],
                'level_range': (15, 35),
                'base_hp': 60,
                'base_attack': 50,
                'base_defense': 15,
                'base_money': 1200,
                'base_xp': 200
            },
            'rogue': {
                'names': ['Sly Smith', 'Sneaky Sean', 'Crafty Chris', 'Cunning Carl', 'Shifty Shane'],
                'level_range': (3, 18),
                'base_hp': 45,
                'base_attack': 30,
                'base_defense': 12,
                'base_money': 400,
                'base_xp': 80
            },
            'knight': {
                'names': ['Sir Galahad', 'Sir Lancelot', 'Sir Percival', 'Sir Gareth', 'Sir Tristan'],
                'level_range': (20, 40),
                'base_hp': 120,
                'base_attack': 40,
                'base_defense': 35,
                'base_money': 1500,
                'base_xp': 300
            }
        }

        npcs_created = []

        for i in range(count):
            # Choose random NPC type
            npc_type = random.choice(list(npc_types.keys()))
            npc_config = npc_types[npc_type]

            # Generate random position within radius
            lat_offset = random.uniform(-radius, radius)
            lon_offset = random.uniform(-radius, radius)
            lat = center_lat + lat_offset
            lon = center_lon + lon_offset

            # Generate level within type's range
            level = random.randint(*npc_config['level_range'])

            # Calculate stats based on level
            level_multiplier = 1 + (level - 1) * 0.1  # 10% increase per level
            
            max_hp = int(npc_config['base_hp'] * level_multiplier)
            attack_power = int(npc_config['base_attack'] * level_multiplier)
            defense_rating = int(npc_config['base_defense'] * level_multiplier)
            money_reward = int(npc_config['base_money'] * level_multiplier)
            xp_reward = int(npc_config['base_xp'] * level_multiplier)

            # Choose random name
            name = random.choice(npc_config['names'])
            
            # Add level suffix for higher level NPCs
            if level >= 20:
                name += " the Elite"
            elif level >= 10:
                name += " the Veteran"

            # Create NPC
            npc = NPC.objects.create(
                name=name,
                npc_type=npc_type,
                level=level,
                lat=lat,  # No need for Decimal conversion, model uses FloatField
                lon=lon,
                max_hp=max_hp,
                hp=max_hp,  # Field is called 'hp' not 'current_hp'
                strength=attack_power,  # Field is called 'strength' not 'attack_power'
                defense=defense_rating,  # Field is called 'defense' not 'defense_rating'
                base_gold_reward=money_reward,  # Field is called 'base_gold_reward'
                base_experience_reward=xp_reward,  # Field is called 'base_experience_reward'
                respawn_time=random.randint(1800, 7200)  # 30-120 minutes in seconds
            )

            npcs_created.append({
                'name': npc.name,
                'type': npc.npc_type,
                'level': npc.level,
                'lat': float(npc.lat),
                'lon': float(npc.lon),
                'hp': npc.max_hp,
                'attack': npc.strength,
                'defense': npc.defense
            })

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {len(npcs_created)} NPCs!')
        )

        # Show summary by type
        type_summary = {}
        for npc in npcs_created:
            npc_type = npc['type']
            if npc_type not in type_summary:
                type_summary[npc_type] = 0
            type_summary[npc_type] += 1

        self.stdout.write("\nNPC Summary:")
        for npc_type, count in type_summary.items():
            self.stdout.write(f"  {npc_type.capitalize()}: {count}")

        # Show some example NPCs
        self.stdout.write("\nExample NPCs created:")
        for npc in npcs_created[:5]:  # Show first 5
            self.stdout.write(
                f"  {npc['name']} (Lv.{npc['level']} {npc['type'].capitalize()}) - "
                f"HP:{npc['hp']}, ATK:{npc['attack']}, DEF:{npc['defense']} - "
                f"({npc['lat']:.6f}, {npc['lon']:.6f})"
            )

        if len(npcs_created) > 5:
            self.stdout.write(f"  ... and {len(npcs_created) - 5} more")
