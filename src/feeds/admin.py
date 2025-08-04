# src/feeds/admin.py
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import ChangeNotification, DataFeed, FeedGeneration, FeedSubscription


class FeedGenerationInline(admin.TabularInline):
    """Inline for feed generations"""

    model = FeedGeneration
    extra = 0
    fields = [
        "generation_id",
        "status",
        "started_at",
        "completed_at",
        "row_count",
        "file_size_display",
    ]
    readonly_fields = [
        "generation_id",
        "started_at",
        "completed_at",
        "file_size_display",
    ]

    def file_size_display(self, obj):
        """Display file size in human readable format"""
        if not obj.file_size:
            return "Unknown"

        size = obj.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    file_size_display.short_description = "File Size"


@admin.register(DataFeed)
class DataFeedAdmin(admin.ModelAdmin):
    """Data feed administration"""

    list_display = [
        "name",
        "customer_name",
        "feed_type",
        "format",
        "frequency",
        "is_active",
        "generation_count",
        "last_generation",
        "created_at",
    ]

    list_filter = [
        "feed_type",
        "format",
        "frequency",
        "is_active",
        "delivery_method",
        "created_at",
    ]

    search_fields = [
        "name",
        "slug",
        "customer__username",
        "customer__email",
        "customer__company_name",
    ]

    readonly_fields = [
        "slug",
        "created_at",
        "updated_at",
        "generation_count",
        "last_generation",
        "next_scheduled",
        "get_filters_display",
    ]

    filter_horizontal = ["categories", "brands"]
    inlines = [FeedGenerationInline]

    fieldsets = (
        (
            "Basic Information",
            {
                # TODO: description does not exist
                "fields": (
                    "name",
                    "slug",
                    "customer",
                    "feed_type",
                ),  # 'description')
            },
        ),
        (
            "Configuration",
            {"fields": ("format", "included_fields", "custom_field_mapping")},
        ),
        (
            "Content Filters",
            {
                # TODO: get_filters_display does not exist
                "fields": (
                    "categories",
                    "brands",
                    "product_tags",
                ),  # 'get_filters_display'),
                "classes": ("collapse",),
            },
        ),
        (
            "Scheduling",
            {"fields": ("is_active", "frequency", "schedule_time", "schedule_day")},
        ),
        (
            "Delivery",
            {
                "fields": ("delivery_method", "delivery_config"),
                "classes": ("collapse",),
            },
        ),
        (
            "Statistics",
            {
                # TODO: last_generation and next_scheduled do not exist
                "fields": (
                    "generation_count",
                ),  # 'last_generation', 'next_scheduled'),
                "classes": ("collapse",),
            },
        ),
        (
            "System Information",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def customer_name(self, obj):
        """Display customer name"""
        return obj.customer.company_name or obj.customer.username

    customer_name.short_description = "Customer"
    customer_name.admin_order_field = "customer__company_name"

    def generation_count(self, obj):
        """Count feed generations"""
        count = obj.generations.count()
        if count > 0:
            url = (
                reverse("admin:feeds_feedgeneration_changelist")
                + f"?feed__id__exact={obj.id}"
            )
            return format_html('<a href="{}">{} generations</a>', url, count)
        return "0 generations"

    generation_count.short_description = "Generations"

    def last_generation(self, obj):
        """Show last generation status"""
        last_gen = obj.generations.order_by("-started_at").first()
        if last_gen:
            status_colors = {
                "completed": "green",
                "failed": "red",
                "generating": "orange",
                "pending": "blue",
            }
            color = status_colors.get(last_gen.status, "gray")
            return format_html(
                '<span style="color: {};">{}</span><br><small>{}</small>',
                color,
                last_gen.get_status_display(),
                last_gen.started_at.strftime("%m/%d %H:%M"),
            )
        return "Never generated"

    last_generation.short_description = "Last Generation"

    def next_scheduled(self, obj):
        """Show next scheduled generation"""
        next_gen = obj.get_next_generation_time()
        if next_gen:
            return next_gen.strftime("%Y-%m-%d %H:%M")
        return "Not scheduled"

    next_scheduled.short_description = "Next Generation"

    def get_filters_display(self, obj):
        """Display content filters"""
        filters = []
        if obj.categories.exists():
            filters.append(
                f"Categories: {', '.join(obj.categories.values_list('name', flat=True)[:3])}"
            )
        if obj.brands.exists():
            filters.append(
                f"Brands: {', '.join(obj.brands.values_list('name', flat=True)[:3])}"
            )
        if obj.product_tags:
            filters.append(f"Tags: {', '.join(obj.product_tags[:3])}")

        return mark_safe("<br>".join(filters)) if filters else "No filters"

    get_filters_display.short_description = "Content Filters"

    actions = ["activate_feeds", "deactivate_feeds", "trigger_generation"]

    def activate_feeds(self, request, queryset):
        """Activate feeds"""
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} feeds activated.")

    activate_feeds.short_description = "Activate selected feeds"

    def deactivate_feeds(self, request, queryset):
        """Deactivate feeds"""
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} feeds deactivated.")

    deactivate_feeds.short_description = "Deactivate selected feeds"

    def trigger_generation(self, request, queryset):
        """Trigger feed generation"""
        from .models import FeedGeneration

        count = 0
        for feed in queryset:
            if not feed.generations.filter(
                status__in=["pending", "generating"]
            ).exists():
                FeedGeneration.objects.create(feed=feed, status="pending")
                count += 1
        self.message_user(request, f"Triggered generation for {count} feeds.")

    trigger_generation.short_description = "Trigger generation for selected feeds"


