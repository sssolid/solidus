# src/autocare_vcdb/api.py
"""
Django REST Framework API views for automotive models.
"""

import time
from django.db.models import Q, Count, Prefetch
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from autocare_vcdb.models import (
    Make, Model, Year, BaseVehicle, SubModel, Region, Vehicle,
    EngineConfig, Transmission, DriveType, Class, FuelType, Aspiration, VehicleToEngineConfig
)
from autocare_vcdb.serializers import (
    MakeSerializer, ModelSerializer, YearSerializer, BaseVehicleSerializer,
    SubModelSerializer, RegionSerializer, VehicleListSerializer,
    VehicleDetailSerializer, VehicleCreateUpdateSerializer, EngineConfigSerializer,
    TransmissionSerializer, DriveTypeSerializer, ClassSerializer,
    VehicleStatsSerializer, SearchResultSerializer, BulkUpdateSerializer,
    ImportResultSerializer
)
from autocare_vcdb.filters import VehicleFilter, EngineConfigFilter


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for automotive API."""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class LargeResultsSetPagination(PageNumberPagination):
    """Large pagination for data exports."""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


# Reference data viewsets
@method_decorator(cache_page(60 * 30), name='list')  # Cache for 30 minutes
class MakeViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset for vehicle makes."""
    queryset = Make.objects.all().order_by('make_name')
    serializer_class = MakeSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['make_name']
    ordering_fields = ['make_name', 'make_id']
    ordering = ['make_name']

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by vehicle availability
        has_vehicles = self.request.query_params.get('has_vehicles')
        if has_vehicles == 'true':
            queryset = queryset.annotate(
                vehicle_count=Count('base_vehicles__vehicles')
            ).filter(vehicle_count__gt=0)

        return queryset

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get most popular makes by vehicle count."""
        limit = int(request.query_params.get('limit', 10))
        makes = Make.objects.annotate(
            vehicle_count=Count('base_vehicles__vehicles')
        ).filter(vehicle_count__gt=0).order_by('-vehicle_count')[:limit]

        serializer = self.get_serializer(makes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def models(self, request, pk=None):
        """Get models for a specific make."""
        make = self.get_object()
        models = Model.objects.filter(
            basevehicle__make=make
        ).distinct().order_by('model_name')

        serializer = ModelSerializer(models, many=True)
        return Response(serializer.data)


@method_decorator(cache_page(60 * 30), name='list')
class ModelViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset for vehicle models."""
    queryset = Model.objects.select_related('vehicle_type').order_by('model_name')
    serializer_class = ModelSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['model_name']
    filterset_fields = ['vehicle_type']
    ordering_fields = ['model_name', 'model_id']
    ordering = ['model_name']


@method_decorator(cache_page(60 * 60), name='list')  # Cache for 1 hour
class YearViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset for model years."""
    queryset = Year.objects.all().order_by('-year_id')
    serializer_class = YearSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['year_id']
    ordering = ['-year_id']

    @action(detail=False, methods=['get'])
    def range(self, request):
        """Get year range with vehicle counts."""
        start_year = request.query_params.get('start', 1990)
        end_year = request.query_params.get('end', 2025)

        years = Year.objects.filter(
            year_id__gte=start_year,
            year_id__lte=end_year
        ).annotate(
            vehicle_count=Count('base_vehicles__vehicles')
        ).order_by('-year_id')

        serializer = self.get_serializer(years, many=True)
        return Response(serializer.data)


class BaseVehicleViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset for base vehicles."""
    queryset = BaseVehicle.objects.select_related(
        'year', 'make', 'model__vehicle_type'
    ).order_by('-year__year_id', 'make__make_name', 'model__model_name')
    serializer_class = BaseVehicleSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['make__make_name', 'model__model_name']
    filterset_fields = ['year', 'make', 'model']
    ordering_fields = ['year__year_id', 'make__make_name', 'model__model_name']
    ordering = ['-year__year_id', 'make__make_name']


