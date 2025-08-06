# src/audit/models.py - Enhanced version
import uuid
import json
from decimal import Decimal
from datetime import datetime
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

User = get_user_model()


class AuditLogManager(models.Manager):
    """Custom manager for audit logs"""

    def create_log(self, user, action, content_object, changes=None, metadata=None, request=None):
        """Create an audit log entry"""
        log_data = {
            'user': user,
            'action': action,
            'content_type': ContentType.objects.get_for_model(content_object),
            'object_id': content_object.pk,
            'object_repr': str(content_object)[:200],
            'changes': changes or {},
            'metadata': metadata or {},
        }

        if request:
            log_data.update({
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                'session_key': request.session.session_key,
                'request_id': getattr(request, 'id', str(uuid.uuid4())),
            })

        return self.create(**log_data)

    def _get_client_ip(self, request):
        """Get client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AuditLog(models.Model):
    """Enhanced audit log with rollback support"""

    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('ROLLBACK', 'Rollback'),
        ('BULK_UPDATE', 'Bulk Update'),
        ('BULK_DELETE', 'Bulk Delete'),
    ]

    # Basic audit info
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)

    # Object identification
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    object_repr = models.CharField(max_length=200, blank=True)

    # Change tracking
    changes = models.JSONField(default=dict, blank=True)
    previous_values = models.JSONField(default=dict, blank=True)  # For rollback
    metadata = models.JSONField(default=dict, blank=True)

    # Request context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    request_id = models.CharField(max_length=36, blank=True, db_index=True)

    # Rollback support
    can_rollback = models.BooleanField(default=True)
    rollback_data = models.JSONField(null=True, blank=True)
    parent_log = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='rollback_logs'
    )

    objects = AuditLogManager()

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['request_id']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} {self.content_type.model} by {self.user} at {self.timestamp}"

    def perform_rollback(self, user, request=None):
        """Perform rollback operation"""
        if not self.can_rollback or not self.rollback_data:
            raise ValueError("Rollback not available for this audit log")

        model_class = self.content_type.model_class()

        try:
            with transaction.atomic():
                # Get the object
                obj = model_class.objects.get(pk=self.object_id)

                # Store current state for audit
                current_state = {}
                for field, value in self.rollback_data.items():
                    if hasattr(obj, field):
                        current_state[field] = {
                            'old': getattr(obj, field),
                            'new': value
                        }
                        setattr(obj, field, value)

                # Set audit context
                obj._current_user = user
                obj._audit_action = 'ROLLBACK'
                obj._parent_audit_log = self

                obj.save()

                # Create rollback audit log
                AuditLog.objects.create_log(
                    user=user,
                    action='ROLLBACK',
                    content_object=obj,
                    changes=current_state,
                    metadata={
                        'rollback_from_log': self.id,
                        'rollback_timestamp': self.timestamp.isoformat(),
                    },
                    request=request
                )

                return True

        except model_class.DoesNotExist:
            raise ValueError("Object no longer exists")
        except Exception as e:
            raise ValueError(f"Rollback failed: {str(e)}")

    def get_formatted_changes(self):
        """Get changes formatted for display"""
        if not self.changes:
            return []

        formatted = []
        for field, change in self.changes.items():
            if isinstance(change, dict) and 'old' in change and 'new' in change:
                formatted.append({
                    'field': field.replace('_', ' ').title(),
                    'old_value': change.get('old', 'None'),
                    'new_value': change.get('new', 'None'),
                })
        return formatted


class ModelSnapshot(models.Model):
    """Complete model state snapshots for complex rollbacks"""

    SNAPSHOT_TYPES = [
        ('daily', 'Daily Snapshot'),
        ('manual', 'Manual Snapshot'),
        ('pre_bulk_operation', 'Pre-Bulk Operation'),
        ('pre_migration', 'Pre-Migration'),
        ('pre_deployment', 'Pre-Deployment'),
    ]

    # Object identification
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Snapshot data
    snapshot_data = models.JSONField()
    snapshot_hash = models.CharField(max_length=64, db_index=True)  # SHA-256 hash

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    snapshot_type = models.CharField(max_length=30, choices=SNAPSHOT_TYPES)
    description = models.TextField(blank=True)

    # Relationships
    related_logs = models.ManyToManyField(AuditLog, blank=True)

    class Meta:
        db_table = 'audit_snapshots'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['created_at', 'snapshot_type']),
            models.Index(fields=['snapshot_hash']),
        ]

    def __str__(self):
        return f"{self.snapshot_type} snapshot of {self.content_type.model} at {self.created_at}"

    def restore_snapshot(self, user, request=None):
        """Restore object to this snapshot state"""
        model_class = self.content_type.model_class()

        try:
            with transaction.atomic():
                obj = model_class.objects.get(pk=self.object_id)

                # Track changes
                changes = {}
                for field, value in self.snapshot_data.items():
                    if hasattr(obj, field):
                        old_value = getattr(obj, field)
                        if old_value != value:
                            changes[field] = {
                                'old': old_value,
                                'new': value
                            }
                            setattr(obj, field, value)

                if changes:
                    obj._current_user = user
                    obj._audit_action = 'ROLLBACK'
                    obj.save()

                    # Create audit log
                    AuditLog.objects.create_log(
                        user=user,
                        action='ROLLBACK',
                        content_object=obj,
                        changes=changes,
                        metadata={
                            'snapshot_id': self.id,
                            'snapshot_type': self.snapshot_type,
                            'snapshot_date': self.created_at.isoformat(),
                        },
                        request=request
                    )

                return True

        except model_class.DoesNotExist:
            raise ValueError("Object no longer exists")


class BulkOperation(models.Model):
    """Track bulk operations for audit purposes"""

    OPERATION_TYPES = [
        ('bulk_create', 'Bulk Create'),
        ('bulk_update', 'Bulk Update'),
        ('bulk_delete', 'Bulk Delete'),
        ('import', 'Data Import'),
        ('export', 'Data Export'),
        ('migration', 'Data Migration'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    # Operation identification
    operation_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    operation_type = models.CharField(max_length=30, choices=OPERATION_TYPES)

    # Content type
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)

    # Status and progress
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.PositiveIntegerField(default=0)  # 0-100
    total_items = models.PositiveIntegerField(default=0)
    processed_items = models.PositiveIntegerField(default=0)
    failed_items = models.PositiveIntegerField(default=0)

    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # User and context
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    description = models.TextField(blank=True)

    # Results and errors
    results = models.JSONField(default=dict, blank=True)
    errors = models.JSONField(default=list, blank=True)

    # Related audit logs
    audit_logs = models.ManyToManyField(AuditLog, blank=True)

    class Meta:
        db_table = 'audit_bulk_operations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['operation_id']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['content_type', 'operation_type']),
        ]

    def __str__(self):
        return f"{self.get_operation_type_display()} - {self.operation_id}"

    def start_operation(self):
        """Mark operation as started"""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])

    def complete_operation(self, success=True):
        """Mark operation as completed"""
        self.status = 'completed' if success else 'failed'
        self.completed_at = timezone.now()
        self.progress = 100 if success else self.progress
        self.save(update_fields=['status', 'completed_at', 'progress'])

    def update_progress(self, processed=None, failed=None):
        """Update operation progress"""
        if processed is not None:
            self.processed_items = processed
        if failed is not None:
            self.failed_items = failed

        if self.total_items > 0:
            self.progress = min(100, (self.processed_items * 100) // self.total_items)

        self.save(update_fields=['processed_items', 'failed_items', 'progress'])