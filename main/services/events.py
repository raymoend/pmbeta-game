from __future__ import annotations
from typing import Optional, Dict, Any, Union
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User

from ..models import GameEvent, Character


def _ensure_character(user_or_character: Union[User, Character]) -> Optional[Character]:
    if isinstance(user_or_character, Character):
        return user_or_character
    try:
        return user_or_character.character  # type: ignore[attr-defined]
    except Exception:
        return None


def log_event(user_or_character: Union[User, Character], *, event_type: str, title: str, message: str, data: Optional[Dict[str, Any]] = None, broadcast: bool = True) -> Optional[GameEvent]:
    """Create a GameEvent row and optionally broadcast a WS notification to the character group.
    event_type must be one of GameEvent.EVENT_TYPES keys.
    """
    ch = _ensure_character(user_or_character)
    if ch is None:
        return None
    try:
        ev = GameEvent.objects.create(
            character=ch,
            event_type=event_type,
            title=title[:100],
            message=message[:300],
            data=data or {},
            is_read=False,
        )
        if broadcast:
            try:
                layer = get_channel_layer()
                payload = {
                    'type': 'notification',
                    'title': title,
                    'message': message,
                    'notification_type': 'info'
                }
                async_to_sync(layer.group_send)(f"character_{ch.id}", payload)
            except Exception:
                pass
        return ev
    except Exception:
        return None

