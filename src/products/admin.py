# src/products/admin.py
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    Brand,
    Category,
    CustomerPricing,
    Product,
    ProductFitment,
    VehicleMake,
    VehicleModel,
)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "product_count", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "code"]
    readonly_fields = ["created_at", "updated_at"]

    def product_count(self, obj):
        count = obj.products.count()
        url = (
            reverse("admin:products_product_changelist") + f"?brand__id__exact={obj.id}"
        )
        return format_html('<a href="{}">{} products</a>', url, count)

    product_count.short_description = "Products"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "parent",
        "slug",
        "product_count",
        "sort_order",
        "is_active",
    ]
    list_filter = ["is_active", "parent"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "Products"


class ProductFitmentInline(admin.TabularInline):
    model = ProductFitment
    extra = 1
    fields = [
        "make",
        "model",
        "year_start",
        "year_end",
        "submodel",
        "engine",
        "position",
    ]
    autocomplete_fields = ["make", "model"]


class CustomerPricingInline(admin.TabularInline):
    model = CustomerPricing
    extra = 0
    fields = ["customer", "price", "discount_percent", "valid_from", "valid_until"]
    readonly_fields = ["created_at", "created_by"]
    autocomplete_fields = ["customer"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "sku",
        "name",
        "brand",
        "display_categories",
        "msrp",
        "fitment_count",
        "is_active",
        "is_featured",
    ]
    list_filter = [
        "is_active",
        "is_featured",
        "brand",
        "categories",
        "created_at",
        "launch_date",
    ]
    search_fields = ["sku", "name", "short_description", "part_numbers", "oem_numbers"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "created_by",
        "fitment_count",
        "display_primary_image",
    ]
    filter_horizontal = ["categories"]
    inlines = [ProductFitmentInline, CustomerPricingInline]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "sku",
                    "name",
                    "brand",
                    "categories",
                    "short_description",
                    "long_description",
                )
            },
        ),
        (
            "Part Numbers",
            {"fields": ("part_numbers", "oem_numbers"), "classes": ("collapse",)},
        ),
        (
            "Specifications",
            {
                "fields": (
                    "features",
                    "specifications",
                    "length",
                    "width",
                    "height",
                    "weight",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Pricing", {"fields": ("msrp", "map_price")}),
        (
            "Status",
            {"fields": ("is_active", "is_featured", "launch_date", "discontinue_date")},
        ),
        (
            "SEO",
            {
                "fields": ("meta_title", "meta_description", "tags"),
                "classes": ("collapse",),
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "created_by",
                    "fitment_count",
                    "display_primary_image",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def display_categories(self, obj):
        return ", ".join([cat.name for cat in obj.categories.all()[:3]])

    display_categories.short_description = "Categories"

    def fitment_count(self, obj):
        return obj.get_fitment_count()

    fitment_count.short_description = "Fitments"

    def display_primary_image(self, obj):
        image = obj.get_primary_image()
        if image and image.file:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px;" />',
                image.file.get_thumbnail_url(),
            )
        return "No image"

    display_primary_image.short_description = "Primary Image"

    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    class Media:
        css = {"all": ("admin/css/products.css",)}
        js = ("admin/js/products.js",)


@admin.register(VehicleMake)
class VehicleMakeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "country", "model_count", "is_active"]
    list_filter = ["is_active", "country"]
    search_fields = ["name", "code"]

    def model_count(self, obj):
        return obj.models.count()

    model_count.short_description = "Models"


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ["name", "make", "code", "fitment_count", "is_active"]
    list_filter = ["is_active", "make"]
    search_fields = ["name", "code", "make__name"]
    autocomplete_fields = ["make"]

    def fitment_count(self, obj):
        return ProductFitment.objects.filter(model=obj).count()

    fitment_count.short_description = "Fitments"


@admin.register(ProductFitment)
class ProductFitmentAdmin(admin.ModelAdmin):
    list_display = [
        "product_sku",
        "make",
        "model",
        "year_range",
        "submodel",
        "engine",
        "position",
    ]
    list_filter = ["make", "model", "position"]
    search_fields = [
        "product__sku",
        "product__name",
        "make__name",
        "model__name",
        "submodel",
        "engine",
    ]
    autocomplete_fields = ["product", "make", "model"]
    readonly_fields = ["created_at", "updated_at"]

    def product_sku(self, obj):
        return obj.product.sku

    product_sku.short_description = "SKU"
    product_sku.admin_order_field = "product__sku"

    def year_range(self, obj):
        return f"{obj.year_start}-{obj.year_end}"

    year_range.short_description = "Years"


@admin.register(CustomerPricing)
class CustomerPricingAdmin(admin.ModelAdmin):
    list_display = [
        "customer_name",
        "product_sku",
        "price",
        "discount_percent",
        "validity_period",
        "created_at",
    ]
    list_filter = ["created_at", "valid_from", "valid_until"]
    search_fields = [
        "customer__username",
        "customer__email",
        "customer__company_name",
        "product__sku",
        "product__name",
    ]
    autocomplete_fields = ["customer", "product"]
    readonly_fields = ["created_at", "updated_at", "created_by"]

    fieldsets = (
        ("Customer & Product", {"fields": ("customer", "product")}),
        ("Pricing", {"fields": ("price", "discount_percent", "notes")}),
        ("Validity", {"fields": ("valid_from", "valid_until")}),
        (
            "System Information",
            {
                "fields": ("created_at", "updated_at", "created_by"),
                "classes": ("collapse",),
            },
        ),
    )

    def customer_name(self, obj):
        return obj.customer.company_name or obj.customer.username

    customer_name.short_description = "Customer"
    customer_name.admin_order_field = "customer__company_name"

    def product_sku(self, obj):
        return obj.product.sku

    product_sku.short_description = "Product SKU"
    product_sku.admin_order_field = "product__sku"

    def validity_period(self, obj):
        if obj.valid_from and obj.valid_until:
            return f"{obj.valid_from} to {obj.valid_until}"
        elif obj.valid_from:
            return f"From {obj.valid_from}"
        elif obj.valid_until:
            return f"Until {obj.valid_until}"
        return "Always valid"

    validity_period.short_description = "Valid Period"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
