# src/autocare_vcdb/templatetags/vcdb_tags.py
"""
Template tags for automotive application.
"""

from django import template
from django.db.models import Count
from django.core.cache import cache
from autocare_vcdb.models import Make, Vehicle, Year

register = template.Library()


@register.simple_tag
def total_vehicles():
    """Get total vehicle count."""
    cache_key = 'automotive:total_vehicles'
    count = cache.get(cache_key)
    if count is None:
        count = Vehicle.objects.count()
        cache.set(cache_key, count, 300)  # 5 minutes
    return count


@register.simple_tag
def popular_makes(limit=5):
    """Get most popular makes by vehicle count."""
    cache_key = f'automotive:popular_makes_{limit}'
    makes = cache.get(cache_key)
    if makes is None:
        makes = list(Make.objects.annotate(
            vehicle_count=Count('base_vehicles__vehicles')
        ).filter(vehicle_count__gt=0).order_by('-vehicle_count')[:limit])
        cache.set(cache_key, makes, 600)  # 10 minutes
    return makes


@register.simple_tag
def recent_years(limit=10):
    """Get recent years with vehicles."""
    cache_key = f'automotive:recent_years_{limit}'
    years = cache.get(cache_key)
    if years is None:
        years = list(Year.objects.annotate(
            vehicle_count=Count('base_vehicles__vehicles')
        ).filter(vehicle_count__gt=0).order_by('-year_id')[:limit])
        cache.set(cache_key, years, 600)  # 10 minutes
    return years


@register.filter
def format_engine_specs(engine_config):
    """Format engine configuration for display."""
    if not engine_config:
        return "N/A"

    base = engine_config.engine_base
    specs = f"{base.liter}L {base.cylinders}cyl"

    if engine_config.fuel_type:
        specs += f" {engine_config.fuel_type.fuel_type_name}"

    if engine_config.aspiration:
        specs += f" {engine_config.aspiration.aspiration_name}"

    return specs


@register.inclusion_tag('autocare_vcdb/tags/vehicle_card.html')
def vehicle_card(vehicle, show_details=True):
    """Render a vehicle card."""
    return {
        'vehicle': vehicle,
        'show_details': show_details
    }


@register.inclusion_tag('autocare_vcdb/tags/search_form.html')
def automotive_search_form():
    """Render automotive search form."""
    return {}