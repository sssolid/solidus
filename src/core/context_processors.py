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
    """Global navigation context for all templates"""
    if not request.user.is_authenticated:
        return {}

    # Employee navigation items
    employee_nav = [
        {'name': 'Products', 'url': 'products:list', 'icon': 'fas fa-box', 'namespace': 'products'},
        {'name': 'Assets', 'url': 'assets:list', 'icon': 'fas fa-images', 'namespace': 'assets'},
        {'name': 'Data Feeds', 'url': 'feeds:list', 'icon': 'fas fa-rss', 'namespace': 'feeds'},
        {'name': 'Users', 'url': 'accounts:user_list', 'icon': 'fas fa-users', 'namespace': 'accounts'},
        {'name': 'Settings', 'url': 'core:system_settings', 'icon': 'fas fa-cog', 'namespace': 'core'},
    ]

    # Customer navigation items
    customer_nav = [
        {'name': 'Product Catalog', 'url': 'products:catalog', 'icon': 'fas fa-shopping-bag'},
        {'name': 'Browse Assets', 'url': 'assets:browse', 'icon': 'fas fa-images'},
    ]

    return {
        'navigation_items': employee_nav if request.user.is_employee else customer_nav,
        'current_namespace': getattr(request.resolver_match, 'namespace', ''),
    }


def ui_context(request):
    """UI-related context for templates"""
    return {
        'modal_sizes': {
            'sm': 'sm',
            'md': 'md',
            'lg': 'lg',
            'xl': 'xl',
        },
        'button_variants': {
            'primary': 'bg-blue-600 hover:bg-blue-700 text-white',
            'secondary': 'bg-gray-600 hover:bg-gray-700 text-white',
            'outline': 'border border-gray-300 text-gray-700 hover:bg-gray-50',
            'danger': 'bg-red-600 hover:bg-red-700 text-white',
        }
    }