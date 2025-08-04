# src/feeds/forms.py
from django import forms
from django.core.exceptions import ValidationError

from accounts.models import User
from products.models import Brand, Category

from .models import DataFeed, FeedSubscription


class DataFeedForm(forms.ModelForm):
    """Form for creating and editing data feeds"""

    class Meta:
        model = DataFeed
        fields = [
            "name",
            # "description",
            "feed_type",
            "format",
            "customer",
            "categories",
            "brands",
            "product_tags",
            # "include_inactive",
            "include_images",
            # "include_fitment",
            # "include_pricing",
            # "field_mapping",
            # "custom_fields",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Feed name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 4,
                    "placeholder": "Feed description...",
                }
            ),
            "feed_type": forms.Select(attrs={"class": "form-select"}),
            "format": forms.Select(attrs={"class": "form-select"}),
            "customer": forms.Select(attrs={"class": "form-select"}),
            "categories": forms.CheckboxSelectMultiple(),
            "brands": forms.CheckboxSelectMultiple(),
            "product_tags": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter tags separated by commas",
                }
            ),
            "include_inactive": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "include_images": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "include_fitment": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "include_pricing": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "field_mapping": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 6,
                    "placeholder": "JSON field mapping configuration",
                }
            ),
            "custom_fields": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 4,
                    "placeholder": "JSON custom fields configuration",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Filter customers based on user permissions
        if user and user.is_customer:
            self.fields["customer"].initial = user
            self.fields["customer"].widget = forms.HiddenInput()
        else:
            self.fields["customer"].queryset = User.objects.filter(
                role="customer", is_active=True
            )

        self.fields["categories"].queryset = Category.objects.filter(is_active=True)
        self.fields["brands"].queryset = Brand.objects.filter(is_active=True)

    def clean_field_mapping(self):
        field_mapping = self.cleaned_data.get("field_mapping")
        if field_mapping:
            try:
                import json

                json.loads(field_mapping)
            except json.JSONDecodeError:
                raise ValidationError("Field mapping must be valid JSON.")
        return field_mapping

    def clean_custom_fields(self):
        custom_fields = self.cleaned_data.get("custom_fields")
        if custom_fields:
            try:
                import json

                json.loads(custom_fields)
            except json.JSONDecodeError:
                raise ValidationError("Custom fields must be valid JSON.")
        return custom_fields


