import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.test import override_settings

from pmbeta.asgi import application
from main.models import Character
from asgiref.sync import sync_to_async


@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS={
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
})
async def test_websocket_connect_and_simple_send(db):
    user = await sync_to_async(User.objects.create_user)(username='wsuser', password='pass')
    await sync_to_async(Character.objects.create)(user=user, name='WS', lat=41.0, lon=-81.0, gold=1000)

    communicator = WebsocketCommunicator(application, "/ws/game/")
    # Provide session auth by force_scope
    communicator.scope['user'] = user

    connected, _ = await communicator.connect()
    assert connected

    # Expect either an initial_data or connection_test depending on consumer path used
    msg = await communicator.receive_json_from()
    assert msg.get('type') in ('connection_test', 'initial_data')

    await communicator.disconnect()
