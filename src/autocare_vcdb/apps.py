from django.apps import AppConfig


class AutocareVCdbConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'autocare_vcdb'
    verbose_name = 'Autocare VCdb Management'

    def ready(self):
        try:
            from autocare_vcdb.signals import signals
        except ImportError:
            pass

        # Register any custom checks
        try:
            from autocare_vcdb.checks import checks
        except ImportError:
            pass