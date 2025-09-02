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


def ensure_in_territory(character, new_lat: float, new_lon: float) -> None:
    """Ensure the target point lies within the player's owned flag circles OR
    within any hex adjacent to their owned hexes. Allows a small starter
    grace radius when the player owns no flags.
    Raises MovementError on violation.
    """
    from ..models import TerritoryFlag as TF
    from .territory import point_in_flag
    from .flags import hex_id_for_latlon

    gs = getattr(settings, 'GAME_SETTINGS', {}) or {}
    pk = getattr(settings, 'PK_SETTINGS', {}) or {}
    starter_grace = int(gs.get('STARTER_GRACE_RADIUS_M', pk.get('STARTER_GRACE_RADIUS_M', 50)))

    # Gather owned flags
    owned = list(TF.objects.filter(owner=character.user))

    # No flags: allow small grace circle around current location
    if not owned:
        dist = haversine_m(character.lat, character.lon, new_lat, new_lon)
        if dist <= max(0, starter_grace):
            return
        raise MovementError('out_of_bounds', 'Outside starter grace radius')

    # Allowed if inside any owned flag circle
    for f in owned:
        if point_in_flag(new_lat, new_lon, f):
            return

    # Hex adjacency check
    q_new, r_new = hex_id_for_latlon(new_lat, new_lon)

    # Build owned cells set (use stored hex_q/hex_r if available; otherwise compute)
    owned_cells = set()
    for f in owned:
        if f.hex_q is not None and f.hex_r is not None:
            owned_cells.add((int(f.hex_q), int(f.hex_r)))
        else:
            owned_cells.add(hex_id_for_latlon(f.lat, f.lon))

    # Directly owned cell
    if (q_new, r_new) in owned_cells:
        return

    # Adjacent to any owned cell (flat-top axial neighbors)
    neighbors = [(+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1)]
    for (oq, orr) in owned_cells:
        for dq, dr in neighbors:
            if (oq + dq, orr + dr) == (q_new, r_new):
                return

    raise MovementError('out_of_bounds', 'Outside owned/adjacent territory')

