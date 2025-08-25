try:
    from celery import shared_task
except Exception:
    # If Celery is not available, define a no-op decorator
    def shared_task(func=None, **kwargs):  # type: ignore
        def wrap(f):
            return f
        return wrap if func is None else wrap(func)

from .services import territory as territory_svc
from .views_rpg import respawn_dead_monsters

@shared_task
def npc_pulse_task(min_per_flag: int = None):
    """Periodic task to maintain persistent NPC population in flag territories.
    If min_per_flag is None, read from settings.GAME_SETTINGS.MIN_FLAG_NPCS.
    """
    # Determine target density
    try:
        from django.conf import settings
        target = int(min_per_flag) if min_per_flag is not None else int(getattr(settings, 'GAME_SETTINGS', {}).get('MIN_FLAG_NPCS', 3))
    except Exception:
        target = 3
    # Allow ready respawns
    respawn_dead_monsters()
    # Ensure minimum alive per flag
    territory_svc.ensure_flag_monsters(min_alive_per_flag=target)

from django.utils import timezone
from django.db.models import F
# Make Celery optional: provide a no-op shared_task decorator if Celery isn't installed
try:
    from celery import shared_task  # type: ignore
except Exception:
    def shared_task(func=None, *args, **kwargs):  # type: ignore
        def decorator(f):
            return f
        return decorator(func) if func else decorator
from .models import TerritoryFlag, Character, ResourceNode

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
