from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .services.flags import (
    list_flags_near as svc_list_flags_near,
    place_flag as svc_place_flag,
    attack_flag as svc_attack_flag,
    capture_flag as svc_capture_flag,
    collect_revenue as svc_collect_revenue,
    FlagError,
)
from .services.territory import spawn_monsters_in_flag, find_next_flag_to_run


def _parse_float(request, name, default=None):
    # Support both JSON and form-encoded
    if request.content_type and 'application/json' in request.content_type:
        try:
            import json
            body = json.loads(request.body or b"{}")
            if name in body:
                return float(body.get(name))
        except Exception:
            pass
    val = request.GET.get(name) if request.method == "GET" else request.POST.get(name)
    if val is None:
        return default
    try:
        return float(val)
    except Exception:
        return None


def _serialize_flag(flag):
    # Resolve owner's chosen flag color if available
    color_hex = None
    try:
        owner = getattr(flag, 'owner', None)
        ch = getattr(owner, 'character', None) if owner else None
        color = getattr(ch, 'flag_color', None)
        color_hex = getattr(color, 'hex_color', None)
    except Exception:
        color_hex = None
    return {
        "id": str(getattr(flag, "id", "")),
        "owner_id": getattr(flag, "owner_id", None),
        "name": getattr(flag, "name", ""),
        "lat": getattr(flag, "lat", None),
        "lon": getattr(flag, "lon", None),
        "level": getattr(flag, "level", 1),
        "hp_current": getattr(flag, "hp_current", 0),
        "hp_max": getattr(flag, "hp_max", 0),
        "status": getattr(flag, "status", "active"),
        "is_private": bool(getattr(flag, "is_private", False)),
        "protection_ends_at": flag.protection_ends_at.isoformat() if getattr(flag, "protection_ends_at", None) else None,
        "capture_window_ends_at": flag.capture_window_ends_at.isoformat() if getattr(flag, "capture_window_ends_at", None) else None,
        "uncollected_balance": getattr(flag, "uncollected_balance", 0),
        "color": color_hex,
    }


def _broadcast_flag_event(flag, event, extra=None, radius_m=800):
    # Default: broadcast to a single group keyed by a coarse tile
    try:
        from .utils.geo import tiles_within_radius
        layer = get_channel_layer()
        tiles = tiles_within_radius(flag.lat, flag.lon, radius_m)
        payload = {"type": "flag_event", "event": event, "flag": _serialize_flag(flag)}
        if extra:
            payload["extra"] = extra
        for g in tiles:
            async_to_sync(layer.group_send)(g, {"type": "flag.event", "payload": payload})
    except Exception:
        # Silent fallback if Channels layer not configured
        pass


@login_required
@require_http_methods(["GET"])
def flags_near(request):
    # Accept optional lat/lon; default to player's current position
    lat = _parse_float(request, "lat")
    lon = _parse_float(request, "lon")
    radius_m = _parse_float(request, "radius_m", 750.0)
    if lat is None or lon is None:
        character = getattr(request.user, "character", None)
        if character is None:
            return JsonResponse({"success": False, "ok": False, "error": "No character found"}, status=400)
        lat = character.lat
        lon = character.lon
    flags = svc_list_flags_near(lat, lon, radius_m)
    return JsonResponse({"success": True, "ok": True, "data": {"flags": flags}})


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def place_flag(request):
    try:
        lat = _parse_float(request, "lat")
        lon = _parse_float(request, "lon")
        name = None
        if request.content_type and 'application/json' in request.content_type:
            import json
            try:
                body = json.loads(request.body or b"{}")
                name = body.get("name")
            except Exception:
                name = None
        if lat is None or lon is None:
            return JsonResponse({"success": False, "ok": False, "error": "lat and lon are required"}, status=400)
        flag = svc_place_flag(request.user, lat, lon, name=name)
        _broadcast_flag_event(flag, "created")
        return JsonResponse({"success": True, "ok": True, "data": _serialize_flag(flag)}, status=201)
    except FlagError as fe:
        return JsonResponse({"success": False, "ok": False, "error": str(fe), "code": getattr(fe, "code", "flag_error")}, status=400)
    except Exception:
        return JsonResponse({"success": False, "ok": False, "error": "Failed to place flag"}, status=500)


@login_required
@require_http_methods(["GET"])
def flags_list(request):
    # Use player's current position as center
    character = getattr(request.user, "character", None)
    if character is None:
        return JsonResponse({"success": False, "ok": False, "error": "No character found"}, status=400)
    radius_m = _parse_float(request, "radius_m", 750.0)
    flags = svc_list_flags_near(character.lat, character.lon, radius_m)
    return JsonResponse({"success": True, "ok": True, "data": {"flags": flags}})


