# src/automotive/forms.py
"""
Django forms for automotive models.
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from autocare_vcdb.models import (
    Vehicle, BaseVehicle, Make, Model, Year, SubModel, Region,
    PublicationStage, EngineConfig, Transmission, BodyStyleConfig,
    BrakeConfig, DriveType, Class, FuelType, Aspiration
)


class BaseAutomotiveForm(forms.ModelForm):
    """Base form with common styling and functionality."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes for styling
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': 'form-select',
                    'data-live-search': 'true'
                })
            elif isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'type': 'date'
                })
            elif isinstance(field.widget, forms.DateTimeInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'type': 'datetime-local'
                })


class VehicleSearchForm(forms.Form):
    """Simple vehicle search form."""
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search vehicles by make, model, or submodel...'),
            'hx-get': '',
            'hx-target': '#search-results',
            'hx-trigger': 'keyup changed delay:500ms'
        }),
        label=_('Search')
    )


class VehicleFilterForm(forms.Form):
    """Advanced vehicle filtering form."""
    year = forms.ModelChoiceField(
        queryset=Year.objects.all().order_by('-year_id'),
        required=False,
        empty_label=_('All Years'),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-get': '',
            'hx-target': '#filter-results',
            'hx-include': '[name="make"], [name="model"], [name="region"]'
        }),
        label=_('Year')
    )

    make = forms.ModelChoiceField(
        queryset=Make.objects.all().order_by('make_name'),
        required=False,
        empty_label=_('All Makes'),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-get': '',
            'hx-target': '#model-select',
            'hx-include': '[name="year"]'
        }),
        label=_('Make')
    )

    model = forms.ModelChoiceField(
        queryset=Model.objects.none(),
        required=False,
        empty_label=_('All Models'),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-get': '',
            'hx-target': '#filter-results',
            'hx-include': '[name="year"], [name="make"], [name="region"]'
        }),
        label=_('Model')
    )

    region = forms.ModelChoiceField(
        queryset=Region.objects.filter(parent__isnull=False).order_by('region_name'),
        required=False,
        empty_label=_('All Regions'),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-get': '',
            'hx-target': '#filter-results',
            'hx-include': '[name="year"], [name="make"], [name="model"]'
        }),
        label=_('Region')
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Dynamically set model queryset based on selected make
        if self.data.get('make'):
            try:
                make_id = int(self.data.get('make'))
                self.fields['model'].queryset = Model.objects.filter(
                    basevehicle__make__make_id=make_id
                ).distinct().order_by('model_name')
            except (ValueError, TypeError):
                pass


