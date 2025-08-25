"""
WebSocket URL routing for PMBeta RPG game
"""
from django.urls import re_path
from . import consumers

# Route both legacy and current websocket paths to the same consumer
websocket_urlpatterns = [
    re_path(r'^ws/game/$', consumers.RPGGameConsumer.as_asgi()),
    re_path(r'^ws/rpg/game/$', consumers.RPGGameConsumer.as_asgi()),
]
