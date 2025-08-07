from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'
    verbose_name = 'Product Management'

    def ready(self):
        try:
            from products.signals import signals
        except ImportError:
            pass

        # Register any custom checks
        try:
            from products.checks import checks
        except ImportError:
            pass