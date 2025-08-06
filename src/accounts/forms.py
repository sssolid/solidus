# src/accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.core.exceptions import ValidationError

from products.models import CustomerPricing, Product

from .models import CustomerProfile, User


class UserCreationForm(BaseUserCreationForm):
    """Form for creating new users"""

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password1",
            "password2",
            "first_name",
            "last_name",
            "role",
            "company_name",
            "phone",
            "customer_number",
            "tax_id",
        ]
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Username",
                    "hx-get": "/accounts/api/check-username/",
                    "hx-trigger": "keyup changed delay:500ms",
                    "hx-target": "#username-availability",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "email@example.com",
                    "hx-get": "/accounts/api/check-email/",
                    "hx-trigger": "keyup changed delay:500ms",
                    "hx-target": "#email-availability",
                }
            ),
            "role": forms.Select(attrs={"class": "form-select"}),
            "company_name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Company Name"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "+1 (555) 123-4567"}
            ),
            "customer_number": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "CUST-12345"}
            ),
            "tax_id": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Tax ID"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update(
            {"class": "form-input", "placeholder": "Password"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "form-input", "placeholder": "Confirm Password"}
        )

        # Make customer fields required for customer role
        self.fields["company_name"].required = False
        self.fields["customer_number"].required = False
        self.fields["tax_id"].required = False

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")

        if role == "customer":
            # Require company name for customers
            if not cleaned_data.get("company_name"):
                self.add_error(
                    "company_name", "Company name is required for customers."
                )

            # Validate customer number uniqueness
            customer_number = cleaned_data.get("customer_number")
            if customer_number:
                if User.objects.filter(customer_number=customer_number).exists():
                    self.add_error(
                        "customer_number", "This customer number is already in use."
                    )

        return cleaned_data


class UserEditForm(forms.ModelForm):
    """Form for editing existing users"""

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "company_name",
            "phone",
            "customer_number",
            "tax_id",
            "is_active",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-input"}),
            "email": forms.EmailInput(attrs={"class": "form-input"}),
            "first_name": forms.TextInput(attrs={"class": "form-input"}),
            "last_name": forms.TextInput(attrs={"class": "form-input"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "company_name": forms.TextInput(attrs={"class": "form-input"}),
            "phone": forms.TextInput(attrs={"class": "form-input"}),
            "customer_number": forms.TextInput(attrs={"class": "form-input"}),
            "tax_id": forms.TextInput(attrs={"class": "form-input"}),
        }


class ProfileEditForm(forms.ModelForm):
    """Form for users to edit their own profile"""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "First Name"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Last Name"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-input", "placeholder": "email@example.com"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "+1 (555) 123-4567"}
            ),
        }


class UserSettingsForm(forms.Form):
    """Form for user preferences and settings"""

    # Notification preferences
    notification_product_updates = forms.BooleanField(
        required=False,
        label="Product Updates",
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    notification_price_changes = forms.BooleanField(
        required=False,
        label="Price Changes",
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    notification_new_assets = forms.BooleanField(
        required=False,
        label="New Assets",
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    notification_feed_ready = forms.BooleanField(
        required=False,
        label="Feed Notifications",
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )
    notification_system = forms.BooleanField(
        required=False,
        label="System Notifications",
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )


class CustomerProfileForm(forms.ModelForm):
    """Form for editing customer profile details"""

    class Meta:
        model = CustomerProfile
        fields = [
            "business_type",
            "annual_revenue",
            "preferred_payment_terms",
            "credit_limit",
        ]
        widgets = {
            "business_type": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "e.g., Auto Parts Retailer",
                }
            ),
            "annual_revenue": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00"}
            ),
            "preferred_payment_terms": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "e.g., Net 30"}
            ),
            "credit_limit": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00"}
            ),
        }


class CustomerPricingForm(forms.ModelForm):
    """Form for managing customer-specific pricing"""

    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "data-placeholder": "Select a product",
                "hx-get": "/api/product-info/",
                "hx-trigger": "change",
                "hx-target": "#product-info",
            }
        ),
    )

    class Meta:
        model = CustomerPricing
        fields = [
            "product",
            "price",
            "discount_percent",
            "valid_from",
            "valid_until",
            "notes",
        ]
        widgets = {
            "price": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}
            ),
            "discount_percent": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "0.00",
                    "step": "0.01",
                    "max": "100",
                }
            ),
            "valid_from": forms.DateInput(
                attrs={"class": "form-input", "type": "date"}
            ),
            "valid_until": forms.DateInput(
                attrs={"class": "form-input", "type": "date"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 3,
                    "placeholder": "Additional notes about this pricing...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop("customer", None)
        super().__init__(*args, **kwargs)

        if self.customer:
            # Filter out products that already have custom pricing
            existing_products = CustomerPricing.objects.filter(
                customer=self.customer
            ).values_list("product_id", flat=True)
            self.fields["product"].queryset = self.fields["product"].queryset.exclude(
                id__in=existing_products
            )

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get("valid_from")
        valid_until = cleaned_data.get("valid_until")

        if valid_from and valid_until and valid_from > valid_until:
            raise ValidationError("Valid from date must be before valid until date.")

        return cleaned_data
