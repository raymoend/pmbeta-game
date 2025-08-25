"""
Seed mafia–alien themed MonsterTemplates and optionally spawn them into flags.
Usage:
  python manage.py seed_themed_npcs [--spawn] [--per-flag N]
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from main.views_rpg import create_monster_templates
from main.models import MonsterTemplate, Monster, TerritoryFlag
from main.services.territory import spawn_monsters_in_flag

class Command(BaseCommand):
    help = 'Seed mafia–alien themed monster templates and optionally spawn them in flags.'

    def add_arguments(self, parser):
        parser.add_argument('--spawn', action='store_true', help='Also spawn creatures inside each existing flag')
        parser.add_argument('--per-flag', type=int, default=3, help='How many to spawn per flag when using --spawn (default 3)')

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Creating monster templates (classic + themed)...')
        create_monster_templates()
        self.stdout.write(self.style.SUCCESS('✓ Templates ensured'))

        themed_names = [
            'Mafia Enforcer','Yakuza Blade','Cartel Sicario','Void Cultist','Drone Marauder','Alien Stalker'
        ]
        themed = list(MonsterTemplate.objects.filter(name__in=themed_names))
        if not themed:
            self.stdout.write(self.style.WARNING('No themed templates found after create_monster_templates.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Found {len(themed)} themed templates.'))

        if options.get('spawn'):
            per = max(1, int(options.get('per_flag') or 3))
            flags = list(TerritoryFlag.objects.all())
            total_spawned = 0
            for f in flags:
                # Try to maintain a mix by filtering to themed templates only
                ids = spawn_monsters_in_flag(f, count=per, template_filter={'name__in': themed_names})
                total_spawned += len(ids)
            self.stdout.write(self.style.SUCCESS(f'Spawned {total_spawned} themed NPCs across {len(flags)} flags.'))
        else:
            self.stdout.write('No spawning requested (use --spawn to spawn into flags).')

