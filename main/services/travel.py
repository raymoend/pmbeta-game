"""
Travel services for jump mechanics.
"""
from __future__ import annotations
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from typing import Dict

from ..models import Character, TerritoryFlag

class TravelError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _cfg(key: str, default: int) -> int:
    gs = getattr(settings, 'GAME_SETTINGS', {}) or {}
    pk = getattr(settings, 'PK_SETTINGS', {}) or {}
    return int(gs.get(key) or pk.get(key, default))


def jump_to_flag(user, flag_id) -> Dict:
    """Teleport the user's character to the owned flag center with cooldown/cost checks.
    Returns { success: bool, error?: str, seconds_remaining?: int, location?: {lat,lon} }
    """
    if not user or not user.is_authenticated:
        raise TravelError('unauthenticated', 'Authentication required')

    try:
        flag = TerritoryFlag.objects.get(id=flag_id)
    except TerritoryFlag.DoesNotExist:
        raise TravelError('not_found', 'Flag not found')

    # Privacy check
    if flag.owner_id != user.id and getattr(flag, 'is_private', False):
        raise TravelError('forbidden', 'Flag is private')

    try:
        character = user.character  # type: ignore[attr-defined]
    except Exception:
        raise TravelError('no_character', 'No character found')

    cooldown_s = _cfg('JUMP_COOLDOWN_S', 60)
    cost_gold = _cfg('JUMP_COST_GOLD', 0)
    now = timezone.now()

    # Cooldown
    last = getattr(character, 'last_jump_at', None)
    if last is not None:
        elapsed = (now - last).total_seconds()
        if elapsed < cooldown_s:
            raise TravelError('cooldown', 'Jump on cooldown')

    # Cost
    if cost_gold > 0 and character.gold < cost_gold:
        raise TravelError('insufficient_gold', 'Not enough gold to jump')

    # Execute jump atomically
    with transaction.atomic():
        if cost_gold > 0:
            character.gold -= cost_gold
        character.lat = flag.lat
        character.lon = flag.lon
        character.last_jump_at = now
        character.save(update_fields=['gold', 'lat', 'lon', 'last_jump_at', 'updated_at'])

    return {
        'success': True,
        'location': {'lat': character.lat, 'lon': character.lon},
    }

