"""
Simple command to spawn monsters using the current RPG system
"""
from django.core.management.base import BaseCommand
from main.models import MonsterTemplate, Monster
import random


class Command(BaseCommand):
    help = 'Spawn monsters using the current RPG system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of monsters to spawn (default: 10)'
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
            default=0.02,  # ~2km radius
            help='Spawn radius in decimal degrees'
        )
        parser.add_argument(
            '--level-min',
            type=int,
            default=1,
            help='Minimum monster level'
        )
        parser.add_argument(
            '--level-max',
            type=int,
            default=10,
            help='Maximum monster level'
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Remove all existing dead monsters first'
        )

    def handle(self, *args, **options):
        count = options['count']
        center_lat = options['area_lat']
        center_lon = options['area_lon']
        radius = options['radius']
        level_min = options['level_min']
        level_max = options['level_max']

        # Clean up dead monsters if requested
        if options['cleanup']:
            dead_monsters = Monster.objects.filter(is_alive=False).delete()[0]
            self.stdout.write(f"Removed {dead_monsters} dead monsters")

        # Get available monster templates
        templates = MonsterTemplate.objects.filter(
            level__gte=level_min,
            level__lte=level_max
        )

        if not templates:
            self.stdout.write(
                self.style.ERROR(
                    f"No monster templates found for level range {level_min}-{level_max}"
                )
            )
            return

        self.stdout.write(f"Available templates: {[t.name for t in templates]}")

        monsters_created = []

        for i in range(count):
            # Random location within radius
            lat_offset = random.uniform(-radius, radius)
            lon_offset = random.uniform(-radius, radius)
            lat = center_lat + lat_offset
            lon = center_lon + lon_offset

            # Choose random template
            template = random.choice(templates)

            try:
                monster = Monster.objects.create(
                    template=template,
                    lat=lat,
                    lon=lon,
                    current_hp=template.base_hp,
                    max_hp=template.base_hp,
                    is_alive=True
                )
                
                monsters_created.append({
                    'name': monster.template.name,
                    'level': monster.template.level,
                    'lat': lat,
                    'lon': lon,
                    'hp': monster.current_hp
                })

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to create monster: {e}")
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully spawned {len(monsters_created)} monsters!')
        )

        # Show summary
        template_summary = {}
        for monster in monsters_created:
            name = monster['name']
            if name not in template_summary:
                template_summary[name] = 0
            template_summary[name] += 1

        self.stdout.write("\nMonster Summary:")
        for monster_name, count in template_summary.items():
            self.stdout.write(f"  {monster_name}: {count}")

        # Show examples
        self.stdout.write("\nSpawned monsters:")
        for monster in monsters_created[:5]:  # Show first 5
            self.stdout.write(
                f"  {monster['name']} (Lv.{monster['level']}) - "
                f"HP:{monster['hp']} at ({monster['lat']:.6f}, {monster['lon']:.6f})"
            )
        
        if len(monsters_created) > 5:
            self.stdout.write(f"  ... and {len(monsters_created) - 5} more")

        # Show current totals
        total_alive = Monster.objects.filter(is_alive=True).count()
        self.stdout.write(f"\nTotal monsters alive in world: {total_alive}")
