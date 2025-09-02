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
from .models import TerritoryFlag, Monster


@shared_task
def npc_pulse_task(min_per_flag: int = None):
    """Periodic task to maintain persistent NPC population in flag territories.
    If min_per_flag is None, read from settings.GAME_SETTINGS.MIN_FLAG_NPCS.
    Also respawns any dead monsters that have reached their respawn time.
    """
    # Determine target density
    try:
        target = int(min_per_flag) if min_per_flag is not None else int(getattr(settings, 'GAME_SETTINGS', {}).get('MIN_FLAG_NPCS', 3))
    except Exception:
        target = 3

    # Respawn monsters that are ready
    now = timezone.now()
    qs = Monster.objects.filter(is_alive=False, respawn_at__isnull=False, respawn_at__lte=now)
    for m in qs:
        try:
            m.respawn()
        except Exception:
            pass

    # Ensure minimum alive per flag
    territory_svc.ensure_flag_monsters(min_alive_per_flag=target)


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