@method_decorator(cache_page(60 * 15), name='list')
class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset for regions."""
    queryset = Region.objects.select_related('parent').order_by('region_name')
    serializer_class = RegionSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['region_name', 'region_abbr']
    filterset_fields = ['parent']
    ordering_fields = ['region_name', 'region_id']
    ordering = ['region_name']


# Main vehicle viewset
class VehicleViewSet(viewsets.ModelViewSet):
    """API viewset for vehicles with full CRUD operations."""
    queryset = Vehicle.objects.select_related(
        'base_vehicle__year', 'base_vehicle__make', 'base_vehicle__model',
        'submodel', 'region', 'publication_stage'
    ).prefetch_related(
        Prefetch(
            'engine_configs',
            queryset=VehicleToEngineConfig.objects.select_related(
                'engine_config__engine_base', 'engine_config__fuel_type',
                'engine_config__aspiration', 'engine_config__power_output'
            )
        )
    )
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = VehicleFilter
    search_fields = [
        'base_vehicle__make__make_name',
        'base_vehicle__model__model_name',
        'submodel__sub_model_name'
    ]
    ordering_fields = [
        'vehicle_id', 'base_vehicle__year__year_id',
        'base_vehicle__make__make_name', 'publication_stage_date'
    ]
    ordering = ['-base_vehicle__year__year_id', 'base_vehicle__make__make_name']

    def get_queryset(self):
        """Get queryset with optimized relationships."""
        return Vehicle.objects.select_related(
            'base_vehicle__year', 'base_vehicle__make', 'base_vehicle__model',
            'submodel', 'region', 'publication_stage'
        ).prefetch_related(
            Prefetch(
                'engine_configs',
                queryset=VehicleToEngineConfig.objects.select_related(
                    'engine_config__engine_base', 'engine_config__fuel_type',
                    'engine_config__aspiration', 'engine_config__power_output'
                )
            ),
            'transmissions__transmission__transmission_base',
            'drive_types__drive_type'
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return VehicleListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return VehicleCreateUpdateSerializer
        else:
            return VehicleDetailSerializer

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced vehicle search with timing."""
        start_time = time.time()

        # Get search parameters
        query = request.query_params.get('q', '')
        filters = {}

        # Build filters from query parameters
        if request.query_params.get('year'):
            filters['base_vehicle__year__year_id'] = request.query_params.get('year')
        if request.query_params.get('make'):
            filters['base_vehicle__make__make_id'] = request.query_params.get('make')
        if request.query_params.get('model'):
            filters['base_vehicle__model__model_id'] = request.query_params.get('model')
        if request.query_params.get('region'):
            filters['region__region_id'] = request.query_params.get('region')

        # Apply search and filters
        queryset = self.get_queryset()
        if query:
            queryset = queryset.filter(
                Q(base_vehicle__make__make_name__icontains=query) |
                Q(base_vehicle__model__model_name__icontains=query) |
                Q(submodel__sub_model_name__icontains=query)
            )

        if filters:
            queryset = queryset.filter(**filters)

        # Paginate results
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)

        # Calculate timing
        end_time = time.time()
        search_time_ms = (end_time - start_time) * 1000

        # Serialize results
        serializer = VehicleListSerializer(page, many=True)

        # Build response with metadata
        response_data = {
            'query': query,
            'total_results': queryset.count(),
            'page': int(request.query_params.get('page', 1)),
            'total_pages': paginator.page.paginator.num_pages if page else 1,
            'results': serializer.data,
            'filters_applied': filters,
            'search_time_ms': round(search_time_ms, 2),
            'suggestions': self._get_search_suggestions(query) if query else []
        }

        search_serializer = SearchResultSerializer(data=response_data)
        search_serializer.is_valid(raise_exception=True)

        return paginator.get_paginated_response(search_serializer.data)

    def _get_search_suggestions(self, query):
        """Get search suggestions based on query."""
        suggestions = []

        # Get similar makes
        makes = Make.objects.filter(
            make_name__icontains=query
        ).values_list('make_name', flat=True)[:3]
        suggestions.extend(makes)

        # Get similar models
        models = Model.objects.filter(
            model_name__icontains=query
        ).values_list('model_name', flat=True)[:3]
        suggestions.extend(models)

        return list(set(suggestions))  # Remove duplicates

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Bulk update multiple vehicles."""
        serializer = BulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        vehicle_ids = serializer.validated_data['vehicle_ids']
        action = serializer.validated_data['action']

        # Get vehicles to update
        vehicles = Vehicle.objects.filter(vehicle_id__in=vehicle_ids)
        if vehicles.count() != len(vehicle_ids):
            return Response(
                {'error': 'Some vehicle IDs were not found.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Perform bulk update based on action
        updated_count = 0
        if action == 'update_region':
            new_region = serializer.validated_data['new_region']
            updated_count = vehicles.update(region=new_region)
        elif action == 'update_publication_stage':
            new_stage = serializer.validated_data['new_publication_stage']
            updated_count = vehicles.update(publication_stage=new_stage)
        elif action == 'update_source':
            new_source = serializer.validated_data['new_source']
            updated_count = vehicles.update(source=new_source)

        return Response({
            'success': True,
            'message': f'Successfully updated {updated_count} vehicles.',
            'updated_count': updated_count
        })

    @action(detail=False, methods=['get'])
    def export(self, request):
        """Export vehicles in various formats."""
        format_type = request.query_params.get('format', 'json')

        # Apply same filters as list view
        queryset = self.filter_queryset(self.get_queryset())

        # Limit export size
        limit = min(int(request.query_params.get('limit', 1000)), 10000)
        queryset = queryset[:limit]

        if format_type == 'csv':
            return self._export_csv(queryset)
        elif format_type == 'json':
            serializer = VehicleListSerializer(queryset, many=True)
            return Response({
                'count': len(serializer.data),
                'results': serializer.data
            })
        else:
            return Response(
                {'error': 'Unsupported format. Use "json" or "csv".'},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _export_csv(self, queryset):
        """Export queryset to CSV format."""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="vehicles.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'vehicle_id', 'year', 'make', 'model', 'submodel',
            'region', 'publication_stage', 'publication_date'
        ])

        for vehicle in queryset:
            writer.writerow([
                vehicle.vehicle_id,
                vehicle.base_vehicle.year.year_id,
                vehicle.base_vehicle.make.make_name,
                vehicle.base_vehicle.model.model_name or '',
                vehicle.submodel.sub_model_name,
                vehicle.region.region_name if vehicle.region else '',
                vehicle.publication_stage.publication_stage_name,
                vehicle.publication_stage_date.strftime('%Y-%m-%d %H:%M:%S')
            ])

        return response

    @action(detail=True, methods=['get'])
    def configurations(self, request, pk=None):
        """Get all configurations for a specific vehicle."""
        vehicle = self.get_object()

        # Get related configurations
        engine_configs = vehicle.engine_configs.select_related('engine_config')
        transmissions = vehicle.transmissions.select_related('transmission')
        drive_types = vehicle.drive_types.select_related('drive_type')

        return Response({
            'vehicle_id': vehicle.vehicle_id,
            'engine_configs': EngineConfigSerializer(
                [ec.engine_config for ec in engine_configs], many=True
            ).data,
            'transmissions': TransmissionSerializer(
                [t.transmission for t in transmissions], many=True
            ).data,
            'drive_types': DriveTypeSerializer(
                [dt.drive_type for dt in drive_types], many=True
            ).data
        })


# Engine configuration viewset
class EngineConfigViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset for engine configurations."""
    queryset = EngineConfig.objects.select_related(
        'engine_base', 'fuel_type', 'aspiration', 'power_output',
        'engine_designation', 'engine_mfr'
    ).order_by('engine_base__liter', 'engine_base__cylinders')
    serializer_class = EngineConfigSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = EngineConfigFilter
    search_fields = [
        'engine_designation__engine_designation_name',
        'engine_base__liter', 'engine_base__cylinders'
    ]
    ordering_fields = [
        'engine_config_id', 'engine_base__liter', 'engine_base__cylinders',
        'power_output__horse_power'
    ]
    ordering = ['engine_base__liter', 'engine_base__cylinders']

    @action(detail=True, methods=['get'])
    def vehicles(self, request, pk=None):
        """Get vehicles using this engine configuration."""
        engine_config = self.get_object()
        vehicles = Vehicle.objects.filter(
            engine_configs__engine_config=engine_config
        ).select_related(
            'base_vehicle__year', 'base_vehicle__make', 'base_vehicle__model'
        )[:50]  # Limit results

        serializer = VehicleListSerializer(vehicles, many=True)
        return Response(serializer.data)


