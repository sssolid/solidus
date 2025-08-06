# src/products/models.py
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.core.cache import cache
from django.db import models
from django.db.models import JSONField
from taggit.managers import TaggableManager

from audit.mixins import AuditMixin

User = get_user_model()


class AuditedModel(AuditMixin, models.Model):
    """Base model with comprehensive audit support"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='%(class)s_created',
        editable=False
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='%(class)s_updated',
        null=True, blank=True,
        editable=False
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        user = getattr(self, '_current_user', None)
        if user and user.is_authenticated:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)


class Brand(AuditedModel):
    """Product brands/manufacturers"""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    logo = models.ImageField(upload_to="brands/", null=True, blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "brands"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Country(AuditedModel):
    """Countries for shipping"""
    name = models.CharField(max_length=100)
    native_name = models.CharField(max_length=100, blank=True)
    code_2 = models.CharField(max_length=2, unique=True, help_text="ISO 3166-1 alpha-2")
    code_3 = models.CharField(max_length=3, unique=True, help_text="ISO 3166-1 alpha-3")
    code_numeric = models.CharField(max_length=3, unique=True, help_text="ISO 3166-1 numeric")

    # Phone/currency
    calling_code = models.CharField(max_length=5, blank=True)
    currency_code = models.CharField(max_length=3, blank=True)
    currency_name = models.CharField(max_length=50, blank=True)
    currency_symbol = models.CharField(max_length=5, blank=True)

    # Geography
    region = models.CharField(max_length=50, blank=True)
    subregion = models.CharField(max_length=50, blank=True)
    capital = models.CharField(max_length=100, blank=True)
    tld = models.CharField(max_length=10, blank=True, help_text="Top level domain")
    latitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_shipping_available = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "countries"
        ordering = ["name"]
        verbose_name_plural = "Countries"
        indexes = [
            models.Index(fields=["code_2"]),
            models.Index(fields=["code_3"]),
            models.Index(fields=["is_active", "is_shipping_available"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.code_2})"


class Product(AuditedModel):
    """Main product model with automotive fitment support"""

    # Basic info
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    number = models.CharField(max_length=50, unique=True, db_index=True)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products")
    title = models.CharField(max_length=100)
    categories = models.ManyToManyField("Category", related_name="products")
    upc = models.CharField(max_length=14, blank=True)

    # Descriptions
    short_description = models.CharField(max_length=20, blank=True)
    long_description = models.TextField(blank=True)
    abbreviated_description = models.CharField(max_length=12, blank=True)
    invoice_description = models.CharField(max_length=20, blank=True)
    slang_description = models.CharField(max_length=20, blank=True)
    marketing_description = models.TextField(blank=True)
    keywords = models.CharField(max_length=500, blank=True)
    features = models.ManyToManyField("ProductFeature", related_name="products")
    seo = models.ForeignKey("ProductSEO", on_delete=models.CASCADE, related_name="products")

    # Automotive specific
    part_numbers = models.ManyToManyField("ProductInterchange", related_name="products")
    oem_numbers = models.ManyToManyField("ProductOEMNumber", related_name="products")
    tariff_code = models.CharField(max_length=12, blank=True)
    unspsc_code = models.CharField(max_length=12, blank=True)

    # Dimensions and weight
    length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dimensional_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    shipping_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Packaging
    quantity_required = models.PositiveIntegerField(default=1)
    quantity_in_package = models.PositiveIntegerField(default=1)
    includes = models.ManyToManyField("ProductIncludes", related_name="products")
    hardware = models.CharField(max_length=10, blank=True)

    # Warranty
    warranty_months = models.PositiveIntegerField(null=True, blank=True)
    warranty_description = models.TextField(blank=True)
    warranty_terms = models.TextField(blank=True)
    warranty_return_policy = models.TextField(blank=True)
    warranty_link = models.URLField(blank=True)

    # Pricing
    jobber = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    export = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    msrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    map_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    additional_shipping = models.BooleanField(default=False)
    sold_as = models.CharField(max_length=10, blank=True)

    # Fitment
    universal = models.BooleanField(default=False)

    # Compliance
    hazardous = models.BooleanField(default=False)
    proposition_65 = models.BooleanField(default=False)

    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    launch_date = models.DateField(null=True, blank=True)
    discontinue_date = models.DateField(null=True, blank=True)

    # Tags
    tags = TaggableManager(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="products_created",
    )

    class Meta:
        db_table = "products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["brand"]),
            models.Index(fields=["is_active", "is_featured"]),
        ]

    def __str__(self):
        return f"{self.sku} - {self.number}"

    def get_primary_image(self):
        """Get the primary product image"""
        return (
            self.assets.filter(asset_type="image", is_primary=True)
            .select_related("asset")
            .first()
        )

    def get_all_images(self):
        """Get all product images"""
        return (
            self.assets.filter(asset_type="image")
            .select_related("asset")
            .order_by("-is_primary", "sort_order")
        )

    def get_fitment_count(self):
        """Get count of vehicle fitments"""
        cache_key = f"product_fitment_count_{self.id}"
        count = cache.get(cache_key)
        if count is None:
            count = self.fitments.count()
            cache.set(cache_key, count, 3600)  # Cache for 1 hour
        return count

    def clear_fitment_cache(self):
        """Clear fitment-related cache"""
        cache.delete(f"product_fitment_count_{self.id}")


class ProductDescription(AuditedModel):
    DESCRIPTION_TYPES = (
        ("MKT", "Marketing"),
        ("LJO", "Long Jeep Only"),
        ("LNJ", "Long Non Jeep"),
        ("LAM", "Long All Models"),
        ("EXT", "Extended"),
        ("ENJ", "Extended Non Jeep"),
        ("EXU", "Extended Unlimited"),
    )

    """Product descriptions"""
    product = models.ForeignKey("Product", on_delete=models.CASCADE, related_name="descriptions")
    type = models.CharField(max_length=3, choices=DESCRIPTION_TYPES)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_descriptions"
        ordering = ["type"]
        verbose_name_plural = "Product Descriptions"
        indexes = [
            models.Index(fields=["type"]),
        ]

    def __str__(self):
        return f"{self.product.number} - {self.type}"


class ProductOrigin(AuditedModel):
    """Product origin countries"""
    product = models.OneToOneField("Product", on_delete=models.CASCADE)
    country_of_origin = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="origin_countries")
    assembled_in = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "product_origin"
        ordering = ["country_of_origin"]
        verbose_name_plural = "Product Origins"

    def __str__(self):
        return f"{self.product.number} - {self.country_of_origin}"


class ProductSEO(AuditedModel):
    """SEO fields for products"""
    product = models.OneToOneField("Product", on_delete=models.CASCADE, related_name="seo_info")
    meta_title = models.CharField(max_length=150, blank=True)
    meta_description = models.TextField(blank=True)

    class Meta:
        db_table = "product_seo"
        ordering = ["meta_title"]
        verbose_name_plural = "Product SEOs"

    def __str__(self):
        return f"{self.product.number} - {self.meta_title}"


class ProductIncludes(AuditedModel):
    """Product includes"""
    product = models.ForeignKey("Product", on_delete=models.CASCADE, related_name="included_items")
    component = models.CharField(max_length=50, unique=True, db_index=True)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "product_includes"
        ordering = ["product__number"]
        verbose_name_plural = "Product Includes"

    def __str__(self):
        return f"{self.product.number} - {self.component}"


class SpecificationType(AuditedModel):
    """Types of specifications that can be applied to products"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    # Data type information
    data_type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Text'),
            ('number', 'Number'),
            ('decimal', 'Decimal'),
            ('boolean', 'Yes/No'),
            ('choice', 'Multiple Choice'),
        ],
        default='text'
    )

    # For choice types
    choice_options = models.JSONField(default=list, blank=True)

    # Display and validation
    unit = models.CharField(max_length=20, blank=True, help_text="e.g., inches, lbs")
    is_required = models.BooleanField(default=False)
    is_filterable = models.BooleanField(default=True)
    is_searchable = models.BooleanField(default=True)

    # Grouping and ordering
    category = models.ForeignKey(
        'SpecificationCategory',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'specification_types'
        ordering = ['category__sort_order', 'sort_order', 'name']

    def __str__(self):
        return self.name


class SpecificationCategory(AuditedModel):
    """Categories for grouping specifications"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'specification_categories'
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'Specification Categories'

    def __str__(self):
        return self.name


class ProductSpecification(AuditedModel):
    """Individual product specifications - replaces JSONField"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='specifications'
    )
    spec_type = models.ForeignKey(
        SpecificationType,
        on_delete=models.PROTECT
    )

    # Value storage - only one should be filled based on spec_type.data_type
    text_value = models.TextField(blank=True)
    number_value = models.BigIntegerField(null=True, blank=True)
    decimal_value = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True)
    boolean_value = models.BooleanField(null=True, blank=True)
    choice_value = models.CharField(max_length=100, blank=True)

    # Metadata
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'product_specifications'
        unique_together = [['product', 'spec_type']]
        indexes = [
            models.Index(fields=['product', 'spec_type']),
            models.Index(fields=['spec_type', 'text_value']),
            models.Index(fields=['spec_type', 'number_value']),
            models.Index(fields=['spec_type', 'decimal_value']),
        ]

    def __str__(self):
        return f"{self.product.sku} - {self.spec_type.name}: {self.get_value()}"

    def get_value(self):
        """Get the actual value based on data type"""
        if self.spec_type.data_type == 'text':
            return self.text_value
        elif self.spec_type.data_type == 'number':
            return self.number_value
        elif self.spec_type.data_type == 'decimal':
            return self.decimal_value
        elif self.spec_type.data_type == 'boolean':
            return self.boolean_value
        elif self.spec_type.data_type == 'choice':
            return self.choice_value
        return None

    def set_value(self, value):
        """Set value based on data type"""
        # Clear all values first
        self.text_value = ''
        self.number_value = None
        self.decimal_value = None
        self.boolean_value = None
        self.choice_value = ''

        # Set appropriate value
        if self.spec_type.data_type == 'text':
            self.text_value = str(value)
        elif self.spec_type.data_type == 'number':
            self.number_value = int(value)
        elif self.spec_type.data_type == 'decimal':
            self.decimal_value = Decimal(str(value))
        elif self.spec_type.data_type == 'boolean':
            self.boolean_value = bool(value)
        elif self.spec_type.data_type == 'choice':
            self.choice_value = str(value)