class BaseVehicleForm(BaseAutomotiveForm):
    """Form for creating/editing base vehicles."""

    class Meta:
        model = BaseVehicle
        fields = ['year', 'make', 'model']
        widgets = {
            'year': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true'
            }),
            'make': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true',
                'hx-get': '',
                'hx-target': '#id_model',
                'hx-include': '[name="year"]'
            }),
            'model': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Order querysets
        self.fields['year'].queryset = Year.objects.order_by('-year_id')
        self.fields['make'].queryset = Make.objects.order_by('make_name')
        self.fields['model'].queryset = Model.objects.order_by('model_name')

        # Set up dynamic model field
        if self.data.get('make'):
            try:
                make_id = int(self.data.get('make'))
                self.fields['model'].queryset = Model.objects.filter(
                    basevehicle__make__make_id=make_id
                ).distinct().order_by('model_name')
            except (ValueError, TypeError):
                pass

    def clean(self):
        cleaned_data = super().clean()
        year = cleaned_data.get('year')
        make = cleaned_data.get('make')
        model = cleaned_data.get('model')

        if year and make and model:
            # Check if this combination already exists
            existing = BaseVehicle.objects.filter(
                year=year, make=make, model=model
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise ValidationError(_('This year/make/model combination already exists.'))

        return cleaned_data


class VehicleForm(BaseAutomotiveForm):
    """Form for creating/editing vehicles."""

    class Meta:
        model = Vehicle
        fields = [
            'base_vehicle', 'submodel', 'region', 'source',
            'publication_stage', 'publication_stage_source'
        ]
        widgets = {
            'base_vehicle': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true'
            }),
            'submodel': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true'
            }),
            'region': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true'
            }),
            'source': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 10
            }),
            'publication_stage': forms.Select(attrs={
                'class': 'form-select'
            }),
            'publication_stage_source': forms.TextInput(attrs={
                'class': 'form-control'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Order querysets
        self.fields['base_vehicle'].queryset = BaseVehicle.objects.select_related(
            'year', 'make', 'model'
        ).order_by('-year__year_id', 'make__make_name', 'model__model_name')

        self.fields['submodel'].queryset = SubModel.objects.order_by('sub_model_name')
        self.fields['region'].queryset = Region.objects.order_by('region_name')
        self.fields['publication_stage'].queryset = PublicationStage.objects.order_by('publication_stage_name')

        # Customize labels for base_vehicle choices
        base_vehicle_choices = [('', '---------')]
        for bv in self.fields['base_vehicle'].queryset[:200]:  # Limit for performance
            label = f"{bv.year.year_id} {bv.make.make_name} {bv.model.model_name or 'Unknown Model'}"
            base_vehicle_choices.append((bv.pk, label))

        self.fields['base_vehicle'].choices = base_vehicle_choices


class EngineConfigForm(BaseAutomotiveForm):
    """Form for creating/editing engine configurations."""

    class Meta:
        model = EngineConfig
        fields = [
            'engine_designation', 'engine_vin', 'valves', 'engine_base',
            'fuel_delivery_config', 'aspiration', 'cylinder_head_type',
            'fuel_type', 'ignition_system_type', 'engine_mfr',
            'engine_version', 'power_output'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add search capabilities to key fields
        for field_name in ['engine_base', 'fuel_type', 'aspiration', 'engine_mfr']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'data-live-search': 'true'
                })


class TransmissionForm(BaseAutomotiveForm):
    """Form for creating/editing transmissions."""

    class Meta:
        model = Transmission
        fields = [
            'transmission_base', 'transmission_mfr_code',
            'transmission_elec_controlled', 'transmission_mfr'
        ]


class AdvancedSearchForm(forms.Form):
    """Advanced vehicle search form with multiple criteria."""

    # Basic vehicle information
    year_from = forms.IntegerField(
        required=False,
        min_value=1900,
        max_value=2050,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('From year')
        }),
        label=_('Year From')
    )

    year_to = forms.IntegerField(
        required=False,
        min_value=1900,
        max_value=2050,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('To year')
        }),
        label=_('Year To')
    )

    make = forms.ModelMultipleChoiceField(
        queryset=Make.objects.all().order_by('make_name'),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'data-live-search': 'true',
            'multiple': True
        }),
        label=_('Makes')
    )

    region = forms.ModelMultipleChoiceField(
        queryset=Region.objects.filter(parent__isnull=False).order_by('region_name'),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'data-live-search': 'true',
            'multiple': True
        }),
        label=_('Regions')
    )

    drive_type = forms.ModelMultipleChoiceField(
        queryset=DriveType.objects.all().order_by('drive_type_name'),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'data-live-search': 'true',
            'multiple': True
        }),
        label=_('Drive Types')
    )

    vehicle_class = forms.ModelMultipleChoiceField(
        queryset=Class.objects.all().order_by('class_name'),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'data-live-search': 'true',
            'multiple': True
        }),
        label=_('Vehicle Classes')
    )

    # Engine criteria
    min_cylinders = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=16,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Minimum cylinders')
        }),
        label=_('Minimum Cylinders')
    )

    fuel_type = forms.ModelMultipleChoiceField(
        queryset=FuelType.objects.all().order_by('fuel_type_name'),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'data-live-search': 'true',
            'multiple': True
        }),
        label=_('Fuel Types')
    )

    aspiration = forms.ModelMultipleChoiceField(
        queryset=Aspiration.objects.all().order_by('aspiration_name'),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'data-live-search': 'true',
            'multiple': True
        }),
        label=_('Aspiration Types')
    )

    # Search options
    include_discontinued = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('Include Discontinued Vehicles')
    )

    results_per_page = forms.ChoiceField(
        choices=[(25, '25'), (50, '50'), (100, '100'), (200, '200')],
        initial=50,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Results Per Page')
    )

    def clean(self):
        cleaned_data = super().clean()
        year_from = cleaned_data.get('year_from')
        year_to = cleaned_data.get('year_to')

        if year_from and year_to and year_from > year_to:
            raise ValidationError(_('Year from must be less than or equal to year to.'))

        return cleaned_data


