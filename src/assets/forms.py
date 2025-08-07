# src/assets/forms.py
from django import forms
from django.core.exceptions import ValidationError
from taggit.forms import TagWidget

from products.models import Product

from .models import Asset, AssetCategory, AssetCollection, ProductAsset


class AssetForm(forms.ModelForm):
    """Form for creating and editing assets"""

    class Meta:
        model = Asset
        fields = [
            "title",
            "description",
            "asset_type",
            # "file",
            "categories",
            "is_active",
            "is_public",
            # "copyright_info",
            # "alt_text",
            # "caption",
            "tags",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Asset title"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 4,
                    "placeholder": "Asset description...",
                }
            ),
            "asset_type": forms.Select(attrs={"class": "form-select"}),
            "file": forms.FileInput(
                attrs={
                    "class": "form-input",
                    "accept": "image/*,video/*,.pdf,.doc,.docx,.zip,.rar",
                }
            ),
            "categories": forms.CheckboxSelectMultiple(),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_public": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "copyright_info": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Copyright information"}
            ),
            "alt_text": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Alternative text for accessibility",
                }
            ),
            "caption": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Asset caption"}
            ),
            "tags": TagWidget(
                attrs={
                    "class": "form-input",
                    "placeholder": "Add tags separated by commas",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categories"].queryset = AssetCategory.objects.filter(
            is_active=True
        )

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file:
            # Check file size (max 100MB by default)
            max_size = 100 * 1024 * 1024  # 100MB
            if file.size > max_size:
                raise ValidationError(
                    f"File size must be less than {max_size // (1024 * 1024)}MB"
                )
        return file


class MultipleFileInput(forms.ClearableFileInput):
    """
    Enable multiple=<input type="file" multiple> *without* triggering ValueError.
    """

    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """
    Accept multiple files: validate all, return a list of files.
    """

    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, list | tuple):
            return [single_clean(f, initial) for f in data]
        return [single_clean(data, initial)]


class AssetUploadForm(forms.Form):
    """Form for bulk asset uploads"""

    files = MultipleFileField(
        required=True,
        widget=MultipleFileInput(
            attrs={
                "class": "form-input",
                "accept": "image/*,video/*,.pdf,.doc,.docx,.zip,.rar",
            }
        ),
        help_text="Select one or more files to upload",
    )

    category = forms.ModelChoiceField(
        queryset=AssetCategory.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Optional: Assign all files to a category",
    )

    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Common tags for all files (comma separated)",
            }
        ),
    )

    is_public = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        help_text="Make all uploaded assets publicly accessible",
    )


class ProductAssetForm(forms.ModelForm):
    """Form for linking assets to products"""

    class Meta:
        model = ProductAsset
        fields = [
            "product",
            "asset",
            "asset_type",
            "is_primary",
            "sort_order",
            "caption",
            "alt_text",
        ]
        widgets = {
            "product": forms.Select(
                attrs={"class": "form-select", "data-placeholder": "Select a product"}
            ),
            "asset": forms.Select(
                attrs={"class": "form-select", "data-placeholder": "Select an asset"}
            ),
            "asset_type": forms.Select(attrs={"class": "form-select"}),
            "is_primary": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "sort_order": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0"}
            ),
            "caption": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Asset caption"}
            ),
            "alt_text": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Alternative text"}
            ),
        }

    def __init__(self, *args, **kwargs):
        product = kwargs.pop("product", None)
        super().__init__(*args, **kwargs)

        self.fields["product"].queryset = Product.objects.filter(is_active=True)
        self.fields["asset"].queryset = Asset.objects.filter(is_active=True)

        if product:
            self.fields["product"].initial = product
            self.fields["product"].widget.attrs["readonly"] = True


class AssetCategoryForm(forms.ModelForm):
    """Form for managing asset categories"""

    class Meta:
        model = AssetCategory
        fields = [
            "name",
            "slug",
            "parent",
            "description",
            "icon",
            "is_active",
            "sort_order",
            "requires_permission",
            "allowed_roles",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Category name"}
            ),
            "slug": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "category-slug"}
            ),
            "parent": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 4,
                    "placeholder": "Category description...",
                }
            ),
            "icon": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "fa-icon-name"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "sort_order": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0"}
            ),
            "requires_permission": forms.CheckboxInput(
                attrs={"class": "form-checkbox"}
            ),
            "allowed_roles": forms.CheckboxSelectMultiple(
                choices=[
                    ("admin", "Admin"),
                    ("employee", "Employee"),
                    ("customer", "Customer"),
                ]
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude self from parent choices to prevent circular references
        if self.instance.pk:
            self.fields["parent"].queryset = AssetCategory.objects.filter(
                is_active=True
            ).exclude(pk=self.instance.pk)
        else:
            self.fields["parent"].queryset = AssetCategory.objects.filter(
                is_active=True
            )


class AssetCollectionForm(forms.ModelForm):
    """Form for managing asset collections"""

    class Meta:
        model = AssetCollection
        fields = [
            "name",
            "slug",
            "description",
            "assets",
            "is_public",
            "allowed_users",
            "cover_image",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Collection name"}
            ),
            "slug": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "collection-slug"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 4,
                    "placeholder": "Collection description...",
                }
            ),
            "assets": forms.CheckboxSelectMultiple(),
            "is_public": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "allowed_users": forms.CheckboxSelectMultiple(),
            "cover_image": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assets"].queryset = Asset.objects.filter(is_active=True)
        self.fields["cover_image"].queryset = Asset.objects.filter(
            asset_type="image", is_active=True
        )

        # Only show users for allowed_users if not public
        from accounts.models import User

        self.fields["allowed_users"].queryset = User.objects.filter(is_active=True)


class AssetSearchForm(forms.Form):
    """Form for searching assets"""

    query = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Search assets by title, description, tags...",
                "hx-get": "/assets/search/",
                "hx-trigger": "keyup changed delay:300ms",
                "hx-target": "#search-results",
            }
        ),
    )

    asset_type = forms.ChoiceField(
        choices=[("", "All Types")] + Asset.ASSET_TYPES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    category = forms.ModelChoiceField(
        queryset=AssetCategory.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    is_public = forms.BooleanField(
        required=False, widget=forms.CheckboxInput(attrs={"class": "form-checkbox"})
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-input", "type": "date"}),
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-input", "type": "date"}),
    )


class AssetFilterForm(forms.Form):
    """Form for asset filtering - used with search_filter partial"""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search assets...',
            'data-auto-submit': 'true',
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        })
    )

    category = forms.ModelChoiceField(
        queryset=AssetCategory.objects.filter(is_active=True),
        required=False,
        empty_label='All Categories',
        widget=forms.Select(attrs={
            'data-auto-submit': 'true',
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        })
    )

    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Asset.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'data-auto-submit': 'true',
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        })
    )

    sort = forms.ChoiceField(
        choices=[
            ('created_at', 'Newest First'),
            ('-created_at', 'Oldest First'),
            ('title', 'Title A-Z'),
            ('-title', 'Title Z-A'),
            ('file_size', 'Smallest First'),
            ('-file_size', 'Largest First'),
        ],
        required=False,
        initial='created_at',
        widget=forms.Select(attrs={
            'data-auto-submit': 'true',
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        })
    )


class AssetTagForm(forms.Form):
    """Form for bulk tagging assets"""

    assets = forms.ModelMultipleChoiceField(
        queryset=Asset.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(),
    )

    action = forms.ChoiceField(
        choices=[
            ("add", "Add Tags"),
            ("remove", "Remove Tags"),
            ("replace", "Replace All Tags"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    tags = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Enter tags separated by commas",
            }
        )
    )
