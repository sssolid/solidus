# src/core/management/commands/reset_migrations.py

import os
import shutil
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings


class Command(BaseCommand):
    help = 'Reset migrations and recreate them in the correct order'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reset without confirmation',
        )

    def handle(self, *args, **options):
        if not options['force']:
            confirm = input(
                'This will delete all migration files and recreate them. '
                'Make sure you have a database backup. Continue? (y/N): '
            )
            if confirm.lower() != 'y':
                self.stdout.write('Aborted.')
                return

        self.stdout.write(self.style.WARNING('Resetting migrations...'))


        # Remove existing migration files
        self.stdout.write('Removing migration files...')

        # Get the base directory (project root contains manage.py, apps are in src/)
        project_root = settings.BASE_DIR.parent if settings.BASE_DIR.name == 'src' else settings.BASE_DIR
        src_dir = project_root / 'src'

        for app in settings.LOCAL_APPS:
            migrations_dir = src_dir / app / 'migrations'
            if migrations_dir.exists():
                # Keep __init__.py but remove everything else
                for file_path in migrations_dir.iterdir():
                    if file_path.name != '__init__.py' and file_path.suffix == '.py':
                        file_path.unlink()
                        self.stdout.write(f'  Removed {file_path}')
                    elif file_path.name.startswith('0') and file_path.suffix == '.py':
                        # Remove numbered migration files
                        file_path.unlink()
                        self.stdout.write(f'  Removed {file_path}')

        # Create new migrations in the correct order
        self.stdout.write('Creating new migrations...')
        for app in settings.LOCAL_APPS:
            self.stdout.write(f'Creating migration for {app}...')
            try:
                call_command('makemigrations', app, verbosity=2)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating migration for {app}: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                'Migration reset complete. Run "python manage.py migrate" to apply.'
            )
        )