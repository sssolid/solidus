# src/assets/admin.py
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Asset, AssetCategory, AssetCollection, AssetDownload, ProductAsset


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    """Asset category administration"""

    list_display = [
        "name",
        "parent",
        "slug",
        "asset_count",
        "icon_display",
        "is_active",
        "sort_order",
        "requires_permission",
    ]

    list_filter = ["is_active", "requires_permission", "parent", "created_at"]

    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "slug", "parent", "description", "icon")},
        ),
        ("Display", {"fields": ("is_active", "sort_order")}),
        (
            "Access Control",
            {
                "fields": ("requires_permission", "allowed_roles"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def asset_count(self, obj):
        """Count assets in category"""
        count = obj.assets.count()
        if count > 0:
            url = (
                reverse("admin:assets_asset_changelist")
                + f"?categories__id__exact={obj.id}"
            )
            return format_html('<a href="{}">{} assets</a>', url, count)
        return "0 assets"

    asset_count.short_description = "Assets"

    def icon_display(self, obj):
        """Display icon"""
        if obj.icon:
            return format_html('<i class="fas {}"></i> {}', obj.icon, obj.icon)
        return "No icon"

    icon_display.short_description = "Icon"


class ProductAssetInline(admin.TabularInline):
    """Inline for product assets"""

    model = ProductAsset
    extra = 0
    fields = [
        "product",
        "asset_type",
        "is_primary",
        "sort_order",
        "caption",
        "alt_text",
    ]
    readonly_fields = ["created_at"]


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    """Asset administration"""

    list_display = [
        "title",
        "asset_type",
        "file_size_display",
        "display_categories",
        "is_active",
        "is_public",
        "download_count",
        "view_count",
        "created_by",
        "created_at",
    ]

    list_filter = [
        "asset_type",
        "is_active",
        "is_public",
        "categories",
        "created_at",
        "created_by",
    ]

    search_fields = [
        "title",
        "description",
        "original_filename",
        # TODO: tags__name does not exist
        # 'tags__name'
    ]

    readonly_fields = [
        "file_hash",
        "file_size",
        "mime_type",
        "original_filename",
        "download_count",
        "view_count",
        "last_accessed",
        "created_at",
        "updated_at",
        "get_file_info",
        "get_metadata_display",
    ]

    filter_horizontal = ["categories"]
    inlines = [ProductAssetInline]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("title", "description", "asset_type", "categories")},
        ),
        (
            "File Information",
            {
                # TODO: get_file_info does not exist
                "fields": (
                    # 'get_file_info',
                    "file_hash",
                    "file_size",
                    "mime_type",
                    "original_filename",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Access Control",
            {
                # TODO: employee_only does not exist
                "fields": ("is_active", "is_public"),  # 'employee_only')
            },
        ),
        (
            "Metadata",
            {
                # TODO: get_metadata_display does not exist
                "fields": (
                    # 'get_metadata_display',
                    "custom_metadata",
                    "tags",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Statistics",
            {
                "fields": ("download_count", "view_count", "last_accessed"),
                "classes": ("collapse",),
            },
        ),
        (
            "System Information",
            {
                "fields": ("created_at", "updated_at", "created_by"),
                "classes": ("collapse",),
            },
        ),
    )

    def file_size_display(self, obj):
        """Display file size in human readable format"""
        if not obj.file_size:
            return "Unknown"

        for unit in ["B", "KB", "MB", "GB"]:
            if obj.file_size < 1024.0:
                return f"{obj.file_size:.1f} {unit}"
            obj.file_size /= 1024.0
        return f"{obj.file_size:.1f} TB"

    file_size_display.short_description = "File Size"
    file_size_display.admin_order_field = "file_size"

    def display_categories(self, obj):
        """Display categories"""
        categories = obj.categories.all()[:3]
        if categories:
            return ", ".join([cat.name for cat in categories])
        return "Uncategorized"

    display_categories.short_description = "Categories"

    def get_file_info(self, obj):
        """Display file information"""
        if obj.file_path:
            return format_html(
                "<strong>Path:</strong> {}<br>"
                "<strong>Hash:</strong> {}<br>"
                "<strong>MIME:</strong> {}",
                obj.file_path,
                obj.file_hash[:16] + "..." if obj.file_hash else "None",
                obj.mime_type,
            )
        return "No file uploaded"

    get_file_info.short_description = "File Information"

    def get_metadata_display(self, obj):
        """Display metadata in formatted way"""
        if obj.metadata:
            items = []
            for key, value in list(obj.metadata.items())[:5]:  # Show first 5 items
                items.append(f"<strong>{key}:</strong> {value}")
            html = "<br>".join(items)
            if len(obj.metadata) > 5:
                html += f"<br><em>... and {len(obj.metadata) - 5} more</em>"
            return mark_safe(html)
        return "No metadata"

    get_metadata_display.short_description = "EXIF/Metadata"

    def save_model(self, request, obj, form, change):
        """Set created_by for new assets"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    actions = ["make_public", "make_private", "activate_assets", "deactivate_assets"]

    def make_public(self, request, queryset):
        """Make assets public"""
        count = queryset.update(is_public=True)
        self.message_user(request, f"{count} assets made public.")

    make_public.short_description = "Make selected assets public"

    def make_private(self, request, queryset):
        """Make assets private"""
        count = queryset.update(is_public=False)
        self.message_user(request, f"{count} assets made private.")

    make_private.short_description = "Make selected assets private"

    def activate_assets(self, request, queryset):
        """Activate assets"""
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} assets activated.")

    activate_assets.short_description = "Activate selected assets"

    def deactivate_assets(self, request, queryset):
        """Deactivate assets"""
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} assets deactivated.")

    deactivate_assets.short_description = "Deactivate selected assets"


@admin.register(AssetCollection)
class AssetCollectionAdmin(admin.ModelAdmin):
    """Asset collection administration"""

    list_display = [
        "name",
        "slug",
        "asset_count",
        "is_public",
        "cover_image_display",
        "created_by",
        "created_at",
    ]

    list_filter = ["is_public", "created_at", "created_by"]

    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]
    filter_horizontal = ["assets", "allowed_users"]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "slug", "description", "cover_image")},
        ),
        ("Assets", {"fields": ("assets",)}),
        (
            "Access Control",
            {"fields": ("is_public", "allowed_users"), "classes": ("collapse",)},
        ),
        (
            "System Information",
            {
                "fields": ("created_at", "updated_at", "created_by"),
                "classes": ("collapse",),
            },
        ),
    )

    def asset_count(self, obj):
        """Count assets in collection"""
        return obj.assets.count()

    asset_count.short_description = "Assets"

    def cover_image_display(self, obj):
        """Display cover image thumbnail"""
        if obj.cover_image and hasattr(obj.cover_image, "get_thumbnail_url"):
            return format_html(
                '<img src="{}" style="max-width: 50px; max-height: 50px;" />',
                obj.cover_image.get_thumbnail_url(),
            )
        return "No image"

    cover_image_display.short_description = "Cover"

    def save_model(self, request, obj, form, change):
        """Set created_by for new collections"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AssetDownload)
class AssetDownloadAdmin(admin.ModelAdmin):
    """Asset download tracking administration"""

    list_display = ["asset", "user", "ip_address", "purpose", "created_at"]

    list_filter = ["created_at", "purpose", "asset__asset_type"]

    search_fields = [
        "asset__title",
        "user__username",
        "user__email",
        "ip_address",
        "purpose",
    ]

    readonly_fields = [
        "asset",
        "user",
        "ip_address",
        "user_agent",
        "referer",
        "created_at",
    ]

    fieldsets = (
        ("Download Information", {"fields": ("asset", "user", "purpose", "notes")}),
        (
            "Technical Details",
            {
                "fields": ("ip_address", "user_agent", "referer"),
                "classes": ("collapse",),
            },
        ),
        ("Timestamp", {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        """Disable manual creation of download records"""
        return False

    def has_change_permission(self, request, obj=None):
        """Make download records read-only"""
        return False


@admin.register(ProductAsset)
class ProductAssetAdmin(admin.ModelAdmin):
    """Product asset link administration"""

    list_display = [
        "product_sku",
        "asset_title",
        "asset_type",
        "is_primary",
        "sort_order",
        "created_at",
    ]

    list_filter = ["asset_type", "is_primary", "created_at"]

    search_fields = ["product__sku", "product__name", "asset__title", "caption"]

    readonly_fields = ["created_at"]

    fieldsets = (
        ("Relationship", {"fields": ("product", "asset", "asset_type")}),
        (
            "Display Settings",
            {"fields": ("is_primary", "sort_order", "caption", "alt_text")},
        ),
        ("Timestamp", {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    def product_sku(self, obj):
        """Display product SKU"""
        return obj.product.sku

    product_sku.short_description = "Product SKU"
    product_sku.admin_order_field = "product__sku"

    def asset_title(self, obj):
        """Display asset title"""
        return obj.asset.title

    asset_title.short_description = "Asset"
    asset_title.admin_order_field = "asset__title"
