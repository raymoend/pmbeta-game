"""
Management command to spawn monsters in the game world
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from main.models import Monster, MonsterTemplate, Region
from main.views_rpg import spawn_random_monsters
import random


class Command(BaseCommand):
    help = 'Spawn monsters in the game world based on regions'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--region',
            type=str,
            help='Specific region name to spawn monsters in'
        )
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Number of monsters to spawn (default: 50)'
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Remove all existing monsters before spawning new ones'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be spawned without actually creating monsters'
        )
    
    def handle(self, *args, **options):
        """Execute the command"""
        
        if options['cleanup']:
            if options['dry_run']:
                monster_count = Monster.objects.count()
                self.stdout.write(f"Would remove {monster_count} existing monsters")
            else:
                deleted_count = Monster.objects.all().delete()[0]
                self.stdout.write(
                    self.style.WARNING(f'Removed {deleted_count} existing monsters')
                )
        
        # Get regions
        if options['region']:
            try:
                regions = [Region.objects.get(name=options['region'])]
                self.stdout.write(f"Spawning in region: {options['region']}")
            except Region.DoesNotExist:
                raise CommandError(f"Region '{options['region']}' not found")
        else:
            regions = Region.objects.all()
            self.stdout.write(f"Spawning in {regions.count()} regions")
        
        if not regions:
            raise CommandError("No regions found. Create regions first.")
        
        # Get monster templates
        templates = MonsterTemplate.objects.all()
        if not templates:
            raise CommandError("No monster templates found. Create templates first.")
        
        total_spawned = 0
        
        for region in regions:
            region_spawned = self.spawn_monsters_in_region(
                region, 
                templates, 
                options['count'] // len(regions),
                options['dry_run']
            )
            total_spawned += region_spawned
            
            self.stdout.write(
                f"Region '{region.name}': {region_spawned} monsters"
            )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(f'Would spawn {total_spawned} monsters total (dry run)')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully spawned {total_spawned} monsters')
            )
    
    def spawn_monsters_in_region(self, region, templates, count, dry_run=False):
        """Spawn monsters in a specific region"""
        spawned = 0
        
        # Filter templates by region level range
        suitable_templates = [
            t for t in templates 
            if region.monster_level_min <= t.level <= region.monster_level_max
        ]
        
        if not suitable_templates:
            self.stdout.write(
                self.style.WARNING(
                    f"No suitable monster templates for region '{region.name}' "
                    f"(levels {region.monster_level_min}-{region.monster_level_max})"
                )
            )
            return 0
        
        for _ in range(count):
            if dry_run:
                spawned += 1
                continue
                
            # Random location within region bounds
            lat = random.uniform(region.lat_min, region.lat_max)
            lon = random.uniform(region.lon_min, region.lon_max)
            
            # Choose random template
            template = random.choice(suitable_templates)
            
            try:
                with transaction.atomic():
                    monster = Monster.objects.create(
                        template=template,
                        lat=lat,
                        lon=lon,
                        current_hp=template.base_hp,
                        max_hp=template.base_hp,
                        is_alive=True
                    )
                    spawned += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to spawn monster: {e}")
                )
        
        return spawned
