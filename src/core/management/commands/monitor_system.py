# src/core/management/commands/monitor_system.py
import time

import psutil

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import connections

from core.models import TaskQueue


class Command(BaseCommand):
    help = "Monitor system health and performance"

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=60,
            help="Monitoring interval in seconds (default: 60)",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run once and exit",
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        run_once = options["once"]

        self.stdout.write("Starting system monitoring...")

        while True:
            self.check_system_health()

            if run_once:
                break

            time.sleep(interval)

    def check_system_health(self):
        """Check various system health metrics"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.stdout.write(f"\n=== System Health Check - {timestamp} ===")

        # Database connectivity
        try:
            db_conn = connections["default"]
            db_conn.cursor()
            self.stdout.write("✓ Database: Connected")
        except Exception as e:
            self.stdout.write(f"✗ Database: Error - {str(e)}")

        # Cache connectivity
        try:
            cache.set("health_check", "ok", 10)
            cache.get("health_check")
            self.stdout.write("✓ Cache: Connected")
        except Exception as e:
            self.stdout.write(f"✗ Cache: Error - {str(e)}")

        # Task queue status
        try:
            pending_tasks = TaskQueue.objects.filter(status="pending").count()
            failed_tasks = TaskQueue.objects.filter(status="failed").count()
            self.stdout.write(
                f"✓ Task Queue: {pending_tasks} pending, {failed_tasks} failed"
            )
        except Exception as e:
            self.stdout.write(f"✗ Task Queue: Error - {str(e)}")

        # System resources
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            self.stdout.write(f"✓ CPU Usage: {cpu_percent}%")
            self.stdout.write(f"✓ Memory Usage: {memory.percent}%")
            self.stdout.write(f"✓ Disk Usage: {disk.percent}%")

            # Warn on high usage
            if cpu_percent > 80:
                self.stdout.write(self.style.WARNING("⚠ High CPU usage detected"))
            if memory.percent > 80:
                self.stdout.write(self.style.WARNING("⚠ High memory usage detected"))
            if disk.percent > 80:
                self.stdout.write(self.style.WARNING("⚠ High disk usage detected"))

        except Exception as e:
            self.stdout.write(f"✗ System Resources: Error - {str(e)}")
