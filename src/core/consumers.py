# core/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""

    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope["user"]

        if self.user.is_anonymous:
            await self.close()
            return

        # Create a group name for this user
        self.user_group_name = f"user_{self.user.id}"

        # Join user group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to notification service'
        }))

        # Update user's last activity
        await self.update_user_activity()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'user_group_name'):
            # Leave user group
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                # Respond to ping to keep connection alive
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))

            elif message_type == 'mark_read':
                # Mark notification as read
                notification_id = data.get('notification_id')
                if notification_id:
                    await self.mark_notification_read(notification_id)

            elif message_type == 'mark_all_read':
                # Mark all notifications as read
                await self.mark_all_notifications_read()

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))

    async def notification_message(self, event):
        """Handle notification messages from channel layer"""
        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))

    async def bulk_update(self, event):
        """Handle bulk update notifications"""
        await self.send(text_data=json.dumps({
            'type': 'bulk_update',
            'entity': event['entity'],
            'action': event['action'],
            'count': event['count'],
            'details': event.get('details', {})
        }))

    async def feed_status(self, event):
        """Handle feed generation status updates"""
        await self.send(text_data=json.dumps({
            'type': 'feed_status',
            'feed_id': event['feed_id'],
            'status': event['status'],
            'progress': event.get('progress'),
            'message': event.get('message')
        }))

    @database_sync_to_async
    def update_user_activity(self):
        """Update user's last activity timestamp"""
        self.user.update_last_activity()

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a specific notification as read"""
        from .models import Notification
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=self.user
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False

    @database_sync_to_async
    def mark_all_notifications_read(self):
        """Mark all user's notifications as read"""
        from .models import Notification
        from django.utils import timezone

        Notification.objects.filter(
            user=self.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )