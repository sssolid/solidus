# src/audit/models.py

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import JSONField
from django.forms.models import model_to_dict
from django.utils import timezone


class AuditLog(models.Model):
    """Comprehensive audit log for all model changes"""

    ACTION_CHOICES = [
        ("create", "Create"),
        ("update", "Update"),
        ("delete", "Delete"),
        ("view", "View"),
        ("download", "Download"),
        ("login", "Login"),
        ("logout", "Logout"),
        ("bulk_action", "Bulk Action"),
    ]

    # User who performed the action
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    # Action details
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    # Object being acted upon
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")
    object_repr = models.CharField(max_length=255, blank=True)

    # Change details
    changes = JSONField(default=dict, blank=True)  # Field changes for updates
    old_values = JSONField(default=dict, blank=True)  # Previous values
    new_values = JSONField(default=dict, blank=True)  # New values

    # Additional context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_id = models.CharField(
        max_length=50, blank=True
    )  # For correlating related actions

    # Metadata
    metadata = JSONField(default=dict, blank=True)  # Additional contextual information

    class Meta:
        db_table = "audit_logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["request_id"]),
        ]

    def __str__(self):
        return f"{self.user} {self.action} {self.object_repr} at {self.timestamp}"

    @classmethod
    def log_action(
        cls, user, action, obj=None, changes=None, metadata=None, request=None
    ):
        """Helper method to create audit log entries"""
        log_entry = cls(user=user, action=action)

        if obj:
            log_entry.content_type = ContentType.objects.get_for_model(obj)
            log_entry.object_id = obj.pk
            log_entry.object_repr = str(obj)[:255]

        if changes:
            log_entry.changes = changes
            log_entry.old_values = changes.get("old", {})
            log_entry.new_values = changes.get("new", {})

        if metadata:
            log_entry.metadata = metadata

        if request:
            log_entry.ip_address = cls.get_client_ip(request)
            log_entry.user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
            log_entry.request_id = getattr(request, "id", "")

        log_entry.save()
        return log_entry

    @staticmethod
    def get_client_ip(request):
        """Get client IP from request"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def get_changes_display(self):
        """Get human-readable changes"""
        if not self.changes:
            return "No changes recorded"

        display_changes = []
        for field, values in self.changes.items():
            if isinstance(values, dict) and "old" in values and "new" in values:
                display_changes.append(
                    f"{field}: '{values['old']}' → '{values['new']}'"
                )
        return ", ".join(display_changes)


class ModelSnapshot(models.Model):
    """Store complete model states for rollback capability"""

    # Reference to the model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()

    # Snapshot data
    snapshot_data = JSONField()
    version = models.IntegerField(default=1)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="model_snapshots",
    )

    # Related audit log
    audit_log = models.ForeignKey(
        AuditLog,
        on_delete=models.CASCADE,
        related_name="snapshots",
        null=True,
        blank=True,
    )

    description = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "model_snapshots"
        ordering = ["-created_at"]
        unique_together = [["content_type", "object_id", "version"]]
        indexes = [
            models.Index(fields=["content_type", "object_id", "created_at"]),
        ]

    def __str__(self):
        return f"Snapshot v{self.version} of {self.content_type} #{self.object_id}"

    @classmethod
    def create_snapshot(cls, obj, user=None, description="", audit_log=None):
        """Create a snapshot of a model instance"""
        content_type = ContentType.objects.get_for_model(obj)

        # Get the latest version number
        latest_version = (
            cls.objects.filter(content_type=content_type, object_id=obj.pk).aggregate(
                max_version=models.Max("version")
            )["max_version"]
            or 0
        )

        # Serialize the model instance
        snapshot_data = model_to_dict(obj)

        # Convert non-serializable fields
        for key, value in snapshot_data.items():
            if hasattr(value, "isoformat"):  # datetime objects
                snapshot_data[key] = value.isoformat()
            elif hasattr(value, "all"):  # Many-to-many fields
                snapshot_data[key] = list(value.values_list("pk", flat=True))

        snapshot = cls.objects.create(
            content_type=content_type,
            object_id=obj.pk,
            snapshot_data=snapshot_data,
            version=latest_version + 1,
            created_by=user,
            description=description,
            audit_log=audit_log,
        )

        return snapshot

    def restore(self):
        """Restore the model to this snapshot state"""
        model_class = self.content_type.model_class()
        obj = model_class.objects.get(pk=self.object_id)

        # Update fields from snapshot
        for field, value in self.snapshot_data.items():
            if hasattr(obj, field) and not field.endswith("_id"):
                setattr(obj, field, value)

        obj.save()

        # Log the restoration
        AuditLog.log_action(
            user=self.created_by,
            action="update",
            obj=obj,
            metadata={
                "restored_from_snapshot": self.id,
                "restored_to_version": self.version,
            },
        )

        return obj


class BulkOperation(models.Model):
    """Track bulk operations for audit purposes"""

    operation_id = models.CharField(max_length=50, unique=True)
    operation_type = models.CharField(max_length=50)

    # User who performed the operation
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="bulk_operations",
    )

    # Operation details
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Stats
    total_items = models.IntegerField(default=0)
    processed_items = models.IntegerField(default=0)
    failed_items = models.IntegerField(default=0)

    # Status
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

    # Results
    results = JSONField(default=dict, blank=True)
    error_details = JSONField(default=list, blank=True)

    class Meta:
        db_table = "bulk_operations"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["operation_id"]),
            models.Index(fields=["user", "started_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.operation_type} by {self.user} - {self.status}"
