from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from ...services import territory as territory_svc
from ...views_rpg import respawn_dead_monsters
from ...models import Character, Monster, MonsterTemplate
import math, random

class Command(BaseCommand):
    help = "Maintain persistent NPC presence inside flags and a baseline in the wild; respawn ready ones."

    def add_arguments(self, parser):
        parser.add_argument('--min-per-flag', type=int, default=None, help='Minimum alive NPCs per flag territory (defaults to GAME_SETTINGS.MIN_FLAG_NPCS)')
        parser.add_argument('--wild-min', type=int, default=None, help='Minimum wild NPCs around each online player (defaults to GAME_SETTINGS.WILD_MIN_NPCS)')
        parser.add_argument('--wild-radius', type=int, default=None, help='Wild spawn radius in meters (defaults to GAME_SETTINGS.WILD_SPAWN_RADIUS_M)')

    def handle(self, *args, **options):
        gs = getattr(settings, 'GAME_SETTINGS', {})
        min_per_flag = int(options.get('min_per_flag') or gs.get('MIN_FLAG_NPCS', 3))
        wild_min = int(options.get('wild_min') or gs.get('WILD_MIN_NPCS', 5))
        wild_radius = int(options.get('wild_radius') or gs.get('WILD_SPAWN_RADIUS_M', 120))
        # First allow any dead monsters to respawn if their timers passed
        respawn_dead_monsters()
        # Ensure minimum population per flag
        res = territory_svc.ensure_flag_monsters(min_alive_per_flag=min_per_flag)
        total = res.pop('total_spawned', 0)
        # Ensure baseline wild NPCs around online players
        wild_spawned = 0
        for ch in Character.objects.filter(is_online=True):
            lat_eps = wild_radius / 111320.0
            lon_eps = wild_radius / (111320.0 * max(1e-6, math.cos(math.radians(ch.lat))))
            nearby = Monster.objects.filter(
                is_alive=True,
                lat__gte=ch.lat - lat_eps,
                lat__lte=ch.lat + lat_eps,
                lon__gte=ch.lon - lon_eps,
                lon__lte=ch.lon + lon_eps,
            ).count()
            if nearby < wild_min:
                to_spawn = wild_min - nearby
                tmpl = MonsterTemplate.objects.filter(level__gte=max(1, ch.level-1), level__lte=ch.level+1).order_by('?').first()
                if not tmpl:
                    tmpl = MonsterTemplate.objects.create(
                        name='Forest Wolf', description='A wild wolf roaming the forest', level=max(1, int(ch.level)),
                        base_hp=40, strength=12, defense=6, agility=14,
                        base_experience=30, base_gold=15, is_aggressive=True,
                        respawn_time_minutes=30
                    )
                for _ in range(to_spawn):
                    ang = random.random() * 2*math.pi
                    dist = random.uniform(10.0, float(wild_radius))
                    lat_off = dist / 111320.0
                    lon_off = dist / (111320.0 * max(1e-6, math.cos(math.radians(ch.lat))))
                    Monster.objects.create(
                        template=tmpl,
                        lat=ch.lat + lat_off * math.sin(ang),
                        lon=ch.lon + lon_off * math.cos(ang),
                        current_hp=tmpl.base_hp,
                        max_hp=tmpl.base_hp,
                        is_alive=True,
                    )
                wild_spawned += to_spawn
        self.stdout.write(self.style.SUCCESS(
            f"[{timezone.now().isoformat()}] NPC pulse complete: flag_spawned={total}, wild_spawned={wild_spawned}, details={res}"
        ))
