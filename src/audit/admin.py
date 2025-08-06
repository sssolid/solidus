# src/audit/admin.py - Fixed version
import json
import logging
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import AuditLog, BulkOperation, ModelSnapshot

logger = logging.getLogger("audit.admin")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Enhanced audit log administration"""

    list_display = [
        'timestamp',
        'user_display',
        'action',
        'object_repr_short',
        'model_name',
        'ip_address',
        'has_changes',
        'request_id_short',
        'can_rollback',
    ]

    list_filter = [
        'action',
        'timestamp',
        'content_type',
        'user',
        'can_rollback'
    ]

    search_fields = [
        'user__username',
        'user__email',
        'object_repr',
        'request_id',
        'ip_address',
    ]

    readonly_fields = [
        'timestamp',
        'user',
        'action',
        'content_type',
        'object_id',
        'object_repr',
        'ip_address',
        'user_agent',
        'request_id',
        'changes_display',
        'metadata_display',
        'content_object_link',
    ]

    fieldsets = (
        (
            "Action Information",
            {
                "fields": (
                    'timestamp',
                    'user',
                    'action',
                    'content_object_link'
                )
            },
        ),
        (
            "Object Details",
            {
                "fields": ('content_type', 'object_id', 'object_repr'),
                "classes": ('collapse',),
            },
        ),
        (
            'Changes',
            {
                'fields': ('changes_display',),
                'classes': ('collapse',)
            }
        ),
        (
            "Request Information",
            {
                "fields": ('ip_address', 'user_agent', 'request_id'),
                "classes": ('collapse',),
            },
        ),
        (
            'Metadata',
            {
                'fields': ('metadata_display',),
                'classes': ('collapse',)
            }
        )
    )

    date_hierarchy = "timestamp"

    def user_display(self, obj):
        """Display user with link"""
        if obj.user:
            try:
                url = reverse('admin:auth_user_change', args=[obj.user.pk])
                return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name() or obj.user.username)
            except:
                return obj.user.get_full_name() or obj.user.username
        return "System"

    user_display.short_description = "User"
    user_display.admin_order_field = "user"

    def object_repr_short(self, obj):
        """Display shortened object representation"""
        if obj.object_repr:
            if len(obj.object_repr) > 50:
                return obj.object_repr[:47] + "..."
            return obj.object_repr
        return "N/A"

    object_repr_short.short_description = "Object"
    object_repr_short.admin_order_field = "object_repr"

    def model_name(self, obj):
        """Display model name"""
        if obj.content_type:
            return f"{obj.content_type.app_label}.{obj.content_type.model}"
        return "N/A"

    model_name.short_description = "Model"
    model_name.admin_order_field = "content_type"

    def has_changes(self, obj):
        """Show if audit log has changes recorded"""
        if obj.changes:
            return format_html('<span style="color: green;">✓ ({})</span>', len(obj.changes))
        return format_html('<span style="color: gray;">✗</span>')

    has_changes.short_description = "Changes"

    def request_id_short(self, obj):
        """Display shortened request ID"""
        if obj.request_id:
            return (
                obj.request_id[:8] + "..."
                if len(obj.request_id) > 8
                else obj.request_id
            )
        return "N/A"

    request_id_short.short_description = "Request ID"

    def content_object_link(self, obj):
        """Display link to related object"""
        if obj.content_object:
            try:
                url = reverse(
                    f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change",
                    args=[obj.object_id],
                )
                return format_html('<a href="{}">{}</a>', url, obj.content_object)
            except Exception as e:
                logger.error(f"Error getting admin URL for {obj}: {str(e)}")
                return str(obj.content_object)
        return "Deleted or N/A"

    content_object_link.short_description = "Related Object"

    def changes_display(self, obj):
        """Display changes in formatted way"""
        if obj.changes:
            items = []
            for field, values in list(obj.changes.items())[:10]:
                if isinstance(values, dict) and "old" in values and "new" in values:
                    old_val = values["old"] or "None"
                    new_val = values["new"] or "None"
                    if len(str(old_val)) > 50:
                        old_val = str(old_val)[:47] + "..."
                    if len(str(new_val)) > 50:
                        new_val = str(new_val)[:47] + "..."
                    items.append(f"<strong>{field}:</strong> '{old_val}' → '{new_val}'")

            html = "<br>".join(items)
            if len(obj.changes) > 10:
                html += f"<br><em>... and {len(obj.changes) - 10} more fields</em>"
            return mark_safe(html)
        return "No changes recorded"

    changes_display.short_description = "Changes"

    def metadata_display(self, obj):
        """Display metadata"""
        if obj.metadata:
            items = []
            for key, value in list(obj.metadata.items())[:5]:
                items.append(f"<strong>{key}:</strong> {value}")
            html = "<br>".join(items)
            if len(obj.metadata) > 5:
                html += f"<br><em>... and {len(obj.metadata) - 5} more</em>"
            return mark_safe(html)
        return "No metadata"

    metadata_display.short_description = "Metadata"

    def can_rollback(self, obj):
        """Show if rollback is possible"""
        if obj.can_rollback and obj.rollback_data:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: gray;">✗</span>')

    can_rollback.short_description = "Rollback"


@admin.register(BulkOperation)
class BulkOperationAdmin(admin.ModelAdmin):
    """Bulk operation administration"""

    list_display = [
        'operation_id',
        'operation_type',
        'content_type',
        'status',
        'progress_display',
        'created_by',
        'created_at',
    ]

    list_filter = [
        'operation_type',
        'status',
        'content_type',
        'created_at',
    ]

    search_fields = [
        'operation_id',
        'description',
        'created_by__username',
    ]

    readonly_fields = [
        'operation_id',
        'created_at',
        'started_at',
        'completed_at',
        'get_results_display',
        'get_error_details_display',
    ]

    fieldsets = (
        ("Operation Information", {
            "fields": ("operation_id", "operation_type", "user", "status")
        }),
        ("Progress", {
            "fields": ("progress_display", "total_items", "processed_items", "failed_items")
        }),
        ("Timing", {
            "fields": ("started_at", "completed_at", "duration_display"),
            "classes": ("collapse",),
        }),
        ("Results", {
            "fields": ("get_results_display",),
            "classes": ("collapse",)
        }),
        ("Errors", {
            "fields": ("get_error_details_display",),
            "classes": ("collapse",)
        }),
    )

    def progress_display(self, obj):
        """Display operation progress with bar"""
        if obj.total_items > 0:
            percentage = (obj.processed_items / obj.total_items) * 100
            color = 'green' if percentage == 100 else 'red' if obj.failed_items > 0 else 'blue'
            return format_html(
                '<div style="width: 100px; background: #f0f0f0; border-radius: 3px;">'
                '<div style="width: {}%; background: {}; height: 20px; border-radius: 3px;"></div>'
                '</div>'
                '<small>{}/{} ({}%)</small>',
                percentage, color, obj.processed_items, obj.total_items, round(percentage, 1)
            )
        return f"{obj.progress}%"

    progress_display.short_description = "Progress"

    def duration_display(self, obj):
        """Display operation duration"""
        if obj.started_at and obj.completed_at:
            duration = obj.completed_at - obj.started_at
            total_seconds = int(duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return "Not completed"

    duration_display.short_description = "Duration"

    def get_results_display(self, obj):
        """Display formatted operation results"""
        if obj.results:
            return format_html('<pre>{}</pre>', json.dumps(obj.results, indent=2))
        return "No results"

    get_results_display.short_description = "Results"

    def get_error_details_display(self, obj):
        """Display formatted error details"""
        if hasattr(obj, 'errors') and obj.errors:
            return format_html('<pre style="color: red;">{}</pre>', json.dumps(obj.errors, indent=2))
        return "No errors"

    get_error_details_display.short_description = "Error Details"


@admin.register(ModelSnapshot)
class ModelSnapshotAdmin(admin.ModelAdmin):
    """Model snapshot administration"""

    list_display = [
        'content_object',
        'snapshot_type',
        'created_at',
        'created_by',
        'snapshot_size',
    ]

    list_filter = [
        'snapshot_type',
        'content_type',
        'created_at',
    ]

    search_fields = [
        'description',
        'created_by__username',
    ]

    readonly_fields = [
        'snapshot_hash',
        'created_at',
        'snapshot_data_display',
    ]

    def snapshot_size(self, obj):
        """Display snapshot data size"""
        import sys
        size = sys.getsizeof(str(obj.snapshot_data))
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    snapshot_size.short_description = "Size"

    def snapshot_data_display(self, obj):
        """Display formatted snapshot data"""
        if obj.snapshot_data:
            return mark_safe("<pre>" + json.dumps(obj.snapshot_data, indent=2) + "</pre>")
        return "No data"

    snapshot_data_display.short_description = "Snapshot Data"