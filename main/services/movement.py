"""
Movement enforcement utilities for server-authoritative checks.
"""
from dataclasses import dataclass
from django.conf import settings
import math


class MovementError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def ensure_move_allowed(character, new_lat: float, new_lon: float) -> None:
    """Ensure movement stays within configured radius of the character's center.
    Sets the move center on first valid move.
    Raises MovementError on violation.
    """
    # Prefer GAME_SETTINGS as primary source (PK feel), fallback to PK_SETTINGS, then defaults
    cfg_game = getattr(settings, 'GAME_SETTINGS', {})
    cfg_pk = getattr(settings, 'PK_SETTINGS', {})
    radius = (
        cfg_game.get('MOVEMENT_RANGE_M')
        or cfg_game.get('MOVEMENT_RANGE')
        or cfg_pk.get('MOVEMENT_RANGE_M')
        or cfg_pk.get('MOVEMENT_RANGE')
        or 800
    )

    # Initialize center if not set
    if character.move_center_lat is None or character.move_center_lon is None:
        character.move_center_lat = character.lat if character.lat is not None else new_lat
        character.move_center_lon = character.lon if character.lon is not None else new_lon
        character.save(update_fields=['move_center_lat', 'move_center_lon'])
        return

    dist_from_center = haversine_m(character.move_center_lat, character.move_center_lon, new_lat, new_lon)
    if dist_from_center > radius:
        raise MovementError('out_of_bounds', f'Move exceeds allowed radius ({int(dist_from_center)}m > {radius}m)')


def ensure_interaction_range(character, target_lat: float, target_lon: float) -> None:
    # Prefer GAME_SETTINGS (PK feel), fallback to PK_SETTINGS
    cfg_game = getattr(settings, 'GAME_SETTINGS', {})
    cfg_pk = getattr(settings, 'PK_SETTINGS', {})
    rng = cfg_game.get('INTERACTION_RANGE_M') or cfg_pk.get('INTERACTION_RANGE_M', 50)
    dist = haversine_m(character.lat, character.lon, target_lat, target_lon)
    if dist > rng:
        raise MovementError('out_of_range', f'Target out of range ({int(dist)}m > {rng}m)')

