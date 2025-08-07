"""
Custom management command to help migrate data from MySQL to PostgreSQL
Usage: python manage.py migrate_from_mysql
"""
from django.core.management.base import BaseCommand
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate data from MySQL database to Django models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mysql-host',
            type=str,
            default='localhost',
            help='MySQL host'
        )
        parser.add_argument(
            '--mysql-db',
            type=str,
            required=True,
            help='MySQL database name'
        )
        parser.add_argument(
            '--mysql-user',
            type=str,
            required=True,
            help='MySQL username'
        )
        parser.add_argument(
            '--mysql-password',
            type=str,
            required=True,
            help='MySQL password'
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting MySQL to Django migration...')

        try:
            import mysql.connector
        except ImportError:
            self.stdout.write(
                self.style.ERROR('mysql-connector-python is required. Install with: pip install mysql-connector-python')
            )
            return

        # Connect to MySQL
        mysql_conn = mysql.connector.connect(
            host=options['mysql_host'],
            database=options['mysql_db'],
            user=options['mysql_user'],
            password=options['mysql_password']
        )

        cursor = mysql_conn.cursor(dictionary=True)

        try:
            with transaction.atomic():
                # Migrate lookup tables first (no dependencies)
                self._migrate_measurement_groups(cursor)
                self._migrate_categories(cursor)
                self._migrate_subcategories(cursor)
                self._migrate_positions(cursor)
                self._migrate_uses(cursor)
                self._migrate_aliases(cursor)
                self._migrate_parts_descriptions(cursor)

                # Migrate main tables
                self._migrate_parts(cursor)
                self._migrate_metadata(cursor)
                self._migrate_part_attributes(cursor)

                # Migrate relationship tables
                self._migrate_part_attribute_assignments(cursor)
                self._migrate_meta_uom_codes(cursor)

                # Migrate change tracking
                self._migrate_change_tracking(cursor)

                self.stdout.write(self.style.SUCCESS('Migration completed successfully!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Migration failed: {str(e)}'))
            raise
        finally:
            cursor.close()
            mysql_conn.close()

    def _migrate_measurement_groups(self, cursor):
        from autocare.models.pcadb import MeasurementGroup

        cursor.execute("SELECT * FROM MeasurementGroup")
        for row in cursor.fetchall():
            MeasurementGroup.objects.get_or_create(
                measurement_group_id=row['MeasurementGroupID'],
                defaults={'measurement_group_name': row['MeasurementGroupName']}
            )
        self.stdout.write('✓ Migrated MeasurementGroups')

    def _migrate_categories(self, cursor):
        from autocare.models.pcadb import Category

        cursor.execute("SELECT * FROM Categories")
        for row in cursor.fetchall():
            Category.objects.get_or_create(
                category_id=row['CategoryID'],
                defaults={'category_name': row['CategoryName']}
            )
        self.stdout.write('✓ Migrated Categories')

    def _migrate_subcategories(self, cursor):
        from autocare.models.pcadb import Subcategory

        cursor.execute("SELECT * FROM Subcategories")
        for row in cursor.fetchall():
            Subcategory.objects.get_or_create(
                sub_category_id=row['SubCategoryID'],
                defaults={'sub_category_name': row['SubCategoryName']}
            )
        self.stdout.write('✓ Migrated Subcategories')

    def _migrate_positions(self, cursor):
        from autocare.models.pcadb import Position

        cursor.execute("SELECT * FROM Positions")
        for row in cursor.fetchall():
            Position.objects.get_or_create(
                position_id=row['PositionID'],
                defaults={'position': row['Position']}
            )
        self.stdout.write('✓ Migrated Positions')

    def _migrate_uses(self, cursor):
        from autocare.models.pcadb import Use

        cursor.execute("SELECT * FROM `Use`")
        for row in cursor.fetchall():
            Use.objects.get_or_create(
                use_id=row['UseID'],
                defaults={'use_description': row['UseDescription']}
            )
        self.stdout.write('✓ Migrated Uses')

    def _migrate_aliases(self, cursor):
        from autocare.models.pcadb import Alias

        cursor.execute("SELECT * FROM Alias")
        for row in cursor.fetchall():
            Alias.objects.get_or_create(
                alias_id=row['AliasID'],
                defaults={'alias_name': row['AliasName']}
            )
        self.stdout.write('✓ Migrated Aliases')

    def _migrate_parts_descriptions(self, cursor):
        from autocare.models.pcadb import PartsDescription

        cursor.execute("SELECT * FROM PartsDescription")
        for row in cursor.fetchall():
            PartsDescription.objects.get_or_create(
                parts_description_id=row['PartsDescriptionID'],
                defaults={'parts_description': row['PartsDescription']}
            )
        self.stdout.write('✓ Migrated PartsDescriptions')

    def _migrate_parts(self, cursor):
        from autocare.models.pcadb import Part, PartsDescription

        cursor.execute("SELECT * FROM Parts")
        for row in cursor.fetchall():
            parts_description = None
            if row['PartsDescriptionID']:
                try:
                    parts_description = PartsDescription.objects.get(
                        parts_description_id=row['PartsDescriptionID']
                    )
                except PartsDescription.DoesNotExist:
                    pass

            Part.objects.get_or_create(
                part_terminology_id=row['PartTerminologyID'],
                defaults={
                    'part_terminology_name': row['PartTerminologyName'],
                    'parts_description': parts_description,
                    'rev_date': row['RevDate']
                }
            )
        self.stdout.write('✓ Migrated Parts')

    def _migrate_metadata(self, cursor):
        from autocare.models.pcadb import MetaData

        cursor.execute("SELECT * FROM MetaData")
        for row in cursor.fetchall():
            MetaData.objects.get_or_create(
                meta_id=row['MetaID'],
                defaults={
                    'meta_name': row['MetaName'],
                    'meta_description': row['MetaDescr'],
                    'meta_format': row['MetaFormat'],
                    'data_type': row['DataType'],
                    'min_length': row['MinLength'],
                    'max_length': row['MaxLength']
                }
            )
        self.stdout.write('✓ Migrated MetaData')

    def _migrate_part_attributes(self, cursor):
        from autocare.models.pcadb import PartAttribute

        cursor.execute("SELECT * FROM PartAttributes")
        for row in cursor.fetchall():
            PartAttribute.objects.get_or_create(
                pa_id=row['PAID'],
                defaults={
                    'pa_name': row['PAName'],
                    'pa_description': row['PADescr']
                }
            )
        self.stdout.write('✓ Migrated PartAttributes')

    def _migrate_part_attribute_assignments(self, cursor):
        from autocare.models.pcadb import PartAttributeAssignment, Part, PartAttribute, MetaData

        cursor.execute("SELECT * FROM PartAttributeAssignment")
        for row in cursor.fetchall():
            try:
                part = Part.objects.get(part_terminology_id=row['PartTerminologyID'])
                part_attribute = PartAttribute.objects.get(pa_id=row['PAID'])
                meta_data = MetaData.objects.get(meta_id=row['MetaID'])

                PartAttributeAssignment.objects.get_or_create(
                    papt_id=row['PAPTID'],
                    defaults={
                        'part': part,
                        'part_attribute': part_attribute,
                        'meta_data': meta_data
                    }
                )
            except (Part.DoesNotExist, PartAttribute.DoesNotExist, MetaData.DoesNotExist) as e:
                logger.warning(f"Skipping PartAttributeAssignment {row['PAPTID']}: {e}")

        self.stdout.write('✓ Migrated PartAttributeAssignments')

    def _migrate_meta_uom_codes(self, cursor):
        from autocare.models.pcadb import MetaUOMCode, MeasurementGroup

        cursor.execute("SELECT * FROM MetaUOMCodes")
        for row in cursor.fetchall():
            try:
                measurement_group = MeasurementGroup.objects.get(
                    measurement_group_id=row['MeasurementGroupID']
                )
                MetaUOMCode.objects.get_or_create(
                    meta_uom_id=row['MetaUOMID'],
                    defaults={
                        'uom_code': row['UOMCode'],
                        'uom_description': row['UOMDescription'],
                        'uom_label': row['UOMLabel'],
                        'measurement_group': measurement_group
                    }
                )
            except MeasurementGroup.DoesNotExist as e:
                logger.warning(f"Skipping MetaUOMCode {row['MetaUOMID']}: {e}")

        self.stdout.write('✓ Migrated MetaUOMCodes')

    def _migrate_change_tracking(self, cursor):
        from autocare.models.pcadb import ChangeReason, ChangeTableName, ChangeAttributeState, Change, ChangeDetail

        # Migrate change reasons
        cursor.execute("SELECT * FROM ChangeReasons")
        for row in cursor.fetchall():
            ChangeReason.objects.get_or_create(
                change_reason_id=row['ChangeReasonID'],
                defaults={'change_reason': row['ChangeReason']}
            )

        # Migrate change table names
        cursor.execute("SELECT * FROM ChangeTableNames")
        for row in cursor.fetchall():
            ChangeTableName.objects.get_or_create(
                table_name_id=row['TableNameID'],
                defaults={
                    'table_name': row['TableName'],
                    'table_description': row['TableDescription']
                }
            )

        # Migrate change attribute states
        cursor.execute("SELECT * FROM ChangeAttributeStates")
        for row in cursor.fetchall():
            ChangeAttributeState.objects.get_or_create(
                change_attribute_state_id=row['ChangeAttributeStateID'],
                defaults={'change_attribute_state': row['ChangeAttributeState']}
            )

        self.stdout.write('✓ Migrated Change Tracking tables')