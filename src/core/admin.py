# src/core/admin.py
import logging

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import FileImport, Notification, SystemSetting, TaskQueue

logger = logging.getLogger("core.admin")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Notification administration"""

    list_display = [
        "user",
        "notification_type",
        "title",
        "is_read",
        "is_archived",
        "created_at",
        "expires_at_display",
        "has_action",
    ]

    list_filter = [
        "notification_type",
        "is_read",
        "is_archived",
        "created_at",
        "expires_at",
    ]

    search_fields = ["user__username", "user__email", "title", "message"]

    readonly_fields = [
        "created_at",
        "read_at",
        "content_object_display",
        "get_metadata_display",
    ]

    fieldsets = (
        ("Recipient", {"fields": ("user",)}),
        ("Notification Details", {"fields": ("notification_type", "title", "message")}),
        (
            "Related Object",
            {
                # TODO: content_object_display does not exist
                "fields": ("content_type", "object_id"),  # 'content_object_display'),
                "classes": ("collapse",),
            },
        ),
        ("Status", {"fields": ("is_read", "is_archived", "read_at")}),
        (
            "Action",
            {"fields": ("action_url", "action_label"), "classes": ("collapse",)},
        ),
        ("Timing", {"fields": ("created_at", "expires_at")}),
        # TODO: get_metadata_display does not exist
        # ('Metadata', {
        #     'fields': ('get_metadata_display',),
        #     'classes': ('collapse',)
        # })
    )

    def expires_at_display(self, obj):
        """Display expiration with color coding"""
        if not obj.expires_at:
            return "Never"

        from datetime import timedelta

        from django.utils import timezone

        if obj.expires_at < timezone.now():
            return format_html('<span style="color: red;">Expired</span>')
        elif obj.expires_at < timezone.now() + timedelta(days=1):
            return format_html('<span style="color: orange;">Soon</span>')
        else:
            return obj.expires_at.strftime("%Y-%m-%d %H:%M")

    expires_at_display.short_description = "Expires"

    def has_action(self, obj):
        """Show if notification has action"""
        if obj.action_url:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: gray;">✗</span>')

    has_action.short_description = "Action"

    def content_object_display(self, obj):
        """Display related object"""
        if obj.content_object:
            try:
                url = reverse(
                    f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change",
                    args=[obj.object_id],
                )
                return format_html('<a href="{}">{}</a>', url, obj.content_object)
            except Exception as e:
                logger.error(f"Error getting admin URL for {obj.content_object}: {e}")
                return str(obj.content_object)
        return "None"

    content_object_display.short_description = "Related Object"

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

    actions = [
        "mark_as_read",
        "mark_as_unread",
        "archive_notifications",
        "delete_expired",
    ]

    def mark_as_read(self, request, queryset):
        """Mark notifications as read"""
        count = 0
        for notification in queryset:
            if not notification.is_read:
                notification.mark_as_read()
                count += 1
        self.message_user(request, f"{count} notifications marked as read.")

    mark_as_read.short_description = "Mark selected as read"

    def mark_as_unread(self, request, queryset):
        """Mark notifications as unread"""
        count = queryset.filter(is_read=True).update(is_read=False, read_at=None)
        self.message_user(request, f"{count} notifications marked as unread.")

    mark_as_unread.short_description = "Mark selected as unread"

    def archive_notifications(self, request, queryset):
        """Archive notifications"""
        count = queryset.update(is_archived=True)
        self.message_user(request, f"{count} notifications archived.")

    archive_notifications.short_description = "Archive selected notifications"

    def delete_expired(self, request, queryset):
        """Delete expired notifications"""
        from django.utils import timezone

        count = queryset.filter(expires_at__lt=timezone.now()).delete()[0]
        self.message_user(request, f"{count} expired notifications deleted.")

    delete_expired.short_description = "Delete expired notifications"


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    """System setting administration"""

    list_display = [
        "key",
        "setting_type",
        "value_display",
        "is_public",
        "updated_at",
        # TODO: updated_by does not exist
        # "updated_by",
    ]

    list_filter = ["setting_type", "is_public", "updated_at"]

    search_fields = ["key", "description", "value"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Setting Information", {"fields": ("key", "setting_type", "is_public")}),
        ("Value", {"fields": ("value", "description")}),
        (
            "System Information",
            {
                # TODO: updated_by does not exist
                "fields": ("created_at", "updated_at",), # "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )

    def value_display(self, obj):
        """Display truncated value"""
        value = str(obj.value)
        if len(value) > 50:
            return value[:47] + "..."
        return value

    value_display.short_description = "Value"
    value_display.admin_order_field = "value"

    def save_model(self, request, obj, form, change):
        """Set updated_by"""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    actions = ["make_public", "make_private", "export_settings"]

    def make_public(self, request, queryset):
        """Make settings public"""
        count = queryset.update(is_public=True)
        self.message_user(request, f"{count} settings made public.")

    make_public.short_description = "Make selected settings public"

    def make_private(self, request, queryset):
        """Make settings private"""
        count = queryset.update(is_public=False)
        self.message_user(request, f"{count} settings made private.")

    make_private.short_description = "Make selected settings private"

    def export_settings(self, request, queryset):
        """Export settings as JSON"""
        import json

        from django.http import HttpResponse

        settings_data = {}
        for setting in queryset:
            settings_data[setting.key] = {
                "value": setting.value,
                "type": setting.setting_type,
                "description": setting.description,
            }

        response = HttpResponse(
            json.dumps(settings_data, indent=2), content_type="application/json"
        )
        response["Content-Disposition"] = 'attachment; filename="system_settings.json"'
        return response

    export_settings.short_description = "Export selected settings as JSON"


@admin.register(TaskQueue)
class TaskQueueAdmin(admin.ModelAdmin):
    """Task queue administration"""

    list_display = [
        "task_id_short",
        "task_type",
        "status",
        "priority",
        "attempts",
        "scheduled_for",
        "duration_display",
        "created_by",
    ]

    list_filter = ["task_type", "status", "priority", "created_at", "scheduled_for"]

    search_fields = ["task_id", "task_type", "created_by__username"]

    readonly_fields = [
        "task_id",
        "attempts",
        "created_at",
        "started_at",
        "completed_at",
        "duration_display",
        "get_task_data_display",
        "get_result_display",
    ]

    fieldsets = (
        (
            "Task Information",
            {"fields": ("task_id", "task_type", "status", "priority")},
        ),
        # TODO: get_task_data_display does not exist
        # ('Task Data', {
        #     'fields': ('get_task_data_display',),
        #     'classes': ('collapse',)
        # }),
        ("Execution", {"fields": ("attempts", "max_attempts", "scheduled_for")}),
        (
            "Timing",
            {
                # TODO: duration_display does not exist
                "fields": (
                    "created_at",
                    "started_at",
                    "completed_at",
                ),  # 'duration_display'),
                "classes": ("collapse",),
            },
        ),
        (
            "Results",
            {
                # TODO: get_results_display does not exist
                "fields": (
                    # 'get_result_display',
                    "error_message",
                ),
                "classes": ("collapse",),
            },
        ),
        ("System Information", {"fields": ("created_by",), "classes": ("collapse",)}),
    )

    def task_id_short(self, obj):
        """Display shortened task ID"""
        return str(obj.task_id)[:8] + "..."

    task_id_short.short_description = "Task ID"

    def duration_display(self, obj):
        """Display task duration"""
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

    def get_task_data_display(self, obj):
        """Display task data"""
        if obj.task_data:
            items = []
            for key, value in list(obj.task_data.items())[:5]:
                items.append(f"<strong>{key}:</strong> {value}")
            html = "<br>".join(items)
            if len(obj.task_data) > 5:
                html += f"<br><em>... and {len(obj.task_data) - 5} more</em>"
            return mark_safe(html)
        return "No task data"

    get_task_data_display.short_description = "Task Data"

    def get_result_display(self, obj):
        """Display task results"""
        if obj.result:
            items = []
            for key, value in list(obj.result.items())[:5]:
                items.append(f"<strong>{key}:</strong> {value}")
            html = "<br>".join(items)
            if len(obj.result) > 5:
                html += f"<br><em>... and {len(obj.result) - 5} more</em>"
            return mark_safe(html)
        return "No results"

    get_result_display.short_description = "Results"

    actions = ["retry_failed_tasks", "cancel_pending_tasks", "cleanup_completed"]

    def retry_failed_tasks(self, request, queryset):
        """Retry failed tasks"""
        count = 0
        for task in queryset.filter(status="failed"):
            if task.can_retry():
                task.status = "pending"
                task.error_message = ""
                task.save(update_fields=["status", "error_message"])
                count += 1
        self.message_user(request, f"{count} tasks queued for retry.")

    retry_failed_tasks.short_description = "Retry failed tasks"

    def cancel_pending_tasks(self, request, queryset):
        """Cancel pending tasks"""
        count = queryset.filter(status="pending").update(status="cancelled")
        self.message_user(request, f"{count} tasks cancelled.")

    cancel_pending_tasks.short_description = "Cancel pending tasks"

    def cleanup_completed(self, request, queryset):
        """Delete completed tasks older than 30 days"""
        from datetime import timedelta

        from django.utils import timezone

        cutoff_date = timezone.now() - timedelta(days=30)
        count = queryset.filter(
            status="completed", completed_at__lt=cutoff_date
        ).delete()[0]
        self.message_user(request, f"{count} old completed tasks deleted.")

    cleanup_completed.short_description = "Cleanup old completed tasks"


@admin.register(FileImport)
class FileImportAdmin(admin.ModelAdmin):
    """File import administration"""

    list_display = [
        "import_id_short",
        "import_type",
        "status",
        "progress_display",
        "started_at",
        "duration_display",
        # 'created_by'
    ]

    list_filter = ["import_type", "status", "started_at"]

    search_fields = [
        "import_id",
        # TODO: filename and created_by__username do not exist
        # "filename",
        # 'created_by__username'
    ]

    readonly_fields = [
        "import_id",
        "started_at",
        "completed_at",
        "duration_display",
        "progress_display",
        "get_results_display",
        "get_errors_display",
    ]

    fieldsets = (
        (
            "Import Information",
            # TODO: filename does not exist
            {"fields": ("import_id", "import_type", "status")}, # "filename"},
        ),
        (
            "Progress",
            {
                "fields": (
                    # TODO: progress_display does not exist
                    # 'progress_display',
                    "total_rows",
                    "processed_rows",
                    "failed_rows",
                )
            },
        ),
        (
            "Timing",
            {
                # TODO: duration_display does not exist
                "fields": (
                    "started_at",
                    "completed_at",
                ),  # 'duration_display'),
                "classes": ("collapse",),
            },
        ),
        # TODO: get_results_display does not exist
        # ('Results', {
        #     'fields': ('get_results_display',),
        #     'classes': ('collapse',)
        # }),
        # TODO: get_errors_display does not exist
        # ('Errors', {
        #     'fields': ('get_errors_display',),
        #     'classes': ('collapse',)
        # }),
        # TODO: created_by does not exist
        # ('System Information', {
        #     'fields': ('created_by',),
        #     'classes': ('collapse',)
        # })
    )

    def import_id_short(self, obj):
        """Display shortened import ID"""
        return str(obj.import_id)[:8] + "..."

    import_id_short.short_description = "Import ID"

    def progress_display(self, obj):
        """Display import progress"""
        if obj.total_rows and obj.total_rows > 0:
            percentage = (obj.processed_rows / obj.total_rows) * 100
            return f"{obj.processed_rows}/{obj.total_rows} ({percentage:.1f}%)"
        return f"{obj.processed_rows} rows"

    progress_display.short_description = "Progress"

    def duration_display(self, obj):
        """Display import duration"""
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
        """Display import results"""
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

    def get_errors_display(self, obj):
        """Display import errors"""
        if obj.errors:
            error_count = len(obj.errors)
            if error_count > 0:
                html = f"<strong>{error_count} errors:</strong><br>"
                for error in obj.errors[:3]:
                    html += f"• {error}<br>"
                if error_count > 3:
                    html += f"<em>... and {error_count - 3} more</em>"
                return mark_safe(html)
        return "No errors"

    get_errors_display.short_description = "Errors"

    def has_add_permission(self, request):
        """Disable manual creation of file imports"""
        return False
