# src/assets/management/commands/process_assets.py
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from assets.models import AssetFile
from assets.utils import AssetFileHandler
from core.models import TaskQueue

logger = logging.getLogger("solidus.assets")


class Command(BaseCommand):
    help = "Process pending asset files"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10,
            help="Number of assets to process in one batch",
        )
        parser.add_argument("--task-id", type=str, help="Process a specific task by ID")

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        task_id = options.get("task_id")

        if task_id:
            # Process specific task
            try:
                task = TaskQueue.objects.get(
                    task_id=task_id, task_type="asset_processing"
                )
                self.process_task(task)
            except TaskQueue.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Task {task_id} not found"))
        else:
            # Process batch of pending tasks
            tasks = TaskQueue.objects.filter(
                task_type="asset_processing",
                status="pending",
                scheduled_for__lte=timezone.now(),
            ).order_by("priority", "created_at")[:batch_size]

            if not tasks:
                self.stdout.write("No pending asset processing tasks")
                return

            self.stdout.write(f"Processing {len(tasks)} asset tasks...")

            for task in tasks:
                try:
                    self.process_task(task)
                except Exception as e:
                    logger.error(f"Error processing task {task.task_id}: {str(e)}")
                    task.mark_failed(str(e))

    def process_task(self, task):
        """Process a single asset task"""
        task.mark_processing()

        try:
            asset_file_id = task.task_data.get("asset_file_id")
            if not asset_file_id:
                raise ValueError("No asset_file_id in task data")

            asset_file = AssetFile.objects.select_related("asset").get(id=asset_file_id)

            self.stdout.write(f"Processing asset: {asset_file.asset.title}")

            # Process the asset file
            success = AssetFileHandler.save_processed_versions(
                asset_file, asset_file.file_path
            )

            if success:
                task.mark_completed(
                    {
                        "asset_id": asset_file.asset.id,
                        "processed_path": asset_file.processed_path,
                        "thumbnail_path": asset_file.thumbnail_path,
                    }
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully processed asset: {asset_file.asset.title}"
                    )
                )
            else:
                raise Exception("Asset processing failed")

        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {str(e)}")
            task.mark_failed(str(e))
            self.stdout.write(
                self.style.ERROR(f"Failed to process task {task.task_id}: {str(e)}")
            )
