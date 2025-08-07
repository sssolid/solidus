# src/autocare_vcdb/signals.py
"""
Signal handlers for automotive models.
"""

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth import get_user_model

from autocare_vcdb.models import Vehicle, BaseVehicle, Make, Model, EngineConfig

User = get_user_model()


@receiver(pre_save, sender=Vehicle)
def set_publication_date(sender, instance, **kwargs):
    """Set publication stage date when publication stage changes."""
    if instance.pk:
        try:
            old_instance = Vehicle.objects.get(pk=instance.pk)
            if old_instance.publication_stage != instance.publication_stage:
                instance.publication_stage_date = timezone.now()
        except Vehicle.DoesNotExist:
            pass
    else:
        # New instance
        if not instance.publication_stage_date:
            instance.publication_stage_date = timezone.now()


@receiver(post_save, sender=Vehicle)
@receiver(post_delete, sender=Vehicle)
def clear_vehicle_cache(sender, instance, **kwargs):
    """Clear cached vehicle data when vehicles are modified."""
    cache.delete_many([
        'automotive:vehicle_count',
        'automotive:recent_vehicles',
        'automotive:popular_makes',
        f'automotive:vehicle_detail_{instance.vehicle_id}'
    ])


@receiver(post_save, sender=BaseVehicle)
@receiver(post_delete, sender=BaseVehicle)
def clear_base_vehicle_cache(sender, instance, **kwargs):
    """Clear cached base vehicle data."""
    cache.delete_many([
        'automotive:base_vehicle_count',
        f'automotive:base_vehicle_{instance.base_vehicle_id}'
    ])


@receiver(post_save, sender=Make)
@receiver(post_delete, sender=Make)
def clear_make_cache(sender, instance, **kwargs):
    """Clear cached make data."""
    cache.delete_many([
        'automotive:makes_list',
        'automotive:popular_makes'
    ])