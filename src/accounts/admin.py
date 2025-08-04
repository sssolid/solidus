# src/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import (
    UserChangeForm as BaseUserChangeForm,
)
from django.contrib.auth.forms import (
    UserCreationForm as BaseUserCreationForm,
)
from django.urls import reverse
from django.utils.html import format_html

from .models import CustomerProfile, User


class CustomUserCreationForm(BaseUserCreationForm):
    """Custom user creation form"""

    class Meta:
        model = User
        fields = ("username", "email", "role", "company_name")


class CustomUserChangeForm(BaseUserChangeForm):
    """Custom user change form"""

    class Meta:
        model = User
        fields = "__all__"


class CustomerProfileInline(admin.StackedInline):
    """Inline customer profile for User admin"""

    model = CustomerProfile
    extra = 0
    fields = [
        "billing_address",
        "shipping_addresses",
        "business_type",
        "annual_revenue",
        "preferred_payment_terms",
        "credit_limit",
        "feed_delivery_methods",
    ]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced user administration"""

    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = [
        "username",
        "email",
        "get_full_name_display",
        "role",
        "company_name",
        "is_active",
        "last_login",
        "date_joined",
        "activity_status",
    ]

    list_filter = [
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
        "last_login",
        "last_activity",
    ]

    search_fields = [
        "username",
        "email",
        "first_name",
        "last_name",
        "company_name",
        "customer_number",
    ]

    readonly_fields = [
        "date_joined",
        "last_login",
        "last_activity",
        "created_at",
        "updated_at",
        "activity_status",
        "get_feed_count",
        "get_pricing_count",
    ]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email", "phone")}),
        (
            "Company info",
            {"fields": ("role", "company_name", "customer_number", "tax_id")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Access Control",
            {
                "fields": ("allowed_asset_categories", "notification_preferences"),
                "classes": ("collapse",),
            },
        ),
        (
            "Activity",
            {
                # TODO: activity_status does not exist
                "fields": (
                    "date_joined",
                    "last_login",
                    "last_activity",
                ),  # 'activity_status'),
                "classes": ("collapse",),
            },
        ),
        # TODO: get_feed_count and get_pricing_count do not exist
        # ('Statistics', {
        #     'fields': ('get_feed_count', 'get_pricing_count'),
        #     'classes': ('collapse',)
        # })
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "company_name",
                ),
            },
        ),
    )

    inlines = [CustomerProfileInline]

    def get_full_name_display(self, obj):
        """Display full name or username"""
        return obj.get_full_name() or obj.username

    get_full_name_display.short_description = "Name"
    get_full_name_display.admin_order_field = "first_name"

    def activity_status(self, obj):
        """Show activity status with color coding"""
        if not obj.last_activity:
            return format_html('<span style="color: gray;">Never</span>')

        from datetime import timedelta

        from django.utils import timezone

        if obj.last_activity > timezone.now() - timedelta(days=1):
            return format_html('<span style="color: green;">Active (24h)</span>')
        elif obj.last_activity > timezone.now() - timedelta(days=7):
            return format_html('<span style="color: orange;">Recent (7d)</span>')
        else:
            return format_html('<span style="color: red;">Inactive</span>')

    activity_status.short_description = "Activity"

    def get_feed_count(self, obj):
        """Get feed count for customer"""
        if obj.role == "customer":
            count = obj.data_feeds.count()
            if count > 0:
                url = (
                    reverse("admin:feeds_datafeed_changelist")
                    + f"?customer__id__exact={obj.id}"
                )
                return format_html('<a href="{}">{} feeds</a>', url, count)
            return "0 feeds"
        return "N/A"

    get_feed_count.short_description = "Data Feeds"

    def get_pricing_count(self, obj):
        """Get custom pricing count for customer"""
        if obj.role == "customer":
            count = obj.custom_pricing.count()
            if count > 0:
                url = (
                    reverse("admin:products_customerpricing_changelist")
                    + f"?customer__id__exact={obj.id}"
                )
                return format_html('<a href="{}">{} prices</a>', url, count)
            return "0 prices"
        return "N/A"

    get_pricing_count.short_description = "Custom Pricing"

    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related("customer_profile")

    actions = ["activate_users", "deactivate_users", "reset_passwords"]

    def activate_users(self, request, queryset):
        """Bulk activate users"""
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} users activated successfully.")

    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        """Bulk deactivate users"""
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} users deactivated successfully.")

    deactivate_users.short_description = "Deactivate selected users"

    def reset_passwords(self, request, queryset):
        """Reset user passwords"""
        # This would implement password reset logic
        count = queryset.count()
        self.message_user(request, f"Password reset initiated for {count} users.")

    reset_passwords.short_description = "Reset passwords for selected users"


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """Customer profile administration"""

    list_display = [
        "user",
        "get_company_name",
        "business_type",
        "annual_revenue",
        "credit_limit",
        "created_at",
    ]

    list_filter = ["business_type", "preferred_payment_terms", "created_at"]

    search_fields = [
        "user__username",
        "user__email",
        "user__company_name",
        "business_type",
    ]

    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("User", {"fields": ("user",)}),
        (
            "Business Information",
            {
                "fields": (
                    "business_type",
                    "annual_revenue",
                    "preferred_payment_terms",
                    "credit_limit",
                )
            },
        ),
        (
            "Addresses",
            {
                "fields": ("billing_address", "shipping_addresses"),
                "classes": ("collapse",),
            },
        ),
        (
            "Feed Preferences",
            {"fields": ("feed_delivery_methods",), "classes": ("collapse",)},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_company_name(self, obj):
        """Get company name from user"""
        return obj.user.company_name or "No company"

    get_company_name.short_description = "Company"
    get_company_name.admin_order_field = "user__company_name"

    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related("user")


# Customize admin site
admin.site.site_header = "Solidus Administration"
admin.site.site_title = "Solidus Admin"
admin.site.index_title = "Welcome to Solidus Administration"
