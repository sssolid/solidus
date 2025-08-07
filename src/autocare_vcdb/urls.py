# src/autocare_vcdb/urls.py
"""
URL patterns for the automotive application.
"""

from django.urls import path, include

from autocare_vcdb.views import *

app_name = 'autocare'

# Main URL patterns
urlpatterns = [
    # Dashboard
    path('', AutomotiveDashboardView.as_view(), name='dashboard'),
    path('stats/', AutomotiveStatsView.as_view(), name='stats'),

    # Vehicle URLs
    path('vehicles/', include([
        path('', VehicleListView.as_view(), name='vehicle_list'),
        path('<int:vehicle_id>/', VehicleDetailView.as_view(), name='vehicle_detail'),
        path('create/', VehicleCreateView.as_view(), name='vehicle_create'),
        path('<int:vehicle_id>/edit/', VehicleUpdateView.as_view(), name='vehicle_edit'),
        path('<int:vehicle_id>/delete/', VehicleDeleteView.as_view(), name='vehicle_delete'),
        path('compare/', VehicleComparisonView.as_view(), name='vehicle_compare'),
        path('search/advanced/', AdvancedVehicleSearchView.as_view(), name='advanced_search'),
        path('export/csv/', export_vehicles_csv, name='export_vehicles_csv'),
    ])),

    # Base Vehicle URLs
    path('base-vehicles/', include([
        path('', BaseVehicleListView.as_view(), name='base_vehicle_list'),
        path('<int:base_vehicle_id>/', BaseVehicleDetailView.as_view(), name='base_vehicle_detail'),
    ])),

    # Engine Configuration URLs
    path('engines/', include([
        path('', EngineConfigListView.as_view(), name='engine_config_list'),
        path('<int:engine_config_id>/', EngineConfigDetailView.as_view(), name='engine_config_detail'),
    ])),

    # HTMX endpoints
    path('htmx/', include([
        path('models-by-make/', htmx_models_by_make, name='htmx_models_by_make'),
        path('vehicle-search/', htmx_vehicle_search, name='htmx_vehicle_search'),
        path('vehicle-filters/', htmx_vehicle_filters, name='htmx_vehicle_filters'),
    ])),

    # API endpoints
    path('api/', include([
        path('makes/autocomplete/', api_makes_autocomplete, name='api_makes_autocomplete'),
        path('models-by-make/', api_models_by_make, name='api_models_by_make'),
        path('vehicle/<int:vehicle_id>/summary/', api_vehicle_summary, name='api_vehicle_summary'),
    ])),

    # Utility endpoints
    path('utils/', include([
        path('refresh-cache/', refresh_vehicle_cache, name='refresh_cache'),
    ])),
]