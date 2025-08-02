# src/products/forms.py
from django import forms
from django.core.exceptions import ValidationError
from taggit.forms import TagWidget

from .models import Brand, Category, Product, ProductFitment


class ProductForm(forms.ModelForm):
    """Form for creating and editing products"""

    class Meta:
        model = Product
        fields = [
            "sku",
            "name",
            "description",
            "brand",
            "categories",
            "weight",
            "dimensions",
            "material",
            "color",
            "finish",
            "part_numbers",
            "oem_numbers",
            "msrp",
            "map_price",
            "is_active",
            "is_featured",
            "launch_date",
            "discontinue_date",
            "meta_title",
            "meta_description",
            "tags",
        ]
        widgets = {
            "sku": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "e.g., ABC-12345"}
            ),
            "name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Product Name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 4,
                    "placeholder": "Detailed product description...",
                }
            ),
            "brand": forms.Select(attrs={"class": "form-select"}),
            "categories": forms.CheckboxSelectMultiple(),
            "weight": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}
            ),
            "dimensions": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "L x W x H (inches)"}
            ),
            "material": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "e.g., Steel, Aluminum"}
            ),
            "color": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "e.g., Black, Silver"}
            ),
            "finish": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "e.g., Powder Coated, Anodized",
                }
            ),
            "part_numbers": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 3,
                    "placeholder": "One part number per line",
                }
            ),
            "oem_numbers": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 3,
                    "placeholder": "One OEM number per line",
                }
            ),
            "msrp": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}
            ),
            "map_price": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "launch_date": forms.DateInput(
                attrs={"class": "form-input", "type": "date"}
            ),
            "discontinue_date": forms.DateInput(
                attrs={"class": "form-input", "type": "date"}
            ),
            "meta_title": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "SEO title (max 150 chars)",
                }
            ),
            "meta_description": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 3,
                    "placeholder": "SEO description (max 300 chars)",
                }
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
        self.fields["brand"].queryset = Brand.objects.filter(is_active=True)
        self.fields["categories"].queryset = Category.objects.filter(is_active=True)

    def clean_sku(self):
        sku = self.cleaned_data.get("sku")
        if sku:
            # Check for unique SKU
            queryset = Product.objects.filter(sku=sku)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise ValidationError("A product with this SKU already exists.")
        return sku

    def clean(self):
        cleaned_data = super().clean()
        launch_date = cleaned_data.get("launch_date")
        discontinue_date = cleaned_data.get("discontinue_date")

        if launch_date and discontinue_date and launch_date > discontinue_date:
            raise ValidationError("Launch date must be before discontinue date.")

        return cleaned_data


class ProductFitmentForm(forms.ModelForm):
    """Form for managing vehicle fitments"""

    class Meta:
        model = ProductFitment
        fields = [
            "year_start",
            "year_end",
            "make",
            "model",
            "submodel",
            "engine",
            "trim",
            "notes",
        ]
        widgets = {
            "year_start": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "2020",
                    "min": "1900",
                    "max": "2050",
                }
            ),
            "year_end": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "2023",
                    "min": "1900",
                    "max": "2050",
                }
            ),
            "make": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "e.g., Ford"}
            ),
            "model": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "e.g., F-150"}
            ),
            "submodel": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "e.g., SuperCrew"}
            ),
            "engine": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "e.g., 5.0L V8"}
            ),
            "trim": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "e.g., XLT, Lariat"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 3,
                    "placeholder": "Additional fitment notes...",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        year_start = cleaned_data.get("year_start")
        year_end = cleaned_data.get("year_end")

        if year_start and year_end and year_start > year_end:
            raise ValidationError("Start year must be before or equal to end year.")

        return cleaned_data


class BrandForm(forms.ModelForm):
    """Form for managing brands"""

    class Meta:
        model = Brand
        fields = ["name", "slug", "description", "logo", "website", "is_active"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Brand Name"}
            ),
            "slug": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "brand-slug"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 4,
                    "placeholder": "Brand description...",
                }
            ),
            "logo": forms.FileInput(attrs={"class": "form-input", "accept": "image/*"}),
            "website": forms.URLInput(
                attrs={"class": "form-input", "placeholder": "https://example.com"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }


class CategoryForm(forms.ModelForm):
    """Form for managing categories"""

    class Meta:
        model = Category
        fields = [
            "name",
            "slug",
            "parent",
            "description",
            "image",
            "meta_title",
            "meta_description",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Category Name"}
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
            "image": forms.FileInput(
                attrs={"class": "form-input", "accept": "image/*"}
            ),
            "meta_title": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "SEO title"}
            ),
            "meta_description": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 3,
                    "placeholder": "SEO description",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude self from parent choices to prevent circular references
        if self.instance.pk:
            self.fields["parent"].queryset = Category.objects.filter(
                is_active=True
            ).exclude(pk=self.instance.pk)
        else:
            self.fields["parent"].queryset = Category.objects.filter(is_active=True)


class ProductSearchForm(forms.Form):
    """Form for searching products"""

    query = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Search products, SKUs, part numbers...",
                "hx-get": "/products/search/",
                "hx-trigger": "keyup changed delay:300ms",
                "hx-target": "#search-results",
            }
        ),
    )

    brand = forms.ModelChoiceField(
        queryset=Brand.objects.filter(is_active=True),
        required=False,
        empty_label="All Brands",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    is_featured = forms.BooleanField(
        required=False, widget=forms.CheckboxInput(attrs={"class": "form-checkbox"})
    )

    price_min = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-input", "placeholder": "Min price", "step": "0.01"}
        ),
    )

    price_max = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-input", "placeholder": "Max price", "step": "0.01"}
        ),
    )