@admin.register(FeedGeneration)
class FeedGenerationAdmin(admin.ModelAdmin):
    """Feed generation administration"""

    list_display = [
        "feed_name",
        "generation_id_short",
        "status",
        "started_at",
        "duration_display",
        "row_count",
        "file_size_display",
        "delivery_status",
    ]

    list_filter = [
        "status",
        "delivery_status",
        "started_at",
        "feed__format",
        "feed__customer",
    ]

    search_fields = [
        "generation_id",
        "feed__name",
        "feed__customer__username",
        "feed__customer__company_name",
    ]

    readonly_fields = [
        "generation_id",
        "started_at",
        "completed_at",
        "duration_display",
        "file_path",
        "file_size",
        "row_count",
        "get_metadata_display",
        "get_error_display",
    ]

    fieldsets = (
        ("Generation Information", {"fields": ("feed", "generation_id", "status")}),
        (
            "Timing",
            {
                # TODO: duration_display does not exist
                "fields": (
                    "started_at",
                    "completed_at",
                ),  # 'duration_display')
            },
        ),
        (
            "File Information",
            {
                "fields": ("file_path", "file_size", "row_count"),
                "classes": ("collapse",),
            },
        ),
        (
            "Delivery",
            {
                "fields": ("delivery_status", "delivered_at", "delivery_details"),
                "classes": ("collapse",),
            },
        ),
        # TODO: get_metadata_display does not exist
        # ('Metadata', {
        #     'fields': ('get_metadata_display',),
        #     'classes': ('collapse',)
        # }),
        # TODO: get_error_display does not exist
        # ('Errors', {
        #     'fields': ('get_error_display',),
        #     'classes': ('collapse',)
        # })
    )

    def feed_name(self, obj):
        """Display feed name"""
        return obj.feed.name

    feed_name.short_description = "Feed"
    feed_name.admin_order_field = "feed__name"

    def generation_id_short(self, obj):
        """Display shortened generation ID"""
        return str(obj.generation_id)[:8] + "..."

    generation_id_short.short_description = "Generation ID"

    def duration_display(self, obj):
        """Display generation duration"""
        duration = obj.duration
        if duration:
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

    def file_size_display(self, obj):
        """Display file size in human readable format"""
        if not obj.file_size:
            return "Unknown"

        size = obj.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    file_size_display.short_description = "File Size"
    file_size_display.admin_order_field = "file_size"

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

    def get_error_display(self, obj):
        """Display error information"""
        if obj.error_message:
            error_html = f"<strong>Error:</strong> {obj.error_message}"
            if obj.error_details:
                error_html += "<br><strong>Details:</strong>"
                for key, value in list(obj.error_details.items())[:3]:
                    error_html += f"<br>&nbsp;&nbsp;<em>{key}:</em> {value}"
            return mark_safe(error_html)
        return "No errors"

    get_error_display.short_description = "Error Information"

    def has_add_permission(self, request):
        """Disable manual creation of generations"""
        return False


