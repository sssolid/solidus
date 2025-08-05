# src/core/context_processors.py

from django.conf import settings
from .models import SystemSetting, Notification


def site_context(request):
    """
    Add site-wide context variables to all templates
    """
    context = {
        'site_name': 'Solidus',
        'debug': settings.DEBUG,
    }

    # Add system settings that are marked as public
    try:
        public_settings = SystemSetting.objects.filter(is_public=True)
        for setting in public_settings:
            context[f'setting_{setting.key}'] = setting.get_value()
    except Exception:
        # Handle case when database isn't ready (e.g., during migrations)
        pass

    # Add user-specific context if user is authenticated
    if request.user.is_authenticated:
        try:
            # Unread notification count
            context['unread_notifications_count'] = Notification.objects.filter(
                user=request.user,
                is_read=False
            ).count()

            # User role helpers
            context['is_customer'] = request.user.role == 'customer'
            context['is_employee'] = request.user.role in ['admin', 'employee']
            context['is_admin'] = request.user.role == 'admin'

        except Exception:
            # Handle case when database isn't ready
            context['unread_notifications_count'] = 0
            context['is_customer'] = False
            context['is_employee'] = False
            context['is_admin'] = False
    else:
        context['unread_notifications_count'] = 0
        context['is_customer'] = False
        context['is_employee'] = False
        context['is_admin'] = False

    return context


def navigation_context(request):
    """
    Add navigation-specific context
    """
    return {
        'current_app': request.resolver_match.app_name if request.resolver_match else '',
        'current_url_name': request.resolver_match.url_name if request.resolver_match else '',
    }