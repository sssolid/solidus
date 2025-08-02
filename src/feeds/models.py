# src/feeds/models.py
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone


class DataFeed(models.Model):
    """Data feed configurations for customers"""

    FEED_TYPES = [
        ("product_catalog", "Product Catalog"),
        ("inventory", "Inventory"),
        ("pricing", "Pricing"),
        ("assets", "Digital Assets"),
        ("fitment", "Vehicle Fitment"),
        ("custom", "Custom"),
    ]

    FORMAT_CHOICES = [
        ("csv", "CSV"),
        ("xml", "XML"),
        ("json", "JSON"),
        ("xlsx", "Excel"),
        ("txt", "Text (Tab-delimited)"),
    ]

    FREQUENCY_CHOICES = [
        ("manual", "Manual"),
        ("hourly", "Hourly"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]

    # Basic info
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="data_feeds"
    )

    # Feed configuration
    feed_type = models.CharField(max_length=30, choices=FEED_TYPES)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)

    # Content filters
    categories = models.ManyToManyField("products.Category", blank=True)
    brands = models.ManyToManyField("products.Brand", blank=True)
    product_tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)

    # Field configuration
    included_fields = ArrayField(models.CharField(max_length=50), default=list)
    custom_field_mapping = models.JSONField(default=dict, blank=True)

    # Schedule
    is_active = models.BooleanField(default=True)
    frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default="manual"
    )
    schedule_time = models.TimeField(null=True, blank=True)  # For daily feeds
    schedule_day = models.IntegerField(
        null=True, blank=True
    )  # 0-6 for weekly, 1-31 for monthly

    # Delivery configuration
    delivery_method = models.CharField(
        max_length=20,
        choices=[
            ("download", "Direct Download"),
            ("email", "Email"),
            ("ftp", "FTP"),
            ("sftp", "SFTP"),
            ("api", "API Webhook"),
        ],
        default="download",
    )
    delivery_config = models.JSONField(
        default=dict, blank=True
    )  # FTP credentials, email, etc.

    # Options
    include_images = models.BooleanField(default=False)
    compress_output = models.BooleanField(default=False)
    encrypt_output = models.BooleanField(default=False)

    # Tracking
    last_generated = models.DateTimeField(null=True, blank=True)
    last_delivered = models.DateTimeField(null=True, blank=True)
    generation_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "data_feeds"
        ordering = ["customer", "name"]
        indexes = [
            models.Index(fields=["customer", "is_active"]),
            models.Index(fields=["frequency", "is_active"]),
        ]

    def __str__(self):
        return f"{self.customer.company_name or self.customer.username} - {self.name}"

    def get_next_run_time(self):
        """Calculate next scheduled run time"""
        if self.frequency == "manual" or not self.is_active:
            return None

        now = timezone.now()

        if self.frequency == "hourly":
            return now + timedelta(hours=1)
        elif self.frequency == "daily" and self.schedule_time:
            next_run = timezone.datetime.combine(now.date(), self.schedule_time)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run
        elif self.frequency == "weekly" and self.schedule_day is not None:
            days_ahead = self.schedule_day - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return now + timedelta(days=days_ahead)
        elif self.frequency == "monthly" and self.schedule_day:
            # Handle month-end cases
            next_month = now.replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1)
            try:
                return now.replace(day=self.schedule_day)
            except ValueError:
                # Day doesn't exist in this month (e.g., Feb 31)
                return next_month

        return None


class FeedGeneration(models.Model):
    """Track individual feed generation instances"""

    feed = models.ForeignKey(
        DataFeed, on_delete=models.CASCADE, related_name="generations"
    )

    # Generation details
    generation_id = models.UUIDField(default=uuid.uuid4, unique=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("generating", "Generating"),
            ("generated", "Generated"),
            ("delivering", "Delivering"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending",
    )

    # File info
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    row_count = models.IntegerField(null=True, blank=True)

    # Delivery info
    delivered_at = models.DateTimeField(null=True, blank=True)
    delivery_status = models.CharField(max_length=50, blank=True)
    delivery_details = models.JSONField(default=dict, blank=True)

    # Error tracking
    error_message = models.TextField(blank=True)
    error_details = models.JSONField(default=dict, blank=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "feed_generations"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["feed", "started_at"]),
            models.Index(fields=["generation_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.feed.name} - {self.started_at}"

    @property
    def duration(self):
        """Calculate generation duration"""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None


class FeedSubscription(models.Model):
    """Customer subscriptions to specific data changes"""

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="feed_subscriptions",
    )

    # Subscription type
    subscription_type = models.CharField(
        max_length=30,
        choices=[
            ("new_products", "New Products"),
            ("price_changes", "Price Changes"),
            ("inventory_updates", "Inventory Updates"),
            ("product_updates", "Product Updates"),
            ("new_assets", "New Assets"),
            ("discontinued", "Discontinued Products"),
        ],
    )

    # Filters
    categories = models.ManyToManyField("products.Category", blank=True)
    brands = models.ManyToManyField("products.Brand", blank=True)
    specific_products = models.ManyToManyField("products.Product", blank=True)

    # Notification settings
    is_active = models.BooleanField(default=True)
    notification_method = models.CharField(
        max_length=20,
        choices=[
            ("email", "Email"),
            ("webhook", "Webhook"),
            ("in_app", "In-App Notification"),
        ],
        default="email",
    )
    notification_config = models.JSONField(default=dict, blank=True)

    # Frequency limiting
    min_interval_hours = models.IntegerField(
        default=24
    )  # Minimum hours between notifications
    last_notified = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "feed_subscriptions"
        unique_together = [["customer", "subscription_type"]]
        indexes = [
            models.Index(fields=["customer", "is_active"]),
            models.Index(fields=["subscription_type", "is_active"]),
        ]

    def __str__(self):
        return f"{self.customer} - {self.get_subscription_type_display()}"

    def can_notify(self):
        """Check if enough time has passed since last notification"""
        if not self.last_notified:
            return True

        hours_passed = (timezone.now() - self.last_notified).total_seconds() / 3600
        return hours_passed >= self.min_interval_hours


class ChangeNotification(models.Model):
    """Track notifications sent for data changes"""

    subscription = models.ForeignKey(
        FeedSubscription, on_delete=models.CASCADE, related_name="notifications"
    )

    # Notification details
    notification_id = models.UUIDField(default=uuid.uuid4, unique=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    # Content
    subject = models.CharField(max_length=255)
    content = models.TextField()
    change_summary = models.JSONField(default=dict)

    # Delivery
    delivery_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    delivery_details = models.JSONField(default=dict, blank=True)

    # Tracking
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "change_notifications"
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["subscription", "sent_at"]),
            models.Index(fields=["notification_id"]),
        ]

    def __str__(self):
        return f"{self.subscription} - {self.sent_at}"