@admin.register(FeedSubscription)
class FeedSubscriptionAdmin(admin.ModelAdmin):
    """Feed subscription administration"""

    list_display = [
        "customer_name",
        "subscription_type",
        "notification_method",
        "is_active",
        "min_interval_hours",
        "last_notified",
        "created_at",
    ]

    list_filter = [
        "subscription_type",
        "notification_method",
        "is_active",
        "created_at",
    ]

    search_fields = ["customer__username", "customer__email", "customer__company_name"]

    readonly_fields = ["last_notified", "created_at", "updated_at", "can_notify_status"]

    filter_horizontal = ["categories", "brands", "specific_products"]

    fieldsets = (
        ("Subscription", {"fields": ("customer", "subscription_type", "is_active")}),
        (
            "Filters",
            {
                "fields": ("categories", "brands", "specific_products"),
                "classes": ("collapse",),
            },
        ),
        (
            "Notification Settings",
            {
                "fields": (
                    "notification_method",
                    "notification_config",
                    "min_interval_hours",
                )
            },
        ),
        (
            "Status",
            {
                # TODO: can_notify_status does not exist
                "fields": ("last_notified",),  # 'can_notify_status'),
                "classes": ("collapse",),
            },
        ),
        (
            "System Information",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def customer_name(self, obj):
        """Display customer name"""
        return obj.customer.company_name or obj.customer.username

    customer_name.short_description = "Customer"
    customer_name.admin_order_field = "customer__company_name"

    def can_notify_status(self, obj):
        """Check if subscription can send notifications"""
        if obj.can_notify():
            return format_html('<span style="color: green;">Ready</span>')
        else:
            from django.utils import timezone

            hours_passed = (
                (timezone.now() - obj.last_notified).total_seconds() / 3600
                if obj.last_notified
                else 0
            )
            hours_remaining = obj.min_interval_hours - hours_passed
            return format_html(
                '<span style="color: orange;">Wait {:.1f}h</span>', hours_remaining
            )

    can_notify_status.short_description = "Notification Status"


@admin.register(ChangeNotification)
class ChangeNotificationAdmin(admin.ModelAdmin):
    """Change notification administration"""

    list_display = [
        "subscription_customer",
        "subject",
        "delivery_status",
        "sent_at",
        "opened_at",
        "clicked_at",
    ]

    list_filter = ["delivery_status", "sent_at", "subscription__subscription_type"]

    search_fields = [
        "subscription__customer__username",
        "subscription__customer__company_name",
        "subject",
        "notification_id",
    ]

    readonly_fields = [
        "notification_id",
        "sent_at",
        "opened_at",
        "clicked_at",
        "get_change_summary_display",
    ]

    fieldsets = (
        ("Notification", {"fields": ("subscription", "notification_id", "subject")}),
        (
            "Content",
            {
                # TODO: get_change_summary_display does not exist
                "fields": ("content",),  # 'get_change_summary_display'),
                "classes": ("collapse",),
            },
        ),
        (
            "Delivery",
            {
                "fields": ("delivery_status", "delivery_details"),
                "classes": ("collapse",),
            },
        ),
        (
            "Tracking",
            {
                "fields": ("sent_at", "opened_at", "clicked_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def subscription_customer(self, obj):
        """Display subscription customer"""
        return (
            obj.subscription.customer.company_name or obj.subscription.customer.username
        )

    subscription_customer.short_description = "Customer"
    subscription_customer.admin_order_field = "subscription__customer__company_name"

    def get_change_summary_display(self, obj):
        """Display change summary"""
        if obj.change_summary:
            items = []
            for key, value in list(obj.change_summary.items())[:5]:
                items.append(f"<strong>{key}:</strong> {value}")
            html = "<br>".join(items)
            if len(obj.change_summary) > 5:
                html += f"<br><em>... and {len(obj.change_summary) - 5} more</em>"
            return mark_safe(html)
        return "No change summary"

    get_change_summary_display.short_description = "Change Summary"

    def has_add_permission(self, request):
        """Disable manual creation of notifications"""
        return False

    def has_change_permission(self, request, obj=None):
        """Make notifications read-only"""
        return False
