from django.apps import AppConfig


class AutocarePCAdbConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'autocare_pcadb'
    verbose_name = 'Autocare PCAdb Management'

    def ready(self):
        try:
            from autocare_pcadb.signals import signals
        except ImportError:
            pass

        # Register any custom checks
        try:
            from autocare_pcadb.checks import checks
        except ImportError:
            pass