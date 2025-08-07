# src/autocare/management/commands/vcdb_stats.py
"""
Management command to display automotive database statistics.
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from autocare_vcdb.models import (
    Vehicle, BaseVehicle, Make, Model, Year, EngineConfig,
    Transmission, Region
)


class Command(BaseCommand):
    help = 'Display automotive database statistics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed statistics'
        )

    def handle(self, *args, **options):
        detailed = options.get('detailed', False)

        self.stdout.write(self.style.SUCCESS("=== Automotive Database Statistics ===\n"))

        # Basic counts
        self.stdout.write("Basic Counts:")
        self.stdout.write(f"  Vehicles: {Vehicle.objects.count():,}")
        self.stdout.write(f"  Base Vehicles: {BaseVehicle.objects.count():,}")
        self.stdout.write(f"  Makes: {Make.objects.count():,}")
        self.stdout.write(f"  Models: {Model.objects.count():,}")
        self.stdout.write(f"  Years: {Year.objects.count():,}")
        self.stdout.write(f"  Engine Configs: {EngineConfig.objects.count():,}")
        self.stdout.write(f"  Transmissions: {Transmission.objects.count():,}")
        self.stdout.write("")

        if detailed:
            # Top makes by vehicle count
            self.stdout.write("Top 10 Makes by Vehicle Count:")
            top_makes = Make.objects.annotate(
                vehicle_count=Count('base_vehicles__vehicles')
            ).filter(vehicle_count__gt=0).order_by('-vehicle_count')[:10]

            for make in top_makes:
                self.stdout.write(f"  {make.make_name}: {make.vehicle_count:,}")
            self.stdout.write("")

            # Vehicles by year range
            self.stdout.write("Vehicles by Year (last 10 years):")
            year_stats = Year.objects.annotate(
                vehicle_count=Count('base_vehicles__vehicles')
            ).filter(vehicle_count__gt=0).order_by('-year_id')[:10]

            for year in year_stats:
                self.stdout.write(f"  {year.year_id}: {year.vehicle_count:,}")
            self.stdout.write("")

            # Regional distribution
            self.stdout.write("Top 10 Regions by Vehicle Count:")
            region_stats = Region.objects.annotate(
                vehicle_count=Count('vehicles')
            ).filter(vehicle_count__gt=0).order_by('-vehicle_count')[:10]

            for region in region_stats:
                name = region.region_name or f"Region {region.region_id}"
                self.stdout.write(f"  {name}: {region.vehicle_count:,}")
            self.stdout.write("")

        self.stdout.write(self.style.SUCCESS("=== End Statistics ==="))