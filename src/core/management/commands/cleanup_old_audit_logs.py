# src/core/management/commands/cleanup_old_audit_logs.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from audit.models import AuditLog
from datetime import timedelta


class Command(BaseCommand):
    help = 'Clean up old audit logs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Delete logs older than this many days (default: 365)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']

        cutoff_date = timezone.now() - timedelta(days=days)

        old_logs = AuditLog.objects.filter(timestamp__lt=cutoff_date)
        count = old_logs.count()

        if dry_run:
            self.stdout.write(
                f'Would delete {count} audit logs older than {days} days '
                f'(before {cutoff_date.date()})'
            )
        else:
            if count > 0:
                old_logs.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Deleted {count} audit logs older than {days} days'
                    )
                )
            else:
                self.stdout.write('No old audit logs to delete')