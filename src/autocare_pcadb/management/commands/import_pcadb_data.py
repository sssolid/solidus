import re

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
import mysql.connector
from autocare_pcadb.models import *

import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Migrate data from MySQL to PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mysql-host', type=str, default=None, help='MySQL host'
        )
        parser.add_argument(
            '--mysql-db', type=str, default=None, help='MySQL database name'
        )
        parser.add_argument(
            '--mysql-user', type=str, default=None, help='MySQL username'
        )
        parser.add_argument(
            '--mysql-password', type=str, default=None, help='MySQL password'
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting MySQL to PostgreSQL migration...')

        mysql_host = options['mysql_host'] or settings.AUTOCARE_DB_HOST
        mysql_database = options['mysql_db'] or settings.AUTOCARE_DB_NAME_PCADB
        mysql_user = options['mysql_user'] or settings.AUTOCARE_DB_USER
        mysql_password = options['mysql_password'] or settings.AUTOCARE_DB_PASSWORD
        
        try:
            # Connect to MySQL
            mysql_conn = mysql.connector.connect(
                host=mysql_host,
                database=mysql_database,
                user=mysql_user,
                password=mysql_password,
            )

            cursor = mysql_conn.cursor(dictionary=True)

            cursor.execute("SET foreign_key_checks = 0;")
            with transaction.atomic():
                # Get all MySQL table names dynamically
                cursor.execute("SHOW TABLES")
                mysql_tables = cursor.fetchall()
                
                for table in mysql_tables:
                    table_name = table['Tables_in_' + mysql_database]  # Fetch the actual table name
                    
                    # Dynamically get the model corresponding to the table name
                    model = self.get_model_by_table_name(table_name)
                    
                    if model:
                        self._migrate_table(cursor, table_name, model)
                    else:
                        logger.warning(f"Model for table {table_name} not found, skipping.")

                self.stdout.write(self.style.SUCCESS('Migration completed successfully!'))
            cursor.execute("SET foreign_key_checks = 1;")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Migration failed: {str(e)}'))
            raise
        finally:
            cursor.close()
            mysql_conn.close()

    def get_model_by_table_name(self, postgres_table_name):
        model = globals().get(postgres_table_name)
        return model

    def _migrate_table(self, cursor, mysql_table_name, model):
        """Migrates a table from MySQL to PostgreSQL, using db_column for mapping."""

        # Disable foreign key checks in MySQL
        self.stdout.write(f'✓ Disabled foreign key checks for {mysql_table_name}')

        try:
            # Perform the migration
            cursor.execute(f"SELECT * FROM `{mysql_table_name}`")
            rows = cursor.fetchall()

            batch_size = 1000  # You can adjust this based on your use case
            bulk_data = []

            for row in rows:
                data = {}
                for field in model._meta.fields:
                    # Use the db_column attribute to map to PascalCase field names in the database
                    field_name = field.db_column  # Use db_column instead of field.name for actual DB column mapping

                    if field_name in row:
                        value = row[field_name]

                        # Handle foreign keys (if any) by resolving them
                        if field.is_relation:
                            related_model = field.related_model
                            related_field_name = field.remote_field.name

                            if value is not None:
                                try:
                                    related_instance = related_model.objects.get(**{related_field_name: value})
                                    data[field.name] = related_instance
                                except related_model.DoesNotExist:
                                    data[field.name] = None
                            else:
                                data[field.name] = None
                        else:
                            if isinstance(value, str):
                                value = value.strip()
                            data[field.name] = value

                bulk_data.append(model(**data))

                # Insert in batches
                if len(bulk_data) >= batch_size:
                    model.objects.bulk_create(bulk_data, ignore_conflicts=True)
                    bulk_data.clear()  # Clear the batch to start a new one

            # Insert remaining records (if any)
            if bulk_data:
                model.objects.bulk_create(bulk_data, ignore_conflicts=True)

            self.stdout.write(f'✓ Migrated {mysql_table_name} to {model.__name__}')

        finally:
            # Re-enable foreign key checks in MySQL
            self.stdout.write(f'✓ Re-enabled foreign key checks for {mysql_table_name}')
