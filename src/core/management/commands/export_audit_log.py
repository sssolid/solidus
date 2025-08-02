# src/core/management/commands/export_audit_log.py
from django.core.management.base import BaseCommand
from audit.models import AuditLog
import csv
import os
from datetime import datetime


class Command(BaseCommand):
    help = 'Export audit log to CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (default: audit_log_YYYYMMDD.csv)',
        )
        parser.add_argument(
            '--days',
            type=int,
            help='Export logs from last N days only',
        )

    def handle(self, *args, **options):
        output_file = options['output']
        days = options['days']

        if not output_file:
            output_file = f'audit_log_{datetime.now().strftime("%Y%m%d")}.csv'

        # Get audit logs
        queryset = AuditLog.objects.select_related('user').order_by('-timestamp')

        if days:
            from django.utils import timezone
            from datetime import timedelta
            cutoff_date = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(timestamp__gte=cutoff_date)

        total = queryset.count()
        self.stdout.write(f'Exporting {total} audit log entries...')

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Write header
            writer.writerow([
                'Timestamp',
                'User',
                'Action',
                'Model',
                'Object ID',
                'Description',
                'IP Address',
                'User Agent'
            ])

            # Write data
            for log in queryset.iterator(chunk_size=1000):
                writer.writerow([
                    log.timestamp,
                    log.user.username if log.user else 'System',
                    log.action,
                    log.model_name,
                    log.object_id,
                    log.description,
                    log.ip_address,
                    log.user_agent
                ])

        self.stdout.write(
            self.style.SUCCESS(f'Audit log exported to {output_file}')
        )