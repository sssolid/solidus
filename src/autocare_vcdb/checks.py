# src/autocare_vcdb/checks.py
"""
System checks for automotive application.
"""

from django.core.checks import Error, Warning, register


@register()
def check_automotive_settings(app_configs, **kwargs):
    """Check automotive-specific settings."""
    errors = []

    # Add any custom checks here
    # For example, checking if required external services are configured

    return errors