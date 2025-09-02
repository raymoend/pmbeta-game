"""
Flag domain services: place, list, attack, capture
"""
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from typing import List, Dict
import math

from ..models import TerritoryFlag, FlagLedger, Character
from .movement import haversine_m, ensure_interaction_range
from .territory import flag_radius_for_level

# === Hex grid helpers (flat-top) using Web Mercator meters with global origin ===
ORIGIN_SHIFT = 20037508.34

def _project(lon: float, lat: float) -> tuple[float, float]:
    x = lon * ORIGIN_SHIFT / 180.0
    y = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
    y = y * ORIGIN_SHIFT / 180.0
    return x, y

def _unproject(x: float, y: float) -> tuple[float, float]:
    lon = (x / ORIGIN_SHIFT) * 180.0
    lat = (y / ORIGIN_SHIFT) * 180.0
    lat = 180.0/math.pi * (2.0 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi/2.0)
    return lon, lat

def _axial_from_xy_flat(x: float, y: float, s: float) -> tuple[float, float]:
    qf = (2.0/3.0) * x / s
    rf = (-1.0/3.0) * x / s + (math.sqrt(3.0)/3.0) * y / s
    return qf, rf

def _cube_round(xf: float, yf: float, zf: float) -> tuple[int, int, int]:
    rx = round(xf); ry = round(yf); rz = round(zf)
    x_diff = abs(rx - xf); y_diff = abs(ry - yf); z_diff = abs(rz - zf)
    if x_diff > y_diff and x_diff > z_diff:
        rx = -ry - rz
    elif y_diff > z_diff:
        ry = -rx - rz
    else:
        rz = -rx - ry
    return int(rx), int(ry), int(rz)

def _axial_round(qf: float, rf: float) -> tuple[int, int]:
    xf = qf
    zf = rf
    yf = -xf - zf
    rx, ry, rz = _cube_round(xf, yf, zf)
    return int(rx), int(rz)

def _xy_from_axial_flat(q: int, r: int, s: float) -> tuple[float, float]:
    x = s * (1.5 * q)
    y = s * (math.sqrt(3.0) * (r + q/2.0))
    return x, y

def _hex_size_m() -> float:
    try:
        gs_game = getattr(settings, 'GAME_SETTINGS', {})
        gs_pk = getattr(settings, 'PK_SETTINGS', {})
        return float(gs_game.get('HEX_SIZE_M', gs_pk.get('HEX_SIZE_M', 250.0)))
    except Exception:
        return 250.0

def hex_id_for_latlon(lat: float, lon: float) -> tuple[int, int]:
    s = _hex_size_m()
    x, y = _project(lon, lat)
    qf, rf = _axial_from_xy_flat(x, y, s)
    return _axial_round(qf, rf)

def hex_center_latlon(q: int, r: int) -> tuple[float, float]:
    s = _hex_size_m()
    x, y = _xy_from_axial_flat(q, r, s)
    lon, lat = _unproject(x, y)
    return lat, lon


class FlagError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _compute_flag_stats(level: int):
    base_income = 10
    base_upkeep = 5
    hp = 100 * level
    return hp, base_income * level, base_upkeep * level


def _flag_radius_m(level: int) -> int:
    """Deprecated: kept for back-compat. Delegates to services.territory.flag_radius_for_level."""
    return flag_radius_for_level(level)


def _min_distance_to_other_flags(lat: float, lon: float) -> float:
    # Simple in-memory compute; optimize later with bbox if needed
    min_d = float('inf')
    for f in TerritoryFlag.objects.all().only('lat', 'lon'):
        d = haversine_m(lat, lon, f.lat, f.lon)
        if d < min_d:
            min_d = d
    return 0 if min_d == float('inf') else min_d


