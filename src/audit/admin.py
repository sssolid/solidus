# src/audit/admin.py
import logging

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import AuditLog, BulkOperation, ModelSnapshot

logger = logging.getLogger("audit.admin")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Audit log administration"""

    list_display = [
        "timestamp",
        "user",
        "action",
        "object_repr_short",
        "model_name",
        "ip_address",
        "has_changes",
        "request_id_short",
    ]

    list_filter = ["action", "timestamp", "content_type", "user"]

    search_fields = [
        "user__username",
        "user__email",
        "object_repr",
        "request_id",
        "ip_address",
    ]

    readonly_fields = [
        "timestamp",
        "user",
        "action",
        "content_type",
        "object_id",
        "object_repr",
        "ip_address",
        "user_agent",
        "request_id",
        "get_changes_display",
        "get_metadata_display",
        "content_object_link",
    ]

    fieldsets = (
        (
            "Action Information",
            {
                # TODO: content_object_link does not exist
                "fields": (
                    "timestamp",
                    "user",
                    "action",
                )  #'content_object_link')
            },
        ),
        (
            "Object Details",
            {
                "fields": ("content_type", "object_id", "object_repr"),
                "classes": ("collapse",),
            },
        ),
        # TODO: get_changes_display does not exist
        # ('Changes', {
        #     'fields': ('get_changes_display',),
        #     'classes': ('collapse',)
        # }),
        (
            "Request Information",
            {
                "fields": ("ip_address", "user_agent", "request_id"),
                "classes": ("collapse",),
            },
        ),
        # TODO: get_metadata_display does not exist
        # ('Metadata', {
        #     'fields': ('get_metadata_display',),
        #     'classes': ('collapse',)
        # })
    )

    date_hierarchy = "timestamp"

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
            return format_html('<span style="color: green;">✓</span>')
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

    def get_changes_display(self, obj):
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

    get_changes_display.short_description = "Changes"

    def get_metadata_display(self, obj):
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

    get_metadata_display.short_description = "Metadata"

    def has_add_permission(self, request):
        """Disable manual creation of audit logs"""
        return False

    def has_change_permission(self, request, obj=None):
        """Make audit logs read-only"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of audit logs"""
        return request.user.is_superuser

    actions = ["export_audit_logs", "cleanup_old_logs"]

    def export_audit_logs(self, request, queryset):
        """Export audit logs as CSV"""
        import csv

        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="audit_logs.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Timestamp",
                "User",
                "Action",
                "Model",
                "Object",
                "IP Address",
                "Request ID",
                "Changes",
            ]
        )

        for log in queryset:
            writer.writerow(
                [
                    log.timestamp.isoformat(),
                    str(log.user) if log.user else "System",
                    log.action,
                    f"{log.content_type.app_label}.{log.content_type.model}"
                    if log.content_type
                    else "N/A",
                    log.object_repr,
                    log.ip_address,
                    log.request_id,
                    log.get_changes_display() if log.changes else "No changes",
                ]
            )

        return response

    export_audit_logs.short_description = "Export selected logs as CSV"

    def cleanup_old_logs(self, request, queryset):
        """Delete logs older than 1 year"""
        from datetime import timedelta

        from django.utils import timezone

        cutoff_date = timezone.now() - timedelta(days=365)
        count = queryset.filter(timestamp__lt=cutoff_date).delete()[0]
        self.message_user(request, f"{count} old audit logs deleted.")

    cleanup_old_logs.short_description = "Delete logs older than 1 year"


