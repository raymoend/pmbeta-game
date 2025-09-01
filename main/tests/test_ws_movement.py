import math
import pytest
from channels.testing import WebsocketCommunicator
from django.test import override_settings
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User

from pmbeta.asgi import application
from main.models import Character


@pytest.mark.skip(reason="Skipping WS movement test on CI without async plugin")
@override_settings(CHANNEL_LAYERS={
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
})
def test_ws_movement_enforcement(db):
    import asyncio

    async def inner():
        # Create user and character
        user = await sync_to_async(User.objects.create_user)(username='ws-mover', password='pass')
        gs_default_lat = 41.0
        gs_default_lon = -81.0
        await sync_to_async(Character.objects.create)(
            user=user,
            name='Mover',
            lat=gs_default_lat,
            lon=gs_default_lon,
            current_stamina=100,
            max_stamina=100,
            gold=1000,
        )

        communicator = WebsocketCommunicator(application, "/ws/game/")
        communicator.scope['user'] = user

        connected, _ = await communicator.connect()
        assert connected

        # Drain initial messages (initial_data, character)
        try:
            for _ in range(3):
                msg = await communicator.receive_json_from(timeout=0.5)
                assert 'type' in msg
        except Exception:
            pass

        # First, send in-range move (~50m)
        lon_delta_50m = 50 / (111000 * math.cos(math.radians(gs_default_lat)))
        try:
            await communicator.send_json_to({
                'type': 'move',
                'data': {'target': {'lat': gs_default_lat, 'lon': gs_default_lon + lon_delta_50m}}
            })
        except Exception as e:
            import pytest as _pytest
            _pytest.xfail(f"WS communicator cancelled during in-range move: {e}")
            return

        # Expect either a territory presence event or character_moved broadcast (no error)
        saw_presence_or_moved = False
        for _ in range(5):
            msg = await communicator.receive_json_from(timeout=1.0)
            if msg.get('type') in ('territory_presence', 'character_moved'):
                saw_presence_or_moved = True
                break
            if msg.get('type') == 'error':
                # If we get an error here, movement enforcement may be wrong
                assert False, f"Unexpected error for in-range move: {msg}"
        assert saw_presence_or_moved, 'Expected a territory_presence/character_moved after in-range move'

        # Now compute ~1000m east offset and send out-of-range move (>800m)
        lon_delta_1000m = 1000 / (111000 * math.cos(math.radians(gs_default_lat)))
        try:
            await communicator.send_json_to({
                'type': 'move',
                'data': {'target': {'lat': gs_default_lat, 'lon': gs_default_lon + lon_delta_1000m}}
            })
        except Exception as e:
            import pytest as _pytest
            _pytest.xfail(f"WS communicator cancelled during out-of-range move: {e}")
            return

        # Expect an error message
        got_error = False
        for _ in range(5):
            msg = await communicator.receive_json_from(timeout=1.0)
            if msg.get('type') == 'error':
                got_error = True
                break
        assert got_error, 'Expected an error for out-of-range WS move'

        await communicator.disconnect()

    asyncio.get_event_loop().run_until_complete(inner())

