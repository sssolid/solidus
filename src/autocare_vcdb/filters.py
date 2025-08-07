# src/autocare_vcdb/filters.py
"""
Django filters for automotive models.
"""

import django_filters
from django import forms
from django.db.models import Q

from autocare_vcdb.models import (
    Vehicle, EngineConfig, Make, Model, Year, Region, DriveType,
    FuelType, Aspiration, Class, PublicationStage
)


class VehicleFilter(django_filters.FilterSet):
    """Filter set for vehicles."""

    # Year range filters
    year_from = django_filters.NumberFilter(
        field_name='base_vehicle__year__year_id',
        lookup_expr='gte',
        label='Year From'
    )
    year_to = django_filters.NumberFilter(
        field_name='base_vehicle__year__year_id',
        lookup_expr='lte',
        label='Year To'
    )

    # Make and model filters
    make = django_filters.ModelMultipleChoiceFilter(
        field_name='base_vehicle__make',
        queryset=Make.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

    model = django_filters.ModelMultipleChoiceFilter(
        field_name='base_vehicle__model',
        queryset=Model.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

    # Region filter
    region = django_filters.ModelMultipleChoiceFilter(
        queryset=Region.objects.filter(parent__isnull=False),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

    # Drive type filter
    drive_type = django_filters.ModelMultipleChoiceFilter(
        field_name='drive_types__drive_type',
        queryset=DriveType.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

    # Vehicle class filter
    vehicle_class = django_filters.ModelMultipleChoiceFilter(
        field_name='classes__vehicle_class',
        queryset=Class.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

    # Publication stage filter
    publication_stage = django_filters.ModelMultipleChoiceFilter(
        queryset=PublicationStage.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

    # Date range filters
    published_after = django_filters.DateTimeFilter(
        field_name='publication_stage_date',
        lookup_expr='gte',
        label='Published After'
    )
    published_before = django_filters.DateTimeFilter(
        field_name='publication_stage_date',
        lookup_expr='lte',
        label='Published Before'
    )

    # Search filter
    search = django_filters.CharFilter(
        method='filter_search',
        label='Search'
    )

    class Meta:
        model = Vehicle
        fields = [
            'year_from', 'year_to', 'make', 'model', 'region',
            'drive_type', 'vehicle_class', 'publication_stage',
            'published_after', 'published_before', 'search'
        ]

    def filter_search(self, queryset, name, value):
        """Custom search filter."""
        if value:
            return queryset.filter(
                Q(base_vehicle__make__make_name__icontains=value) |
                Q(base_vehicle__model__model_name__icontains=value) |
                Q(submodel__sub_model_name__icontains=value)
            )
        return queryset


class EngineConfigFilter(django_filters.FilterSet):
    """Filter set for engine configurations."""

    # Displacement filters
    liter_min = django_filters.NumberFilter(
        field_name='engine_base__liter',
        lookup_expr='gte',
        label='Minimum Displacement (L)'
    )
    liter_max = django_filters.NumberFilter(
        field_name='engine_base__liter',
        lookup_expr='lte',
        label='Maximum Displacement (L)'
    )

    # Cylinder filters
    cylinders = django_filters.MultipleChoiceFilter(
        field_name='engine_base__cylinders',
        choices=[
            ('3', '3 Cylinders'),
            ('4', '4 Cylinders'),
            ('6', '6 Cylinders'),
            ('8', '8 Cylinders'),
            ('10', '10 Cylinders'),
            ('12', '12 Cylinders'),
        ],
        widget=forms.CheckboxSelectMultiple()
    )

    # Fuel type filter
    fuel_type = django_filters.ModelMultipleChoiceFilter(
        queryset=FuelType.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

    # Aspiration filter
    aspiration = django_filters.ModelMultipleChoiceFilter(
        queryset=Aspiration.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

    # Power range filters
    hp_min = django_filters.NumberFilter(
        field_name='power_output__horse_power',
        lookup_expr='gte',
        label='Minimum Horsepower'
    )
    hp_max = django_filters.NumberFilter(
        field_name='power_output__horse_power',
        lookup_expr='lte',
        label='Maximum Horsepower'
    )

    class Meta:
        model = EngineConfig
        fields = [
            'liter_min', 'liter_max', 'cylinders', 'fuel_type',
            'aspiration', 'hp_min', 'hp_max'
        ]