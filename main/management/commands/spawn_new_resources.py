"""
Management command to spawn resource nodes for the new RPG resource system
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import ResourceNode
import random
from decimal import Decimal


class Command(BaseCommand):
    help = 'Spawn resource nodes for the new RPG resource collection system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Number of resource nodes to spawn (default: 50)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing resource nodes before spawning new ones'
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
            default=0.05,  # ~5km radius
            help='Spawn radius in decimal degrees (~0.01 = 1km)'
        )

    def handle(self, *args, **options):
        count = options['count']
        clear_existing = options['clear']
        center_lat = options['area_lat']
        center_lon = options['area_lon']
        radius = options['radius']

        if clear_existing:
            deleted_count = ResourceNode.objects.all().delete()[0]
            self.stdout.write(
                self.style.WARNING(f'Deleted {deleted_count} existing resource nodes')
            )

        # Resource types with their characteristics for the new system
        resource_types = {
            'tree': {
                'weight': 25,  # Common
                'level_range': (1, 8),
                'base_quantity': 5,
                'quantity_variance': 3,
                'respawn_time_range': (30, 60)  # 30-60 minutes
            },
            'berry_bush': {
                'weight': 15,  # Focus on healing berries
                'level_range': (1, 5),
                'base_quantity': 4,
                'quantity_variance': 2,
                'respawn_time_range': (20, 40)  # 20-40 minutes
            },
            'stone_quarry': {
                'weight': 20,
                'level_range': (1, 10),
                'base_quantity': 6,
                'quantity_variance': 3,
                'respawn_time_range': (40, 80)  # 40-80 minutes
            },
            'farm': {
                'weight': 15,  # Food source
                'level_range': (1, 6),
                'base_quantity': 4,
                'quantity_variance': 2,
                'respawn_time_range': (25, 50)  # 25-50 minutes
            },
            'iron_mine': {
                'weight': 10,
                'level_range': (3, 12),
                'base_quantity': 3,
                'quantity_variance': 2,
                'respawn_time_range': (60, 120)  # 60-120 minutes
            },
            'gold_mine': {
                'weight': 5,  # Rare
                'level_range': (5, 15),
                'base_quantity': 2,
                'quantity_variance': 1,
                'respawn_time_range': (90, 180)  # 90-180 minutes
            },
            'herb_patch': {
                'weight': 8,  # Also provides berries
                'level_range': (2, 8),
                'base_quantity': 3,
                'quantity_variance': 2,
                'respawn_time_range': (30, 60)  # 30-60 minutes
            },
            'well': {
                'weight': 5,  # Water/food source
                'level_range': (1, 4),
                'base_quantity': 8,
                'quantity_variance': 4,
                'respawn_time_range': (15, 30)  # 15-30 minutes
            },
            'cave': {
                'weight': 4,  # Uncommon, mixed materials
                'level_range': (4, 12),
                'base_quantity': 2,
                'quantity_variance': 1,
                'respawn_time_range': (70, 140)  # 70-140 minutes
            },
            'ruins': {
                'weight': 2,  # Very rare
                'level_range': (8, 20),
                'base_quantity': 1,
                'quantity_variance': 1,
                'respawn_time_range': (180, 360)  # 3-6 hours
            }
        }

        # Create weighted list for random selection
        weighted_types = []
        for resource_type, config in resource_types.items():
            weighted_types.extend([resource_type] * config['weight'])

        resources_created = []

        for i in range(count):
            # Choose random resource type based on weights
            resource_type = random.choice(weighted_types)
            resource_config = resource_types[resource_type]

            # Generate random position within radius
            lat_offset = random.uniform(-radius, radius)
            lon_offset = random.uniform(-radius, radius)
            lat = center_lat + lat_offset
            lon = center_lon + lon_offset

            # Generate level within type's range
            level = random.randint(*resource_config['level_range'])

            # Calculate quantity based on level and variance
            base_qty = resource_config['base_quantity']
            variance = resource_config['quantity_variance']
            level_bonus = level // 3  # Bonus quantity every 3 levels
            
            quantity = base_qty + level_bonus + random.randint(-variance, variance)
            quantity = max(1, quantity)  # Ensure at least 1

            # Set max quantity (for respawning)
            max_quantity = quantity

            # Random respawn time within range
            respawn_time = random.randint(*resource_config['respawn_time_range'])

            # Calculate base experience based on level
            base_experience = 10 + (level * 2)

            # Create resource node
            try:
                resource = ResourceNode.objects.create(
                    resource_type=resource_type,
                    level=level,
                    lat=lat,
                    lon=lon,
                    quantity=quantity,
                    max_quantity=max_quantity,
                    respawn_time=respawn_time,
                    base_experience=base_experience
                )

                resources_created.append({
                    'type': resource.resource_type,
                    'level': resource.level,
                    'lat': float(resource.lat),
                    'lon': float(resource.lon),
                    'quantity': resource.quantity,
                    'max_quantity': resource.max_quantity,
                    'respawn_time': resource.respawn_time,
                    'base_experience': resource.base_experience
                })
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to create resource at ({lat:.6f}, {lon:.6f}): {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {len(resources_created)} resource nodes!')
        )

        # Show summary by type
        type_summary = {}
        for resource in resources_created:
            resource_type = resource['type']
            if resource_type not in type_summary:
                type_summary[resource_type] = 0
            type_summary[resource_type] += 1

        self.stdout.write("\nResource Summary:")
        for resource_type, count in type_summary.items():
            percentage = (count / len(resources_created)) * 100
            self.stdout.write(f"  {resource_type.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")

        # Show some example resources
        self.stdout.write("\nExample resources created:")
        examples_by_type = {}
        for resource in resources_created:
            resource_type = resource['type']
            if resource_type not in examples_by_type:
                examples_by_type[resource_type] = resource

        for resource_type, resource in examples_by_type.items():
            self.stdout.write(
                f"  {resource['type'].replace('_', ' ').title()} (Lv.{resource['level']}) - "
                f"Qty:{resource['quantity']}/{resource['max_quantity']}, "
                f"XP:{resource['base_experience']}, "
                f"Respawn:{resource['respawn_time']}min - "
                f"({resource['lat']:.6f}, {resource['lon']:.6f})"
            )

        # Show healing resource distribution
        healing_resources = [r for r in resources_created if r['type'] in ['berry_bush', 'herb_patch', 'tree']]
        food_resources = [r for r in resources_created if r['type'] in ['farm', 'well']]
        
        self.stdout.write(f"\nHealing Resources:")
        self.stdout.write(f"  Berry sources (bushes, herbs, trees): {len(healing_resources)}")
        self.stdout.write(f"  Food sources (farms, wells): {len(food_resources)}")
        
        if healing_resources:
            self.stdout.write(f"\nBerry source locations (first 3):")
            for heal in healing_resources[:3]:
                self.stdout.write(
                    f"  {heal['type'].replace('_', ' ').title()} Lv.{heal['level']} at "
                    f"({heal['lat']:.6f}, {heal['lon']:.6f})"
                )

        self.stdout.write(f"\nTotal resources that can provide berries for healing: {len(healing_resources)}")
        self.stdout.write(
            self.style.SUCCESS(
                f"\nResource nodes have been spawned! Players can now collect wood, stone, food, "
                f"gold, and berries (for 25% healing) from these nodes."
            )
        )