class Feature(AuditedModel):
    """Available product features"""
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    category = models.ForeignKey(
        'FeatureCategory',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    # Display properties
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome icon class")
    color = models.CharField(max_length=7, blank=True, help_text="Hex color code")

    # Status
    is_active = models.BooleanField(default=True)
    is_premium = models.BooleanField(default=False)

    # Ordering
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'features'
        ordering = ['category__sort_order', 'sort_order', 'name']

    def __str__(self):
        return self.name


class FeatureCategory(AuditedModel):
    """Categories for grouping features"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'feature_categories'
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'Feature Categories'

    def __str__(self):
        return self.name


class ProductFeature(AuditedModel):
    """Product-feature relationships"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='feature_list'
    )
    feature = models.ForeignKey(
        Feature,
        on_delete=models.PROTECT
    )

    # Relationship metadata
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    # Value for features that have measurable attributes
    value = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'product_features'
        unique_together = [['product', 'feature']]
        indexes = [
            models.Index(fields=['product', 'is_primary']),
            models.Index(fields=['feature', 'product']),
        ]

    def __str__(self):
        return f"{self.product.sku} - {self.feature.name}"


class InterchangeType(models.Model):
    """Types of interchange numbers"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'interchange_types'
        ordering = ['name']

    def __str__(self):
        return self.name


class ProductInterchange(AuditedModel):
    """Product interchange numbers"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='interchange_list'
    )
    interchange_type = models.ForeignKey(
        InterchangeType,
        on_delete=models.PROTECT,
        default=1  # Assume default type exists
    )
    number = models.CharField(max_length=50, db_index=True)
    manufacturer = models.CharField(max_length=100, blank=True)
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'product_interchanges'
        unique_together = [['product', 'number', 'interchange_type']]
        indexes = [
            models.Index(fields=['number']),
            models.Index(fields=['product', 'is_primary']),
            models.Index(fields=['interchange_type', 'number']),
        ]

    def __str__(self):
        return f"{self.product.sku} - {self.number}"


