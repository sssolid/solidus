# src/autocare/views/vcdb.py
"""
Django views for automotive models with HTMX support.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Prefetch, QuerySet
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.utils.translation import gettext_lazy as _
from django_htmx.http import HttpResponseClientRedirect

from autocare_vcdb.models import (
    Vehicle, BaseVehicle, Make, Model, Year, EngineConfig, Transmission,
    BodyStyleConfig, BrakeConfig, DriveType, VehicleToEngineConfig,
    VehicleToTransmission, Class, Region
)
from autocare_vcdb.forms import (
    VehicleSearchForm, VehicleFilterForm, BaseVehicleForm, VehicleForm,
    EngineConfigForm, TransmissionForm
)


# Dashboard and main views
class AutomotiveDashboardView(LoginRequiredMixin, TemplateView):
    """Main automotive dashboard with statistics and quick access."""
    template_name = 'autocare_vcdb/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get summary statistics
        context['stats'] = {
            'total_vehicles': Vehicle.objects.count(),
            'total_makes': Make.objects.count(),
            'total_models': Model.objects.count(),
            'total_years': Year.objects.count(),
            'recent_vehicles': Vehicle.objects.select_related(
                'base_vehicle__year', 'base_vehicle__make', 'base_vehicle__model'
            ).order_by('-publication_stage_date')[:10]
        }

        # Popular makes by vehicle count
        context['popular_makes'] = Make.objects.annotate(
            vehicle_count=Count('base_vehicles__vehicles')
        ).filter(vehicle_count__gt=0).order_by('-vehicle_count')[:10]

        # Recent years with vehicle counts
        context['recent_years'] = Year.objects.annotate(
            vehicle_count=Count('base_vehicles__vehicles')
        ).filter(vehicle_count__gt=0).order_by('-year_id')[:10]

        return context


# Vehicle views
class VehicleListView(LoginRequiredMixin, ListView):
    """List view for vehicles with search and filtering."""
    model = Vehicle
    template_name = 'autocare_vcdb/vehicle_list.html'
    context_object_name = 'vehicles'
    paginate_by = 25

    def get_queryset(self):
        queryset = Vehicle.objects.select_related(
            'base_vehicle__year', 'base_vehicle__make', 'base_vehicle__model',
            'submodel', 'region', 'publication_stage'
        ).prefetch_related(
            'engine_configs__engine_config__engine_base',
            'transmissions__transmission__transmission_base',
            'drive_types__drive_type'
        )

        # Apply search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(base_vehicle__make__make_name__icontains=search_query) |
                Q(base_vehicle__model__model_name__icontains=search_query) |
                Q(submodel__sub_model_name__icontains=search_query)
            )

        # Apply filters
        year_filter = self.request.GET.get('year')
        if year_filter:
            queryset = queryset.filter(base_vehicle__year__year_id=year_filter)

        make_filter = self.request.GET.get('make')
        if make_filter:
            queryset = queryset.filter(base_vehicle__make__make_id=make_filter)

        model_filter = self.request.GET.get('model')
        if model_filter:
            queryset = queryset.filter(base_vehicle__model__model_id=model_filter)

        region_filter = self.request.GET.get('region')
        if region_filter:
            queryset = queryset.filter(region__region_id=region_filter)

        return queryset.order_by('-base_vehicle__year__year_id', 'base_vehicle__make__make_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = VehicleSearchForm(self.request.GET or None)
        context['filter_form'] = VehicleFilterForm(self.request.GET or None)

        # Add filter options for HTMX updates
        context['years'] = Year.objects.order_by('-year_id')
        context['makes'] = Make.objects.order_by('make_name')
        context['regions'] = Region.objects.filter(parent__isnull=False).order_by('region_name')

        return context


class VehicleDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a vehicle with all configurations."""
    model = Vehicle
    template_name = 'autocare_vcdb/vehicle_detail.html'
    context_object_name = 'vehicle'
    pk_url_kwarg = 'vehicle_id'

    def get_queryset(self):
        return Vehicle.objects.select_related(
            'base_vehicle__year', 'base_vehicle__make', 'base_vehicle__model',
            'submodel', 'region', 'publication_stage'
        ).prefetch_related(
            Prefetch(
                'engine_configs',
                queryset=VehicleToEngineConfig.objects.select_related(
                    'engine_config__engine_base',
                    'engine_config__fuel_type',
                    'engine_config__aspiration',
                    'engine_config__power_output'
                )
            ),
            'transmissions__transmission__transmission_base__transmission_type',
            'body_style_configs__body_style_config__body_type',
            'brake_configs__brake_config__brake_system',
            'drive_types__drive_type',
            'steering_configs__steering_config',
            'spring_type_configs__spring_type_config',
            'bed_configs__bed_config',
            'classes__vehicle_class'
        )