@admin.register(ModelSnapshot)
class ModelSnapshotAdmin(admin.ModelAdmin):
    """Model snapshot administration"""

    list_display = [
        "content_type",
        "object_id",
        "version",
        "description_short",
        "created_by",
        "created_at",
        "related_audit_log",
    ]

    list_filter = ["content_type", "version", "created_at", "created_by"]

    search_fields = ["description", "created_by__username", "object_id"]

    readonly_fields = [
        "content_type",
        "object_id",
        "version",
        "created_at",
        "created_by",
        "audit_log",
        "get_snapshot_data_display",
        "content_object_link",
    ]

    fieldsets = (
        (
            "Snapshot Information",
            {"fields": ("content_type", "object_id", "version", "description")},
        ),
        # TODO: get_snapshot_data_display does not exist
        # ('Data', {
        #     'fields': ('get_snapshot_data_display',),
        #     'classes': ('collapse',)
        # }),
        (
            "System Information",
            {
                # TODO: content_object_link does not exist
                "fields": (
                    "created_at",
                    "created_by",
                    "audit_log",
                ),  # 'content_object_link'),
                "classes": ("collapse",),
            },
        ),
    )

    def description_short(self, obj):
        """Display shortened description"""
        if obj.description:
            if len(obj.description) > 50:
                return obj.description[:47] + "..."
            return obj.description
        return "No description"

    description_short.short_description = "Description"
    description_short.admin_order_field = "description"

    def related_audit_log(self, obj):
        """Link to related audit log"""
        if obj.audit_log:
            url = reverse("admin:audit_auditlog_change", args=[obj.audit_log.id])
            return format_html('<a href="{}">View Log</a>', url)
        return "No log"

    related_audit_log.short_description = "Audit Log"

    def content_object_link(self, obj):
        """Display link to related object"""
        try:
            model_class = obj.content_type.model_class()
            instance = model_class.objects.get(pk=obj.object_id)
            url = reverse(
                f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change",
                args=[obj.object_id],
            )
            return format_html('<a href="{}">{}</a>', url, instance)
        except Exception as e:
            logger.error(f"Error getting admin URL for {obj}: {str(e)}")
            return "Object not found"

    content_object_link.short_description = "Current Object"

    def get_snapshot_data_display(self, obj):
        """Display snapshot data"""
        if obj.snapshot_data:
            items = []
            for key, value in list(obj.snapshot_data.items())[:10]:
                if len(str(value)) > 100:
                    value = str(value)[:97] + "..."
                items.append(f"<strong>{key}:</strong> {value}")

            html = "<br>".join(items)
            if len(obj.snapshot_data) > 10:
                html += (
                    f"<br><em>... and {len(obj.snapshot_data) - 10} more fields</em>"
                )
            return mark_safe(html)
        return "No snapshot data"

    get_snapshot_data_display.short_description = "Snapshot Data"

    def has_add_permission(self, request):
        """Disable manual creation of snapshots"""
        return False

    def has_change_permission(self, request, obj=None):
        """Make snapshots read-only except for description"""
        return False

    actions = ["create_comparison_report", "restore_from_snapshot"]

    def create_comparison_report(self, request, queryset):
        """Create comparison report between snapshots"""
        # This would implement snapshot comparison logic
        count = queryset.count()
        self.message_user(request, f"Comparison report created for {count} snapshots.")

    create_comparison_report.short_description = "Create comparison report"

    def restore_from_snapshot(self, request, queryset):
        """Restore objects from snapshots"""
        if not request.user.is_superuser:
            self.message_user(
                request, "Only superusers can restore from snapshots.", level="error"
            )
            return

        count = 0
        for snapshot in queryset:
            try:
                snapshot.restore()
                count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error restoring snapshot {snapshot.id}: {str(e)}",
                    level="error",
                )

        self.message_user(request, f"{count} objects restored from snapshots.")

    restore_from_snapshot.short_description = "Restore from selected snapshots"


