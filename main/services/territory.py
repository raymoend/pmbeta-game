"""
Territory utilities for circle-based zones and NPC spawning.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple
from django.conf import settings
import math

from .movement import haversine_m
from ..models import TerritoryFlag, Monster, MonsterTemplate

EPS = 1e-6


# Unified radius helpers
def flag_radius_for_level(level: int) -> int:
    """Return territory radius in meters.
    Priority of configuration (first found wins):
    - settings.PK_SETTINGS.CLAIM_RADIUS_M or CLAIM_RADIUS
    - settings.GAME_SETTINGS.FLAG_RADIUS_M or FLAG_RADIUS
    Optional per-level growth if *_RADIUS_PER_LEVEL_M is provided.
    Defaults to fixed 600m when not configured.
    """
    gs_game = getattr(settings, 'GAME_SETTINGS', {})
    gs_pk = getattr(settings, 'PK_SETTINGS', {})
    fixed = (
        gs_game.get('CLAIM_RADIUS_M')
        or gs_game.get('CLAIM_RADIUS')
        or gs_game.get('FLAG_RADIUS_M')
        or gs_game.get('FLAG_RADIUS')
        or gs_pk.get('CLAIM_RADIUS_M')
        or gs_pk.get('CLAIM_RADIUS')
    )
    per_level = (
        gs_game.get('CLAIM_RADIUS_PER_LEVEL_M')
        or gs_game.get('FLAG_RADIUS_PER_LEVEL_M')
        or gs_pk.get('CLAIM_RADIUS_PER_LEVEL_M')
        or 0
    )
    try:
        if fixed is not None:
            base = int(fixed)
            inc = int(per_level) if per_level else 0
            return max(0, base + max(0, level - 1) * inc)
    except Exception:
        pass
    return 600


def flag_radius_for_flag(flag: TerritoryFlag) -> int:
    return flag_radius_for_level(getattr(flag, 'level', 1))


# Back-compat alias used by existing code
def flag_radius_m(flag: TerritoryFlag) -> int:
    return flag_radius_for_flag(flag)


def point_in_flag(lat: float, lon: float, flag: TerritoryFlag) -> bool:
    r = flag_radius_m(flag)
    return haversine_m(lat, lon, flag.lat, flag.lon) <= r + EPS


def are_adjacent(f1: TerritoryFlag, f2: TerritoryFlag) -> bool:
    # Touching or overlapping (overlap should not happen by rules, but handle tangent)
    d = haversine_m(f1.lat, f1.lon, f2.lat, f2.lon)
    return d <= (flag_radius_m(f1) + flag_radius_m(f2)) + EPS


@dataclass
class TerritoryGroup:
    owner_id: int
    flags: List[TerritoryFlag]

    @property
    def size(self) -> int:
        return len(self.flags)


def compute_groups(flags: List[TerritoryFlag]) -> List[TerritoryGroup]:
    # Union-by-owner then adjacency via BFS
    by_owner: Dict[int, List[TerritoryFlag]] = {}
    for f in flags:
        by_owner.setdefault(f.owner_id, []).append(f)

    groups: List[TerritoryGroup] = []
    for owner_id, flist in by_owner.items():
        visited = set()
        for i, f in enumerate(flist):
            if i in visited:
                continue
            # BFS
            q = [i]
            visited.add(i)
            comp = [flist[i]]
            while q:
                idx = q.pop()
                for j, g in enumerate(flist):
                    if j in visited:
                        continue
                    if are_adjacent(flist[idx], g):
                        visited.add(j)
                        q.append(j)
                        comp.append(g)
            groups.append(TerritoryGroup(owner_id=owner_id, flags=comp))
    return groups


def spawn_monsters_for_groups(base_per_circle: int = 2, template_filter=None) -> int:
    """Spawn monsters within territory circles. The number spawned per group
    scales with the number of connected circles in that group.
    Returns number of monsters spawned.
    """
    flags = list(TerritoryFlag.objects.all())
    groups = compute_groups(flags)

    # Choose templates
    templates_qs = MonsterTemplate.objects.all()
    if template_filter:
        templates_qs = templates_qs.filter(**template_filter)
    templates = list(templates_qs)
    if not templates:
        return 0

    import random
    spawned = 0
    for grp in groups:
        target = base_per_circle * max(1, grp.size)
        # Count existing monsters within these flags
        def in_group(m: Monster) -> bool:
            return any(point_in_flag(m.lat, m.lon, f) for f in grp.flags)

        existing = [m for m in Monster.objects.filter(is_alive=True) if in_group(m)]
        to_spawn = max(0, target - len(existing))
        for _ in range(to_spawn):
            # pick a random flag circle in the group
            f = random.choice(grp.flags)
            r = flag_radius_m(f)
            # sample a random point uniformly in circle
            # pick a random distance and angle; convert meters to lat/lon approximately
            angle = random.random() * 2 * 3.1415926535
            # radius sample proportional to sqrt(u)
            dist = r * (random.random() ** 0.5)
            # convert meters to degrees roughly (small distances)
            dlat = (dist / 111320.0) * math.cos(0)  # simple approx
            dlon = dist / (111320.0 * max(1e-6, math.cos(f.lat * 3.1415926535/180)))
            lat = f.lat + dlat * math.sin(angle)
            lon = f.lon + dlon * math.cos(angle)
            t = random.choice(templates)
            Monster.objects.create(
                template=t,
                lat=lat,
                lon=lon,
                current_hp=t.base_hp,
                max_hp=t.base_hp,
                is_alive=True,
            )
            spawned += 1
    return spawned


def ensure_flag_monsters(min_alive_per_flag: int = 3, template_filter=None) -> dict:
    """Ensure each territory flag has at least `min_alive_per_flag` alive monsters
    inside its territory. Spawns the deficit uniformly within the circle.
    Returns a dict keyed by flag id with counts {existing, spawned}.
    """
    results = {}
    flags = list(TerritoryFlag.objects.all())
    if not flags:
        return results

    # Preload templates list once
    qs = MonsterTemplate.objects.all()
    if template_filter:
        qs = qs.filter(**template_filter)
    templates = list(qs)
    if not templates:
        # Create a default if none exist
        t = MonsterTemplate.objects.create(
            name='Territory Guard', description='A vigilant defender', level=2,
            base_hp=45, strength=10, defense=6, agility=8,
            base_experience=20, base_gold=10, is_aggressive=True,
            respawn_time_minutes=20
        )
        templates = [t]

    spawned_total = 0
    for flag in flags:
        # Count alive monsters inside this flag
        alive = [m for m in Monster.objects.filter(is_alive=True)
                 if point_in_flag(m.lat, m.lon, flag)]
        existing = len(alive)
        deficit = max(0, int(min_alive_per_flag) - existing)
        spawned = 0
        if deficit > 0:
            ids = spawn_monsters_in_flag(flag, count=deficit, template_filter=template_filter)
            spawned = len(ids)
            spawned_total += spawned
        results[str(flag.id)] = {'existing': existing, 'spawned': spawned}
    results['total_spawned'] = spawned_total
    return results


def _uniform_point_in_circle(lat_center: float, lon_center: float, radius_m: float) -> tuple[float, float]:
    """Sample a quasi-uniform random point within a circle (small-distance approx)."""
    import random
    angle = random.random() * 2 * math.pi
    dist = radius_m * (random.random() ** 0.5)
    dlat = dist / 111320.0
    dlon = dist / (111320.0 * max(1e-6, math.cos(lat_center * math.pi/180.0)))
    lat = lat_center + dlat * math.sin(angle)
    lon = lon_center + dlon * math.cos(angle)
    return lat, lon


def spawn_monsters_in_flag(flag: TerritoryFlag, count: int = 5, template_filter=None) -> list:
    """Spawn exactly 'count' monsters uniformly inside a flag's circle.
    Returns the list of created monster IDs (UUID strings).
    """
    qs = MonsterTemplate.objects.all()
    if template_filter:
        qs = qs.filter(**template_filter)
    templates = list(qs)
    if not templates:
        # Create a simple default template if none exist
        t = MonsterTemplate.objects.create(
            name='Territory Guard', description='A vigilant defender', level=2,
            base_hp=45, strength=10, defense=6, agility=10,
            base_experience=25, base_gold=15, is_aggressive=True,
            respawn_time_minutes=30
        )
        templates = [t]

    created_ids = []
    r = flag_radius_m(flag)
    for _ in range(max(0, int(count))):
        lat, lon = _uniform_point_in_circle(flag.lat, flag.lon, r)
        t = templates[int(math.floor((len(created_ids) * 9301 + 49297) % (len(templates) or 1)))] if len(templates) > 1 else templates[0]
        m = Monster.objects.create(
            template=t,
            lat=lat,
            lon=lon,
            current_hp=t.base_hp,
            max_hp=t.base_hp,
            is_alive=True,
        )
        created_ids.append(str(m.id))
    return created_ids

# ===== PK-style claim wrappers (aliases) =====
# These provide claim-named helpers that delegate to the existing flag helpers.

def compute_empires(claims):
    """Alias to compute_groups for TerritoryFlag collections."""
    return compute_groups(claims)


def spawn_monsters_for_empires(base_per_hex: int = 2, template_filter=None) -> int:
    """Alias to spawn_monsters_for_groups with PK-style parameter naming."""
    return spawn_monsters_for_groups(base_per_circle=base_per_hex, template_filter=template_filter)


def ensure_claim_monsters(min_alive_per_claim: int = 3, template_filter=None) -> dict:
    """Alias to ensure_flag_monsters with PK-style parameter naming."""
    return ensure_flag_monsters(min_alive_per_flag=min_alive_per_claim, template_filter=template_filter)


def _uniform_point_in_hex(lat_center: float, lon_center: float, radius_m: float) -> tuple[float, float]:
    """Sample a quasi-uniform random point within a hex approximated as a circle."""
    return _uniform_point_in_circle(lat_center, lon_center, radius_m)


def spawn_monsters_in_claim(claim, count: int = 5, template_filter=None) -> list:
    """Alias to spawn_monsters_in_flag with PK-style parameter naming."""
    return spawn_monsters_in_flag(claim, count=count, template_filter=template_filter)


def find_next_claim_to_explore(user, current_claim_id=None):
    """Alias to find_next_flag_to_run with PK-style parameter naming."""
    return find_next_flag_to_run(user, current_flag_id=current_claim_id)


def find_next_flag_to_run(user, current_flag_id=None) -> TerritoryFlag | None:
    """Return the next owned flag after current_flag_id (wrap-around). If user has
    no flags, return None."""
    try:
        from ..models import TerritoryFlag as TF
    except Exception:
        return None
    qs = TF.objects.filter(owner=user).order_by('created_at')
    flags = list(qs)
    if not flags:
        return None
    if not current_flag_id:
        return flags[0]
    order = [str(f.id) for f in flags]
    try:
        idx = order.index(str(current_flag_id))
        return flags[(idx + 1) % len(flags)]
    except ValueError:
        return flags[0]

