# src/core/templatetags/partial_components.py
from django import template
from django.template.loader import render_to_string

register = template.Library()

@register.inclusion_tag('partials/forms/field.html')
def render_field(field, field_type='input', field_class=None):
    """Template tag for rendering form fields consistently"""
    return {
        'field': field,
        'field_type': field_type,
        'field_class': field_class,
    }

@register.inclusion_tag('partials/status/badge.html')
def status_badge(status, show_icon=True, size='sm'):
    """Template tag for status badges"""
    return {
        'status': status,
        'show_icon': show_icon,
        'size': size,
    }

@register.inclusion_tag('partials/ui/button.html')
def button(text, url=None, variant='primary', size='md', icon=None, onclick=None, type='button'):
    """Template tag for consistent buttons"""
    return {
        'button': {
            'text': text,
            'url': url,
            'variant': variant,
            'size': size,
            'icon': icon,
            'onclick': onclick,
            'type': type,
        }
    }

@register.simple_tag
def breadcrumb_item(name, url=None, icon=None):
    """Add breadcrumb item to context"""
    # This would work with a context processor or middleware
    return {
        'name': name,
        'url': url,
        'icon': icon,
    }