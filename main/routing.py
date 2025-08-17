"""
WebSocket URL routing for PMBeta RPG game
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/game/$', consumers.RPGGameConsumer.as_asgi()),
]