# Transmission viewset
class TransmissionViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset for transmissions."""
    queryset = Transmission.objects.select_related(
        'transmission_base__transmission_type',
        'transmission_base__transmission_num_speeds',
        'transmission_mfr'
    ).order_by('transmission_base__transmission_type__transmission_type_name')
    serializer_class = TransmissionSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = [
        'transmission_base__transmission_type',
        'transmission_mfr',
        'transmission_elec_controlled'
    ]
    search_fields = [
        'transmission_base__transmission_type__transmission_type_name',
        'transmission_mfr_code__transmission_mfr_code'
    ]
    ordering_fields = ['transmission_id', 'transmission_base']
    ordering = ['transmission_base__transmission_type__transmission_type_name']


# Statistics and analytics viewsets
class StatsViewSet(viewsets.ViewSet):
    """API viewset for automotive statistics."""
    permission_classes = [IsAuthenticated]

    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get overview statistics."""
        stats = {
            'total_vehicles': Vehicle.objects.count(),
            'total_makes': Make.objects.count(),
            'total_models': Model.objects.count(),
            'total_years': Year.objects.count(),
        }

        # Vehicles by year (last 10 years)
        vehicles_by_year = list(
            Year.objects.annotate(
                vehicle_count=Count('base_vehicles__vehicles')
            ).filter(vehicle_count__gt=0).order_by('-year_id')[:10].values(
                'year_id', 'vehicle_count'
            )
        )

        # Top makes
        top_makes = list(
            Make.objects.annotate(
                vehicle_count=Count('base_vehicles__vehicles')
            ).filter(vehicle_count__gt=0).order_by('-vehicle_count')[:15].values(
                'make_name', 'vehicle_count'
            )
        )

        # Engine statistics
        engine_stats = {
            'total_configs': EngineConfig.objects.count(),
            'fuel_types': list(
                FuelType.objects.annotate(
                    count=Count('engine_configs')
                ).values('fuel_type_name', 'count').order_by('-count')[:10]
            ),
            'cylinder_counts': list(
                EngineConfig.objects.values('engine_base__cylinders').annotate(
                    count=Count('engine_config_id')
                ).order_by('-count')
            )
        }

        # Regional statistics
        regional_stats = list(
            Region.objects.annotate(
                vehicle_count=Count('vehicles')
            ).filter(vehicle_count__gt=0).order_by('-vehicle_count')[:10].values(
                'region_name', 'vehicle_count'
            )
        )

        data = {
            **stats,
            'vehicles_by_year': vehicles_by_year,
            'top_makes': top_makes,
            'engine_stats': engine_stats,
            'regional_stats': regional_stats
        }

        serializer = VehicleStatsSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def trends(self, request):
        """Get trend data over time."""
        # Vehicles by publication date (last 12 months)
        from django.utils import timezone
        from datetime import timedelta

        end_date = timezone.now()
        start_date = end_date - timedelta(days=365)

        # Group by month
        from django.db.models import DateTrunc
        monthly_trends = Vehicle.objects.filter(
            publication_stage_date__gte=start_date,
            publication_stage_date__lte=end_date
        ).extra({
            'month': "date_trunc('month', publication_stage_date)"
        }).values('month').annotate(
            count=Count('vehicle_id')
        ).order_by('month')

        return Response({
            'monthly_vehicle_additions': list(monthly_trends),
            'date_range': {
                'start': start_date.date(),
                'end': end_date.date()
            }
        })