class VehicleCreateView(LoginRequiredMixin, CreateView):
    """Create new vehicle."""
    model = Vehicle
    form_class = VehicleForm
    template_name = 'autocare_vcdb/vehicle_form.html'
    success_url = reverse_lazy('autocare:vcdb:vehicle_list')

    def form_valid(self, form):
        messages.success(self.request, _('Vehicle created successfully.'))
        return super().form_valid(form)


class VehicleUpdateView(LoginRequiredMixin, UpdateView):
    """Update existing vehicle."""
    model = Vehicle
    form_class = VehicleForm
    template_name = 'autocare_vcdb/vehicle_form.html'
    pk_url_kwarg = 'vehicle_id'

    def get_success_url(self):
        return reverse_lazy('autocare:vcdb:vehicle_detail', kwargs={'vehicle_id': self.object.vehicle_id})

    def form_valid(self, form):
        messages.success(self.request, _('Vehicle updated successfully.'))
        return super().form_valid(form)


class VehicleDeleteView(LoginRequiredMixin, DeleteView):
    """Delete vehicle."""
    model = Vehicle
    template_name = 'autocare_vcdb/vehicle_confirm_delete.html'
    pk_url_kwarg = 'vehicle_id'
    success_url = reverse_lazy('automotive:vehicle_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Vehicle deleted successfully.'))
        return super().delete(request, *args, **kwargs)


# Base Vehicle views
class BaseVehicleListView(LoginRequiredMixin, ListView):
    """List view for base vehicles."""
    model = BaseVehicle
    template_name = 'autocare_vcdb/base_vehicle_list.html'
    context_object_name = 'base_vehicles'
    paginate_by = 50

    def get_queryset(self):
        queryset = BaseVehicle.objects.select_related(
            'year', 'make', 'model__vehicle_type'
        ).annotate(
            vehicle_count=Count('vehicles')
        )

        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(make__make_name__icontains=search_query) |
                Q(model__model_name__icontains=search_query)
            )

        return queryset.order_by('-year__year_id', 'make__make_name', 'model__model_name')


class BaseVehicleDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a base vehicle."""
    model = BaseVehicle
    template_name = 'autocare_vcdb/base_vehicle_detail.html'
    context_object_name = 'base_vehicle'
    pk_url_kwarg = 'base_vehicle_id'

    def get_queryset(self):
        return BaseVehicle.objects.select_related(
            'year', 'make', 'model__vehicle_type'
        ).prefetch_related('vehicles__submodel')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vehicles'] = self.object.vehicles.select_related('submodel', 'region')
        return context


# Engine Configuration views
class EngineConfigListView(LoginRequiredMixin, ListView):
    """List view for engine configurations."""
    model = EngineConfig
    template_name = 'autocare_vcdb/engine_config_list.html'
    context_object_name = 'engine_configs'
    paginate_by = 25

    def get_queryset(self):
        return EngineConfig.objects.select_related(
            'engine_base', 'fuel_type', 'aspiration', 'power_output',
            'engine_designation', 'engine_mfr'
        )


class EngineConfigDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of an engine configuration."""
    model = EngineConfig
    template_name = 'autocare_vcdb/engine_config_detail.html'
    context_object_name = 'engine_config'
    pk_url_kwarg = 'engine_config_id'

    def get_queryset(self):
        return EngineConfig.objects.select_related(
            'engine_base', 'fuel_type', 'aspiration', 'power_output',
            'engine_designation', 'engine_vin', 'valves',
            'fuel_delivery_config', 'cylinder_head_type',
            'ignition_system_type', 'engine_mfr', 'engine_version'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get vehicles using this engine config
        context['vehicles'] = Vehicle.objects.filter(
            engine_configs__engine_config=self.object
        ).select_related(
            'base_vehicle__year', 'base_vehicle__make', 'base_vehicle__model'
        )[:20]
        return context


# HTMX specific views
@login_required
@require_http_methods(["GET"])
def htmx_models_by_make(request):
    """Return models for a specific make via HTMX."""
    make_id = request.GET.get('make_id')
    models = []

    if make_id:
        models = Model.objects.filter(
            Q(model_name__isnull=False) &
            Q(basevehicle__make__make_id=make_id)
        ).distinct().order_by('model_name')

    return render(request, 'autocare_vcdb/htmx/model_options.html', {
        'models': models
    })


@login_required
@require_http_methods(["GET"])
def htmx_vehicle_search(request):
    """HTMX vehicle search results."""
    search_form = VehicleSearchForm(request.GET or None)
    vehicles = Vehicle.objects.none()

    if search_form.is_valid() and search_form.cleaned_data.get('search'):
        search_query = search_form.cleaned_data['search']
        vehicles = Vehicle.objects.filter(
            Q(base_vehicle__make__make_name__icontains=search_query) |
            Q(base_vehicle__model__model_name__icontains=search_query) |
            Q(submodel__sub_model_name__icontains=search_query)
        ).select_related(
            'base_vehicle__year', 'base_vehicle__make', 'base_vehicle__model',
            'submodel'
        )[:20]

    return render(request, 'autocare_vcdb/htmx/vehicle_search_results.html', {
        'vehicles': vehicles,
        'search_query': search_form.cleaned_data.get('search', '') if search_form.is_valid() else ''
    })


@login_required
@require_http_methods(["GET"])
def htmx_vehicle_filters(request):
    """HTMX vehicle filter results."""
    filter_form = VehicleFilterForm(request.GET or None)
    vehicles = Vehicle.objects.select_related(
        'base_vehicle__year', 'base_vehicle__make', 'base_vehicle__model',
        'submodel', 'region'
    )

    if filter_form.is_valid():
        if filter_form.cleaned_data.get('year'):
            vehicles = vehicles.filter(base_vehicle__year=filter_form.cleaned_data['year'])
        if filter_form.cleaned_data.get('make'):
            vehicles = vehicles.filter(base_vehicle__make=filter_form.cleaned_data['make'])
        if filter_form.cleaned_data.get('model'):
            vehicles = vehicles.filter(base_vehicle__model=filter_form.cleaned_data['model'])
        if filter_form.cleaned_data.get('region'):
            vehicles = vehicles.filter(region=filter_form.cleaned_data['region'])

    # Paginate results
    paginator = Paginator(vehicles, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'autocare_vcdb/htmx/vehicle_filter_results.html', {
        'page_obj': page_obj,
        'vehicles': page_obj.object_list
    })


# API-style views for HTMX/AJAX
@login_required
@require_http_methods(["GET"])
def api_makes_autocomplete(request):
    """Autocomplete API for makes."""
    term = request.GET.get('term', '')
    makes = Make.objects.filter(
        make_name__icontains=term
    ).order_by('make_name')[:20]

    results = [
        {'id': make.make_id, 'text': make.make_name}
        for make in makes
    ]

    return JsonResponse({'results': results})


@login_required
@require_http_methods(["GET"])
def api_models_by_make(request):
    """API to get models for a specific make."""
    make_id = request.GET.get('make_id')
    models = []

    if make_id:
        models = Model.objects.filter(
            basevehicle__make__make_id=make_id
        ).distinct().order_by('model_name')

    results = [
        {'id': model.model_id, 'text': model.model_name or f'Model {model.model_id}'}
        for model in models
    ]

    return JsonResponse({'results': results})


@login_required
@require_http_methods(["GET"])
def api_vehicle_summary(request, vehicle_id):
    """Get vehicle summary data for popups/tooltips."""
    qs: QuerySet = Vehicle.objects.select_related(
        'base_vehicle__year',
        'base_vehicle__make',
        'base_vehicle__model',
        'submodel'
    )

    vehicle = get_object_or_404(qs, vehicle_id=vehicle_id)

    # Get primary configurations
    engine_config = vehicle.engine_configs.select_related(
        'engine_config__engine_base', 'engine_config__fuel_type'
    ).first()

    transmission = vehicle.transmissions.select_related(
        'transmission__transmission_base__transmission_type'
    ).first()

    drive_type = vehicle.drive_types.select_related('drive_type').first()

    data = {
        'vehicle_id': vehicle.vehicle_id,
        'year': vehicle.base_vehicle.year.year_id,
        'make': vehicle.base_vehicle.make.make_name,
        'model': vehicle.base_vehicle.model.model_name,
        'submodel': vehicle.submodel.sub_model_name,
        'engine': str(engine_config.engine_config) if engine_config else None,
        'transmission': str(transmission.transmission) if transmission else None,
        'drive_type': drive_type.drive_type.drive_type_name if drive_type else None,
    }

    return JsonResponse(data)


# Statistics and reporting views
class AutomotiveStatsView(LoginRequiredMixin, TemplateView):
    """Statistics and analytics view."""
    template_name = 'autocare_vcdb/stats.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Vehicle statistics by year
        context['vehicles_by_year'] = list(
            Year.objects.annotate(
                vehicle_count=Count('base_vehicles__vehicles')
            ).filter(vehicle_count__gt=0).order_by('-year_id')[:20].values(
                'year_id', 'vehicle_count'
            )
        )

        # Top makes by vehicle count
        context['top_makes'] = list(
            Make.objects.annotate(
                vehicle_count=Count('base_vehicles__vehicles')
            ).filter(vehicle_count__gt=0).order_by('-vehicle_count')[:15].values(
                'make_name', 'vehicle_count'
            )
        )

        # Engine statistics
        context['engine_stats'] = {
            'total_configs': EngineConfig.objects.count(),
            'fuel_types': list(
                EngineConfig.objects.values('fuel_type__fuel_type_name').annotate(
                    count=Count('engine_config_id')
                ).order_by('-count')[:10]
            ),
            'cylinder_counts': list(
                EngineConfig.objects.values('engine_base__cylinders').annotate(
                    count=Count('engine_config_id')
                ).order_by('-count')
            )
        }

        # Regional distribution
        context['regional_stats'] = list(
            Region.objects.annotate(
                vehicle_count=Count('vehicles')
            ).filter(vehicle_count__gt=0).order_by('-vehicle_count')[:10].values(
                'region_name', 'vehicle_count'
            )
        )

        return context


# Export views
@login_required
@require_http_methods(["GET"])
def export_vehicles_csv(request):
    """Export vehicles to CSV format."""
    import csv
    from django.utils import timezone

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="vehicles_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Vehicle ID', 'Year', 'Make', 'Model', 'Submodel',
        'Region', 'Publication Stage', 'Publication Date'
    ])

    vehicles = Vehicle.objects.select_related(
        'base_vehicle__year', 'base_vehicle__make', 'base_vehicle__model',
        'submodel', 'region', 'publication_stage'
    )

    # Apply same filters as list view
    search_query = request.GET.get('search')
    if search_query:
        vehicles = vehicles.filter(
            Q(base_vehicle__make__make_name__icontains=search_query) |
            Q(base_vehicle__model__model_name__icontains=search_query) |
            Q(submodel__sub_model_name__icontains=search_query)
        )

    for vehicle in vehicles.iterator():
        writer.writerow([
            vehicle.vehicle_id,
            vehicle.base_vehicle.year.year_id,
            vehicle.base_vehicle.make.make_name,
            vehicle.base_vehicle.model.model_name or '',
            vehicle.submodel.sub_model_name,
            vehicle.region.region_name or '',
            vehicle.publication_stage.publication_stage_name,
            vehicle.publication_stage_date.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return response


# Maintenance and utility views
@login_required
@require_http_methods(["POST"])
def refresh_vehicle_cache(request):
    """Refresh cached vehicle data."""
    if not request.user.is_staff:
        messages.error(request, _('Permission denied.'))
        return redirect('automotive:dashboard')

    # Clear any cached data here
    # cache.clear()

    messages.success(request, _('Vehicle cache refreshed successfully.'))

    if request.htmx:
        return HttpResponse('<div class="alert alert-success">Cache refreshed!</div>')

    return redirect('automotive:dashboard')


class VehicleComparisonView(LoginRequiredMixin, TemplateView):
    """Compare multiple vehicles side by side."""
    template_name = 'autocare_vcdb/vehicle_comparison.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get vehicle IDs from query parameters
        vehicle_ids = self.request.GET.getlist('vehicle_id')

        if vehicle_ids:
            vehicles = Vehicle.objects.filter(
                vehicle_id__in=vehicle_ids
            ).select_related(
                'base_vehicle__year', 'base_vehicle__make', 'base_vehicle__model',
                'submodel', 'region'
            ).prefetch_related(
                'engine_configs__engine_config',
                'transmissions__transmission',
                'drive_types__drive_type',
                'body_style_configs__body_style_config',
                'brake_configs__brake_config'
            )

            context['vehicles'] = vehicles
        else:
            context['vehicles'] = []

        return context


# Advanced search view
class AdvancedVehicleSearchView(LoginRequiredMixin, TemplateView):
    """Advanced vehicle search with multiple criteria."""
    template_name = 'autocare_vcdb/advanced_search.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Provide options for advanced search
        context['years'] = Year.objects.order_by('-year_id')
        context['makes'] = Make.objects.order_by('make_name')
        context['regions'] = Region.objects.filter(parent__isnull=False).order_by('region_name')
        context['drive_types'] = DriveType.objects.order_by('drive_type_name')
        context['vehicle_classes'] = Class.objects.order_by('class_name')

        # Process search if submitted
        if self.request.GET:
            vehicles = self._perform_advanced_search()
            context['vehicles'] = vehicles
            context['show_results'] = True
        else:
            context['show_results'] = False

        return context

    def _perform_advanced_search(self):
        """Perform advanced search based on GET parameters."""
        vehicles = Vehicle.objects.select_related(
            'base_vehicle__year', 'base_vehicle__make', 'base_vehicle__model',
            'submodel', 'region'
        )

        # Year range
        year_from = self.request.GET.get('year_from')
        year_to = self.request.GET.get('year_to')
        if year_from:
            vehicles = vehicles.filter(base_vehicle__year__year_id__gte=year_from)
        if year_to:
            vehicles = vehicles.filter(base_vehicle__year__year_id__lte=year_to)

        # Make
        make_ids = self.request.GET.getlist('make')
        if make_ids:
            vehicles = vehicles.filter(base_vehicle__make__make_id__in=make_ids)

        # Region
        region_ids = self.request.GET.getlist('region')
        if region_ids:
            vehicles = vehicles.filter(region__region_id__in=region_ids)

        # Drive type
        drive_type_ids = self.request.GET.getlist('drive_type')
        if drive_type_ids:
            vehicles = vehicles.filter(drive_types__drive_type__drive_type_id__in=drive_type_ids)

        # Vehicle class
        class_ids = self.request.GET.getlist('vehicle_class')
        if class_ids:
            vehicles = vehicles.filter(classes__vehicle_class__class_id__in=class_ids)

        # Engine criteria
        min_cylinders = self.request.GET.get('min_cylinders')
        if min_cylinders:
            vehicles = vehicles.filter(
                engine_configs__engine_config__engine_base__cylinders__gte=min_cylinders
            )

        fuel_type_ids = self.request.GET.getlist('fuel_type')
        if fuel_type_ids:
            vehicles = vehicles.filter(
                engine_configs__engine_config__fuel_type__fuel_type_id__in=fuel_type_ids
            )

        return vehicles.distinct()[:100]  # Limit results