class VehicleComparisonForm(forms.Form):
    """Form for selecting vehicles to compare."""

    vehicles = forms.ModelMultipleChoiceField(
        queryset=Vehicle.objects.select_related(
            'base_vehicle__year', 'base_vehicle__make', 'base_vehicle__model',
            'submodel'
        ).order_by('-base_vehicle__year__year_id', 'base_vehicle__make__make_name'),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'data-live-search': 'true',
            'multiple': True,
            'size': '10'
        }),
        label=_('Select Vehicles to Compare'),
        help_text=_('Hold Ctrl/Cmd to select multiple vehicles (max 5)')
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Customize vehicle choices to show full description
        vehicle_choices = []
        for vehicle in self.fields['vehicles'].queryset[:500]:  # Limit for performance
            label = f"{vehicle.base_vehicle.year.year_id} {vehicle.base_vehicle.make.make_name} {vehicle.base_vehicle.model.model_name or 'Unknown'} {vehicle.submodel.sub_model_name}"
            vehicle_choices.append((vehicle.pk, label))

        self.fields['vehicles'].choices = vehicle_choices

    def clean_vehicles(self):
        vehicles = self.cleaned_data.get('vehicles')
        if vehicles and len(vehicles) > 5:
            raise ValidationError(_('You can compare a maximum of 5 vehicles at once.'))
        if vehicles and len(vehicles) < 2:
            raise ValidationError(_('Select at least 2 vehicles to compare.'))
        return vehicles


class BulkUpdateForm(forms.Form):
    """Form for bulk updating vehicle records."""

    ACTION_CHOICES = [
        ('', _('Select Action')),
        ('update_region', _('Update Region')),
        ('update_publication_stage', _('Update Publication Stage')),
        ('update_source', _('Update Source')),
        ('delete', _('Delete Selected')),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Action')
    )

    # Fields for updates
    new_region = forms.ModelChoiceField(
        queryset=Region.objects.filter(parent__isnull=False).order_by('region_name'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('New Region')
    )

    new_publication_stage = forms.ModelChoiceField(
        queryset=PublicationStage.objects.all().order_by('publication_stage_name'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('New Publication Stage')
    )

    new_source = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label=_('New Source')
    )

    confirm_delete = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('Confirm deletion (cannot be undone)')
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')

        if action == 'update_region' and not cleaned_data.get('new_region'):
            self.add_error('new_region', _('This field is required for the selected action.'))

        if action == 'update_publication_stage' and not cleaned_data.get('new_publication_stage'):
            self.add_error('new_publication_stage', _('This field is required for the selected action.'))

        if action == 'update_source' and not cleaned_data.get('new_source'):
            self.add_error('new_source', _('This field is required for the selected action.'))

        if action == 'delete' and not cleaned_data.get('confirm_delete'):
            self.add_error('confirm_delete', _('You must confirm deletion.'))

        return cleaned_data


class DataImportForm(forms.Form):
    """Form for importing vehicle data."""

    IMPORT_FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('json', 'JSON'),
    ]

    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls,.json'
        }),
        label=_('Data File'),
        help_text=_('Upload a CSV, Excel, or JSON file with vehicle data.')
    )

    format = forms.ChoiceField(
        choices=IMPORT_FORMAT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('File Format')
    )

    update_existing = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('Update Existing Records'),
        help_text=_('If checked, existing records will be updated. Otherwise, only new records will be created.')
    )

    skip_errors = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('Skip Errors'),
        help_text=_('Continue processing even if some records have errors.')
    )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Basic file validation
            max_size = 50 * 1024 * 1024  # 50MB
            if file.size > max_size:
                raise ValidationError(_('File size cannot exceed 50MB.'))

            # Check file extension
            allowed_extensions = ['.csv', '.xlsx', '.xls', '.json']
            file_extension = file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise ValidationError(_('Invalid file format. Please upload a CSV, Excel, or JSON file.'))

        return file