# src/autocare_vcdb/api_urls.py
"""
URL patterns for the automotive application.
"""

from django.urls import path, include

from autocare_vcdb.api import *
from rest_framework.routers import DefaultRouter

app_name = 'autocare'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'makes', MakeViewSet)
router.register(r'models', ModelViewSet)
router.register(r'years', YearViewSet)
router.register(r'base-vehicles', BaseVehicleViewSet)
router.register(r'regions', RegionViewSet)
router.register(r'vehicles', VehicleViewSet)
router.register(r'engine-configs', EngineConfigViewSet)
router.register(r'transmissions', TransmissionViewSet)
router.register(r'stats', StatsViewSet, basename='stats')
router.register(r'import-export', ImportExportViewSet, basename='import-export')

# Main URL patterns
urlpatterns = [path('', include(router.urls)),]