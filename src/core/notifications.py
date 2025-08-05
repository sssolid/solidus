# src/core/notifications.py
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import models

from .models import Notification


class NotificationService:
    """Service for managing notifications"""

    @staticmethod
    def send_notification(user, notification_type, title, message, **kwargs):
        """
        Send a notification to a user

        Args:
            user: User instance
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            **kwargs: Additional notification fields
        """
        # Create notification in database
        notification = Notification.create_for_user(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            **kwargs,
        )

        # Send through WebSocket if user is connected
        NotificationService.send_websocket_notification(user, notification)

        return notification

    @staticmethod
    def send_websocket_notification(user, notification):
        """Send notification through WebSocket"""
        channel_layer = get_channel_layer()

        # Prepare notification data
        notification_data = {
            "id": notification.id,
            "type": notification.notification_type,
            "title": notification.title,
            "message": notification.message,
            "created_at": notification.created_at.isoformat(),
            "is_read": notification.is_read,
            "action_url": notification.action_url,
            "action_label": notification.action_label,
        }

        # Send to user's group
        async_to_sync(channel_layer.group_send)(
            f"user_{user.id}",
            {"type": "notification_message", "notification": notification_data},
        )

    @staticmethod
    def send_bulk_update_notification(users, entity, action, count, details=None):
        """Send bulk update notification to multiple users"""
        channel_layer = get_channel_layer()

        for user in users:
            async_to_sync(channel_layer.group_send)(
                f"user_{user.id}",
                {
                    "type": "bulk_update",
                    "entity": entity,
                    "action": action,
                    "count": count,
                    "details": details or {},
                },
            )

    @staticmethod
    def send_feed_status_update(user, feed_id, status, progress=None, message=None):
        """Send feed generation status update"""
        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            f"user_{user.id}",
            {
                "type": "feed_status",
                "feed_id": str(feed_id),
                "status": status,
                "progress": progress,
                "message": message,
            },
        )

    @staticmethod
    def notify_product_update(product, users=None):
        """Notify about product updates"""
        from accounts.models import User

        # If no specific users, notify all employees and subscribed customers
        if users is None:
            users = User.objects.filter(
                models.Q(role__in=["admin", "employee"])
                | models.Q(
                    feed_subscriptions__subscription_type="product_updates",
                    feed_subscriptions__is_active=True,
                    feed_subscriptions__specific_products=product,
                )
            ).distinct()

        for user in users:
            if user.get_notification_preference("product_updates"):
                NotificationService.send_notification(
                    user=user,
                    notification_type="product_update",
                    title=f"Product Updated: {product.number}",
                    message=f"The product {product.sku} has been updated.",
                    content_object=product,
                    action_url=f"/products/{product.id}/",
                    action_label="View Product",
                )

    @staticmethod
    def notify_price_change(product, old_price, new_price, affected_users):
        """Notify about price changes"""
        for user in affected_users:
            if user.get_notification_preference("price_changes"):
                NotificationService.send_notification(
                    user=user,
                    notification_type="price_change",
                    title=f"Price Change: {product.number}",
                    message=f"Price changed from ${old_price} to ${new_price}",
                    content_object=product,
                    metadata={
                        "old_price": str(old_price),
                        "new_price": str(new_price),
                        "change_percentage": round(
                            ((new_price - old_price) / old_price) * 100, 2
                        ),
                    },
                    action_url=f"/products/{product.id}/",
                    action_label="View Product",
                )

    @staticmethod
    def notify_new_asset(asset, users=None):
        """Notify about new assets"""
        from accounts.models import User

        if users is None:
            # Notify employees and customers with access to the asset's categories
            users = User.objects.filter(
                models.Q(role__in=["admin", "employee"])
                | models.Q(
                    feed_subscriptions__subscription_type="new_assets",
                    feed_subscriptions__is_active=True,
                )
            ).distinct()

        for user in users:
            # Check if user can access this asset category
            categories = asset.categories.all()
            can_access = any(
                user.can_access_asset_category(cat.slug) for cat in categories
            )

            if can_access and user.get_notification_preference("new_assets"):
                NotificationService.send_notification(
                    user=user,
                    notification_type="new_asset",
                    title=f"New Asset Available: {asset.title}",
                    message=f"A new {asset.asset_type} has been added to the system.",
                    content_object=asset,
                    action_url=f"/assets/{asset.id}/",
                    action_label="View Asset",
                )

    @staticmethod
    def notify_feed_ready(feed_generation):
        """Notify when a data feed is ready"""
        user = feed_generation.feed.customer

        if user.get_notification_preference("feed_ready"):
            NotificationService.send_notification(
                user=user,
                notification_type="feed_ready",
                title=f"Data Feed Ready: {feed_generation.feed.name}",
                message=f"Your {feed_generation.feed.get_feed_type_display()} feed is ready for download.",
                content_object=feed_generation,
                metadata={
                    "feed_id": str(feed_generation.generation_id),
                    "row_count": feed_generation.row_count,
                    "file_size": feed_generation.file_size,
                },
                action_url=f"/feeds/download/{feed_generation.generation_id}/",
                action_label="Download Feed",
            )
