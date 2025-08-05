# src/core/models.py

import uuid
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class SystemSetting(models.Model):
    """System-wide configuration settings"""

    SETTING_TYPES = [
        ("string", "String"),
        ("integer", "Integer"),
        ("float", "Float"),
        ("boolean", "Boolean"),
        ("json", "JSON"),
    ]

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    setting_type = models.CharField(
        max_length=20, choices=SETTING_TYPES, default="string"
    )
    description = models.TextField(blank=True)
    is_public = models.BooleanField(
        default=False, help_text="Whether this setting is visible to non-staff users"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_settings"
        ordering = ["key"]

    def __str__(self):
        return f"{self.key} = {self.value}"

    def get_value(self):
        """Convert string value to appropriate type"""
        if self.setting_type == "integer":
            return int(self.value)
        elif self.setting_type == "float":
            return float(self.value)
        elif self.setting_type == "boolean":
            return self.value.lower() in ("true", "1", "yes")
        elif self.setting_type == "json":
            import json
            return json.loads(self.value)
        return self.value

    @classmethod
    def get(cls, key, default=None):
        """Get a setting value by key"""
        try:
            setting = cls.objects.get(key=key)
            return setting.get_value()
        except cls.DoesNotExist:
            return default


class TaskQueue(models.Model):
    """Simple task queue for background processing"""

    TASK_TYPES = [
        ("asset_processing", "Asset Processing"),
        ("feed_generation", "Feed Generation"),
        ("bulk_update", "Bulk Update"),
        ("notification", "Notification"),
        ("cleanup", "Cleanup"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    # Task identification
    task_id = models.UUIDField(default=uuid.uuid4, unique=True)
    task_type = models.CharField(max_length=30, choices=TASK_TYPES)

    # Task data
    task_data = models.JSONField(default=dict)
    priority = models.IntegerField(default=5)  # 1-10, lower is higher priority

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Execution details
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)

    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Results
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    # User who created the task
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tasks",
    )

    class Meta:
        db_table = "task_queue"
        ordering = ["priority", "created_at"]
        indexes = [
            models.Index(fields=["status", "scheduled_for"]),
            models.Index(fields=["task_type", "status"]),
            models.Index(fields=["task_id"]),
        ]

    def __str__(self):
        return f"{self.task_type} - {self.task_id}"

    def can_retry(self):
        """Check if task can be retried"""
        return self.attempts < self.max_attempts and self.status == "failed"

    def mark_processing(self):
        """Mark task as processing"""
        self.status = "processing"
        self.started_at = timezone.now()
        self.attempts += 1
        self.save(update_fields=["status", "started_at", "attempts"])

    def mark_completed(self, result=None):
        """Mark task as completed"""
        self.status = "completed"
        self.completed_at = timezone.now()
        if result:
            self.result = result
        self.save(update_fields=["status", "completed_at", "result"])

    def mark_failed(self, error_message):
        """Mark task as failed"""
        self.status = "failed"
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=["status", "completed_at", "error_message"])


class FileImport(models.Model):
    """Track file imports for bulk data updates"""

    IMPORT_TYPES = [
        ("products", "Products"),
        ("pricing", "Pricing"),
        ("inventory", "Inventory"),
        ("assets", "Assets"),
        ("fitment", "Fitment Data"),
    ]

    # Import identification
    import_id = models.UUIDField(default=uuid.uuid4, unique=True)
    import_type = models.CharField(max_length=30, choices=IMPORT_TYPES)

    # File information
    original_filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.BigIntegerField()
    file_hash = models.CharField(max_length=64)  # SHA-256 hash

    # Processing status
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        default="pending",
    )

    # Processing details
    total_rows = models.IntegerField(null=True, blank=True)
    processed_rows = models.IntegerField(default=0)
    successful_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)

    # Error tracking
    error_log = models.JSONField(default=list, blank=True)
    validation_errors = models.JSONField(default=list, blank=True)

    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # User who initiated the import
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="file_imports",
    )

    # Configuration
    import_config = models.JSONField(
        default=dict, blank=True
    )  # Column mappings, etc.

    class Meta:
        db_table = "file_imports"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["import_type", "status"]),
            models.Index(fields=["created_by", "created_at"]),
            models.Index(fields=["import_id"]),
        ]

    def __str__(self):
        return f"{self.import_type} import - {self.original_filename}"

    @property
    def progress_percentage(self):
        """Calculate import progress percentage"""
        if not self.total_rows:
            return 0
        return min(100, (self.processed_rows / self.total_rows) * 100)

    @property
    def success_rate(self):
        """Calculate success rate percentage"""
        if not self.processed_rows:
            return 0
        return (self.successful_rows / self.processed_rows) * 100

    def mark_processing(self):
        """Mark import as processing"""
        self.status = "processing"
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_completed(self):
        """Mark import as completed"""
        self.status = "completed"
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])

    def mark_failed(self, error_message):
        """Mark import as failed"""
        self.status = "failed"
        self.completed_at = timezone.now()
        if error_message:
            self.error_log.append(
                {"timestamp": timezone.now().isoformat(), "error": error_message}
            )
        self.save(update_fields=["status", "completed_at", "error_log"])

    def add_validation_error(self, row_number, field, error):
        """Add a validation error"""
        self.validation_errors.append(
            {"row": row_number, "field": field, "error": error}
        )
        self.save(update_fields=["validation_errors"])


class Notification(models.Model):
    """Real-time notifications for users"""

    NOTIFICATION_TYPES = [
        ("info", "Information"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("error", "Error"),
        ("product_update", "Product Update"),
        ("price_change", "Price Change"),
        ("new_asset", "New Asset"),
        ("feed_ready", "Feed Ready"),
        ("system", "System"),
    ]

    # Recipient
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )

    # Notification details
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()

    # Related object (optional)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    # Status
    is_read = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)

    # Actions
    action_url = models.CharField(max_length=500, blank=True)
    action_label = models.CharField(max_length=100, blank=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"]),
            models.Index(fields=["notification_type"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    def mark_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    def mark_archived(self):
        """Archive notification"""
        self.is_archived = True
        self.save(update_fields=["is_archived"])

    @property
    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    @classmethod
    def create_notification(
        cls,
        user,
        notification_type,
        title,
        message,
        content_object=None,
        action_url="",
        action_label="",
        metadata=None,
        expires_in_hours=None,
    ):
        """Helper method to create notifications"""
        expires_at = None
        if expires_in_hours:
            expires_at = timezone.now() + timezone.timedelta(hours=expires_in_hours)

        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            content_object=content_object,
            action_url=action_url,
            action_label=action_label,
            metadata=metadata or {},
            expires_at=expires_at,
        )