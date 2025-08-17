"""
Management command to spawn resource nodes around the world for PM-style gameplay
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import ResourceNode
import random
from decimal import Decimal


class Command(BaseCommand):
    help = 'Spawn resource nodes around the world for PM-style gameplay'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=100,
            help='Number of resource nodes to spawn (default: 100)'
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
            deleted_count = ResourceNode.objects.all().delete()[0]
            self.stdout.write(
                self.style.WARNING(f'Deleted {deleted_count} existing resource nodes')
            )

        # Resource types with their characteristics
        resource_types = {
            'tree': {
                'weight': 30,  # Most common
                'level_range': (1, 10),
                'base_quantity': 5,
                'quantity_variance': 3,
                'respawn_time_range': (20, 60)  # 20-60 minutes
            },
            'iron_mine': {
                'weight': 15,
                'level_range': (3, 15),
                'base_quantity': 3,
                'quantity_variance': 2,
                'respawn_time_range': (45, 120)  # 45-120 minutes
            },
            'gold_mine': {
                'weight': 5,  # Rare
                'level_range': (5, 20),
                'base_quantity': 2,
                'quantity_variance': 1,
                'respawn_time_range': (90, 180)  # 90-180 minutes
            },
            'stone_quarry': {
                'weight': 20,
                'level_range': (1, 12),
                'base_quantity': 4,
                'quantity_variance': 2,
                'respawn_time_range': (30, 90)  # 30-90 minutes
            },
            'herb_patch': {
                'weight': 15,
                'level_range': (1, 8),
                'base_quantity': 3,
                'quantity_variance': 2,
                'respawn_time_range': (15, 45)  # 15-45 minutes
            },
            'ruins': {
                'weight': 3,  # Very rare
                'level_range': (10, 25),
                'base_quantity': 1,
                'quantity_variance': 1,
                'respawn_time_range': (180, 360)  # 3-6 hours
            },
            'cave': {
                'weight': 8,
                'level_range': (5, 18),
                'base_quantity': 2,
                'quantity_variance': 1,
                'respawn_time_range': (60, 150)  # 1-2.5 hours
            },
            'well': {
                'weight': 4,  # Uncommon
                'level_range': (1, 5),
                'base_quantity': 10,
                'quantity_variance': 5,
                'respawn_time_range': (10, 30)  # 10-30 minutes
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

            # Create resource node
            resource = ResourceNode.objects.create(
                resource_type=resource_type,
                level=level,
                lat=Decimal(str(lat)),
                lon=Decimal(str(lon)),
                quantity=quantity,
                max_quantity=max_quantity,
                respawn_time=respawn_time
            )

            resources_created.append({
                'type': resource.resource_type,
                'level': resource.level,
                'lat': float(resource.lat),
                'lon': float(resource.lon),
                'quantity': resource.quantity,
                'max_quantity': resource.max_quantity,
                'respawn_time': resource.respawn_time
            })

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
                f"Respawn:{resource['respawn_time']}min - "
                f"({resource['lat']:.6f}, {resource['lon']:.6f})"
            )

        # Show rarity distribution
        rare_resources = [r for r in resources_created if r['type'] in ['gold_mine', 'ruins']]
        common_resources = [r for r in resources_created if r['type'] in ['tree', 'stone_quarry']]
        
        self.stdout.write(f"\nRarity Distribution:")
        self.stdout.write(f"  Common resources (trees, stone): {len(common_resources)}")
        self.stdout.write(f"  Rare resources (gold, ruins): {len(rare_resources)}")
        
        if rare_resources:
            self.stdout.write(f"\nRare resource locations:")
            for rare in rare_resources[:3]:  # Show first 3 rare ones
                self.stdout.write(
                    f"  {rare['type'].replace('_', ' ').title()} Lv.{rare['level']} at "
                    f"({rare['lat']:.6f}, {rare['lon']:.6f})"
                )
