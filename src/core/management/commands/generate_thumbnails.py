# src/core/management/commands/generate_thumbnails.py
import os

from PIL import Image

from django.core.management.base import BaseCommand

from assets.models import Asset


class Command(BaseCommand):
    help = "Generate thumbnails for all image assets"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenerate existing thumbnails",
        )
        parser.add_argument(
            "--size",
            type=int,
            default=300,
            help="Thumbnail size (default: 300px)",
        )

    def handle(self, *args, **options):
        force = options["force"]
        size = options["size"]

        image_assets = Asset.objects.filter(asset_type="image", is_active=True)

        total = image_assets.count()
        processed = 0
        errors = 0

        self.stdout.write(f"Processing {total} image assets...")

        for asset in image_assets:
            try:
                if not force and asset.thumbnail_path:
                    self.stdout.write(f"Skipping {asset.title} (thumbnail exists)")
                    continue

                if asset.file and os.path.exists(asset.file.path):
                    # Generate thumbnail
                    with Image.open(asset.file.path) as img:
                        img.thumbnail((size, size), Image.Resampling.LANCZOS)

                        # Save thumbnail
                        thumb_dir = os.path.join(
                            os.path.dirname(asset.file.path), "thumbnails"
                        )
                        os.makedirs(thumb_dir, exist_ok=True)

                        thumb_path = os.path.join(
                            thumb_dir, f"thumb_{os.path.basename(asset.file.path)}"
                        )

                        img.save(thumb_path)

                        # Update asset
                        asset.thumbnail_path = os.path.relpath(
                            thumb_path, asset.file.storage.location
                        )
                        asset.save()

                        processed += 1
                        self.stdout.write(f"Generated thumbnail for {asset.title}")

            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f"Error processing {asset.title}: {str(e)}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Thumbnail generation complete! "
                f"Processed: {processed}, Errors: {errors}"
            )
        )
