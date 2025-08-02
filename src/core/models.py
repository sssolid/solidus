# src/core/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import uuid


class Notification(models.Model):
    """Real-time notifications for users"""
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('product_update', 'Product Update'),
        ('price_change', 'Price Change'),
        ('new_asset', 'New Asset'),
        ('feed_ready', 'Feed Ready'),
        ('system', 'System'),
    ]

    # Recipient
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    # Notification details
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()

    # Related object (optional)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

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
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.user} - {self.title}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @classmethod
    def create_for_user(cls, user, notification_type, title, message, **kwargs):
        """Helper to create a notification"""
        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            **kwargs
        )

    @classmethod
    def cleanup_expired(cls):
        """Remove expired notifications"""
        return cls.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()


class SystemSetting(models.Model):
    """System-wide configuration settings"""
    SETTING_TYPES = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
    ]

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    setting_type = models.CharField(max_length=10, choices=SETTING_TYPES, default='string')

    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)  # Can be exposed to frontend

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'system_settings'
        ordering = ['key']

    def __str__(self):
        return self.key

    def get_value(self):
        """Get typed value"""
        if self.setting_type == 'integer':
            return int(self.value)
        elif self.setting_type == 'float':
            return float(self.value)
        elif self.setting_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes')
        elif self.setting_type == 'json':
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
        ('asset_processing', 'Asset Processing'),
        ('feed_generation', 'Feed Generation'),
        ('bulk_update', 'Bulk Update'),
        ('notification', 'Notification'),
        ('cleanup', 'Cleanup'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    # Task identification
    task_id = models.UUIDField(default=uuid.uuid4, unique=True)
    task_type = models.CharField(max_length=30, choices=TASK_TYPES)

    # Task data
    task_data = models.JSONField(default=dict)
    priority = models.IntegerField(default=5)  # 1-10, lower is higher priority

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

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
        related_name='created_tasks'
    )

    class Meta:
        db_table = 'task_queue'
        ordering = ['priority', 'created_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_for']),
            models.Index(fields=['task_type', 'status']),
            models.Index(fields=['task_id']),
        ]

    def __str__(self):
        return f"{self.task_type} - {self.task_id}"

    def can_retry(self):
        """Check if task can be retried"""
        return self.attempts < self.max_attempts and self.status == 'failed'

    def mark_processing(self):
        """Mark task as processing"""
        self.status = 'processing'
        self.started_at = timezone.now()
        self.attempts += 1
        self.save(update_fields=['status', 'started_at', 'attempts'])

    def mark_completed(self, result=None):
        """Mark task as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if result:
            self.result = result
        self.save(update_fields=['status', 'completed_at', 'result'])

    def mark_failed(self, error_message):
        """Mark task as failed"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'error_message'])


class FileImport(models.Model):
    """Track file imports for bulk data updates"""
    IMPORT_TYPES = [
        ('products', 'Products'),
        ('pricing', 'Pricing'),
        ('inventory', 'Inventory'),
        ('assets', 'Assets'),
        ('fitment', 'Fitment Data'),
    ]

    # Import identification
    import_id = models.UUIDField(default=uuid.uuid4, unique=True)
    import_type = models.CharField(max_length=20, choices=IMPORT_TYPES)

    # File info
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.BigIntegerField()

    # Processing status
    status = models.CharField(
        max_length=20,
        choices=[
            ('uploaded', 'Uploaded'),
            ('validating', 'Validating'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='uploaded'
    )

    # Statistics
    total_rows = models.IntegerField(default=0)
    processed_rows = models.IntegerField(default=0)
    successful_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)

    # Validation results
    validation_errors = models.JSONField(default=list, blank=True)
    processing_errors = models.JSONField(default=list, blank=True)

    # Options
    options = models.JSONField(default=dict, blank=True)  # Import-specific options

    # Timing
    uploaded_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # User
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='file_imports'
    )

    class Meta:
        db_table = 'file_imports'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['import_id']),
            models.Index(fields=['import_type', 'status']),
            models.Index(fields=['uploaded_by', 'uploaded_at']),
        ]

    def __str__(self):
        return f"{self.import_type} - {self.filename}"

    @property
    def progress_percentage(self):
        """Calculate progress percentage"""
        if self.total_rows == 0:
            return 0
        return int((self.processed_rows / self.total_rows) * 100)