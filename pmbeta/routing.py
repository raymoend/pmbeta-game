"""
WebSocket routing for PMBeta RPG game
"""
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

from main.consumers_rpg import RPGGameConsumer

websocket_urlpatterns = [
    path('ws/game/', RPGGameConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
