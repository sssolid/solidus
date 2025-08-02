# src/core/management/commands/create_dev_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from products.models import Product, Brand, Category
from assets.models import Asset, AssetCategory
from feeds.models import DataFeed
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Create development data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing data before creating new data',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Deleting existing data...')
            Product.objects.all().delete()
            Brand.objects.all().delete()
            Category.objects.all().delete()
            Asset.objects.all().delete()
            AssetCategory.objects.all().delete()
            DataFeed.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        self.stdout.write('Creating development data...')

        # Create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@solidus.local',
                'first_name': 'Admin',
                'last_name': 'User',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(f'Created admin user: admin/admin123')

        # Create employee users
        employee_user, created = User.objects.get_or_create(
            username='employee',
            defaults={
                'email': 'employee@solidus.local',
                'first_name': 'Employee',
                'last_name': 'User',
                'role': 'employee',
                'is_staff': True,
            }
        )
        if created:
            employee_user.set_password('employee123')
            employee_user.save()
            self.stdout.write(f'Created employee user: employee/employee123')

        # Create customer users
        customers = [
            ('customer1', 'Customer One', 'Acme Auto Parts', 'CUST-001'),
            ('customer2', 'Customer Two', 'Best Auto Supply', 'CUST-002'),
            ('customer3', 'Customer Three', 'Car Parts Plus', 'CUST-003'),
        ]

        for username, full_name, company, customer_num in customers:
            first_name, last_name = full_name.split(' ', 1)
            customer_user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': 'customer',
                    'company_name': company,
                    'customer_number': customer_num,
                }
            )
            if created:
                customer_user.set_password('customer123')
                customer_user.save()
                self.stdout.write(f'Created customer user: {username}/customer123')

        # Create brands
        brands_data = [
            ('Ford', 'Ford Motor Company'),
            ('Chevrolet', 'Chevrolet Division of General Motors'),
            ('Toyota', 'Toyota Motor Corporation'),
            ('Honda', 'Honda Motor Company'),
            ('BMW', 'Bayerische Motoren Werke AG'),
        ]

        for name, description in brands_data:
            brand, created = Brand.objects.get_or_create(
                name=name,
                defaults={
                    'slug': name.lower(),
                    'description': description,
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f'Created brand: {name}')

        # Create categories
        categories_data = [
            ('Engine', 'Engine components and parts'),
            ('Transmission', 'Transmission and drivetrain parts'),
            ('Brakes', 'Brake system components'),
            ('Suspension', 'Suspension and steering parts'),
            ('Electrical', 'Electrical components and accessories'),
            ('Exhaust', 'Exhaust system components'),
            ('Body', 'Body panels and trim'),
            ('Interior', 'Interior components and accessories'),
        ]

        for name, description in categories_data:
            category, created = Category.objects.get_or_create(
                name=name,
                defaults={
                    'slug': name.lower(),
                    'description': description,
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f'Created category: {name}')

        # Create asset categories
        asset_categories_data = [
            ('product-images', 'Product Images', 'fa-image'),
            ('manuals', 'Product Manuals', 'fa-file-pdf'),
            ('marketing', 'Marketing Materials', 'fa-bullhorn'),
            ('technical', 'Technical Documents', 'fa-cogs'),
        ]

        for slug, name, icon in asset_categories_data:
            asset_category, created = AssetCategory.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'icon': icon,
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f'Created asset category: {name}')

        # Create sample products
        brands = Brand.objects.all()
        categories = Category.objects.all()

        products_data = [
            ('FRD-ENG-001', 'Ford 5.0L V8 Coyote Engine', 'High-performance V8 engine'),
            ('CHV-TRN-002', 'Chevrolet 4L60E Transmission', 'Automatic transmission'),
            ('TOY-BRK-003', 'Toyota Brake Pad Set', 'Front brake pads for Camry'),
            ('HND-SUS-004', 'Honda Strut Assembly', 'Front strut for Civic'),
            ('BMW-ELC-005', 'BMW Alternator', 'High-output alternator'),
            ('FRD-EXH-006', 'Ford Exhaust Manifold', 'Performance exhaust manifold'),
            ('CHV-BOD-007', 'Chevrolet Hood', 'Steel hood panel'),
            ('TOY-INT-008', 'Toyota Dashboard', 'Interior dashboard assembly'),
        ]

        for sku, name, description in products_data:
            brand = random.choice(brands)
            category = random.choice(categories)

            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': name,
                    'description': description,
                    'brand': brand,
                    'weight': round(random.uniform(1.0, 50.0), 2),
                    'msrp': round(random.uniform(50.0, 2000.0), 2),
                    'map_price': round(random.uniform(40.0, 1800.0), 2),
                    'is_active': True,
                    'is_featured': random.choice([True, False]),
                    'created_by': employee_user,
                }
            )

            if created:
                product.categories.add(category)
                product.tags.add('sample', 'development', brand.name.lower())
                self.stdout.write(f'Created product: {sku} - {name}')

        # Create sample data feeds
        customer_users = User.objects.filter(role='customer')

        for customer in customer_users:
            feed, created = DataFeed.objects.get_or_create(
                name=f'{customer.company_name} Product Feed',
                defaults={
                    'description': f'Product catalog feed for {customer.company_name}',
                    'customer': customer,
                    'feed_type': 'product_catalog',
                    'format': 'json',
                    'is_active': True,
                    'created_by': employee_user,
                }
            )
            if created:
                self.stdout.write(f'Created feed: {feed.name}')

        self.stdout.write(
            self.style.SUCCESS('Successfully created development data!')
        )
        self.stdout.write('\nLogin credentials:')
        self.stdout.write('Admin: admin/admin123')
        self.stdout.write('Employee: employee/employee123')
        self.stdout.write('Customer: customer1/customer123')