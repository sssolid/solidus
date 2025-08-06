from django.apps import AppConfig


class AutocareConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'autocare'
    verbose_name = 'Autocare Management'

    def ready(self):
        # Import signal handlers if needed
        pass