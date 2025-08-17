"""
Respawn dead animals near their original habitats
This maintains the habitat-based animal distribution over time
"""
from django.core.management.base import BaseCommand
from main.models import MonsterTemplate, Monster, ResourceNode
import random
import math


class Command(BaseCommand):
    help = 'Respawn dead animals near appropriate habitats to maintain ecosystem'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-interval',
            type=int,
            default=30,
            help='Minutes since death before respawn is allowed (default: 30)'
        )
        parser.add_argument(
            '--max-per-habitat',
            type=int,
            default=2,
            help='Maximum animals per habitat location (default: 2)'
        )
        parser.add_argument(
            '--spawn-distance',
            type=float,
            default=75.0,
            help='Distance from habitat to spawn animals (meters, default: 75)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be respawned without creating animals'
        )

    def handle(self, *args, **options):
        check_interval = options['check_interval']
        max_per_habitat = options['max_per_habitat']
        spawn_distance = options['spawn_distance']
        dry_run = options['dry_run']

        # Animal habitat mappings (same as in spawn_animals_from_habitats)
        animal_habitats = {
            'Forest Wolf': ['tree', 'herb_patch'],
            'Cave Bear': ['cave', 'stone_quarry'],
            'Rabbit': ['berry_bush', 'farm', 'herb_patch', 'well'],
        }

        # Get animal templates
        animal_templates = {}
        for animal_name in animal_habitats.keys():
            try:
                template = MonsterTemplate.objects.get(name=animal_name)
                animal_templates[animal_name] = template
            except MonsterTemplate.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Animal template '{animal_name}' not found")
                )

        if not animal_templates:
            self.stdout.write(self.style.ERROR("No animal templates found"))
            return

        respawned_animals = []
        
        # Process each animal type
        for animal_name, habitat_types in animal_habitats.items():
            if animal_name not in animal_templates:
                continue

            template = animal_templates[animal_name]
            
            # Find all habitat nodes for this animal
            habitat_nodes = ResourceNode.objects.filter(
                resource_type__in=habitat_types
            )

            if not habitat_nodes:
                continue

            self.stdout.write(f"\nChecking {animal_name} habitats...")

            # For each habitat, check if it needs more animals
            for habitat in habitat_nodes:
                # Count current alive animals near this habitat
                current_animals = self.count_animals_near_habitat(
                    habitat, animal_name, spawn_distance
                )

                # Calculate how many more animals this habitat can support
                animals_needed = max_per_habitat - current_animals

                if animals_needed <= 0:
                    continue  # Habitat is at capacity

                # Try to respawn animals near this habitat
                for _ in range(animals_needed):
                    # Check if there are any dead animals that can respawn
                    if self.should_respawn_animal(template, check_interval):
                        # Generate position near habitat
                        lat, lon = self.generate_nearby_position(
                            habitat.lat, habitat.lon, spawn_distance
                        )

                        if dry_run:
                            respawned_animals.append({
                                'name': animal_name,
                                'habitat': habitat.get_resource_type_display(),
                                'lat': lat,
                                'lon': lon,
                                'reason': f'Maintaining {current_animals}/{max_per_habitat} population'
                            })
                        else:
                            try:
                                monster = Monster.objects.create(
                                    template=template,
                                    lat=lat,
                                    lon=lon,
                                    current_hp=template.base_hp,
                                    max_hp=template.base_hp,
                                    is_alive=True
                                )
                                
                                respawned_animals.append({
                                    'name': animal_name,
                                    'habitat': habitat.get_resource_type_display(),
                                    'lat': lat,
                                    'lon': lon,
                                    'distance': self.calculate_distance(
                                        lat, lon, habitat.lat, habitat.lon
                                    )
                                })
                            except Exception as e:
                                self.stdout.write(
                                    self.style.ERROR(f"Failed to respawn {animal_name}: {e}")
                                )

        # Show results
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Would respawn {len(respawned_animals)} animals (dry run)')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Respawned {len(respawned_animals)} animals!')
            )

        # Summary
        if respawned_animals:
            animal_summary = {}
            for animal in respawned_animals:
                name = animal['name']
                if name not in animal_summary:
                    animal_summary[name] = 0
                animal_summary[name] += 1

            self.stdout.write("\nRespawn Summary:")
            for animal_name, count in animal_summary.items():
                self.stdout.write(f"  {animal_name}: {count}")

            # Show examples
            self.stdout.write("\nRespawned near habitats:")
            for animal in respawned_animals[:5]:  # Show first 5
                distance_info = ""
                if 'distance' in animal:
                    distance_info = f" ({animal['distance']:.1f}m from habitat)"
                elif 'reason' in animal:
                    distance_info = f" ({animal['reason']})"
                
                self.stdout.write(
                    f"  {animal['name']} near {animal['habitat']} at "
                    f"({animal['lat']:.6f}, {animal['lon']:.6f}){distance_info}"
                )
            
            if len(respawned_animals) > 5:
                self.stdout.write(f"  ... and {len(respawned_animals) - 5} more")

        # Show current totals
        if not dry_run:
            total_animals = Monster.objects.filter(
                template__name__in=list(animal_templates.keys()),
                is_alive=True
            ).count()
            self.stdout.write(f"\nTotal habitat animals now alive: {total_animals}")
        
        if not respawned_animals:
            self.stdout.write("No animals needed respawning - habitats are well populated!")

    def count_animals_near_habitat(self, habitat, animal_name, max_distance):
        """Count alive animals of specific type near a habitat"""
        count = 0
        for animal in Monster.objects.filter(template__name=animal_name, is_alive=True):
            distance = self.calculate_distance(
                animal.lat, animal.lon, habitat.lat, habitat.lon
            )
            if distance <= max_distance:
                count += 1
        return count

    def should_respawn_animal(self, template, check_interval_minutes):
        """Check if it's time to respawn this type of animal"""
        from django.utils import timezone
        from datetime import timedelta
        
        # For simplicity, we'll just check if there's room for more of this animal type
        # In a real system, you might track individual death times
        total_alive = Monster.objects.filter(template=template, is_alive=True).count()
        
        # Allow respawning if population is below a reasonable level
        # This is a simple population control mechanism
        max_population = 15  # Adjust based on your game balance
        return total_alive < max_population

    def generate_nearby_position(self, center_lat, center_lon, max_distance_meters):
        """Generate a random position within max_distance_meters of center point"""
        # Convert meters to approximate degrees
        max_distance_degrees = max_distance_meters / 111000.0
        
        # Generate random angle and distance
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(max_distance_degrees * 0.3, max_distance_degrees)
        
        # Calculate new position
        lat_offset = distance * math.cos(angle)
        lon_offset = distance * math.sin(angle) / math.cos(math.radians(center_lat))
        
        return center_lat + lat_offset, center_lon + lon_offset

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in meters"""
        R = 6371000  # Earth radius in meters
        lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
        delta_lat, delta_lon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * 
             math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
