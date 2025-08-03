# src/core/consumers.py
"""
WebSocket consumers for real-time functionality
"""

import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """Handle real-time notifications for users"""

    async def connect(self):
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]
        self.group_name = f"notifications_{self.user_id}"

        # Check if user is authenticated and authorized
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close()
            return

        # Only allow users to connect to their own notification channel
        if str(user.id) != self.user_id:
            await self.close()
            return

        # Join notification group
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave notification group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get("type")

            if message_type == "mark_read":
                notification_id = text_data_json.get("notification_id")
                await self.mark_notification_read(notification_id)
        except json.JSONDecodeError:
            pass

    async def notification_message(self, event):
        """Send notification to WebSocket"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "message": event["message"],
                    "level": event.get("level", "info"),
                    "timestamp": event.get("timestamp"),
                    "id": event.get("id"),
                    "url": event.get("url"),
                    "user_id": event.get("user_id"),
                }
            )
        )

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a notification as read"""
        from .models import Notification

        try:
            notification = Notification.objects.get(
                id=notification_id, user_id=self.user_id
            )
            notification.is_read = True
            notification.save()
        except Notification.DoesNotExist:
            pass


class UpdatesConsumer(AsyncWebsocketConsumer):
    """Handle real-time updates for specific rooms/contexts"""

    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"updates_{self.room_name}"

        # Check if user is authenticated
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get("type")

            # Handle different message types
            if message_type == "status_update":
                await self.send_status_update(text_data_json)
        except json.JSONDecodeError:
            pass

    async def update_message(self, event):
        """Send update to WebSocket"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "update",
                    "update_type": event.get("update_type"),
                    "data": event.get("data"),
                    "timestamp": event.get("timestamp"),
                }
            )
        )

    async def send_status_update(self, data):
        """Send status update to room group"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "update_message",
                "update_type": "status",
                "data": data,
                "timestamp": data.get("timestamp"),
            },
        )
