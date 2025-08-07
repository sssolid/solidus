# src/autocare/management/commands/import_vcdb_data.py
"""
Management command to import automotive data from various sources.
"""

import csv
import json
import time
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from autocare_vcdb.models import (
    Make, Model, Year, BaseVehicle, SubModel, Region, Vehicle,
    PublicationStage
)


class Command(BaseCommand):
    help = 'Import automotive data from CSV, JSON, or Excel files'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to the data file to import'
        )
        parser.add_argument(
            '--format',
            choices=['csv', 'json', 'excel'],
            default='csv',
            help='Format of the input file (default: csv)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process in each batch (default: 1000)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without making any changes'
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing records if they exist'
        )
        parser.add_argument(
            '--skip-errors',
            action='store_true',
            help='Continue processing even if some records have errors'
        )

    def handle(self, *args, **options):
        start_time = time.time()
        file_path = options['file_path']
        file_format = options['format']
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        update_existing = options['update_existing']
        skip_errors = options['skip_errors']

        self.stdout.write(f"Starting import from {file_path}")

        try:
            if file_format == 'csv':
                result = self.import_csv(
                    file_path, batch_size, dry_run, update_existing, skip_errors
                )
            elif file_format == 'json':
                result = self.import_json(
                    file_path, batch_size, dry_run, update_existing, skip_errors
                )
            elif file_format == 'excel':
                result = self.import_excel(
                    file_path, batch_size, dry_run, update_existing, skip_errors
                )
            else:
                raise CommandError(f"Unsupported format: {file_format}")

            end_time = time.time()
            processing_time = end_time - start_time

            self.stdout.write(
                self.style.SUCCESS(
                    f"Import completed in {processing_time:.2f} seconds"
                )
            )
            self.stdout.write(f"Total records: {result['total']}")
            self.stdout.write(f"Successful: {result['success']}")
            self.stdout.write(f"Errors: {result['errors']}")

            if result['error_details']:
                self.stdout.write(self.style.WARNING("Error details:"))
                for error in result['error_details'][:10]:  # Show first 10 errors
                    self.stdout.write(f"  {error}")

        except Exception as e:
            raise CommandError(f"Import failed: {str(e)}")

    def import_csv(self, file_path, batch_size, dry_run, update_existing, skip_errors):
        """Import data from CSV file."""
        total_records = 0
        successful_imports = 0
        error_count = 0
        error_details = []

        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            batch = []

            for row in reader:
                total_records += 1
                batch.append(row)

                if len(batch) >= batch_size:
                    result = self.process_batch(
                        batch, dry_run, update_existing, skip_errors
                    )
                    successful_imports += result['success']
                    error_count += result['errors']
                    error_details.extend(result['error_details'])
                    batch = []

            # Process remaining records
            if batch:
                result = self.process_batch(
                    batch, dry_run, update_existing, skip_errors
                )
                successful_imports += result['success']
                error_count += result['errors']
                error_details.extend(result['error_details'])

        return {
            'total': total_records,
            'success': successful_imports,
            'errors': error_count,
            'error_details': error_details
        }

    def import_json(self, file_path, batch_size, dry_run, update_existing, skip_errors):
        """Import data from JSON file."""
        with open(file_path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)

        # Assume JSON contains a list of vehicle records
        if not isinstance(data, list):
            data = [data]

        total_records = len(data)
        successful_imports = 0
        error_count = 0
        error_details = []

        # Process in batches
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            result = self.process_batch(
                batch, dry_run, update_existing, skip_errors
            )
            successful_imports += result['success']
            error_count += result['errors']
            error_details.extend(result['error_details'])

        return {
            'total': total_records,
            'success': successful_imports,
            'errors': error_count,
            'error_details': error_details
        }

    def import_excel(self, file_path, batch_size, dry_run, update_existing, skip_errors):
        """Import data from Excel file."""
        try:
            import pandas as pd
        except ImportError:
            raise CommandError("pandas is required for Excel import. Install with: pip install pandas openpyxl")

        df = pd.read_excel(file_path)
        data = df.to_dict('records')

        total_records = len(data)
        successful_imports = 0
        error_count = 0
        error_details = []

        # Process in batches
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            result = self.process_batch(
                batch, dry_run, update_existing, skip_errors
            )
            successful_imports += result['success']
            error_count += result['errors']
            error_details.extend(result['error_details'])

        return {
            'total': total_records,
            'success': successful_imports,
            'errors': error_count,
            'error_details': error_details
        }

    def process_batch(self, batch, dry_run, update_existing, skip_errors):
        """Process a batch of records."""
        successful_imports = 0
        error_count = 0
        error_details = []

        if not dry_run:
            try:
                with transaction.atomic():
                    for record in batch:
                        try:
                            self.process_record(record, update_existing)
                            successful_imports += 1
                        except Exception as e:
                            error_count += 1
                            error_details.append(f"Record {record}: {str(e)}")
                            if not skip_errors:
                                raise
            except Exception as e:
                if not skip_errors:
                    raise CommandError(f"Batch processing failed: {str(e)}")
        else:
            # Dry run - just validate records
            for record in batch:
                try:
                    self.validate_record(record)
                    successful_imports += 1
                except Exception as e:
                    error_count += 1
                    error_details.append(f"Record {record}: {str(e)}")

        return {
            'success': successful_imports,
            'errors': error_count,
            'error_details': error_details
        }

    def process_record(self, record, update_existing):
        """Process a single vehicle record."""
        # Expected fields: year, make_name, model_name, submodel_name, region_name
        year_id = int(record.get('year', 0))
        make_name = record.get('make_name', '').strip()
        model_name = record.get('model_name', '').strip()
        submodel_name = record.get('submodel_name', '').strip()
        region_name = record.get('region_name', '').strip()

        if not all([year_id, make_name, model_name, submodel_name]):
            raise ValueError("Missing required fields")

        # Get or create related objects
        year, _ = Year.objects.get_or_create(year_id=year_id)
        make, _ = Make.objects.get_or_create(
            make_name=make_name,
            defaults={'make_id': Make.objects.count() + 1}
        )
        model, _ = Model.objects.get_or_create(
            model_name=model_name,
            defaults={
                'model_id': Model.objects.count() + 1,
                'vehicle_type_id': 1  # Default vehicle type
            }
        )
        submodel, _ = SubModel.objects.get_or_create(
            sub_model_name=submodel_name,
            defaults={'sub_model_id': SubModel.objects.count() + 1}
        )

        # Handle region
        region = None
        if region_name:
            region, _ = Region.objects.get_or_create(
                region_name=region_name,
                defaults={'region_id': Region.objects.count() + 1}
            )

        # Get or create base vehicle
        base_vehicle, _ = BaseVehicle.objects.get_or_create(
            year=year,
            make=make,
            model=model,
            defaults={'base_vehicle_id': BaseVehicle.objects.count() + 1}
        )

        # Get default publication stage
        publication_stage, _ = PublicationStage.objects.get_or_create(
            publication_stage_id=1,
            defaults={'publication_stage_name': 'Published'}
        )

        # Create or update vehicle
        vehicle_data = {
            'base_vehicle': base_vehicle,
            'submodel': submodel,
            'region': region or Region.objects.first(),
            'publication_stage': publication_stage,
            'publication_stage_source': 'Import',
            'publication_stage_date': timezone.now(),
        }

        if update_existing:
            vehicle, created = Vehicle.objects.update_or_create(
                vehicle_id=record.get('vehicle_id') if 'vehicle_id' in record else None,
                defaults=vehicle_data
            )
        else:
            vehicle = Vehicle.objects.create(
                vehicle_id=Vehicle.objects.count() + 1,
                **vehicle_data
            )

    def validate_record(self, record):
        """Validate a record without saving it."""
        required_fields = ['year', 'make_name', 'model_name', 'submodel_name']
        for field in required_fields:
            if not record.get(field):
                raise ValueError(f"Missing required field: {field}")

        # Additional validation logic can be added here
        year_id = int(record.get('year', 0))
        if year_id < 1900 or year_id > 2050:
            raise ValueError(f"Invalid year: {year_id}")