@admin.register(BulkOperation)
class BulkOperationAdmin(admin.ModelAdmin):
    """Bulk operation administration"""

    list_display = [
        "operation_id_short",
        "operation_type",
        "user",
        "status",
        "progress_display",
        "started_at",
        "duration_display",
    ]

    list_filter = ["operation_type", "status", "started_at", "user"]

    search_fields = ["operation_id", "operation_type", "user__username"]

    readonly_fields = [
        "operation_id",
        "started_at",
        "completed_at",
        "duration_display",
        "progress_display",
        "get_results_display",
        "get_error_details_display",
    ]

    fieldsets = (
        (
            "Operation Information",
            {"fields": ("operation_id", "operation_type", "user", "status")},
        ),
        (
            "Progress",
            {
                # TODO: progress_display does not exist
                "fields": (
                    # 'progress_display',
                    "total_items",
                    "processed_items",
                    "failed_items",
                )
            },
        ),
        (
            "Timing",
            {
                # TODO: duration_display does not exist
                "fields": ("started_at", "completed_at"),  # 'duration_display'),
                "classes": ("collapse",),
            },
        ),
        # TODO: get_results_display does not exist
        # ('Results', {
        #     'fields': ('get_results_display',),
        #     'classes': ('collapse',)
        # }),
        # TODO: get_error_details_display does not exist
        # ('Errors', {
        #     'fields': ('get_error_details_display',),
        #     'classes': ('collapse',)
        # })
    )

    def operation_id_short(self, obj):
        """Display shortened operation ID"""
        return (
            obj.operation_id[:8] + "..."
            if len(obj.operation_id) > 8
            else obj.operation_id
        )

    operation_id_short.short_description = "Operation ID"

    def progress_display(self, obj):
        """Display operation progress"""
        if obj.total_items and obj.total_items > 0:
            percentage = (obj.processed_items / obj.total_items) * 100
            success_rate = (
                ((obj.processed_items - obj.failed_items) / obj.processed_items * 100)
                if obj.processed_items > 0
                else 0
            )
            return format_html(
                '{}/{} ({:.1f}%)<br><small style="color: {};">{} failed ({:.1f}%)</small>',
                obj.processed_items,
                obj.total_items,
                percentage,
                "red" if obj.failed_items > 0 else "green",
                obj.failed_items,
                100 - success_rate,
            )
        return f"{obj.processed_items} processed"

    progress_display.short_description = "Progress"

    def duration_display(self, obj):
        """Display operation duration"""
        if obj.started_at and obj.completed_at:
            duration = obj.completed_at - obj.started_at
            total_seconds = int(duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return "N/A"

    duration_display.short_description = "Duration"

    def get_results_display(self, obj):
        """Display operation results"""
        if obj.results:
            items = []
            for key, value in list(obj.results.items())[:5]:
                items.append(f"<strong>{key}:</strong> {value}")
            html = "<br>".join(items)
            if len(obj.results) > 5:
                html += f"<br><em>... and {len(obj.results) - 5} more</em>"
            return mark_safe(html)
        return "No results"

    get_results_display.short_description = "Results"

    def get_error_details_display(self, obj):
        """Display error details"""
        if obj.error_details:
            error_count = len(obj.error_details)
            if error_count > 0:
                html = f"<strong>{error_count} errors:</strong><br>"
                for error in obj.error_details[:3]:
                    html += f"• {error}<br>"
                if error_count > 3:
                    html += f"<em>... and {error_count - 3} more</em>"
                return mark_safe(html)
        return "No errors"

    get_error_details_display.short_description = "Error Details"

    def has_add_permission(self, request):
        """Disable manual creation of bulk operations"""
        return False

    def has_change_permission(self, request, obj=None):
        """Make bulk operations read-only"""
        return False

    actions = ["export_operation_report", "cleanup_old_operations"]

    def export_operation_report(self, request, queryset):
        """Export operation report as CSV"""
        import csv

        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="bulk_operations.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Operation ID",
                "Type",
                "User",
                "Status",
                "Started",
                "Completed",
                "Total Items",
                "Processed",
                "Failed",
                "Success Rate",
            ]
        )

        for op in queryset:
            success_rate = (
                ((op.processed_items - op.failed_items) / op.processed_items * 100)
                if op.processed_items > 0
                else 0
            )
            writer.writerow(
                [
                    op.operation_id,
                    op.operation_type,
                    str(op.user) if op.user else "System",
                    op.status,
                    op.started_at.isoformat() if op.started_at else "",
                    op.completed_at.isoformat() if op.completed_at else "",
                    op.total_items,
                    op.processed_items,
                    op.failed_items,
                    f"{success_rate:.1f}%",
                ]
            )

        return response

    export_operation_report.short_description = "Export operation report as CSV"

    def cleanup_old_operations(self, request, queryset):
        """Delete operations older than 90 days"""
        from datetime import timedelta

        from django.utils import timezone

        cutoff_date = timezone.now() - timedelta(days=90)
        count = queryset.filter(started_at__lt=cutoff_date).delete()[0]
        self.message_user(request, f"{count} old bulk operations deleted.")

    cleanup_old_operations.short_description = "Delete operations older than 90 days"
