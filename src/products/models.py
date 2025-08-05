# src/products/models.py
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.core.cache import cache
from django.db import models
from django.db.models import JSONField
from taggit.managers import TaggableManager


class Brand(models.Model):
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


class Category(models.Model):
    """Product categories with hierarchy"""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", null=True, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # SEO fields
    meta_title = models.CharField(max_length=150, blank=True)
    meta_description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "categories"
        ordering = ["sort_order", "name"]
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent} > {self.name}"
        return self.name

    def get_ancestors(self):
        """Get all parent categories"""
        ancestors = []
        parent = self.parent
        while parent:
            ancestors.append(parent)
            parent = parent.parent
        return ancestors[::-1]

    def get_descendants(self):
        """Get all child categories recursively"""
        descendants = []
        children = self.children.filter(is_active=True)
        for child in children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants


class Description(models.Model):
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
    type = models.CharField(max_length=1, choices=DESCRIPTION_TYPES)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_descriptions"
        ordering = ["type"]
        verbose_name_plural = "Product Descriptions"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        return f"{self.product.number} - {self.type}"


class Country(models.Model):
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


class ProductOrigin(models.Model):
    """Product origin countries"""
    product = models.OneToOneField("Product", on_delete=models.CASCADE)
    country_of_origin = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="origin_countries")
    assembled_in = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "product_origin"
        ordering = ["country_of_origin"]
        verbose_name_plural = "Product Origins"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        return f"{self.product.number} - {self.country_of_origin}"


class ProductSEO(models.Model):
    """SEO fields for products"""
    product = models.OneToOneField("Product", on_delete=models.CASCADE, related_name="seo")
    meta_title = models.CharField(max_length=150, blank=True)
    meta_description = models.TextField(blank=True)


class ProductInterchanges(models.Model):
    """Product interchange data"""
    product = models.ForeignKey("Product", on_delete=models.CASCADE, related_name="interchanges")
    number = models.CharField(max_length=50, unique=True, db_index=True)


class ProductOEMNumbers(models.Model):
    """Product OEM numbers"""
    product = models.ForeignKey("Product", on_delete=models.CASCADE, related_name="oem_numbers")
    number = models.CharField(max_length=50, unique=True, db_index=True)


class ProductIncludes(models.Model):
    """Product includes"""
    product = models.ForeignKey("Product", on_delete=models.CASCADE, related_name="includes")
    component = models.CharField(max_length=50, unique=True, db_index=True)
    quantity = models.PositiveIntegerField(default=1)


class ProductFeatures(models.Model):
    """Product features"""
    product = models.ForeignKey("Product", on_delete=models.CASCADE, related_name="features")
    feature = models.CharField(max_length=256, unique=True, db_index=True)


class Product(models.Model):
    """Main product model with automotive fitment support"""

    # Basic info
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    number = models.CharField(max_length=50, unique=True, db_index=True)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products")
    title = models.CharField(max_length=100)
    categories = models.ManyToManyField(Category, related_name="products")
    upc = models.CharField(max_length=14, blank=True)

    # Descriptions
    short_description = models.CharField(max_length=20, blank=True)
    long_description = models.TextField(blank=True)
    abbreviated_description = models.CharField(max_length=12, blank=True)
    invoice_description = models.CharField(max_length=20, blank=True)
    slang_description = models.CharField(max_length=20, blank=True)
    marketing_description = models.TextField(blank=True)
    keywords = models.CharField(max_length=255, blank=True)
    features = models.ManyToManyField(ProductFeatures, related_name="products")

    # Automotive specific
    part_numbers = models.ManyToManyField(ProductInterchanges, related_name="products")
    oem_numbers = models.ManyToManyField(ProductOEMNumbers, related_name="products")
    tariff_code = models.CharField(max_length=12, blank=True)
    unspsc_code = models.CharField(max_length=12, blank=True)

    # Specifications stored as JSON for flexibility
    specifications = JSONField(default=dict, blank=True)

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
    includes = models.ManyToManyField(ProductIncludes, related_name="products")

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
    hardware = models.CharField(max_length=10, blank=True)
    universal = models.BooleanField(default=False)
    hazardous = models.BooleanField(default=False)

    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    launch_date = models.DateField(null=True, blank=True)
    discontinue_date = models.DateField(null=True, blank=True)

    # SEO
    seo = models.ForeignKey(ProductSEO, on_delete=models.CASCADE, related_name="products")

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
            GinIndex(fields=["part_numbers"]),
            GinIndex(fields=["oem_numbers"]),
        ]

    def __str__(self):
        return f"{self.sku} - {self.name}"

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