@login_required
@require_http_methods(["GET"])
def flag_detail(request, flag_id):
    from .models import TerritoryFlag
    try:
        f = TerritoryFlag.objects.get(id=flag_id)
    except TerritoryFlag.DoesNotExist:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)
    return JsonResponse({"ok": True, "flag": _serialize_flag(f)})


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def attack_flag(request, flag_id):
    lat = _parse_float(request, "lat")
    lon = _parse_float(request, "lon")
    # Optional custom damage for debugging/tools
    dmg = None
    try:
        if request.content_type and 'application/json' in request.content_type:
            import json
            body = json.loads(request.body or b"{}")
            if 'damage' in body:
                dmg = int(body.get('damage'))
        else:
            if 'damage' in request.POST:
                dmg = int(request.POST.get('damage'))
    except Exception:
        dmg = None
    if lat is None or lon is None:
        return HttpResponseBadRequest("lat and lon are required")
    result = svc_attack_flag(request.user, flag_id, lat, lon, damage=dmg if isinstance(dmg, int) and dmg > 0 else 50)
    # Expect service to return damage/results, and we’ll fetch latest flag state for broadcast
    from .models import TerritoryFlag
    flag = TerritoryFlag.objects.get(id=flag_id)
    _broadcast_flag_event(flag, "under_attack", extra=result)
    return JsonResponse({"ok": True, "result": result, "flag": _serialize_flag(flag)})


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def capture_flag(request, flag_id):
    lat = _parse_float(request, "lat", None)
    lon = _parse_float(request, "lon", None)
    result = svc_capture_flag(request.user, flag_id, lat, lon) if lat is not None and lon is not None else svc_capture_flag(request.user, flag_id, 0, 0)
    from .models import TerritoryFlag
    flag = TerritoryFlag.objects.get(id=flag_id)
    _broadcast_flag_event(flag, "captured", extra=result)
    return JsonResponse({"ok": True, "result": result, "flag": _serialize_flag(flag)})


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def collect_revenue(request, flag_id):
    result = svc_collect_revenue(request.user, flag_id)
    from .models import TerritoryFlag
    flag = TerritoryFlag.objects.get(id=flag_id)
    _broadcast_flag_event(flag, "revenue_collected", extra=result)
    return JsonResponse({"ok": True, "result": result, "flag": _serialize_flag(flag)})


@login_required
@require_http_methods(["PATCH"])
@transaction.atomic
def update_flag(request, flag_id):
    from .models import TerritoryFlag
    try:
        flag = TerritoryFlag.objects.select_for_update().get(id=flag_id)
    except TerritoryFlag.DoesNotExist:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)
    if flag.owner_id != request.user.id:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
    # Parse JSON body for updates (currently only name)
    try:
        import json
        data = json.loads(request.body or b"{}")
    except Exception:
        data = {}
    name = data.get("name")
    is_private = data.get("is_private")
    changed_fields = []
    if isinstance(name, str):
        flag.name = name[:64]
        changed_fields.append("name")
    if isinstance(is_private, bool):
        # Only owner can change privacy (checked above)
        flag.is_private = is_private
        changed_fields.append("is_private")
    if changed_fields:
        flag.save(update_fields=changed_fields + ["updated_at"])
        _broadcast_flag_event(flag, "updated", extra={"fields": changed_fields})
    return JsonResponse({"ok": True, "flag": _serialize_flag(flag)})


@login_required
@require_http_methods(["DELETE"])
@transaction.atomic
def delete_flag(request, flag_id):
    from .models import TerritoryFlag
    try:
        flag = TerritoryFlag.objects.select_for_update().get(id=flag_id)
    except TerritoryFlag.DoesNotExist:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)
    if flag.owner_id != request.user.id:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
    flag_id_str = str(flag.id)
    flag.delete()
    # Broadcast a deletion event with minimal info
    try:
        layer = get_channel_layer()
        payload = {"type": "flag_event", "event": "deleted", "flag": {"id": flag_id_str}}
        from .utils.geo import tiles_within_radius
        for g in tiles_within_radius(getattr(request.user.character, 'lat', 0.0), getattr(request.user.character, 'lon', 0.0), 800):
            async_to_sync(layer.group_send)(g, {"type": "flag.event", "payload": payload})
    except Exception:
        pass
    return JsonResponse({"ok": True, "deleted": True, "id": flag_id_str})



