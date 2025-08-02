# src/audit/signals.py
import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out

# Bulk operation tracking
from django.db.models.signals import m2m_changed, post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

from .models import AuditLog, ModelSnapshot

logger = logging.getLogger("solidus.audit")
User = get_user_model()

# Models to track for audit
AUDITED_MODELS = [
    "products.Product",
    "products.CustomerPricing",
    "assets.Asset",
    "accounts.User",
    "feeds.DataFeed",
]


def get_model_from_string(model_string):
    """Get model class from app.Model string"""
    try:
        app_label, model_name = model_string.split(".")
        from django.apps import apps

        return apps.get_model(app_label, model_name)
    except Exception as e:
        import logging

        logger = logging.getLogger("solidus.audit")
        logger.error(f"Error in audit signals: {str(e)}")
        return None


def get_field_changes(old_instance, new_instance):
    """Compare two model instances and return field changes"""
    if not old_instance:
        return {}

    changes = {}

    # Get all fields
    for field in new_instance._meta.fields:
        field_name = field.name
        old_value = getattr(old_instance, field_name)
        new_value = getattr(new_instance, field_name)

        # Skip if values are the same
        if old_value == new_value:
            continue

        # Convert values to serializable format
        if hasattr(old_value, "isoformat"):
            old_value = old_value.isoformat()
        if hasattr(new_value, "isoformat"):
            new_value = new_value.isoformat()

        changes[field_name] = {
            "old": str(old_value) if old_value is not None else None,
            "new": str(new_value) if new_value is not None else None,
        }

    return changes


class AuditSignalHandler:
    """Handle model signals for audit logging"""

    @staticmethod
    def get_current_user():
        """Get current user from thread local storage"""
        from threading import local

        _thread_locals = local()
        return getattr(_thread_locals, "user", None)

    @staticmethod
    def should_audit_model(sender):
        """Check if model should be audited"""
        model_string = f"{sender._meta.app_label}.{sender.__name__}"
        return model_string in AUDITED_MODELS

    @staticmethod
    @receiver(pre_save)
    def log_model_changes(sender, instance, **kwargs):
        """Log model changes before save"""
        if not AuditSignalHandler.should_audit_model(sender):
            return

        # Store old instance for comparison in post_save
        if instance.pk:
            try:
                instance._old_instance = sender.objects.get(pk=instance.pk)
            except sender.DoesNotExist:
                instance._old_instance = None
        else:
            instance._old_instance = None

    @staticmethod
    @receiver(post_save)
    def log_model_save(sender, instance, created, **kwargs):
        """Log model save after it happens"""
        if not AuditSignalHandler.should_audit_model(sender):
            return

        try:
            user = AuditSignalHandler.get_current_user()

            if created:
                # Log creation
                AuditLog.log_action(
                    user=user,
                    action="create",
                    obj=instance,
                    metadata={"model": f"{sender._meta.app_label}.{sender.__name__}"},
                )

                # Create initial snapshot
                ModelSnapshot.create_snapshot(
                    obj=instance, user=user, description="Initial creation"
                )
            else:
                # Log update
                old_instance = getattr(instance, "_old_instance", None)
                changes = get_field_changes(old_instance, instance)

                if changes:
                    audit_log = AuditLog.log_action(
                        user=user,
                        action="update",
                        obj=instance,
                        changes=changes,
                        metadata={
                            "model": f"{sender._meta.app_label}.{sender.__name__}"
                        },
                    )

                    # Create snapshot for significant changes
                    significant_fields = [
                        "price",
                        "msrp",
                        "is_active",
                        "customer_pricing",
                    ]
                    if any(field in changes for field in significant_fields):
                        ModelSnapshot.create_snapshot(
                            obj=instance,
                            user=user,
                            description=f"Update: {', '.join(changes.keys())}",
                            audit_log=audit_log,
                        )

        except Exception as e:
            logger.error(f"Error in audit signal handler: {str(e)}")

    @staticmethod
    @receiver(pre_delete)
    def log_model_delete(sender, instance, **kwargs):
        """Log model deletion"""
        if not AuditSignalHandler.should_audit_model(sender):
            return

        try:
            user = AuditSignalHandler.get_current_user()

            # Create final snapshot before deletion
            ModelSnapshot.create_snapshot(
                obj=instance, user=user, description="Final state before deletion"
            )

            # Log deletion
            AuditLog.log_action(
                user=user,
                action="delete",
                obj=instance,
                metadata={
                    "model": f"{sender._meta.app_label}.{sender.__name__}",
                    "deleted_data": model_to_dict(instance),
                },
            )

        except Exception as e:
            logger.error(f"Error in delete signal handler: {str(e)}")


# Authentication signals
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log user login"""
    AuditLog.log_action(
        user=user,
        action="login",
        metadata={
            "ip_address": AuditLog.get_client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        },
        request=request,
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout"""
    if user:
        AuditLog.log_action(user=user, action="logout", request=request)


@receiver(m2m_changed)
def log_m2m_changes(sender, instance, action, pk_set, **kwargs):
    """Log many-to-many relationship changes"""
    if action in ["post_add", "post_remove", "post_clear"]:
        model_string = f"{instance._meta.app_label}.{instance.__class__.__name__}"
        if model_string in AUDITED_MODELS:
            user = AuditSignalHandler.get_current_user()

            AuditLog.log_action(
                user=user,
                action="update",
                obj=instance,
                metadata={
                    "m2m_action": action,
                    "m2m_field": sender._meta.db_table,
                    "pk_set": list(pk_set) if pk_set else [],
                },
            )
