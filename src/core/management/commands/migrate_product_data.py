from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.contrib.auth import get_user_model

from libs.conn_filemaker import Filemaker
from utils.jvm import start_jvm
from products.models import (
    Product
)

User = get_user_model()

start_jvm()

# Load the filemaker dsn
with open("libs/filemaker.dsn", "r") as fp:
    dsn_filemaker = fp.read()


class Command(BaseCommand):
    help = "Migrate product data"

    def handle(self, *args, **options):
        self.stdout.write("Starting product data migration...")

        admin_user = self.get_or_create_admin_user()
        if not admin_user:
            self.stdout.write(self.style.ERROR("No admin user available. Aborting."))
            return

        self.migrate_categories(admin_user)
        self.migrate_part_numbers(admin_user)

        self.stdout.write(self.style.SUCCESS("Product data migration completed."))

    def get_or_create_admin_user(self):
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write("No superuser found. Creating default 'migration_admin'.")
            admin_user = User.objects.create_user(
                username='migration_admin',
                email='admin@example.com',
                is_staff=True,
                is_superuser=True
            )
        return admin_user

    def migrate_categories(self, admin_user):
        self.stdout.write("Migrating categories...")

        with Filemaker(dsn_filemaker) as fm:
            query = "select AS400_Category as category, AS400_CategoryDescription as description from Master where ToggleActive = 'Yes'"
            fm.cursor.execute(query)
            categories = fm.cursor.fetchall()

        for category in categories:
            Category.objects.get_or_create(
                category=category[0],
                defaults={
                    'description': category[1],
                    'created_by': admin_user
                }
            )

    def migrate_part_numbers(self, admin_user):
        self.stdout.write("Migrating products...")

        with Filemaker(dsn_filemaker) as fm:
            query = "select AS400_NumberStripped AS number from Master where ToggleActive = 'Yes'"
            fm.cursor.execute(query)
            products = fm.cursor.fetchall()


        for product in products:
            Product.objects.get_or_create(
                number=product,
                defaults={
                    'created_by': admin_user
                }
            )