class SubscriptionForm(forms.ModelForm):
    """Form for managing feed subscriptions"""

    class Meta:
        model = FeedSubscription
        fields = [
            # "feed",
            "customer",
            # "schedule_type",
            # "schedule_config",
            # "notification_email",
            "is_active",
        ]
        widgets = {
            "feed": forms.Select(attrs={"class": "form-select"}),
            "customer": forms.Select(attrs={"class": "form-select"}),
            "schedule_type": forms.Select(attrs={"class": "form-select"}),
            "schedule_config": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 4,
                    "placeholder": "JSON schedule configuration",
                }
            ),
            "notification_email": forms.EmailInput(
                attrs={"class": "form-input", "placeholder": "notification@example.com"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user and user.is_customer:
            self.fields["customer"].initial = user
            self.fields["customer"].widget = forms.HiddenInput()
            # Only show feeds accessible to this customer
            self.fields["feed"].queryset = DataFeed.objects.filter(
                customer=user, is_active=True
            )
        else:
            self.fields["customer"].queryset = User.objects.filter(
                role="customer", is_active=True
            )
            self.fields["feed"].queryset = DataFeed.objects.filter(is_active=True)

    def clean_schedule_config(self):
        schedule_config = self.cleaned_data.get("schedule_config")
        if schedule_config:
            try:
                import json

                json.loads(schedule_config)
            except json.JSONDecodeError:
                raise ValidationError("Schedule configuration must be valid JSON.")
        return schedule_config


class DeliveryConfigForm(forms.ModelForm):
    """Form for configuring feed delivery methods"""

    class Meta:
        model = DataFeed
        fields = [
            # "feed",
            "delivery_method",
            # "config",
            "is_active",
        ]
        widgets = {
            "feed": forms.Select(attrs={"class": "form-select"}),
            "delivery_method": forms.Select(attrs={"class": "form-select"}),
            "config": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 6,
                    "placeholder": "JSON delivery configuration",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def clean_config(self):
        config = self.cleaned_data.get("config")
        if config:
            try:
                import json

                json.loads(config)
            except json.JSONDecodeError:
                raise ValidationError("Delivery configuration must be valid JSON.")
        return config


class FeedGenerationForm(forms.Form):
    """Form for manually generating feeds"""

    feed = forms.ModelChoiceField(
        queryset=DataFeed.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-textarea",
                "rows": 3,
                "placeholder": "Optional notes for this generation...",
            }
        ),
    )

    notify_customer = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        help_text="Send notification when generation is complete",
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user and user.is_customer:
            self.fields["feed"].queryset = DataFeed.objects.filter(
                customer=user, is_active=True
            )


class FeedSearchForm(forms.Form):
    """Form for searching feeds"""

    query = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Search feeds by name, description...",
                "hx-get": "/feeds/search/",
                "hx-trigger": "keyup changed delay:300ms",
                "hx-target": "#search-results",
            }
        ),
    )

    feed_type = forms.ChoiceField(
        choices=[("", "All Types")] + DataFeed.FEED_TYPES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    format = forms.ChoiceField(
        choices=[("", "All Formats")] + DataFeed.FORMAT_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    customer = forms.ModelChoiceField(
        queryset=User.objects.filter(role="customer", is_active=True),
        required=False,
        empty_label="All Customers",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    is_active = forms.BooleanField(
        required=False, widget=forms.CheckboxInput(attrs={"class": "form-checkbox"})
    )


class BulkFeedUpdateForm(forms.Form):
    """Form for bulk updating feeds"""

    feeds = forms.ModelMultipleChoiceField(
        queryset=DataFeed.objects.all(), widget=forms.CheckboxSelectMultiple()
    )

    action = forms.ChoiceField(
        choices=[
            ("activate", "Activate"),
            ("deactivate", "Deactivate"),
            ("generate", "Generate"),
            ("delete", "Delete"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-textarea",
                "rows": 3,
                "placeholder": "Optional notes for this bulk operation...",
            }
        ),
    )


class FeedFieldMappingForm(forms.Form):
    """Dynamic form for field mapping configuration"""

    def __init__(self, *args, **kwargs):
        feed_type = kwargs.pop("feed_type", None)
        super().__init__(*args, **kwargs)

        if feed_type == "product_catalog":
            self.add_product_fields()
        elif feed_type == "assets":
            self.add_asset_fields()
        elif feed_type == "fitment":
            self.add_fitment_fields()

    def add_product_fields(self):
        """Add product-specific field mappings"""
        product_fields = [
            ("sku", "Product SKU"),
            ("name", "Product Name"),
            ("description", "Description"),
            ("brand", "Brand"),
            ("price", "Price"),
            ("weight", "Weight"),
            ("dimensions", "Dimensions"),
        ]

        for field_name, field_label in product_fields:
            self.fields[f"map_{field_name}"] = forms.CharField(
                label=field_label,
                required=False,
                widget=forms.TextInput(
                    attrs={
                        "class": "form-input",
                        "placeholder": f"Custom field name for {field_label}",
                    }
                ),
            )

    def add_asset_fields(self):
        """Add asset-specific field mappings"""
        asset_fields = [
            ("title", "Asset Title"),
            ("description", "Description"),
            ("file_name", "File Name"),
            ("file_size", "File Size"),
            ("asset_type", "Asset Type"),
        ]

        for field_name, field_label in asset_fields:
            self.fields[f"map_{field_name}"] = forms.CharField(
                label=field_label,
                required=False,
                widget=forms.TextInput(
                    attrs={
                        "class": "form-input",
                        "placeholder": f"Custom field name for {field_label}",
                    }
                ),
            )

    def add_fitment_fields(self):
        """Add fitment-specific field mappings"""
        fitment_fields = [
            ("year_start", "Start Year"),
            ("year_end", "End Year"),
            ("make", "Make"),
            ("model", "Model"),
            ("engine", "Engine"),
        ]

        for field_name, field_label in fitment_fields:
            self.fields[f"map_{field_name}"] = forms.CharField(
                label=field_label,
                required=False,
                widget=forms.TextInput(
                    attrs={
                        "class": "form-input",
                        "placeholder": f"Custom field name for {field_label}",
                    }
                ),
            )
