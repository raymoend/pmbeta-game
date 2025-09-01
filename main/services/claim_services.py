"""
Claim domain services: thin adapters over flag services.
Provides claim-named APIs that delegate to the existing flag/territory system.
This preserves current models (TerritoryFlag, FlagLedger) while exposing a
PK-flavored service surface (place_claim, attack_claim, etc.).
"""
from __future__ import annotations
from typing import List, Dict, Optional
from django.utils import timezone

# Reuse the existing flag service implementations
from .flags import (
    place_flag as _place_flag,
    list_flags_near as _list_flags_near,
    attack_flag as _attack_flag,
    capture_flag as _capture_flag,
    collect_revenue as _collect_revenue,
    process_flags_tick as _process_flags_tick,
    FlagError as _FlagError,
)

# Re-export error type under a claim-friendly alias
class ClaimError(_FlagError):
    pass


# ============ Placement / Listing ============

def place_claim(user, lat: float, lon: float, name: Optional[str] = None):
    """Place a claim (delegates to place_flag)."""
    try:
        return _place_flag(user, lat, lon, name)
    except _FlagError as fe:
        # Surface as ClaimError for callers expecting claim domain
        raise ClaimError(getattr(fe, 'code', 'claim_error'), str(fe))


def list_claims_near(lat: float, lon: float, radius_m: float = 1500) -> List[Dict]:
    """List claims near a coordinate (delegates to list_flags_near).
    Default radius is PK-style 1500m for local focus.
    """
    return _list_flags_near(lat, lon, radius_m)


# ============ Combat / Capture ============

def attack_claim(user, claim_id: str, at_lat: float, at_lon: float, damage: int = 40) -> Dict:
    """Attack a claim (delegates to attack_flag)."""
    try:
        return _attack_flag(user, claim_id, at_lat, at_lon, damage=max(1, int(damage)))
    except _FlagError as fe:
        raise ClaimError(getattr(fe, 'code', 'claim_error'), str(fe))


def capture_claim(user, claim_id: str, at_lat: float, at_lon: float) -> Dict:
    """Capture a claim (delegates to capture_flag)."""
    try:
        return _capture_flag(user, claim_id, at_lat, at_lon)
    except _FlagError as fe:
        raise ClaimError(getattr(fe, 'code', 'claim_error'), str(fe))


# ============ Economy ============

def collect_revenue(user, claim_id: str) -> Dict:
    """Collect revenue from a claim (delegates to collect_revenue)."""
    try:
        return _collect_revenue(user, claim_id)
    except _FlagError as fe:
        raise ClaimError(getattr(fe, 'code', 'claim_error'), str(fe))


# ============ Tick processing ============

def process_claims_tick(now=None):
    return _process_flags_tick(now=now or timezone.now())