@transaction.atomic
def place_flag(user: User, lat: float, lon: float, name: str | None = None) -> TerritoryFlag:
    if not user.is_authenticated:
        raise FlagError('unauthenticated', 'User must be authenticated')

    gs_game = getattr(settings, 'GAME_SETTINGS', {})
    gs_pk = getattr(settings, 'PK_SETTINGS', {})
    placement_cost = int(
        gs_game.get('CLAIM_PLACEMENT_COST')
        or gs_game.get('FLAG_PLACEMENT_COST', 100)
        or gs_pk.get('CLAIM_PLACEMENT_COST', 100)
    )

    from ..models import TerritoryFlag as TF
    has_any = TF.objects.filter(owner=user).exists()

    # Cost check: debit from Character.gold (if present)
    character = getattr(user, 'character', None)
    if character is None:
        raise FlagError('no_character', 'No character found for user')

    # Snap requested location to hex center (global, fixed lattice)
    q_new, r_new = hex_id_for_latlon(lat, lon)
    snapped_lat, snapped_lon = hex_center_latlon(q_new, r_new)

    # Enforce minimum placement distance from any existing flag
    min_sep = int(
        gs_game.get('CLAIM_PLACEMENT_MIN_DISTANCE')
        or gs_game.get('FLAG_PLACEMENT_MIN_DISTANCE', 400)
        or gs_pk.get('CLAIM_PLACEMENT_MIN_DISTANCE', 400)
    )
    for f in TF.objects.all().only('lat','lon'):
        d = haversine_m(snapped_lat, snapped_lon, f.lat, f.lon)
        if d < min_sep:
            raise FlagError('too_close', f'Minimum distance is {min_sep}m')

    # Prevent duplicate occupation: one hex = one owner
    # Build set of occupied cells across all flags
    occupied = set()
    for f in TF.objects.all().only('lat','lon'):
        qf, rf = hex_id_for_latlon(f.lat, f.lon)
        occupied.add((qf, rf))
    if (q_new, r_new) in occupied:
        raise FlagError('occupied', 'This hex is already occupied by a flag')

    # If player already has flags, enforce adjacency: the target cell must be adjacent to existing owned territory
    if has_any:
        owned_cells = set(hex_id_for_latlon(f.lat, f.lon) for f in TF.objects.filter(owner=user).only('lat','lon'))
        # Neighbor directions for flat-top axial
        neigh = [(+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1)]
        # Accept either neighbor orientation; addition is more intuitive when thinking "new next to existing"
        is_adjacent = any(((q_new - dq, r_new - dr) in owned_cells) or ((q_new + dq, r_new + dr) in owned_cells) for (dq, dr) in neigh)
        if not is_adjacent:
            raise FlagError('not_adjacent', 'New flags must be placed in a hex adjacent to your territory')

    if character.gold < placement_cost:
        raise FlagError('insufficient_gold', 'Not enough gold to place a flag')

    # Create flag with stats at computed center
    hp_max, income_per_hour, upkeep_per_day = _compute_flag_stats(1)
    flag = TerritoryFlag.objects.create(
        owner=user,
        name=name or '',
        lat=snapped_lat,
        lon=snapped_lon,
        hex_q=q_new,
        hex_r=r_new,
        level=1,
        hp_current=hp_max,
        hp_max=hp_max,
        income_per_hour=income_per_hour,
        upkeep_per_day=upkeep_per_day,
    )

    # Debit and ledger
    character.gold -= placement_cost
    character.save(update_fields=['gold'])
    FlagLedger.objects.create(flag=flag, entry_type=FlagLedger.EntryType.ADJUST, amount=-placement_cost, notes='Placement cost')

    return flag


