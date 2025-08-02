# src/core/routing.py
"""
WebSocket URL routing for real-time features
"""

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/notifications/(?P<user_id>\w+)/$", consumers.NotificationConsumer.as_asgi()
    ),
    re_path(r"ws/updates/(?P<room_name>\w+)/$", consumers.UpdatesConsumer.as_asgi()),
]
