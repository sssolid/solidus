# src/autocare/management/commands/export_vcdb_data.py
"""
Management command to export automotive data to various formats.
"""

import csv
import json
import time

from django.core.management import CommandError
from django.core.management.base import BaseCommand
from django.core.serializers import serialize
from autocare_vcdb.models import Vehicle


class Command(BaseCommand):
    help = 'Export automotive data to CSV, JSON, or Excel files'

    def add_arguments(self, parser):
        parser.add_argument(
            'output_path',
            type=str,
            help='Path for the output file'
        )
        parser.add_argument(
            '--format',
            choices=['csv', 'json', 'excel'],
            default='csv',
            help='Format of the output file (default: csv)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit the number of records to export'
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Filter by specific year'
        )
        parser.add_argument(
            '--make',
            type=str,
            help='Filter by specific make name'
        )

    def handle(self, *args, **options):
        start_time = time.time()

        # Build queryset with filters
        queryset = Vehicle.objects.select_related(
            'base_vehicle__year', 'base_vehicle__make', 'base_vehicle__model',
            'submodel', 'region', 'publication_stage'
        )

        if options.get('year'):
            queryset = queryset.filter(base_vehicle__year__year_id=options['year'])

        if options.get('make'):
            queryset = queryset.filter(
                base_vehicle__make__make_name__icontains=options['make']
            )

        if options.get('limit'):
            queryset = queryset[:options['limit']]

        # Export based on format
        output_path = options['output_path']
        file_format = options['format']

        if file_format == 'csv':
            self.export_csv(queryset, output_path)
        elif file_format == 'json':
            self.export_json(queryset, output_path)
        elif file_format == 'excel':
            self.export_excel(queryset, output_path)

        end_time = time.time()
        processing_time = end_time - start_time

        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {queryset.count()} records to {output_path} "
                f"in {processing_time:.2f} seconds"
            )
        )

    def export_csv(self, queryset, output_path):
        """Export to CSV format."""
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Header
            writer.writerow([
                'vehicle_id', 'year', 'make_name', 'model_name', 'submodel_name',
                'region_name', 'publication_stage', 'publication_date'
            ])

            # Data
            for vehicle in queryset.iterator():
                writer.writerow([
                    vehicle.vehicle_id,
                    vehicle.base_vehicle.year.year_id,
                    vehicle.base_vehicle.make.make_name,
                    vehicle.base_vehicle.model.model_name or '',
                    vehicle.submodel.sub_model_name,
                    vehicle.region.region_name if vehicle.region else '',
                    vehicle.publication_stage.publication_stage_name,
                    vehicle.publication_stage_date.strftime('%Y-%m-%d %H:%M:%S')
                ])

    def export_json(self, queryset, output_path):
        """Export to JSON format."""
        data = []
        for vehicle in queryset.iterator():
            data.append({
                'vehicle_id': vehicle.vehicle_id,
                'year': vehicle.base_vehicle.year.year_id,
                'make_name': vehicle.base_vehicle.make.make_name,
                'model_name': vehicle.base_vehicle.model.model_name or '',
                'submodel_name': vehicle.submodel.sub_model_name,
                'region_name': vehicle.region.region_name if vehicle.region else '',
                'publication_stage': vehicle.publication_stage.publication_stage_name,
                'publication_date': vehicle.publication_stage_date.isoformat()
            })

        with open(output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)

    def export_excel(self, queryset, output_path):
        """Export to Excel format."""
        try:
            import pandas as pd
        except ImportError:
            raise CommandError(
                "pandas is required for Excel export. Install with: pip install pandas openpyxl"
            )

        data = []
        for vehicle in queryset.iterator():
            data.append({
                'vehicle_id': vehicle.vehicle_id,
                'year': vehicle.base_vehicle.year.year_id,
                'make_name': vehicle.base_vehicle.make.make_name,
                'model_name': vehicle.base_vehicle.model.model_name or '',
                'submodel_name': vehicle.submodel.sub_model_name,
                'region_name': vehicle.region.region_name if vehicle.region else '',
                'publication_stage': vehicle.publication_stage.publication_stage_name,
                'publication_date': vehicle.publication_stage_date
            })

        df = pd.DataFrame(data)
        df.to_excel(output_path, index=False, engine='openpyxl')