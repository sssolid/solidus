# src/core/management/commands/create_dev_data.py
"""
Management command to create development data for testing and development
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = "Create development data for testing and development purposes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing data before creating new data",
        )
        parser.add_argument(
            "--users",
            type=int,
            default=20,
            help="Number of users to create (default: 20)",
        )
        parser.add_argument(
            "--products",
            type=int,
            default=100,
            help="Number of products to create (default: 100)",
        )
        parser.add_argument(
            "--assets",
            type=int,
            default=50,
            help="Number of assets to create (default: 50)",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write(self.style.WARNING("Resetting existing data..."))
            self.reset_data()

        self.stdout.write(self.style.SUCCESS("Creating development data..."))

        # Create users
        self.create_users(options["users"])

        # Create brands and categories
        self.create_brands_and_categories()

        # Create products
        self.create_products(options["products"])

        # Create assets
        self.create_assets(options["assets"])

        # Create feeds
        self.create_feeds()

        # Create audit logs
        self.create_audit_logs()

        self.stdout.write(self.style.SUCCESS("Successfully created development data!"))

    def reset_data(self):
        """Reset existing data"""
        from src.assets.models import Asset, AssetCategory
        from src.audit.models import AuditLog
        from src.feeds.models import DataFeed
        from src.products.models import Brand, Category, Product

        # Delete in order to respect foreign keys
        AuditLog.objects.all().delete()
        DataFeed.objects.all().delete()
        Asset.objects.all().delete()
        AssetCategory.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        Brand.objects.all().delete()

        # Delete non-superuser users
        User.objects.filter(is_superuser=False).delete()

        self.stdout.write(self.style.SUCCESS("Data reset complete."))

    def create_users(self, count):
        """Create users with different roles"""
        from src.accounts.models import CustomerProfile

        # Create admin user if it doesn't exist
        if not User.objects.filter(username="admin").exists():
            _admin = User.objects.create_user(
                username="admin",
                email="admin@solidus.local",
                password="admin123",
                first_name="Admin",
                last_name="User",
                is_superuser=True,
                is_staff=True,
            )
            self.stdout.write("Created admin user: admin/admin123")

        # Create employee user
        if not User.objects.filter(username="employee").exists():
            _employee = User.objects.create_user(
                username="employee",
                email="employee@solidus.local",
                password="employee123",
                first_name="John",
                last_name="Employee",
                is_staff=True,
            )
            self.stdout.write("Created employee user: employee/employee123")

        # Create customer users
        companies = [
            "AutoZone",
            "O'Reilly Auto Parts",
            "Advance Auto Parts",
            "NAPA Auto Parts",
            "Pep Boys",
            "CarQuest",
            "Parts Authority",
            "Summit Racing",
            "JEGS",
            "RockAuto",
        ]

        for i in range(count):
            username = f"customer{i + 1}"
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=f"{username}@example.com",
                    password="customer123",
                    first_name=f"Customer{i + 1}",
                    last_name="User",
                )

                # Create customer profile
                company = random.choice(companies)
                CustomerProfile.objects.create(
                    user=user,
                    company=company,
                    phone=f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                    address=f"{random.randint(100, 9999)} Main St",
                    city=random.choice(
                        ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]
                    ),
                    state=random.choice(["NY", "CA", "IL", "TX", "AZ"]),
                    zip_code=f"{random.randint(10000, 99999)}",
                    account_number=f"ACCT{i + 1:04d}",
                    credit_limit=Decimal(random.randint(5000, 50000)),
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {count} customer users (password: customer123)"
            )
        )

    def create_brands_and_categories(self):
        """Create brands and categories"""
        from src.products.models import Brand, Category

        # Create brands
        brand_names = [
            "ACDelco",
            "Bosch",
            "Denso",
            "NGK",
            "Champion",
            "Motorcraft",
            "Gates",
            "Dayco",
            "Beck/Arnley",
            "Standard Motor Products",
            "Delphi",
            "Continental",
            "Mahle",
            "Febi",
            "Lemforder",
        ]

        for name in brand_names:
            brand, created = Brand.objects.get_or_create(
                name=name,
                defaults={
                    "description": f"{name} automotive parts and components",
                    "website": f'https://www.{name.lower().replace("/", "").replace(" ", "")}.com',
                    "is_active": True,
                },
            )

        # Create categories
        categories_data = [
            ("Engine Parts", "Engine components and related parts"),
            ("Brake System", "Brake pads, rotors, and brake components"),
            ("Suspension", "Suspension components and steering parts"),
            ("Electrical", "Electrical components and wiring"),
            ("Exhaust System", "Exhaust pipes, mufflers, and catalytic converters"),
            ("Cooling System", "Radiators, thermostats, and cooling components"),
            ("Fuel System", "Fuel pumps, filters, and injection components"),
            ("Transmission", "Transmission parts and components"),
            ("Body Parts", "Exterior and interior body components"),
            ("Filters", "Air, oil, and fuel filters"),
        ]

        for name, description in categories_data:
            category, created = Category.objects.get_or_create(
                name=name, defaults={"description": description, "is_active": True}
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(brand_names)} brands and {len(categories_data)} categories"
            )
        )

    def create_products(self, count):
        """Create products with realistic data"""
        from src.products.models import Brand, Category, Product

        brands = list(Brand.objects.all())
        categories = list(Category.objects.all())

        product_templates = [
            ("Air Filter", "High-quality air filter for optimal engine performance"),
            ("Brake Pad Set", "Premium brake pads for superior stopping power"),
            ("Spark Plug", "Long-lasting spark plug for reliable ignition"),
            ("Oil Filter", "Efficient oil filter for engine protection"),
            ("Fuel Pump", "Reliable fuel pump for consistent fuel delivery"),
            ("Thermostat", "Precision thermostat for engine temperature control"),
            ("Water Pump", "Durable water pump for cooling system"),
            ("Alternator", "High-output alternator for electrical system"),
            ("Starter Motor", "Reliable starter motor for dependable starting"),
            ("Radiator", "Efficient radiator for engine cooling"),
        ]

        for i in range(count):
            template = random.choice(product_templates)
            brand = random.choice(brands)
            category = random.choice(categories)

            # Generate realistic part numbers and prices
            part_number = f"{brand.name[:3].upper()}{random.randint(1000, 9999)}"
            base_price = random.uniform(15.99, 299.99)
            retail_price = round(base_price, 2)
            msrp = round(retail_price * random.uniform(1.2, 1.8), 2)
            cost = round(retail_price * random.uniform(0.4, 0.7), 2)

            product = Product.objects.create(
                name=f"{brand.name} {template[0]}",
                description=template[1],
                sku=part_number,
                upc=f"{random.randint(100000000000, 999999999999)}",
                brand=brand,
                retail_price=Decimal(str(retail_price)),
                msrp=Decimal(str(msrp)),
                cost=Decimal(str(cost)),
                weight=Decimal(str(random.uniform(0.5, 25.0))),
                dimensions=f'{random.randint(5, 20)}" x {random.randint(3, 15)}" x {random.randint(2, 10)}"',
                stock_quantity=random.randint(0, 100),
                low_stock_threshold=random.randint(5, 20),
                location=f"A{random.randint(1, 20)}-{random.randint(1, 10)}",
                is_active=random.choice([True, True, True, False]),  # 75% active
                is_featured=random.choice([True, False, False, False]),  # 25% featured
            )

            # Add to category
            product.categories.add(category)

            # Add some tags
            possible_tags = [
                "OEM",
                "Performance",
                "Heavy Duty",
                "Economy",
                "Premium",
                "New",
            ]
            for tag_name in random.sample(possible_tags, random.randint(1, 3)):
                from taggit.models import Tag

                tag, _ = Tag.objects.get_or_create(name=tag_name)
                product.tags.add(tag)

        self.stdout.write(self.style.SUCCESS(f"Created {count} products"))

    def create_assets(self, count):
        """Create sample assets"""
        from src.assets.models import Asset, AssetCategory

        # Create asset categories
        asset_categories = [
            ("Product Images", "Product photography and images"),
            ("Technical Documents", "Manuals, specifications, and technical docs"),
            ("Marketing Materials", "Brochures, catalogs, and marketing content"),
            ("Installation Guides", "Step-by-step installation instructions"),
        ]

        for name, description in asset_categories:
            AssetCategory.objects.get_or_create(
                name=name, defaults={"description": description}
            )

        categories = list(AssetCategory.objects.all())
        users = list(User.objects.filter(is_staff=True))

        # Sample file types and their data
        file_types = [
            ("image/jpeg", "jpg", "product_image_{}.jpg"),
            ("image/png", "png", "product_diagram_{}.png"),
            ("application/pdf", "pdf", "manual_{}.pdf"),
            ("application/msword", "doc", "spec_sheet_{}.doc"),
        ]

        for i in range(count):
            file_type, ext, filename_template = random.choice(file_types)
            category = random.choice(categories)
            user = random.choice(users)

            asset = Asset.objects.create(
                title=f"Sample Asset {i + 1}",
                description=f"Sample {category.name.lower()} asset for testing purposes",
                file_type=file_type,
                file_size=random.randint(50000, 5000000),  # 50KB to 5MB
                original_filename=filename_template.format(i + 1),
                category=category,
                uploaded_by=user,
                is_public=random.choice([True, False]),
                employee_only=random.choice([True, False]),
                created_at=timezone.now() - timedelta(days=random.randint(1, 365)),
            )

            # Add some tags
            possible_tags = ["Product", "Manual", "Guide", "Specification", "Image"]
            for tag_name in random.sample(possible_tags, random.randint(1, 2)):
                from taggit.models import Tag

                tag, _ = Tag.objects.get_or_create(name=tag_name)
                asset.tags.add(tag)

        self.stdout.write(self.style.SUCCESS(f"Created {count} sample assets"))

    def create_feeds(self):
        """Create sample data feeds"""
        from src.feeds.models import DataFeed, FeedGeneration

        customers = User.objects.filter(customerprofile__isnull=False)[:5]

        for customer in customers:
            # Create 1-3 feeds per customer
            for i in range(random.randint(1, 3)):
                feed = DataFeed.objects.create(
                    name=f"{customer.customerprofile.company} Product Feed {i + 1}",
                    description=f"Product feed for {customer.customerprofile.company}",
                    customer=customer,
                    format=random.choice(["json", "xml", "csv"]),
                    frequency=random.choice(["daily", "weekly", "monthly"]),
                    fields=["sku", "name", "brand", "price", "stock"],
                    filters={"is_active": True},
                    delivery_config={
                        "method": "download",
                        "filename": f"products_{customer.username}.{{}}",
                    },
                    is_active=True,
                    created_by=User.objects.filter(is_staff=True).first(),
                )

                # Create some feed generations
                for j in range(random.randint(1, 5)):
                    generation_date = timezone.now() - timedelta(
                        days=random.randint(1, 30)
                    )
                    FeedGeneration.objects.create(
                        feed=feed,
                        status=random.choice(["completed", "completed", "failed"]),
                        record_count=random.randint(50, 500),
                        file_size=random.randint(10000, 500000),
                        started_at=generation_date,
                        completed_at=generation_date
                        + timedelta(minutes=random.randint(1, 10)),
                        created_by=feed.created_by,
                    )

        self.stdout.write(
            self.style.SUCCESS(f"Created sample feeds for {len(customers)} customers")
        )

    def create_audit_logs(self):
        """Create sample audit logs"""
        from src.audit.models import AuditLog

        users = list(User.objects.all())
        actions = ["CREATE", "UPDATE", "DELETE", "VIEW"]
        models = ["Product", "Asset", "User", "DataFeed"]

        for i in range(100):
            AuditLog.objects.create(
                user=random.choice(users),
                action=random.choice(actions),
                model_name=random.choice(models),
                object_id=random.randint(1, 100),
                object_repr=f"Sample Object {i + 1}",
                changes={"field": "old_value", "new_field": "new_value"},
                ip_address=f"192.168.1.{random.randint(1, 254)}",
                user_agent="Mozilla/5.0 (Sample Browser)",
                timestamp=timezone.now() - timedelta(days=random.randint(1, 90)),
            )

        self.stdout.write(self.style.SUCCESS("Created 100 sample audit log entries"))
