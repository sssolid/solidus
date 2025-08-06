# src/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Extended user model with roles and customer-specific fields"""

    ROLE_CHOICES = [
        ("admin", "Administrator"),
        ("employee", "Employee"),
        ("customer", "Customer"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="customer")
    company_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    # Customer-specific fields
    customer_number = models.CharField(
        max_length=50, blank=True, unique=True, null=True
    )
    tax_id = models.CharField(max_length=50, blank=True)

    # Preferences
    notification_preferences = models.JSONField(default=dict, blank=True)

    # Tracking
    last_activity = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["customer_number"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    @property
    def is_customer(self):
        return self.role == "customer"

    @property
    def is_employee(self):
        return self.role in ["admin", "employee"]

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def allowed_categories(self):
        return [access.category.slug for access in self.asset_category_access.all()]

    def update_last_activity(self):
        """Update last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=["last_activity"])

    def get_notification_preference(self, notification_type):
        """Get notification preference for a specific type"""
        return self.notification_preferences.get(notification_type, True)

    def set_notification_preference(self, notification_type, enabled):
        """Set notification preference"""
        if self.notification_preferences is None:
            self.notification_preferences = {}
        self.notification_preferences[notification_type] = enabled
        self.save(update_fields=["notification_preferences"])


class CustomerProfile(models.Model):
    """Additional customer-specific information"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="customer_profile"
    )

    # Billing/Shipping
    billing_address = models.JSONField(default=dict, blank=True)
    shipping_addresses = models.JSONField(default=list, blank=True)

    # Business info
    business_type = models.CharField(max_length=100, blank=True)
    annual_revenue = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    # Preferences
    preferred_payment_terms = models.CharField(max_length=50, blank=True)
    credit_limit = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    # Data feed preferences
    feed_delivery_methods = models.JSONField(
        default=dict, help_text="Preferred delivery methods for data feeds"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customer_profiles"

    def __str__(self):
        return f"Profile for {self.user.company_name or self.user.username}"


class UserAssetCategoryAccess(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='asset_category_access')
    category = models.ForeignKey('assets.AssetCategory', on_delete=models.CASCADE)
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='granted_access')

    class Meta:
        unique_together = [['user', 'category']]