def list_flags_near(lat: float, lon: float, radius_m: float = 2000) -> List[Dict]:
    # naive scan; optimize later
    results = []
    color_cache: dict[int, str | None] = {}
    for f in TerritoryFlag.objects.select_related('owner').all():
        d = haversine_m(lat, lon, f.lat, f.lon)
        if d <= radius_m:
            # Resolve owner's chosen color (cached by owner_id)
            color_hex = color_cache.get(f.owner_id, None)
            if f.owner_id not in color_cache:
                try:
                    ch = Character.objects.select_related('flag_color').only('flag_color__hex_color').get(user_id=f.owner_id)
                    color_hex = getattr(getattr(ch, 'flag_color', None), 'hex_color', None)
                except Character.DoesNotExist:
                    color_hex = None
                color_cache[f.owner_id] = color_hex
            results.append({
                'id': str(f.id),
                'name': f.name,
                'owner_id': f.owner_id,
                'owner_name': getattr(f.owner, 'username', None),
                'lat': f.lat,
                'lon': f.lon,
                'level': f.level,
                'status': f.status,
                'is_private': bool(getattr(f, 'is_private', False)),
                'hp_current': f.hp_current,
                'hp_max': f.hp_max,
                'uncollected_balance': int(getattr(f, 'uncollected_balance', 0)),
                'distance_m': int(d),
                'color': color_hex,
            })
    results.sort(key=lambda x: x['distance_m'])
    return results


@transaction.atomic
def attack_flag(user: User, flag_id: str, at_lat: float, at_lon: float, damage: int = 50) -> Dict:
    if not user.is_authenticated:
        raise FlagError('unauthenticated', 'User must be authenticated')
    try:
        flag = TerritoryFlag.objects.select_for_update().get(id=flag_id)
    except TerritoryFlag.DoesNotExist:
        raise FlagError('not_found', 'Flag not found')

    # Owner cannot attack own flag
    if flag.owner_id == user.id:
        raise FlagError('own_flag', 'Cannot attack your own flag')

    # Protection window
    now = timezone.now()
    if flag.protection_ends_at and now < flag.protection_ends_at:
        raise FlagError('protected', 'Flag is under protection')

    # Range check (interaction range)
    character = getattr(user, 'character', None)
    if character is None:
        raise FlagError('no_character', 'No character found')
    ensure_interaction_range(character, flag.lat, flag.lon)

    # Apply damage
    before = flag.hp_current
    after = max(0, before - max(1, damage))
    flag.hp_current = after

    if after == 0:
        flag.status = TerritoryFlag.Status.CAPTURABLE
        cfg_game = getattr(settings, 'GAME_SETTINGS', {})
        cfg_pk = getattr(settings, 'PK_SETTINGS', {})
        window_s = cfg_game.get('CLAIM_CAPTURE_WINDOW_S') or cfg_game.get('FLAG_CAPTURE_WINDOW_S', 300) or cfg_pk.get('CLAIM_CAPTURE_WINDOW_S', 300)
        flag.capture_window_ends_at = now + timezone.timedelta(seconds=window_s)
    else:
        flag.status = TerritoryFlag.Status.UNDER_ATTACK

    flag.save(update_fields=['hp_current', 'status', 'capture_window_ends_at', 'updated_at'])

    # Log attack event for attacker
    try:
        from . import events as evt
        evt.log_event(user, event_type='combat', title='Flag attacked', message=f'You dealt {before - after} damage', data={'flag_id': str(flag.id), 'hp_after': after})
    except Exception:
        pass

    return {
        'hp_before': before,
        'hp_after': after,
        'status': flag.status,
        'capture_window_ends_at': flag.capture_window_ends_at.isoformat() if flag.capture_window_ends_at else None,
    }


