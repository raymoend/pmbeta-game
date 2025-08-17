"""
Spawn animals from their natural habitat locations
Animals will spawn near appropriate resource nodes that represent their habitats
"""
from django.core.management.base import BaseCommand
from main.models import MonsterTemplate, Monster, ResourceNode
import random
import math


class Command(BaseCommand):
    help = 'Spawn animals near their natural habitats (resource nodes)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--animals-per-habitat',
            type=int,
            default=2,
            help='Average number of animals to spawn per habitat (default: 2)'
        )
        parser.add_argument(
            '--spawn-distance',
            type=float,
            default=100.0,
            help='Maximum distance from habitat to spawn animals (meters, default: 100)'
        )
        parser.add_argument(
            '--clear-animals',
            action='store_true',
            help='Remove all existing animal monsters first'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be spawned without creating monsters'
        )

    def handle(self, *args, **options):
        animals_per_habitat = options['animals_per_habitat']
        spawn_distance = options['spawn_distance']
        clear_animals = options['clear_animals']
        dry_run = options['dry_run']

        # Define animal-habitat relationships
        animal_habitats = {
            'Forest Wolf': ['tree', 'herb_patch'],  # Wolves near forests
            'Cave Bear': ['cave', 'stone_quarry'],  # Bears near caves and rocky areas
            'Rabbit': ['berry_bush', 'farm', 'herb_patch'],  # Rabbits near food sources
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
            self.stdout.write(
                self.style.ERROR("No animal templates found. Available templates:")
            )
            for template in MonsterTemplate.objects.all():
                self.stdout.write(f"  - {template.name}")
            return

        # Clear existing animals if requested
        if clear_animals:
            animal_names = list(animal_templates.keys())
            if not dry_run:
                deleted = Monster.objects.filter(
                    template__name__in=animal_names
                ).delete()[0]
                self.stdout.write(f"Removed {deleted} existing animal monsters")
            else:
                count = Monster.objects.filter(
                    template__name__in=animal_names
                ).count()
                self.stdout.write(f"Would remove {count} existing animal monsters")

        spawned_animals = []

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
                self.stdout.write(
                    f"No habitats found for {animal_name} (looking for: {habitat_types})"
                )
                continue

            self.stdout.write(
                f"\nSpawning {animal_name} near {len(habitat_nodes)} habitat(s): "
                f"{', '.join(habitat_types)}"
            )

            # Spawn animals near each habitat
            for habitat in habitat_nodes:
                # Random number of animals per habitat (0 to 2x average)
                num_animals = random.randint(0, animals_per_habitat * 2)
                
                for _ in range(num_animals):
                    # Generate random position near the habitat
                    lat, lon = self.generate_nearby_position(
                        habitat.lat, habitat.lon, spawn_distance
                    )

                    if dry_run:
                        spawned_animals.append({
                            'name': animal_name,
                            'level': template.level,
                            'habitat': habitat.get_resource_type_display(),
                            'lat': lat,
                            'lon': lon
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
                            
                            spawned_animals.append({
                                'name': animal_name,
                                'level': template.level,
                                'habitat': habitat.get_resource_type_display(),
                                'lat': lat,
                                'lon': lon,
                                'habitat_distance': self.calculate_distance(
                                    lat, lon, habitat.lat, habitat.lon
                                )
                            })
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"Failed to spawn {animal_name}: {e}")
                            )

        # Show results
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Would spawn {len(spawned_animals)} animals (dry run)')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully spawned {len(spawned_animals)} animals!')
            )

        # Summary by animal type
        animal_summary = {}
        for animal in spawned_animals:
            name = animal['name']
            if name not in animal_summary:
                animal_summary[name] = 0
            animal_summary[name] += 1

        self.stdout.write("\nAnimal Summary:")
        for animal_name, count in animal_summary.items():
            self.stdout.write(f"  {animal_name}: {count}")

        # Show examples of spawned animals
        if spawned_animals:
            self.stdout.write("\nExample spawns:")
            for animal in spawned_animals[:8]:  # Show first 8
                distance_info = ""
                if 'habitat_distance' in animal:
                    distance_info = f" ({animal['habitat_distance']:.1f}m from habitat)"
                
                self.stdout.write(
                    f"  {animal['name']} near {animal['habitat']} at "
                    f"({animal['lat']:.6f}, {animal['lon']:.6f}){distance_info}"
                )
            
            if len(spawned_animals) > 8:
                self.stdout.write(f"  ... and {len(spawned_animals) - 8} more")

        # Show current animal totals
        if not dry_run:
            total_animals = Monster.objects.filter(
                template__name__in=list(animal_templates.keys()),
                is_alive=True
            ).count()
            self.stdout.write(f"\nTotal animals alive in world: {total_animals}")

    def generate_nearby_position(self, center_lat, center_lon, max_distance_meters):
        """Generate a random position within max_distance_meters of center point"""
        # Convert meters to approximate degrees
        # Roughly 1 degree = 111,000 meters
        max_distance_degrees = max_distance_meters / 111000.0
        
        # Generate random angle and distance
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(0, max_distance_degrees)
        
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
