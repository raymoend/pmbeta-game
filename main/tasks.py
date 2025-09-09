try:
    from celery import shared_task
except Exception:
    # Celery optional: define a no-op decorator for test/dev without Celery installed
    def shared_task(func=None, **kwargs):  # type: ignore
        def wrap(f):
            return f
        return wrap if func is None else wrap(func)
from django.utils import timezone
from django.db.models import F
from django.conf import settings

from .services import territory as territory_svc
from .models import TerritoryFlag, Monster, Character, MonsterTemplate, ResourceNode
import math, random


@shared_task
def npc_pulse_task(min_per_flag: int = None):
    """Periodic task to maintain persistent NPC population.
    - Ensures a minimum population inside territory flags.
    - Respawns any dead monsters whose timers have elapsed.
    - Maintains a baseline of wild NPCs around each online player.
    """
    # Read configuration
    gs = getattr(settings, 'GAME_SETTINGS', {})
    try:
        target = int(min_per_flag) if min_per_flag is not None else int(gs.get('MIN_FLAG_NPCS', 3))
    except Exception:
        target = 3
    try:
        wild_min = int(gs.get('WILD_MIN_NPCS', 5))
    except Exception:
        wild_min = 5
    try:
        wild_radius = int(gs.get('WILD_SPAWN_RADIUS_M', 120))
    except Exception:
        wild_radius = 120

    # 1) Respawn monsters that are ready
    now = timezone.now()
    qs = Monster.objects.filter(is_alive=False, respawn_at__isnull=False, respawn_at__lte=now)
    for m in qs:
        try:
            m.respawn()
        except Exception:
            # best-effort
            pass

    # 2) Ensure minimum alive per flag
    try:
        territory_svc.ensure_flag_monsters(min_alive_per_flag=target)
    except Exception:
        # best-effort
        pass

    # 3) Ensure a baseline of wild NPCs around online players
    try:
        for ch in Character.objects.filter(is_online=True):
            try:
                lat_eps = wild_radius / 111320.0
                lon_eps = wild_radius / (111320.0 * max(1e-6, math.cos(math.radians(float(ch.lat) if ch.lat is not None else 0.0))))
            except Exception:
                # Fallback small box if character lat invalid
                lat_eps = wild_radius / 111320.0
                lon_eps = lat_eps
            # Count nearby alive monsters
            nearby = Monster.objects.filter(
                is_alive=True,
                lat__gte=(ch.lat - lat_eps),
                lat__lte=(ch.lat + lat_eps),
                lon__gte=(ch.lon - lon_eps),
                lon__lte=(ch.lon + lon_eps),
            ).count()
            if nearby >= wild_min:
                continue
            to_spawn = int(wild_min - nearby)
            # Choose a template near character level if available
            tmpl = MonsterTemplate.objects.filter(
                level__gte=max(1, int(getattr(ch, 'level', 1)) - 1),
                level__lte=int(getattr(ch, 'level', 1)) + 1
            ).order_by('?').first()
            if not tmpl:
                # Create a simple default template if none exist yet
                lvl = max(1, int(getattr(ch, 'level', 1) or 1))
                try:
                    tmpl = MonsterTemplate.objects.create(
                        name='Forest Wolf', description='A wild wolf roaming the forest', level=lvl,
                        base_hp=40, strength=12, defense=6, agility=14,
                        base_experience=30, base_gold=15, is_aggressive=True,
                        respawn_time_minutes=30
                    )
                except Exception:
                    tmpl = MonsterTemplate.objects.first()
            # Spawn the deficit around the character within the configured radius
            for _ in range(max(0, to_spawn)):
                try:
                    ang = random.random() * 2 * math.pi
                    # keep a small minimum distance so they don't spawn on top of the player
                    dist = random.uniform(10.0, float(wild_radius))
                    dlat = dist / 111320.0
                    dlon = dist / (111320.0 * max(1e-6, math.cos(math.radians(float(ch.lat) if ch.lat is not None else 0.0))))
                    Monster.objects.create(
                        template=tmpl,
                        lat=float(ch.lat) + dlat * math.sin(ang),
                        lon=float(ch.lon) + dlon * math.cos(ang),
                        current_hp=int(getattr(tmpl, 'base_hp', 40) or 40),
                        max_hp=int(getattr(tmpl, 'base_hp', 40) or 40),
                        is_alive=True,
                    )
                except Exception:
                    # best-effort per spawn
                    pass
    except Exception:
        # best-effort overall
        pass


@shared_task
def resource_regen_task(batch_limit: int = 500) -> int:
    """Periodic task to regenerate depleted resource nodes whose cooldowns expired.
    Returns the number of resources that were respawned.
    """
    try:
        now = timezone.now()
        # Select depleted nodes that have a recorded last_harvested timestamp
        qs = ResourceNode.objects.filter(is_depleted=True, last_harvested__isnull=False).order_by('last_harvested')
        count = 0
        for res in qs[: max(0, int(batch_limit))]:
            try:
                if res.respawn_if_ready():
                    count += 1
            except Exception:
                # continue scanning others
                pass
        return count
    except Exception:
        return 0


@shared_task
def accrue_flag_income():
    now = timezone.now()
    updated = 0
    for flag in TerritoryFlag.objects.all():
        # compute minutes since last_income_at
        delta = now - flag.last_income_at
        minutes = max(0, int(delta.total_seconds() // 60))
        if minutes > 0 and flag.status in ['active', 'under_attack', 'capturable']:
            income = int((flag.income_per_hour / 60) * minutes)
            flag.uncollected_balance = F('uncollected_balance') + income
            flag.last_income_at = now
            flag.save(update_fields=['uncollected_balance', 'last_income_at', 'updated_at'])
            updated += 1
    return updated


@shared_task
def deduct_flag_upkeep():
    now = timezone.now()
    for flag in TerritoryFlag.objects.all():
        # deduct once per day; if more than 24h passed since last_upkeep_at
        delta = now - flag.last_upkeep_at
        if delta.total_seconds() >= 24 * 3600:
            flag.uncollected_balance = F('uncollected_balance') - flag.upkeep_per_day
            flag.last_upkeep_at = now
            flag.save(update_fields=['uncollected_balance', 'last_upkeep_at', 'updated_at'])
    return True