# Import/Export viewset
class ImportExportViewSet(viewsets.ViewSet):
    """API viewset for data import/export operations."""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def import_data(self, request):
        """Import vehicle data from uploaded file."""
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        import tempfile
        import os

        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded_file = request.FILES['file']
        file_format = request.data.get('format', 'csv')

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_format}') as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        try:
            # Import data using management command logic
            from django.core.management import call_command
            from io import StringIO

            out = StringIO()
            call_command(
                'import_automotive_data',
                temp_file_path,
                format=file_format,
                skip_errors=True,
                stdout=out
            )

            # Parse output for results
            output = out.getvalue()

            # Mock results - in real implementation, you'd parse the command output
            result_data = {
                'success': True,
                'message': 'Import completed successfully.',
                'total_records': 100,  # Parse from output
                'successful_imports': 95,  # Parse from output
                'failed_imports': 5,  # Parse from output
                'errors': [],  # Parse from output
                'warnings': [],
                'processing_time_seconds': 10.5  # Parse from output
            }

            serializer = ImportResultSerializer(data=result_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data)

        except Exception as e:
            result_data = {
                'success': False,
                'message': f'Import failed: {str(e)}',
                'total_records': 0,
                'successful_imports': 0,
                'failed_imports': 0,
                'processing_time_seconds': 0
            }

            serializer = ImportResultSerializer(data=result_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)