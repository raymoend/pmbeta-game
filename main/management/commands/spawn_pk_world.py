"""
Django Management Command to spawn PK world content
"""
from django.core.management.base import BaseCommand
from main.models import PKResource
import random
import math


class Command(BaseCommand):
    help = 'Spawn PK resources around the world for testing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=100,
            help='Number of resources to spawn (default: 100)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing resources before spawning new ones',
        )
    
    def handle(self, *args, **options):
        count = options['count']
        
        if options['clear']:
            self.stdout.write('Clearing existing resources...')
            PKResource.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Cleared existing resources'))
        
        # Spawn locations (same as player spawn points)
        spawn_locations = [
            (40.7589, -73.9851),  # New York
            (51.5074, -0.1278),   # London  
            (35.6762, 139.6503),  # Tokyo
            (37.7749, -122.4194), # San Francisco
        ]
        
        resources_created = []
        resource_types = ['tree', 'rock', 'mine', 'ruins']
        
        for _ in range(count):
            # Pick random spawn center
            center_lat, center_lon = random.choice(spawn_locations)
            
            # Random position within 5km radius
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, 0.05)  # ~5km in degrees
            
            resource_lat = center_lat + distance * math.cos(angle)
            resource_lon = center_lon + distance * math.sin(angle)
            
            # Random resource type
            resource_type = random.choice(resource_types)
            
            # Set yields based on type
            yields = {
                'tree': {
                    'lumber_yield': random.randint(15, 35),
                    'stone_yield': 0,
                    'ore_yield': 0,
                    'gold_yield': random.randint(2, 8),
                    'food_yield': 0
                },
                'rock': {
                    'lumber_yield': 0,
                    'stone_yield': random.randint(15, 25),
                    'ore_yield': random.randint(2, 8),
                    'gold_yield': random.randint(1, 5),
                    'food_yield': 0
                },
                'mine': {
                    'lumber_yield': 0,
                    'stone_yield': random.randint(3, 8),
                    'ore_yield': random.randint(10, 20),
                    'gold_yield': random.randint(5, 15),
                    'food_yield': 0
                },
                'ruins': {
                    'lumber_yield': random.randint(5, 15),
                    'stone_yield': random.randint(5, 15),
                    'ore_yield': random.randint(5, 15),
                    'gold_yield': random.randint(20, 60),
                    'food_yield': random.randint(10, 30)
                }
            }
            
            resource = PKResource.objects.create(
                resource_type=resource_type,
                lat=resource_lat,
                lon=resource_lon,
                level=random.randint(1, 5),
                health=random.randint(80, 100),
                max_health=100,
                **yields[resource_type]
            )
            
            resources_created.append(resource)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Successfully spawned {len(resources_created)} resources around the world!'
            )
        )
        
        # Show breakdown by type
        by_type = {}
        for resource in resources_created:
            by_type[resource.resource_type] = by_type.get(resource.resource_type, 0) + 1
        
        self.stdout.write('\nResource breakdown:')
        for resource_type, count in by_type.items():
            self.stdout.write(f'  - {resource_type.title()}: {count}')
        
        # Show by location
        self.stdout.write('\nSpawn locations used:')
        for i, (lat, lon) in enumerate(spawn_locations):
            nearby_count = sum(1 for r in resources_created 
                             if abs(r.lat - lat) < 0.05 and abs(r.lon - lon) < 0.05)
            location_names = ['New York', 'London', 'Tokyo', 'San Francisco']
            self.stdout.write(f'  - {location_names[i]}: ~{nearby_count} resources')
