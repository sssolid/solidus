# src/autocare_vcdb/serializers.py
"""
Django REST Framework serializers for automotive models.
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from autocare_vcdb.models import (
    # Basic models
    Make, Model, Year, BaseVehicle, SubModel, Region, Vehicle,

    # Engine models
    EngineBase, EngineConfig, FuelType, Aspiration, CylinderHeadType,
    IgnitionSystemType, Mfr, EngineDesignation, EngineVIN, EngineVersion,
    Valves, PowerOutput,

    # Transmission models
    Transmission, TransmissionBase, TransmissionType, TransmissionNumSpeeds,
    TransmissionControlType,

    # Other system models
    BodyStyleConfig, BodyType, BodyNumDoors, BrakeConfig, BrakeType,
    BrakeSystem, BrakeABS, DriveType, SteeringConfig, SpringTypeConfig,
    BedConfig, Class,

    # Relationship models
    VehicleToEngineConfig, VehicleToTransmission, VehicleToDriveType, PublicationStage,
)


class BaseAutomotiveSerializer(serializers.ModelSerializer):
    """Base serializer with audit fields."""
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    updated_by = serializers.StringRelatedField(read_only=True)


# Basic reference serializers
class MakeSerializer(BaseAutomotiveSerializer):
    """Serializer for vehicle makes."""
    vehicle_count = serializers.SerializerMethodField()

    class Meta:
        model = Make
        fields = ['make_id', 'make_name', 'vehicle_count', 'created_at', 'updated_at']
        read_only_fields = ['make_id', 'created_at', 'updated_at']

    def get_vehicle_count(self, obj):
        return obj.base_vehicles.aggregate(
            count=serializers.Count('vehicles')
        )['count'] or 0


class ModelSerializer(BaseAutomotiveSerializer):
    """Serializer for vehicle models."""
    vehicle_type_name = serializers.CharField(
        source='vehicle_type.vehicle_type_name',
        read_only=True
    )

    class Meta:
        model = Model
        fields = [
            'model_id', 'model_name', 'vehicle_type', 'vehicle_type_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['model_id', 'created_at', 'updated_at']


class YearSerializer(BaseAutomotiveSerializer):
    """Serializer for model years."""
    vehicle_count = serializers.SerializerMethodField()

    class Meta:
        model = Year
        fields = ['year_id', 'vehicle_count', 'created_at', 'updated_at']
        read_only_fields = ['year_id', 'created_at', 'updated_at']

    def get_vehicle_count(self, obj):
        return obj.base_vehicles.aggregate(
            count=serializers.Count('vehicles')
        )['count'] or 0


class BaseVehicleSerializer(BaseAutomotiveSerializer):
    """Serializer for base vehicles."""
    year_display = serializers.CharField(source='year.year_id', read_only=True)
    make_name = serializers.CharField(source='make.make_name', read_only=True)
    model_name = serializers.CharField(source='model.model_name', read_only=True)
    vehicle_count = serializers.SerializerMethodField()

    class Meta:
        model = BaseVehicle
        fields = [
            'base_vehicle_id', 'year', 'year_display', 'make', 'make_name',
            'model', 'model_name', 'vehicle_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['base_vehicle_id', 'created_at', 'updated_at']

    def get_vehicle_count(self, obj):
        return obj.vehicles.count()


class SubModelSerializer(BaseAutomotiveSerializer):
    """Serializer for sub-models."""

    class Meta:
        model = SubModel
        fields = ['sub_model_id', 'sub_model_name', 'created_at', 'updated_at']
        read_only_fields = ['sub_model_id', 'created_at', 'updated_at']


class RegionSerializer(BaseAutomotiveSerializer):
    """Serializer for regions."""
    parent_name = serializers.CharField(source='parent.region_name', read_only=True)

    class Meta:
        model = Region
        fields = [
            'region_id', 'parent', 'parent_name', 'region_abbr',
            'region_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['region_id', 'created_at', 'updated_at']


# Engine-related serializers
class EngineBaseSerializer(BaseAutomotiveSerializer):
    """Serializer for engine base specifications."""
    displacement_display = serializers.SerializerMethodField()

    class Meta:
        model = EngineBase
        fields = [
            'engine_base_id', 'liter', 'cc', 'cid', 'cylinders', 'block_type',
            'eng_bore_in', 'eng_bore_metric', 'eng_stroke_in', 'eng_stroke_metric',
            'displacement_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ['engine_base_id', 'created_at', 'updated_at']

    def get_displacement_display(self, obj):
        return f"{obj.liter}L {obj.cylinders}cyl"


class FuelTypeSerializer(BaseAutomotiveSerializer):
    """Serializer for fuel types."""

    class Meta:
        model = FuelType
        fields = ['fuel_type_id', 'fuel_type_name', 'created_at', 'updated_at']
        read_only_fields = ['fuel_type_id', 'created_at', 'updated_at']


class AspirationSerializer(BaseAutomotiveSerializer):
    """Serializer for aspiration types."""

    class Meta:
        model = Aspiration
        fields = ['aspiration_id', 'aspiration_name', 'created_at', 'updated_at']
        read_only_fields = ['aspiration_id', 'created_at', 'updated_at']


class PowerOutputSerializer(BaseAutomotiveSerializer):
    """Serializer for power output specifications."""

    class Meta:
        model = PowerOutput
        fields = ['power_output_id', 'horse_power', 'kilowatt_power', 'created_at', 'updated_at']
        read_only_fields = ['power_output_id', 'created_at', 'updated_at']


class EngineConfigSerializer(BaseAutomotiveSerializer):
    """Serializer for complete engine configurations."""
    engine_base_display = serializers.CharField(source='engine_base.__str__', read_only=True)
    fuel_type_name = serializers.CharField(source='fuel_type.fuel_type_name', read_only=True)
    aspiration_name = serializers.CharField(source='aspiration.aspiration_name', read_only=True)
    power_output_display = serializers.CharField(source='power_output.__str__', read_only=True)
    engine_mfr_name = serializers.CharField(source='engine_mfr.mfr_name', read_only=True)

    class Meta:
        model = EngineConfig
        fields = [
            'engine_config_id', 'engine_designation', 'engine_vin', 'valves',
            'engine_base', 'engine_base_display', 'fuel_delivery_config',
            'aspiration', 'aspiration_name', 'cylinder_head_type',
            'fuel_type', 'fuel_type_name', 'ignition_system_type',
            'engine_mfr', 'engine_mfr_name', 'engine_version',
            'power_output', 'power_output_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['engine_config_id', 'created_at', 'updated_at']


# Transmission serializers
class TransmissionTypeSerializer(BaseAutomotiveSerializer):
    """Serializer for transmission types."""

    class Meta:
        model = TransmissionType
        fields = ['transmission_type_id', 'transmission_type_name', 'created_at', 'updated_at']
        read_only_fields = ['transmission_type_id', 'created_at', 'updated_at']


class TransmissionNumSpeedsSerializer(BaseAutomotiveSerializer):
    """Serializer for transmission speed counts."""

    class Meta:
        model = TransmissionNumSpeeds
        fields = ['transmission_num_speeds_id', 'transmission_num_speeds', 'created_at', 'updated_at']
        read_only_fields = ['transmission_num_speeds_id', 'created_at', 'updated_at']


class TransmissionBaseSerializer(BaseAutomotiveSerializer):
    """Serializer for transmission base configurations."""
    transmission_type_name = serializers.CharField(
        source='transmission_type.transmission_type_name', read_only=True
    )
    speeds_display = serializers.CharField(
        source='transmission_num_speeds.__str__', read_only=True
    )

    class Meta:
        model = TransmissionBase
        fields = [
            'transmission_base_id', 'transmission_type', 'transmission_type_name',
            'transmission_num_speeds', 'speeds_display', 'transmission_control_type',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['transmission_base_id', 'created_at', 'updated_at']


class TransmissionSerializer(BaseAutomotiveSerializer):
    """Serializer for complete transmission configurations."""
    transmission_base_display = serializers.CharField(
        source='transmission_base.__str__', read_only=True
    )
    transmission_mfr_name = serializers.CharField(
        source='transmission_mfr.mfr_name', read_only=True
    )

    class Meta:
        model = Transmission
        fields = [
            'transmission_id', 'transmission_base', 'transmission_base_display',
            'transmission_mfr_code', 'transmission_elec_controlled',
            'transmission_mfr', 'transmission_mfr_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['transmission_id', 'created_at', 'updated_at']


# Other system serializers
class DriveTypeSerializer(BaseAutomotiveSerializer):
    """Serializer for drive types."""

    class Meta:
        model = DriveType
        fields = ['drive_type_id', 'drive_type_name', 'created_at', 'updated_at']
        read_only_fields = ['drive_type_id', 'created_at', 'updated_at']


class BodyTypeSerializer(BaseAutomotiveSerializer):
    """Serializer for body types."""

    class Meta:
        model = BodyType
        fields = ['body_type_id', 'body_type_name', 'created_at', 'updated_at']
        read_only_fields = ['body_type_id', 'created_at', 'updated_at']


class BodyStyleConfigSerializer(BaseAutomotiveSerializer):
    """Serializer for body style configurations."""
    body_type_name = serializers.CharField(source='body_type.body_type_name', read_only=True)
    doors_display = serializers.CharField(source='body_num_doors.__str__', read_only=True)

    class Meta:
        model = BodyStyleConfig
        fields = [
            'body_style_config_id', 'body_num_doors', 'doors_display',
            'body_type', 'body_type_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['body_style_config_id', 'created_at', 'updated_at']


class ClassSerializer(BaseAutomotiveSerializer):
    """Serializer for vehicle classes."""

    class Meta:
        model = Class
        fields = ['class_id', 'class_name', 'created_at', 'updated_at']
        read_only_fields = ['class_id', 'created_at', 'updated_at']


# Vehicle relationship serializers
class VehicleToEngineConfigSerializer(BaseAutomotiveSerializer):
    """Serializer for vehicle-to-engine relationships."""
    engine_config_display = serializers.CharField(
        source='engine_config.__str__', read_only=True
    )

    class Meta:
        model = VehicleToEngineConfig
        fields = [
            'vehicle_to_engine_config_id', 'vehicle', 'engine_config',
            'engine_config_display', 'source', 'created_at', 'updated_at'
        ]
        read_only_fields = ['vehicle_to_engine_config_id', 'created_at', 'updated_at']


class VehicleToTransmissionSerializer(BaseAutomotiveSerializer):
    """Serializer for vehicle-to-transmission relationships."""
    transmission_display = serializers.CharField(
        source='transmission.__str__', read_only=True
    )

    class Meta:
        model = VehicleToTransmission
        fields = [
            'vehicle_to_transmission_id', 'vehicle', 'transmission',
            'transmission_display', 'source', 'created_at', 'updated_at'
        ]
        read_only_fields = ['vehicle_to_transmission_id', 'created_at', 'updated_at']


class VehicleToDriveTypeSerializer(BaseAutomotiveSerializer):
    """Serializer for vehicle-to-drive-type relationships."""
    drive_type_name = serializers.CharField(
        source='drive_type.drive_type_name', read_only=True
    )

    class Meta:
        model = VehicleToDriveType
        fields = [
            'vehicle_to_drive_type_id', 'vehicle', 'drive_type',
            'drive_type_name', 'source', 'created_at', 'updated_at'
        ]
        read_only_fields = ['vehicle_to_drive_type_id', 'created_at', 'updated_at']


# Main Vehicle serializer
class VehicleListSerializer(BaseAutomotiveSerializer):
    """Serializer for vehicle list view."""
    year = serializers.CharField(source='base_vehicle.year.year_id', read_only=True)
    make_name = serializers.CharField(source='base_vehicle.make.make_name', read_only=True)
    model_name = serializers.CharField(source='base_vehicle.model.model_name', read_only=True)
    submodel_name = serializers.CharField(source='submodel.sub_model_name', read_only=True)
    region_name = serializers.CharField(source='region.region_name', read_only=True)
    publication_stage_name = serializers.CharField(
        source='publication_stage.publication_stage_name', read_only=True
    )

    class Meta:
        model = Vehicle
        fields = [
            'vehicle_id', 'year', 'make_name', 'model_name', 'submodel_name',
            'region_name', 'source', 'publication_stage_name',
            'publication_stage_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['vehicle_id', 'created_at', 'updated_at']


class VehicleDetailSerializer(BaseAutomotiveSerializer):
    """Detailed serializer for individual vehicles."""
    base_vehicle = BaseVehicleSerializer(read_only=True)
    submodel = SubModelSerializer(read_only=True)
    region = RegionSerializer(read_only=True)

    # Related configurations
    engine_configs = VehicleToEngineConfigSerializer(many=True, read_only=True)
    transmissions = VehicleToTransmissionSerializer(many=True, read_only=True)
    drive_types = VehicleToDriveTypeSerializer(many=True, read_only=True)

    # Summary fields
    primary_engine = serializers.SerializerMethodField()
    primary_transmission = serializers.SerializerMethodField()
    primary_drive_type = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            'vehicle_id', 'base_vehicle', 'submodel', 'region', 'source',
            'publication_stage', 'publication_stage_source', 'publication_stage_date',
            'engine_configs', 'transmissions', 'drive_types',
            'primary_engine', 'primary_transmission', 'primary_drive_type',
            'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['vehicle_id', 'created_at', 'updated_at', 'created_by', 'updated_by']

    def get_primary_engine(self, obj):
        """Get the primary engine configuration."""
        engine_config = obj.engine_configs.first()
        if engine_config:
            return EngineConfigSerializer(engine_config.engine_config).data
        return None

    def get_primary_transmission(self, obj):
        """Get the primary transmission."""
        transmission = obj.transmissions.first()
        if transmission:
            return TransmissionSerializer(transmission.transmission).data
        return None

    def get_primary_drive_type(self, obj):
        """Get the primary drive type."""
        drive_type = obj.drive_types.first()
        if drive_type:
            return DriveTypeSerializer(drive_type.drive_type).data
        return None


class VehicleCreateUpdateSerializer(BaseAutomotiveSerializer):
    """Serializer for creating and updating vehicles."""

    class Meta:
        model = Vehicle
        fields = [
            'base_vehicle', 'submodel', 'region', 'source',
            'publication_stage', 'publication_stage_source'
        ]

    def validate(self, data):
        """Custom validation for vehicle data."""
        # Check for duplicate vehicle combinations
        if self.instance:
            # Updating existing vehicle
            existing = Vehicle.objects.filter(
                base_vehicle=data.get('base_vehicle', self.instance.base_vehicle),
                submodel=data.get('submodel', self.instance.submodel),
                region=data.get('region', self.instance.region)
            ).exclude(pk=self.instance.pk)
        else:
            # Creating new vehicle
            existing = Vehicle.objects.filter(
                base_vehicle=data['base_vehicle'],
                submodel=data['submodel'],
                region=data['region']
            )

        if existing.exists():
            raise serializers.ValidationError(
                _('A vehicle with this base vehicle, submodel, and region already exists.')
            )

        return data


# Statistics serializers
class VehicleStatsSerializer(serializers.Serializer):
    """Serializer for vehicle statistics."""
    total_vehicles = serializers.IntegerField()
    total_makes = serializers.IntegerField()
    total_models = serializers.IntegerField()
    total_years = serializers.IntegerField()

    vehicles_by_year = serializers.ListField(
        child=serializers.DictField(), read_only=True
    )
    top_makes = serializers.ListField(
        child=serializers.DictField(), read_only=True
    )
    engine_stats = serializers.DictField(read_only=True)
    regional_stats = serializers.ListField(
        child=serializers.DictField(), read_only=True
    )


class SearchResultSerializer(serializers.Serializer):
    """Serializer for search results."""
    query = serializers.CharField()
    total_results = serializers.IntegerField()
    page = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    results = VehicleListSerializer(many=True)

    # Search metadata
    filters_applied = serializers.DictField(read_only=True)
    search_time_ms = serializers.FloatField(read_only=True)
    suggestions = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )


# Bulk operation serializers
class BulkUpdateSerializer(serializers.Serializer):
    """Serializer for bulk update operations."""
    vehicle_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text=_('List of vehicle IDs to update')
    )
    action = serializers.ChoiceField(choices=[
        ('update_region', _('Update Region')),
        ('update_publication_stage', _('Update Publication Stage')),
        ('update_source', _('Update Source')),
    ])

    # Update fields
    new_region = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.all(), required=False
    )
    new_publication_stage = serializers.PrimaryKeyRelatedField(
        queryset=PublicationStage.objects.all(), required=False
    )
    new_source = serializers.CharField(max_length=10, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, data):
        action = data.get('action')

        if action == 'update_region' and not data.get('new_region'):
            raise serializers.ValidationError({
                'new_region': _('This field is required for the selected action.')
            })

        if action == 'update_publication_stage' and not data.get('new_publication_stage'):
            raise serializers.ValidationError({
                'new_publication_stage': _('This field is required for the selected action.')
            })

        if action == 'update_source' and not data.get('new_source'):
            raise serializers.ValidationError({
                'new_source': _('This field is required for the selected action.')
            })

        return data


class ImportResultSerializer(serializers.Serializer):
    """Serializer for data import results."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    total_records = serializers.IntegerField()
    successful_imports = serializers.IntegerField()
    failed_imports = serializers.IntegerField()
    errors = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    warnings = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    processing_time_seconds = serializers.FloatField()