@transaction.atomic
def capture_flag(user: User, flag_id: str, at_lat: float, at_lon: float) -> Dict:
    if not user.is_authenticated:
        raise FlagError('unauthenticated', 'User must be authenticated')
    try:
        flag = TerritoryFlag.objects.select_for_update().get(id=flag_id)
    except TerritoryFlag.DoesNotExist:
        raise FlagError('not_found', 'Flag not found')

    now = timezone.now()
    if flag.status != TerritoryFlag.Status.CAPTURABLE:
        raise FlagError('not_capturable', 'Flag not capturable')
    if not flag.capture_window_ends_at or now > flag.capture_window_ends_at:
        raise FlagError('capture_window_closed', 'Capture window closed')

    # Range check (influence presence)
    character = getattr(user, 'character', None)
    if character is None:
        raise FlagError('no_character', 'No character found')
    cfg_game = getattr(settings, 'GAME_SETTINGS', {})
    cfg_pk = getattr(settings, 'PK_SETTINGS', {})
    influence_r = cfg_game.get('CLAIM_INFLUENCE_RADIUS_M') or cfg_game.get('FLAG_INFLUENCE_RADIUS_M', 150) or cfg_pk.get('CLAIM_INFLUENCE_RADIUS_M', 150)
    d = haversine_m(character.lat, character.lon, flag.lat, flag.lon)
    if d > influence_r:
        raise FlagError('too_far', 'Too far to capture')

    # Transfer ownership and set protection
    flag.owner = user
    flag.status = TerritoryFlag.Status.ACTIVE
    flag.hp_current = flag.hp_max
    protect_s = cfg_game.get('CLAIM_PROTECTION_S') or cfg_game.get('FLAG_PROTECTION_S', 600) or cfg_pk.get('CLAIM_PROTECTION_S', 600)
    flag.protection_ends_at = now + timezone.timedelta(seconds=protect_s)
    flag.capture_window_ends_at = None
    flag.save(update_fields=['owner', 'status', 'hp_current', 'protection_ends_at', 'capture_window_ends_at', 'updated_at'])

    # Log capture event for new owner
    try:
        from . import events as evt
        evt.log_event(user, event_type='combat', title='Flag captured', message='You captured a flag', data={'flag_id': str(flag.id)})
    except Exception:
        pass

    return {
        'captured': True,
        'owner_id': flag.owner_id,
        'status': flag.status,
        'protection_ends_at': flag.protection_ends_at.isoformat() if flag.protection_ends_at else None,
    }

@transaction.atomic
def collect_revenue(user: User, flag_id: str) -> Dict:
    if not user.is_authenticated:
        raise FlagError('unauthenticated', 'User must be authenticated')
    try:
        flag = TerritoryFlag.objects.select_for_update().get(id=flag_id)
    except TerritoryFlag.DoesNotExist:
        raise FlagError('not_found', 'Flag not found')

    if flag.owner_id != user.id:
        raise FlagError('forbidden', 'Only the owner can collect revenue')

    # move balance to character.gold
    character = getattr(user, 'character', None)
    if character is None:
        raise FlagError('no_character', 'No character found')

    amount = int(flag.uncollected_balance)
    flag.uncollected_balance = 0
    flag.save(update_fields=['uncollected_balance', 'updated_at'])
    if amount > 0:
        character.gold += amount
        character.save(update_fields=['gold'])
        FlagLedger.objects.create(flag=flag, entry_type=FlagLedger.EntryType.COLLECT, amount=-amount, notes='Collected by owner')
        # Log event and notify owner
        try:
            from . import events as evt
            evt.log_event(character, event_type='loot_dropped', title='Revenue Collected', message=f'+{amount} gold from flag', data={'flag_id': str(flag.id), 'gold': amount})
        except Exception:
            pass

    return {'collected': amount, 'new_gold': character.gold}


def process_flags_tick(now=None):
    """Accrue income, apply upkeep/decay, and manage windows per tick."""
    now = now or timezone.now()
    with transaction.atomic():
        for f in TerritoryFlag.objects.select_for_update().all():
            # Simple accrual model: income_per_hour to per-minute
            income_per_min = max(0, int(getattr(f, 'income_per_hour', 0) / 60))
            upkeep_per_min = max(0, int(getattr(f, 'upkeep_per_day', 0) / (24 * 60)))
            f.uncollected_balance = max(0, int(f.uncollected_balance) + income_per_min - upkeep_per_min)

            # Close protection window
            if f.protection_ends_at and f.protection_ends_at <= now and f.status == TerritoryFlag.Status.ACTIVE:
                f.protection_ends_at = None

            # Expire capture window if needed
            if f.capture_window_ends_at and f.capture_window_ends_at <= now and f.status == TerritoryFlag.Status.CAPTURABLE:
                f.status = TerritoryFlag.Status.ACTIVE
                f.capture_window_ends_at = None

            f.save(update_fields=['uncollected_balance', 'protection_ends_at', 'capture_window_ends_at', 'status', 'updated_at'])
