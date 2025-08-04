# src/assets/models.py
import hashlib
import os

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.core.files.storage import default_storage
from django.db import models
from django.utils import timezone
from taggit.managers import TaggableManager


class AssetCategory(models.Model):
    """Categories for organizing assets"""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    # Access control
    requires_permission = models.BooleanField(default=False)
    allowed_roles = ArrayField(
        models.CharField(max_length=20), default=list, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asset_categories"
        ordering = ["sort_order", "name"]
        verbose_name_plural = "Asset Categories"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent} > {self.name}"
        return self.name


class Asset(models.Model):
    """Main asset model for digital asset management"""

    ASSET_TYPES = [
        ("image", "Image"),
        ("video", "Video"),
        ("document", "Document"),
        ("archive", "Archive"),
        ("other", "Other"),
    ]

    # Basic info
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)

    # File info
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()  # in bytes
    file_hash = models.CharField(max_length=64, unique=True)  # SHA256 hash
    mime_type = models.CharField(max_length=100)

    # Organization
    categories = models.ManyToManyField(
        AssetCategory, related_name="assets", blank=True
    )
    tags = TaggableManager(blank=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)  # EXIF and other metadata
    custom_metadata = models.JSONField(
        default=dict, blank=True
    )  # User-defined metadata

    # Status
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False)

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assets_created",
    )

    # Usage tracking
    download_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "assets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["asset_type"]),
            models.Index(fields=["file_hash"]),
            models.Index(fields=["is_active", "is_public"]),
            models.Index(fields=["created_at"]),
            GinIndex(fields=["metadata"], name="asset_metadata_gin"),
        ]

    def __str__(self):
        return self.title

    def calculate_file_hash(self, file_content):
        """Calculate SHA256 hash of file content"""
        sha256_hash = hashlib.sha256()
        for chunk in file_content.chunks():
            sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def increment_download_count(self):
        """Increment download counter"""
        self.download_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=["download_count", "last_accessed"])

    def increment_view_count(self):
        """Increment view counter"""
        self.view_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=["view_count", "last_accessed"])

    def get_file_extension(self):
        """Get file extension"""
        return os.path.splitext(self.original_filename)[1].lower()


class AssetFile(models.Model):
    """Actual file storage for assets with versions"""

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="files")

    # File paths
    file_path = models.CharField(max_length=500)
    processed_path = models.CharField(max_length=500, blank=True)
    thumbnail_path = models.CharField(max_length=500, blank=True)

    # Version info
    version = models.IntegerField(default=1)
    is_current = models.BooleanField(default=True)

    # Processing info
    is_processed = models.BooleanField(default=False)
    processing_status = models.CharField(max_length=50, default="pending")
    processing_error = models.TextField(blank=True)

    # Image specific
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "asset_files"
        ordering = ["-version"]
        unique_together = [["asset", "version"]]
        indexes = [
            models.Index(fields=["asset", "is_current"]),
        ]

    def __str__(self):
        return f"{self.asset.title} - v{self.version}"

    def get_absolute_url(self):
        """Get the URL for the processed file or original"""
        if self.processed_path:
            return default_storage.url(self.processed_path)
        return default_storage.url(self.file_path)

    def get_thumbnail_url(self):
        """Get the thumbnail URL"""
        if self.thumbnail_path:
            return default_storage.url(self.thumbnail_path)
        return self.get_absolute_url()


class ProductAsset(models.Model):
    """Link between products and assets"""

    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, related_name="assets"
    )
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="products")

    # Asset role
    asset_type = models.CharField(
        max_length=50,
        choices=[
            ("image", "Product Image"),
            ("manual", "Manual"),
            ("datasheet", "Data Sheet"),
            ("installation", "Installation Guide"),
            ("marketing", "Marketing Material"),
            ("video", "Video"),
            ("other", "Other"),
        ],
    )

    # Display settings
    is_primary = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    # Metadata
    caption = models.CharField(max_length=255, blank=True)
    alt_text = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product_assets"
        ordering = ["sort_order", "created_at"]
        indexes = [
            models.Index(fields=["product", "asset_type"]),
            models.Index(fields=["is_primary"]),
        ]

    def __str__(self):
        return f"{self.product.sku} - {self.asset.title}"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per product
        if self.is_primary and self.asset_type == "image":
            ProductAsset.objects.filter(
                product=self.product, asset_type="image", is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class AssetCollection(models.Model):
    """Collections for grouping assets"""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    # Assets in collection
    assets = models.ManyToManyField(Asset, related_name="collections", blank=True)

    # Access control
    is_public = models.BooleanField(default=False)
    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="allowed_collections", blank=True
    )

    # Metadata
    cover_image = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="collection_covers",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="asset_collections_created",
    )

    class Meta:
        db_table = "asset_collections"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_public"]),
        ]

    def __str__(self):
        return self.name


class AssetDownload(models.Model):
    """Track asset downloads"""

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="downloads")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )

    # Download info
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    referer = models.URLField(blank=True)

    # Context
    purpose = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "asset_downloads"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["asset", "user"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.user} downloaded {self.asset.title}"