class ProductOEMNumber(AuditedModel):
    """Product OEM numbers"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='oem_number_list'
    )
    number = models.CharField(max_length=50, db_index=True)
    manufacturer = models.CharField(max_length=100)
    is_primary = models.BooleanField(default=False)
    is_superseded = models.BooleanField(default=False)
    superseded_by = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'product_oem_numbers'
        unique_together = [['product', 'number', 'manufacturer']]
        indexes = [
            models.Index(fields=['number']),
            models.Index(fields=['manufacturer', 'number']),
            models.Index(fields=['product', 'is_primary']),
        ]

    def __str__(self):
        return f"{self.product.sku} - {self.manufacturer}: {self.number}"


class VehicleMake(models.Model):
    """Vehicle manufacturers"""

    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)
    country = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vehicle_makes"
        ordering = ["name"]

    def __str__(self):
        return self.name


class VehicleModel(models.Model):
    """Vehicle models"""

    make = models.ForeignKey(
        VehicleMake, on_delete=models.CASCADE, related_name="models"
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vehicle_models"
        ordering = ["make", "name"]
        unique_together = [["make", "code"]]
        indexes = [
            models.Index(fields=["make", "name"]),
        ]

    def __str__(self):
        return f"{self.make.name} {self.name}"


class ProductFitment(models.Model):
    """Vehicle fitment data for products"""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="fitments"
    )
    make = models.ForeignKey(VehicleMake, on_delete=models.CASCADE)
    model = models.ForeignKey(VehicleModel, on_delete=models.CASCADE)

    # Year range
    year_start = models.IntegerField()
    year_end = models.IntegerField()

    # Additional fitment details
    submodel = models.CharField(max_length=100, blank=True)
    engine = models.CharField(max_length=100, blank=True)
    position = models.CharField(max_length=50, blank=True)  # Front, Rear, etc.
    notes = models.TextField(blank=True)

    # Fitment attributes as JSON for flexibility
    attributes = JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_fitments"
        indexes = [
            models.Index(fields=["product", "make", "model"]),
            models.Index(fields=["year_start", "year_end"]),
            models.Index(fields=["make", "model", "year_start", "year_end"]),
        ]

    def __str__(self):
        return f"{self.product.sku} - {self.make.name} {self.model.name} ({self.year_start}-{self.year_end})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.product.clear_fitment_cache()

    def delete(self, *args, **kwargs):
        product = self.product
        super().delete(*args, **kwargs)
        product.clear_fitment_cache()


class CustomerPricing(models.Model):
    """Customer-specific pricing"""

    customer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="custom_pricing"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="customer_prices"
    )

    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    # Validity period
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="pricing_created",
    )

    class Meta:
        db_table = "customer_pricing"
        unique_together = [["customer", "product"]]
        indexes = [
            models.Index(fields=["customer", "product"]),
            models.Index(fields=["valid_from", "valid_until"]),
        ]

    def __str__(self):
        return f"{self.customer.company_name or self.customer.username} - {self.product.sku}: ${self.price}"
