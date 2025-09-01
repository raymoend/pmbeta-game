"""
Stamina (energy) helpers: regeneration over time and action costs.
No schema changes: uses Django cache to track last regen tick per character.
Configurable via settings.GAME_SETTINGS with safe defaults.
"""
from __future__ import annotations
from typing import Tuple, Dict
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


def _cfg() -> Dict[str, float]:
    try:
        gs = getattr(settings, 'GAME_SETTINGS', {}) or {}
    except Exception:
        gs = {}
    # Defaults tuned for mobile-friendly pacing
    return {
        'STAMINA_REGEN_PER_SEC': float(gs.get('STAMINA_REGEN_PER_SEC', 0.5)),           # 0.5 stam/sec
        'STAMINA_COST_PER_METER': float(gs.get('STAMINA_COST_PER_METER', 0.01)),       # 0.01 stam per meter
        'STAMINA_COST_MIN_MOVE': float(gs.get('STAMINA_COST_MIN_MOVE', 0.0)),          # minimum cost for any move
        'STAMINA_COST_ATTACK': float(gs.get('STAMINA_COST_ATTACK', 5)),                # per attack
        'STAMINA_COST_DEFEND': float(gs.get('STAMINA_COST_DEFEND', 2)),                # per defend
        'STAMINA_COST_HARVEST': float(gs.get('STAMINA_COST_HARVEST', 2)),              # per harvest
    }


def get_stamina_costs() -> Dict[str, float]:
    c = _cfg()
    return {
        'ATTACK': c['STAMINA_COST_ATTACK'],
        'DEFEND': c['STAMINA_COST_DEFEND'],
        'HARVEST': c['STAMINA_COST_HARVEST'],
        'PER_METER': c['STAMINA_COST_PER_METER'],
        'MIN_MOVE': c['STAMINA_COST_MIN_MOVE'],
        'REGEN_PER_SEC': c['STAMINA_REGEN_PER_SEC'],
    }


def _cache_key(character_id) -> str:
    return f"stam:last:{character_id}"


def regen_stamina(character) -> int:
    """
    Regenerate stamina since last tick stored in cache.
    Returns the integer amount regenerated and updates character if changed.
    """
    now = timezone.now()
    key = _cache_key(character.id)
    last_ts = cache.get(key)
    cache.set(key, now, 1800)  # move forward regardless to avoid double counting
    if not last_ts:
        return 0
    try:
        dt = max(0.0, (now - last_ts).total_seconds())
    except Exception:
        dt = 0.0
    per_sec = _cfg()['STAMINA_REGEN_PER_SEC']
    if per_sec <= 0 or dt <= 0:
        return 0
    gain = int(dt * per_sec)
    if gain <= 0:
        return 0
    before = int(getattr(character, 'current_stamina', 0) or 0)
    after = min(int(getattr(character, 'max_stamina', 0) or 0), before + gain)
    if after != before:
        character.current_stamina = after
        try:
            character.save(update_fields=['current_stamina'])
        except Exception:
            pass
        return after - before
    return 0


def movement_stamina_cost(distance_m: float) -> int:
    c = _cfg()
    per_m = max(0.0, c['STAMINA_COST_PER_METER'])
    min_cost = max(0.0, c['STAMINA_COST_MIN_MOVE'])
    try:
        import math
        cost = math.ceil(max(min_cost, float(distance_m) * per_m)) if (per_m > 0 or min_cost > 0) else 0
        return int(cost)
    except Exception:
        return int(min_cost) if (per_m <= 0.0 and min_cost > 0.0) else 0


def consume_stamina(character, cost: int) -> bool:
    """Attempt to consume stamina. Returns True if consumed, False if insufficient."""
    cst = max(0, int(cost or 0))
    if cst <= 0:
        return True
    cur = int(getattr(character, 'current_stamina', 0) or 0)
    if cur < cst:
        return False
    character.current_stamina = cur - cst
    try:
        character.save(update_fields=['current_stamina'])
    except Exception:
        pass
    return True
