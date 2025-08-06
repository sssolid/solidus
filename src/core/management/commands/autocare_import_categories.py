from django.conf import settings
from django.core.management.base import BaseCommand
from products.models import Category
import mysql.connector
from collections import defaultdict
from django.utils.text import slugify

def generate_slug(name, code=None):
    base_slug = slugify(name)
    if not base_slug and code:
        base_slug = f"category-{code}"
    return base_slug

class Command(BaseCommand):
    help = "Import AutoCare categories from MySQL into Django PostgreSQL"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually apply changes to the Django database"
        )

    def handle_categories(self, cursor, apply=False):
        cursor.execute("SELECT CategoryID, CategoryName FROM Categories")
        mysql_categories = cursor.fetchall()

        self.stdout.write(f"📦 Fetched {len(mysql_categories)} categories from MySQL.")

        existing_categories = {
            cat.id: cat for cat in Category.objects.all()
        }

        new = []
        changed = []
        unchanged = []

        for row in mysql_categories:
            id = row["CategoryID"]
            raw_name = row["CategoryName"]
            name = raw_name.strip()

            if id not in existing_categories:
                new.append((id, name))
            else:
                existing = existing_categories[id]
                if existing.name.strip() != name:
                    changed.append((id, existing.name, name))
                else:
                    unchanged.append(id)

        self.stdout.write(f"\n📝 Summary:")
        self.stdout.write(f"  ➕ New categories: {len(new)}")
        self.stdout.write(f"  ✏️  Updated categories: {len(changed)}")
        self.stdout.write(f"  ✔️  Unchanged categories: {len(unchanged)}")

        if not apply:
            self.stdout.write("\nℹ️ Run again with `--apply` to perform the import.\n")
            return

        # Apply changes
        for i, (id, name) in enumerate(new, start=0):
            slug = generate_slug(name, code=id)
            Category.objects.create(
                name=name,
                slug=slug,
                parent=None,
                description="",
                image=f"categories/{slug}.png",
                sort_order=i + 1,
                is_active=True,
                # SEO fields
                meta_title=name,
                meta_description=""
            )
        for id, old_name, new_name in changed:
            category = existing_categories[id]
            category.name = new_name
            category.save(update_fields=["name"])

        self.stdout.write(self.style.SUCCESS("✅ Categories import complete."))

    def handle_subcategories(self, cursor, apply=False):
        cursor.execute("SELECT SubCategoryID, SubCategoryName FROM Subcategories")
        mysql_subcategories = cursor.fetchall()

        self.stdout.write(f"📦 Fetched {len(mysql_subcategories)} subcategories from MySQL.")

        existing_subcategories = {
            cat.id: cat for cat in Category.objects.all()
        }

        new = []
        changed = []
        unchanged = []

        for row in mysql_subcategories:
            id = row["SubCategoryID"]
            raw_name = row["SubCategoryName"]
            name = raw_name.strip()

            if id not in existing_subcategories:
                new.append((id, name))
            else:
                existing = existing_subcategories[id]
                if existing.name.strip() != name:
                    changed.append((id, existing.name, name))
                else:
                    unchanged.append(id)

        self.stdout.write(f"\n📝 Summary:")
        self.stdout.write(f"  ➕ New subcategories: {len(new)}")
        self.stdout.write(f"  ✏️  Updated subcategories: {len(changed)}")
        self.stdout.write(f"  ✔️  Unchanged subcategories: {len(unchanged)}")

        if not apply:
            self.stdout.write("\nℹ️ Run again with `--apply` to perform the import.\n")
            return

        # Apply changes
        for i, (id, name) in enumerate(new, start=0):
            slug = generate_slug(name, code=id)
            Category.objects.create(
                name=name,
                slug=slug,
                parent=None,
                description="",
                image=f"categories/{slug}.png",
                sort_order=i + 1,
                is_active=True,
                # SEO fields
                meta_title=name,
                meta_description=""
            )
        for id, old_name, new_name in changed:
            subcategory = existing_subcategories[id]
            subcategory.name = new_name
            subcategory.save(update_fields=["name"])

        self.stdout.write(self.style.SUCCESS("✅ Subcategories import complete."))

    def handle_category_hierarchy(self, cursor, apply=False):
        cursor.execute("SELECT DISTINCT CategoryID, SubCategoryID FROM CodeMaster")
        relations = cursor.fetchall()

        # Build mapping of SubCategoryID → set of CategoryIDs
        sub_to_parents = defaultdict(set)
        for row in relations:
            sub_to_parents[row['SubCategoryID']].add(row['CategoryID'])

        ambiguous = []
        updated = []

        for sub_id, parent_ids in sub_to_parents.items():
            if len(parent_ids) > 1:
                ambiguous.append((sub_id, list(parent_ids)))
                continue

            parent_id = list(parent_ids)[0]
            try:
                subcategory = Category.objects.get(id=sub_id)
                parent = Category.objects.get(id=parent_id)
            except Category.DoesNotExist:
                continue  # Can log if needed

            if subcategory.parent_id != parent.id:
                updated.append((subcategory, parent))
                if apply:
                    subcategory.parent = parent
                    subcategory.save(update_fields=['parent'])

        self.stdout.write(f"🔗 SubCategories with assigned parent: {len(updated)}")
        self.stdout.write(f"⚠️ Ambiguous subcategory relationships: {len(ambiguous)}")

        if ambiguous:
            for sub_id, parents in ambiguous:
                self.stdout.write(f"  - SubCategory {sub_id} has multiple parents: {parents}")

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        self.stdout.write("🔌 Connecting to MySQL...")
        mysql_conn = mysql.connector.connect(
            host="localhost",         # or '127.0.0.1' if local
            port=3306,
            user=settings.AUTOCARE_DB_USER,
            password=settings.AUTOCARE_DB_PASSWORD,
            database="pcadb"
        )

        cursor = mysql_conn.cursor(dictionary=True)

        self.handle_categories(cursor, apply_changes)
        self.handle_subcategories(cursor, apply_changes)
        self.handle_category_hierarchy(cursor, apply_changes)

        mysql_conn.close()

        self.stdout.write(self.style.SUCCESS("✅ Import complete."))
