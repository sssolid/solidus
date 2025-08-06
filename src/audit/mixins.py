# src/audit/mixins.py
from django.db import models
from django.contrib.contenttypes.models import ContentType
import threading

# Thread-local storage for audit context
_thread_locals = threading.local()


def set_audit_context(user=None, request=None, action=None, metadata=None):
    """Set audit context for current thread"""
    _thread_locals.user = user
    _thread_locals.request = request
    _thread_locals.action = action
    _thread_locals.metadata = metadata or {}


def get_audit_context():
    """Get audit context for current thread"""
    return {
        'user': getattr(_thread_locals, 'user', None),
        'request': getattr(_thread_locals, 'request', None),
        'action': getattr(_thread_locals, 'action', None),
        'metadata': getattr(_thread_locals, 'metadata', {}),
    }


class AuditMixin:
    """Mixin to add audit capabilities to models"""

    def save(self, *args, **kwargs):
        # Determine if this is a create or update
        is_create = self.pk is None
        action = 'CREATE' if is_create else 'UPDATE'

        # Get audit context
        context = get_audit_context()
        user = context.get('user') or getattr(self, '_current_user', None)
        request = context.get('request')
        audit_action = context.get('action') or getattr(self, '_audit_action', action)
        metadata = context.get('metadata', {})

        # Store old values for change tracking
        old_values = {}
        changes = {}

        if not is_create:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                for field in self._meta.fields:
                    field_name = field.name
                    old_value = getattr(old_instance, field_name)
                    new_value = getattr(self, field_name)

                    if old_value != new_value:
                        old_values[field_name] = old_value
                        changes[field_name] = {
                            'old': old_value,
                            'new': new_value
                        }
            except self.__class__.DoesNotExist:
                pass

        # Save the model
        super().save(*args, **kwargs)

        # Create audit log
        if user:
            from .models import AuditLog
            AuditLog.objects.create_log(
                user=user,
                action=audit_action,
                content_object=self,
                changes=changes,
                metadata={
                    **metadata,
                    'field_count': len(changes),
                    'model_version': getattr(self, 'version', 1),
                },
                request=request
            )

            # Store rollback data for non-delete operations
            if audit_action != 'DELETE' and old_values:
                # Store rollback data
                pass

    def delete(self, *args, **kwargs):
        # Get audit context
        context = get_audit_context()
        user = context.get('user') or getattr(self, '_current_user', None)
        request = context.get('request')
        metadata = context.get('metadata', {})

        # Store complete object state for potential restoration
        object_data = {}
        for field in self._meta.fields:
            object_data[field.name] = getattr(self, field.name)

        # Perform deletion
        result = super().delete(*args, **kwargs)

        # Create audit log
        if user:
            from .models import AuditLog
            AuditLog.objects.create_log(
                user=user,
                action='DELETE',
                content_object=self,
                changes={'deleted': True},
                metadata={
                    **metadata,
                    'object_data': object_data,
                    'can_restore': True,
                },
                request=request
            )

        return result