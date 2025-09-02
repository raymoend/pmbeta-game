"""
WebSocket URL routing for PMBeta RPG game (consolidated on consumers_rpg)
"""
from django.urls import re_path
from .consumers_rpg import RPGGameConsumer

# Route both legacy and current websocket paths to the same consumer
websocket_urlpatterns = [
    re_path(r'^ws/game/$', RPGGameConsumer.as_asgi()),
    re_path(r'^ws/rpg/game/$', RPGGameConsumer.as_asgi()),
]
