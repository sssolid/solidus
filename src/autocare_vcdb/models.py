# src/autocare/models/vcdb.py
"""
Automotive models for vehicle configuration and specifications.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from audit.mixins import AuditMixin

User = get_user_model()


class Abbreviation(AuditMixin, models.Model):
    """Standard abbreviations used throughout the system."""
    abbreviation = models.CharField(max_length=3, primary_key=True)
    description = models.CharField(max_length=20)
    long_description = models.CharField(max_length=200)

    class Meta:
        db_table = 'vcdb_abbreviation'
        ordering = ['abbreviation']
        verbose_name = _('Abbreviation')
        verbose_name_plural = _('Abbreviations')

    def __str__(self):
        return f"{self.abbreviation} - {self.description}"


class Aspiration(AuditMixin, models.Model):
    """Engine aspiration types (naturally aspirated, turbocharged, etc.)."""
    aspiration_id = models.IntegerField(primary_key=True)
    aspiration_name = models.CharField(max_length=30)

    class Meta:
        db_table = 'vcdb_aspiration'
        ordering = ['aspiration_name']
        verbose_name = _('Aspiration')
        verbose_name_plural = _('Aspirations')

    def __str__(self):
        return self.aspiration_name


class AttachmentType(AuditMixin, models.Model):
    """Types of attachments that can be associated with records."""
    attachment_type_name = models.CharField(max_length=20, unique=True)

    class Meta:
        db_table = 'vcdb_attachment_type'
        ordering = ['attachment_type_name']
        verbose_name = _('Attachment Type')
        verbose_name_plural = _('Attachment Types')

    def __str__(self):
        return self.attachment_type_name


class Attachment(AuditMixin, models.Model):
    """File attachments for various entities."""
    attachment_type = models.ForeignKey(
        AttachmentType,
        on_delete=models.PROTECT,
        related_name='attachments'
    )
    attachment_file_name = models.CharField(max_length=50)
    attachment_url = models.URLField(max_length=100)
    attachment_description = models.CharField(max_length=50)

    class Meta:
        db_table = 'vcdb_attachment'
        ordering = ['attachment_file_name']
        verbose_name = _('Attachment')
        verbose_name_plural = _('Attachments')
        indexes = [
            models.Index(fields=['attachment_type']),
            models.Index(fields=['attachment_file_name']),
        ]

    def __str__(self):
        return f"{self.attachment_file_name} ({self.attachment_type})"


class Make(AuditMixin, models.Model):
    """Vehicle manufacturers/makes."""
    make_id = models.IntegerField(primary_key=True)
    make_name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'vcdb_make'
        ordering = ['make_name']
        verbose_name = _('Make')
        verbose_name_plural = _('Makes')
        indexes = [
            models.Index(fields=['make_name']),
        ]

    def __str__(self):
        return self.make_name


class VehicleTypeGroup(AuditMixin, models.Model):
    """Groups of vehicle types for organization."""
    vehicle_type_group_id = models.IntegerField(primary_key=True)
    vehicle_type_group_name = models.CharField(max_length=50)

    class Meta:
        db_table = 'vcdb_vehicle_type_group'
        ordering = ['vehicle_type_group_name']
        verbose_name = _('Vehicle Type Group')
        verbose_name_plural = _('Vehicle Type Groups')

    def __str__(self):
        return self.vehicle_type_group_name


class VehicleType(AuditMixin, models.Model):
    """Types of vehicles (car, truck, SUV, etc.)."""
    vehicle_type_id = models.IntegerField(primary_key=True)
    vehicle_type_name = models.CharField(max_length=50)
    vehicle_type_group = models.ForeignKey(
        VehicleTypeGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicle_types'
    )

    class Meta:
        db_table = 'vcdb_vehicle_type'
        ordering = ['vehicle_type_name']
        verbose_name = _('Vehicle Type')
        verbose_name_plural = _('Vehicle Types')
        indexes = [
            models.Index(fields=['vehicle_type_group']),
        ]

    def __str__(self):
        return self.vehicle_type_name


class Model(AuditMixin, models.Model):
    """Vehicle models."""
    model_id = models.IntegerField(primary_key=True)
    model_name = models.CharField(max_length=100, null=True, blank=True)
    vehicle_type = models.ForeignKey(
        VehicleType,
        on_delete=models.PROTECT,
        related_name='models'
    )

    class Meta:
        db_table = 'vcdb_model'
        ordering = ['model_name']
        verbose_name = _('Model')
        verbose_name_plural = _('Models')
        indexes = [
            models.Index(fields=['vehicle_type']),
            models.Index(fields=['model_name']),
        ]

    def __str__(self):
        return self.model_name or f"Model {self.model_id}"


class Year(AuditMixin, models.Model):
    """Model years for vehicles."""
    year_id = models.IntegerField(primary_key=True)

    class Meta:
        db_table = 'vcdb_year'
        ordering = ['-year_id']
        verbose_name = _('Year')
        verbose_name_plural = _('Years')

    def __str__(self):
        return str(self.year_id)


class BaseVehicle(AuditMixin, models.Model):
    """Base vehicle configurations combining year, make, and model."""
    base_vehicle_id = models.IntegerField(primary_key=True)
    year = models.ForeignKey(Year, on_delete=models.PROTECT, related_name='base_vehicles')
    make = models.ForeignKey(Make, on_delete=models.PROTECT, related_name='base_vehicles')
    model = models.ForeignKey(Model, on_delete=models.PROTECT, related_name='base_vehicles')

    class Meta:
        db_table = 'vcdb_base_vehicle'
        ordering = ['-year__year_id', 'make__make_name', 'model__model_name']
        verbose_name = _('Base Vehicle')
        verbose_name_plural = _('Base Vehicles')
        indexes = [
            models.Index(fields=['year']),
            models.Index(fields=['make']),
            models.Index(fields=['model']),
            models.Index(fields=['year', 'make', 'model']),
        ]

    def __str__(self):
        return f"{self.year} {self.make} {self.model}"


class SubModel(AuditMixin, models.Model):
    """Vehicle sub-models and trim levels."""
    sub_model_id = models.IntegerField(primary_key=True)
    sub_model_name = models.CharField(max_length=50)

    class Meta:
        db_table = 'vcdb_sub_model'
        ordering = ['sub_model_name']
        verbose_name = _('Sub Model')
        verbose_name_plural = _('Sub Models')
        indexes = [
            models.Index(fields=['sub_model_name']),
        ]

    def __str__(self):
        return self.sub_model_name


class Region(AuditMixin, models.Model):
    """Geographic regions and markets."""
    region_id = models.IntegerField(primary_key=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    region_abbr = models.CharField(max_length=3, null=True, blank=True)
    region_name = models.CharField(max_length=30, null=True, blank=True)

    class Meta:
        db_table = 'vcdb_region'
        ordering = ['region_name']
        verbose_name = _('Region')
        verbose_name_plural = _('Regions')
        indexes = [
            models.Index(fields=['parent']),
            models.Index(fields=['region_abbr']),
        ]

    def __str__(self):
        return self.region_name or f"Region {self.region_id}"


class PublicationStage(AuditMixin, models.Model):
    """Publication stages for data lifecycle management."""
    publication_stage_id = models.IntegerField(primary_key=True)
    publication_stage_name = models.CharField(max_length=100)

    class Meta:
        db_table = 'vcdb_publication_stage'
        ordering = ['publication_stage_name']
        verbose_name = _('Publication Stage')
        verbose_name_plural = _('Publication Stages')

    def __str__(self):
        return self.publication_stage_name


class Vehicle(AuditMixin, models.Model):
    """Complete vehicle configurations."""
    vehicle_id = models.IntegerField(primary_key=True)
    base_vehicle = models.ForeignKey(
        BaseVehicle,
        on_delete=models.PROTECT,
        related_name='vehicles'
    )
    submodel = models.ForeignKey(
        SubModel,
        on_delete=models.PROTECT,
        related_name='vehicles'
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name='vehicles'
    )
    source = models.CharField(max_length=10, null=True, blank=True)
    publication_stage = models.ForeignKey(
        PublicationStage,
        on_delete=models.PROTECT,
        default=4,
        related_name='vehicles'
    )
    publication_stage_source = models.CharField(max_length=100)
    publication_stage_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vcdb_vehicle'
        ordering = ['-base_vehicle__year__year_id', 'base_vehicle__make__make_name']
        verbose_name = _('Vehicle')
        verbose_name_plural = _('Vehicles')
        indexes = [
            models.Index(fields=['base_vehicle']),
            models.Index(fields=['submodel']),
            models.Index(fields=['region']),
            models.Index(fields=['publication_stage']),
            models.Index(fields=['publication_stage_date']),
        ]

    def __str__(self):
        return f"{self.base_vehicle} {self.submodel}"


# Engine-related models
class EngineBase(AuditMixin, models.Model):
    """Base engine specifications."""
    engine_base_id = models.IntegerField(primary_key=True)
    liter = models.CharField(max_length=6)
    cc = models.CharField(max_length=8)
    cid = models.CharField(max_length=7)
    cylinders = models.CharField(max_length=2)
    block_type = models.CharField(max_length=2)
    eng_bore_in = models.CharField(max_length=10)
    eng_bore_metric = models.CharField(max_length=10)
    eng_stroke_in = models.CharField(max_length=10)
    eng_stroke_metric = models.CharField(max_length=10)

    class Meta:
        db_table = 'vcdb_engine_base'
        ordering = ['liter', 'cylinders']
        verbose_name = _('Engine Base')
        verbose_name_plural = _('Engine Bases')
        indexes = [
            models.Index(fields=['liter']),
            models.Index(fields=['cc']),
            models.Index(fields=['cid']),
            models.Index(fields=['cylinders']),
            models.Index(fields=['block_type']),
        ]

    def __str__(self):
        return f"{self.liter}L {self.cylinders}cyl"


class CylinderHeadType(AuditMixin, models.Model):
    """Cylinder head configurations."""
    cylinder_head_type_id = models.IntegerField(primary_key=True)
    cylinder_head_type_name = models.CharField(max_length=30)

    class Meta:
        db_table = 'vcdb_cylinder_head_type'
        ordering = ['cylinder_head_type_name']
        verbose_name = _('Cylinder Head Type')
        verbose_name_plural = _('Cylinder Head Types')

    def __str__(self):
        return self.cylinder_head_type_name


class FuelType(AuditMixin, models.Model):
    """Types of fuel used by engines."""
    fuel_type_id = models.IntegerField(primary_key=True)
    fuel_type_name = models.CharField(max_length=100)

    class Meta:
        db_table = 'vcdb_fuel_type'
        ordering = ['fuel_type_name']
        verbose_name = _('Fuel Type')
        verbose_name_plural = _('Fuel Types')

    def __str__(self):
        return self.fuel_type_name


class FuelDeliveryType(AuditMixin, models.Model):
    """Primary fuel delivery methods."""
    fuel_delivery_type_id = models.IntegerField(primary_key=True)
    fuel_delivery_type_name = models.CharField(max_length=50)

    class Meta:
        db_table = 'vcdb_fuel_delivery_type'
        ordering = ['fuel_delivery_type_name']
        verbose_name = _('Fuel Delivery Type')
        verbose_name_plural = _('Fuel Delivery Types')

    def __str__(self):
        return self.fuel_delivery_type_name


class FuelDeliverySubType(AuditMixin, models.Model):
    """Fuel delivery sub-types."""
    fuel_delivery_sub_type_id = models.IntegerField(primary_key=True)
    fuel_delivery_sub_type_name = models.CharField(max_length=50)

    class Meta:
        db_table = 'vcdb_fuel_delivery_sub_type'
        ordering = ['fuel_delivery_sub_type_name']
        verbose_name = _('Fuel Delivery Sub Type')
        verbose_name_plural = _('Fuel Delivery Sub Types')

    def __str__(self):
        return self.fuel_delivery_sub_type_name


class FuelSystemControlType(AuditMixin, models.Model):
    """Fuel system control methods."""
    fuel_system_control_type_id = models.IntegerField(primary_key=True)
    fuel_system_control_type_name = models.CharField(max_length=50)

    class Meta:
        db_table = 'vcdb_fuel_system_control_type'
        ordering = ['fuel_system_control_type_name']
        verbose_name = _('Fuel System Control Type')
        verbose_name_plural = _('Fuel System Control Types')

    def __str__(self):
        return self.fuel_system_control_type_name


class FuelSystemDesign(AuditMixin, models.Model):
    """Fuel system designs."""
    fuel_system_design_id = models.IntegerField(primary_key=True)
    fuel_system_design_name = models.CharField(max_length=50)

    class Meta:
        db_table = 'vcdb_fuel_system_design'
        ordering = ['fuel_system_design_name']
        verbose_name = _('Fuel System Design')
        verbose_name_plural = _('Fuel System Designs')

    def __str__(self):
        return self.fuel_system_design_name


class FuelDeliveryConfig(AuditMixin, models.Model):
    """Complete fuel delivery system configurations."""
    fuel_delivery_config_id = models.IntegerField(primary_key=True)
    fuel_delivery_type = models.ForeignKey(
        FuelDeliveryType,
        on_delete=models.PROTECT,
        related_name='configs'
    )
    fuel_delivery_sub_type = models.ForeignKey(
        FuelDeliverySubType,
        on_delete=models.PROTECT,
        related_name='configs'
    )
    fuel_system_control_type = models.ForeignKey(
        FuelSystemControlType,
        on_delete=models.PROTECT,
        related_name='configs'
    )
    fuel_system_design = models.ForeignKey(
        FuelSystemDesign,
        on_delete=models.PROTECT,
        related_name='configs'
    )

    class Meta:
        db_table = 'vcdb_fuel_delivery_config'
        ordering = ['fuel_delivery_type__fuel_delivery_type_name']
        verbose_name = _('Fuel Delivery Config')
        verbose_name_plural = _('Fuel Delivery Configs')
        indexes = [
            models.Index(fields=['fuel_delivery_type']),
            models.Index(fields=['fuel_delivery_sub_type']),
            models.Index(fields=['fuel_system_control_type']),
            models.Index(fields=['fuel_system_design']),
        ]

    def __str__(self):
        return f"{self.fuel_delivery_type} - {self.fuel_delivery_sub_type}"


class IgnitionSystemType(AuditMixin, models.Model):
    """Ignition system types."""
    ignition_system_type_id = models.IntegerField(primary_key=True)
    ignition_system_type_name = models.CharField(max_length=30)

    class Meta:
        db_table = 'vcdb_ignition_system_type'
        ordering = ['ignition_system_type_name']
        verbose_name = _('Ignition System Type')
        verbose_name_plural = _('Ignition System Types')

    def __str__(self):
        return self.ignition_system_type_name


class Mfr(AuditMixin, models.Model):
    """Manufacturers (different from Makes - these are component manufacturers)."""
    mfr_id = models.IntegerField(primary_key=True)
    mfr_name = models.CharField(max_length=30)

    class Meta:
        db_table = 'vcdb_mfr'
        ordering = ['mfr_name']
        verbose_name = _('Manufacturer')
        verbose_name_plural = _('Manufacturers')
        indexes = [
            models.Index(fields=['mfr_name']),
        ]

    def __str__(self):
        return self.mfr_name


class EngineDesignation(AuditMixin, models.Model):
    """Engine designation codes."""
    engine_designation_id = models.IntegerField(primary_key=True)
    engine_designation_name = models.CharField(max_length=30)

    class Meta:
        db_table = 'vcdb_engine_designation'
        ordering = ['engine_designation_name']
        verbose_name = _('Engine Designation')
        verbose_name_plural = _('Engine Designations')

    def __str__(self):
        return self.engine_designation_name


class EngineVin(AuditMixin, models.Model):
    """Engine VIN codes."""
    engine_vin_id = models.IntegerField(primary_key=True)
    engine_vin_name = models.CharField(max_length=5)

    class Meta:
        db_table = 'vcdb_engine_vin'
        ordering = ['engine_vin_name']
        verbose_name = _('Engine VIN')
        verbose_name_plural = _('Engine VINs')

    def __str__(self):
        return self.engine_vin_name


class EngineVersion(AuditMixin, models.Model):
    """Engine versions."""
    engine_version_id = models.IntegerField(primary_key=True)
    engine_version = models.CharField(max_length=20)

    class Meta:
        db_table = 'vcdb_engine_version'
        ordering = ['engine_version']
        verbose_name = _('Engine Version')
        verbose_name_plural = _('Engine Versions')

    def __str__(self):
        return self.engine_version


class Valves(AuditMixin, models.Model):
    """Valve configurations."""
    valves_id = models.IntegerField(primary_key=True)
    valves_per_engine = models.CharField(max_length=3)

    class Meta:
        db_table = 'vcdb_valves'
        ordering = ['valves_per_engine']
        verbose_name = _('Valves')
        verbose_name_plural = _('Valves')

    def __str__(self):
        return f"{self.valves_per_engine} valves"


class PowerOutput(AuditMixin, models.Model):
    """Engine power output specifications."""
    power_output_id = models.IntegerField(primary_key=True)
    horse_power = models.CharField(max_length=10)
    kilowatt_power = models.CharField(max_length=10)

    class Meta:
        db_table = 'vcdb_power_output'
        ordering = ['-horse_power']
        verbose_name = _('Power Output')
        verbose_name_plural = _('Power Outputs')

    def __str__(self):
        return f"{self.horse_power} HP / {self.kilowatt_power} kW"


class EngineConfig(AuditMixin, models.Model):
    """Complete engine configurations."""
    engine_config_id = models.IntegerField(primary_key=True)
    engine_designation = models.ForeignKey(
        EngineDesignation,
        on_delete=models.PROTECT,
        related_name='engine_configs'
    )
    engine_vin = models.ForeignKey(
        EngineVin,
        on_delete=models.PROTECT,
        related_name='engine_configs'
    )
    valves = models.ForeignKey(
        Valves,
        on_delete=models.PROTECT,
        related_name='engine_configs'
    )
    engine_base = models.ForeignKey(
        EngineBase,
        on_delete=models.PROTECT,
        related_name='engine_configs'
    )
    fuel_delivery_config = models.ForeignKey(
        FuelDeliveryConfig,
        on_delete=models.PROTECT,
        related_name='engine_configs'
    )
    aspiration = models.ForeignKey(
        Aspiration,
        on_delete=models.PROTECT,
        related_name='engine_configs'
    )
    cylinder_head_type = models.ForeignKey(
        CylinderHeadType,
        on_delete=models.PROTECT,
        related_name='engine_configs'
    )
    fuel_type = models.ForeignKey(
        FuelType,
        on_delete=models.PROTECT,
        related_name='engine_configs'
    )
    ignition_system_type = models.ForeignKey(
        IgnitionSystemType,
        on_delete=models.PROTECT,
        related_name='engine_configs'
    )
    engine_mfr = models.ForeignKey(
        Mfr,
        on_delete=models.PROTECT,
        related_name='engine_configs'
    )
    engine_version = models.ForeignKey(
        EngineVersion,
        on_delete=models.PROTECT,
        related_name='engine_configs'
    )
    power_output = models.ForeignKey(
        PowerOutput,
        on_delete=models.PROTECT,
        default=1,
        related_name='engine_configs'
    )

    class Meta:
        db_table = 'vcdb_engine_config'
        ordering = ['engine_base__liter', 'engine_base__cylinders']
        verbose_name = _('Engine Config')
        verbose_name_plural = _('Engine Configs')
        indexes = [
            models.Index(fields=['engine_designation']),
            models.Index(fields=['engine_vin']),
            models.Index(fields=['valves']),
            models.Index(fields=['engine_base']),
            models.Index(fields=['fuel_delivery_config']),
            models.Index(fields=['aspiration']),
            models.Index(fields=['cylinder_head_type']),
            models.Index(fields=['fuel_type']),
            models.Index(fields=['ignition_system_type']),
            models.Index(fields=['engine_mfr']),
            models.Index(fields=['engine_version']),
        ]

    def __str__(self):
        return f"{self.engine_base} {self.engine_designation}"


# Transmission-related models
class TransmissionType(AuditMixin, models.Model):
    """Transmission types (manual, automatic, etc.)."""
    transmission_type_id = models.IntegerField(primary_key=True)
    transmission_type_name = models.CharField(max_length=30)

    class Meta:
        db_table = 'vcdb_transmission_type'
        ordering = ['transmission_type_name']
        verbose_name = _('Transmission Type')
        verbose_name_plural = _('Transmission Types')

    def __str__(self):
        return self.transmission_type_name


class TransmissionNumSpeeds(AuditMixin, models.Model):
    """Number of transmission speeds."""
    transmission_num_speeds_id = models.IntegerField(primary_key=True)
    transmission_num_speeds = models.CharField(max_length=3)

    class Meta:
        db_table = 'vcdb_transmission_num_speeds'
        ordering = ['transmission_num_speeds']
        verbose_name = _('Transmission Num Speeds')
        verbose_name_plural = _('Transmission Num Speeds')

    def __str__(self):
        return f"{self.transmission_num_speeds} speeds"


class TransmissionControlType(AuditMixin, models.Model):
    """Transmission control types."""
    transmission_control_type_id = models.IntegerField(primary_key=True)
    transmission_control_type_name = models.CharField(max_length=30)

    class Meta:
        db_table = 'vcdb_transmission_control_type'
        ordering = ['transmission_control_type_name']
        verbose_name = _('Transmission Control Type')
        verbose_name_plural = _('Transmission Control Types')

    def __str__(self):
        return self.transmission_control_type_name


class TransmissionBase(AuditMixin, models.Model):
    """Base transmission configurations."""
    transmission_base_id = models.IntegerField(primary_key=True)
    transmission_type = models.ForeignKey(
        TransmissionType,
        on_delete=models.PROTECT,
        related_name='transmission_bases'
    )
    transmission_num_speeds = models.ForeignKey(
        TransmissionNumSpeeds,
        on_delete=models.PROTECT,
        related_name='transmission_bases'
    )
    transmission_control_type = models.ForeignKey(
        TransmissionControlType,
        on_delete=models.PROTECT,
        related_name='transmission_bases'
    )

    class Meta:
        db_table = 'vcdb_transmission_base'
        ordering = ['transmission_type__transmission_type_name']
        verbose_name = _('Transmission Base')
        verbose_name_plural = _('Transmission Bases')
        indexes = [
            models.Index(fields=['transmission_type']),
            models.Index(fields=['transmission_num_speeds']),
            models.Index(fields=['transmission_control_type']),
        ]

    def __str__(self):
        return f"{self.transmission_type} {self.transmission_num_speeds}"


class TransmissionMfrCode(AuditMixin, models.Model):
    """Transmission manufacturer codes."""
    transmission_mfr_code_id = models.IntegerField(primary_key=True)
    transmission_mfr_code = models.CharField(max_length=30)

    class Meta:
        db_table = 'vcdb_transmission_mfr_code'
        ordering = ['transmission_mfr_code']
        verbose_name = _('Transmission Mfr Code')
        verbose_name_plural = _('Transmission Mfr Codes')

    def __str__(self):
        return self.transmission_mfr_code


class ElecControlled(AuditMixin, models.Model):
    """Electronic control indicators."""
    elec_controlled_id = models.IntegerField(primary_key=True)
    elec_controlled = models.CharField(max_length=3)

    class Meta:
        db_table = 'vcdb_elec_controlled'
        ordering = ['elec_controlled']
        verbose_name = _('Electronic Controlled')
        verbose_name_plural = _('Electronic Controlled')

    def __str__(self):
        return self.elec_controlled


class Transmission(AuditMixin, models.Model):
    """Complete transmission configurations."""
    transmission_id = models.IntegerField(primary_key=True)
    transmission_base = models.ForeignKey(
        TransmissionBase,
        on_delete=models.PROTECT,
        related_name='transmissions'
    )
    transmission_mfr_code = models.ForeignKey(
        TransmissionMfrCode,
        on_delete=models.PROTECT,
        related_name='transmissions'
    )
    transmission_elec_controlled = models.ForeignKey(
        ElecControlled,
        on_delete=models.PROTECT,
        related_name='transmissions'
    )
    transmission_mfr = models.ForeignKey(
        Mfr,
        on_delete=models.PROTECT,
        related_name='transmissions'
    )

    class Meta:
        db_table = 'vcdb_transmission'
        ordering = ['transmission_base']
        verbose_name = _('Transmission')
        verbose_name_plural = _('Transmissions')
        indexes = [
            models.Index(fields=['transmission_base']),
            models.Index(fields=['transmission_mfr_code']),
            models.Index(fields=['transmission_mfr']),
        ]

    def __str__(self):
        return f"{self.transmission_base} ({self.transmission_mfr_code})"


# Body and styling models
class BodyType(AuditMixin, models.Model):
    """Vehicle body types."""
    body_type_id = models.IntegerField(primary_key=True)
    body_type_name = models.CharField(max_length=50)

    class Meta:
        db_table = 'vcdb_body_type'
        ordering = ['body_type_name']
        verbose_name = _('Body Type')
        verbose_name_plural = _('Body Types')

    def __str__(self):
        return self.body_type_name


class BodyNumDoors(AuditMixin, models.Model):
    """Number of doors configurations."""
    body_num_doors_id = models.IntegerField(primary_key=True)
    body_num_doors = models.CharField(max_length=3)

    class Meta:
        db_table = 'vcdb_body_num_doors'
        ordering = ['body_num_doors']
        verbose_name = _('Body Number of Doors')
        verbose_name_plural = _('Body Number of Doors')

    def __str__(self):
        return f"{self.body_num_doors} doors"


class BodyStyleConfig(AuditMixin, models.Model):
    """Body style configurations."""
    body_style_config_id = models.IntegerField(primary_key=True)
    body_num_doors = models.ForeignKey(
        BodyNumDoors,
        on_delete=models.PROTECT,
        related_name='body_style_configs'
    )
    body_type = models.ForeignKey(
        BodyType,
        on_delete=models.PROTECT,
        related_name='body_style_configs'
    )

    class Meta:
        db_table = 'vcdb_body_style_config'
        ordering = ['body_type__body_type_name']
        verbose_name = _('Body Style Config')
        verbose_name_plural = _('Body Style Configs')
        indexes = [
            models.Index(fields=['body_num_doors']),
            models.Index(fields=['body_type']),
        ]

    def __str__(self):
        return f"{self.body_type} {self.body_num_doors}"


class MfrBodyCode(AuditMixin, models.Model):
    """Manufacturer body codes."""
    mfr_body_code_id = models.IntegerField(primary_key=True)
    mfr_body_code_name = models.CharField(max_length=10)

    class Meta:
        db_table = 'vcdb_mfr_body_code'
        ordering = ['mfr_body_code_name']
        verbose_name = _('Mfr Body Code')
        verbose_name_plural = _('Mfr Body Codes')

    def __str__(self):
        return self.mfr_body_code_name


class WheelBase(AuditMixin, models.Model):
    """Wheelbase measurements."""
    wheel_base_id = models.IntegerField(primary_key=True)
    wheel_base = models.CharField(max_length=10)
    wheel_base_metric = models.CharField(max_length=10)

    class Meta:
        db_table = 'vcdb_wheel_base'
        ordering = ['wheel_base']
        verbose_name = _('Wheel Base')
        verbose_name_plural = _('Wheel Bases')

    def __str__(self):
        return f"{self.wheel_base} in / {self.wheel_base_metric} mm"


# Brake system models
class BrakeType(AuditMixin, models.Model):
    """Types of brakes."""
    brake_type_id = models.IntegerField(primary_key=True)
    brake_type_name = models.CharField(max_length=30)

    class Meta:
        db_table = 'vcdb_brake_type'
        ordering = ['brake_type_name']
        verbose_name = _('Brake Type')
        verbose_name_plural = _('Brake Types')

    def __str__(self):
        return self.brake_type_name


class BrakeSystem(AuditMixin, models.Model):
    """Brake system types."""
    brake_system_id = models.IntegerField(primary_key=True)
    brake_system_name = models.CharField(max_length=30)

    class Meta:
        db_table = 'vcdb_brake_system'
        ordering = ['brake_system_name']
        verbose_name = _('Brake System')
        verbose_name_plural = _('Brake Systems')

    def __str__(self):
        return self.brake_system_name


class BrakeAbs(AuditMixin, models.Model):
    """ABS brake configurations."""
    brake_abs_id = models.IntegerField(primary_key=True)
    brake_abs_name = models.CharField(max_length=30)

    class Meta:
        db_table = 'vcdb_brake_abs'
        ordering = ['brake_abs_name']
        verbose_name = _('Brake ABS')
        verbose_name_plural = _('Brake ABS')

    def __str__(self):
        return self.brake_abs_name


class BrakeConfig(AuditMixin, models.Model):
    """Complete brake system configurations."""
    brake_config_id = models.IntegerField(primary_key=True)
    front_brake_type = models.ForeignKey(
        BrakeType,
        on_delete=models.PROTECT,
        related_name='front_brake_configs'
    )
    rear_brake_type = models.ForeignKey(
        BrakeType,
        on_delete=models.PROTECT,
        related_name='rear_brake_configs'
    )
    brake_system = models.ForeignKey(
        BrakeSystem,
        on_delete=models.PROTECT,
        related_name='brake_configs'
    )
    brake_abs = models.ForeignKey(
        BrakeAbs,
        on_delete=models.PROTECT,
        related_name='brake_configs'
    )

    class Meta:
        db_table = 'vcdb_brake_config'
        ordering = ['brake_system__brake_system_name']
        verbose_name = _('Brake Config')
        verbose_name_plural = _('Brake Configs')
        indexes = [
            models.Index(fields=['front_brake_type']),
            models.Index(fields=['rear_brake_type']),
            models.Index(fields=['brake_system']),
            models.Index(fields=['brake_abs']),
        ]

    def __str__(self):
        return f"F: {self.front_brake_type} / R: {self.rear_brake_type}"


# Drive type
class DriveType(AuditMixin, models.Model):
    """Vehicle drive types (FWD, RWD, AWD, etc.)."""
    drive_type_id = models.IntegerField(primary_key=True)
    drive_type_name = models.CharField(max_length=30)

    class Meta:
        db_table = 'vcdb_drive_type'
        ordering = ['drive_type_name']
        verbose_name = _('Drive Type')
        verbose_name_plural = _('Drive Types')

    def __str__(self):
        return self.drive_type_name


# Steering system models
class SteeringType(AuditMixin, models.Model):
    """Steering types."""
    steering_type_id = models.IntegerField(primary_key=True)
    steering_type_name = models.CharField(max_length=30)

    class Meta:
        db_table = 'vcdb_steering_type'
        ordering = ['steering_type_name']
        verbose_name = _('Steering Type')
        verbose_name_plural = _('Steering Types')

    def __str__(self):
        return self.steering_type_name


class SteeringSystem(AuditMixin, models.Model):
    """Steering systems."""
    steering_system_id = models.IntegerField(primary_key=True)
    steering_system_name = models.CharField(max_length=30)

    class Meta:
        db_table = 'vcdb_steering_system'
        ordering = ['steering_system_name']
        verbose_name = _('Steering System')
        verbose_name_plural = _('Steering Systems')

    def __str__(self):
        return self.steering_system_name


class SteeringConfig(AuditMixin, models.Model):
    """Complete steering configurations."""
    steering_config_id = models.IntegerField(primary_key=True)
    steering_type = models.ForeignKey(
        SteeringType,
        on_delete=models.PROTECT,
        related_name='steering_configs'
    )
    steering_system = models.ForeignKey(
        SteeringSystem,
        on_delete=models.PROTECT,
        related_name='steering_configs'
    )

    class Meta:
        db_table = 'vcdb_steering_config'
        ordering = ['steering_type__steering_type_name']
        verbose_name = _('Steering Config')
        verbose_name_plural = _('Steering Configs')
        indexes = [
            models.Index(fields=['steering_type']),
            models.Index(fields=['steering_system']),
        ]

    def __str__(self):
        return f"{self.steering_type} - {self.steering_system}"


# Spring/suspension system models
class SpringType(AuditMixin, models.Model):
    """Spring/suspension types."""
    spring_type_id = models.IntegerField(primary_key=True)
    spring_type_name = models.CharField(max_length=50)

    class Meta:
        db_table = 'vcdb_spring_type'
        ordering = ['spring_type_name']
        verbose_name = _('Spring Type')
        verbose_name_plural = _('Spring Types')

    def __str__(self):
        return self.spring_type_name


class SpringTypeConfig(AuditMixin, models.Model):
    """Complete spring/suspension configurations."""
    spring_type_config_id = models.IntegerField(primary_key=True)
    front_spring_type = models.ForeignKey(
        SpringType,
        on_delete=models.PROTECT,
        related_name='front_spring_configs'
    )
    rear_spring_type = models.ForeignKey(
        SpringType,
        on_delete=models.PROTECT,
        related_name='rear_spring_configs'
    )

    class Meta:
        db_table = 'vcdb_spring_type_config'
        ordering = ['front_spring_type__spring_type_name']
        verbose_name = _('Spring Type Config')
        verbose_name_plural = _('Spring Type Configs')
        indexes = [
            models.Index(fields=['front_spring_type']),
            models.Index(fields=['rear_spring_type']),
        ]

    def __str__(self):
        return f"F: {self.front_spring_type} / R: {self.rear_spring_type}"


# Bed configuration models (for trucks)
class BedType(AuditMixin, models.Model):
    """Truck bed types."""
    bed_type_id = models.IntegerField(primary_key=True)
    bed_type_name = models.CharField(max_length=50)

    class Meta:
        db_table = 'vcdb_bed_type'
        ordering = ['bed_type_name']
        verbose_name = _('Bed Type')
        verbose_name_plural = _('Bed Types')

    def __str__(self):
        return self.bed_type_name


class BedLength(AuditMixin, models.Model):
    """Truck bed lengths."""
    bed_length_id = models.IntegerField(primary_key=True)
    bed_length = models.CharField(max_length=10)
    bed_length_metric = models.CharField(max_length=10)

    class Meta:
        db_table = 'vcdb_bed_length'
        ordering = ['bed_length']
        verbose_name = _('Bed Length')
        verbose_name_plural = _('Bed Lengths')

    def __str__(self):
        return f"{self.bed_length} ft / {self.bed_length_metric} m"


class BedConfig(AuditMixin, models.Model):
    """Truck bed configurations."""
    bed_config_id = models.IntegerField(primary_key=True)
    bed_length = models.ForeignKey(
        BedLength,
        on_delete=models.PROTECT,
        related_name='bed_configs'
    )
    bed_type = models.ForeignKey(
        BedType,
        on_delete=models.PROTECT,
        related_name='bed_configs'
    )

    class Meta:
        db_table = 'vcdb_bed_config'
        ordering = ['bed_type__bed_type_name']
        verbose_name = _('Bed Config')
        verbose_name_plural = _('Bed Configs')
        indexes = [
            models.Index(fields=['bed_length']),
            models.Index(fields=['bed_type']),
        ]

    def __str__(self):
        return f"{self.bed_type} {self.bed_length}"


class Class(AuditMixin, models.Model):
    """Vehicle class classifications."""
    class_id = models.IntegerField(primary_key=True)
    class_name = models.CharField(max_length=30)

    class Meta:
        db_table = 'vcdb_class'
        ordering = ['class_name']
        verbose_name = _('Class')
        verbose_name_plural = _('Classes')

    def __str__(self):
        return self.class_name


# Vehicle-to-component relationship models
class VehicleToEngineConfig(AuditMixin, models.Model):
    """Links vehicles to their engine configurations."""
    vehicle_to_engine_config_id = models.IntegerField(primary_key=True)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='engine_configs'
    )
    engine_config = models.ForeignKey(
        EngineConfig,
        on_delete=models.PROTECT,
        related_name='vehicles'
    )
    source = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'vcdb_vehicle_to_engine_config'
        ordering = ['vehicle']
        verbose_name = _('Vehicle to Engine Config')
        verbose_name_plural = _('Vehicle to Engine Configs')
        indexes = [
            models.Index(fields=['vehicle']),
            models.Index(fields=['engine_config']),
        ]

    def __str__(self):
        return f"{self.vehicle} -> {self.engine_config}"


class VehicleToTransmission(AuditMixin, models.Model):
    """Links vehicles to their transmissions."""
    vehicle_to_transmission_id = models.IntegerField(primary_key=True)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='transmissions'
    )
    transmission = models.ForeignKey(
        Transmission,
        on_delete=models.PROTECT,
        related_name='vehicles'
    )
    source = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'vcdb_vehicle_to_transmission'
        ordering = ['vehicle']
        verbose_name = _('Vehicle to Transmission')
        verbose_name_plural = _('Vehicle to Transmissions')
        indexes = [
            models.Index(fields=['vehicle']),
            models.Index(fields=['transmission']),
        ]

    def __str__(self):
        return f"{self.vehicle} -> {self.transmission}"


class VehicleToBodyStyleConfig(AuditMixin, models.Model):
    """Links vehicles to their body style configurations."""
    vehicle_to_body_style_config_id = models.IntegerField(primary_key=True)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='body_style_configs'
    )
    body_style_config = models.ForeignKey(
        BodyStyleConfig,
        on_delete=models.PROTECT,
        related_name='vehicles'
    )
    source = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'vcdb_vehicle_to_body_style_config'
        ordering = ['vehicle']
        verbose_name = _('Vehicle to Body Style Config')
        verbose_name_plural = _('Vehicle to Body Style Configs')
        indexes = [
            models.Index(fields=['vehicle']),
            models.Index(fields=['body_style_config']),
        ]

    def __str__(self):
        return f"{self.vehicle} -> {self.body_style_config}"


class VehicleToBrakeConfig(AuditMixin, models.Model):
    """Links vehicles to their brake configurations."""
    vehicle_to_brake_config_id = models.IntegerField(primary_key=True)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='brake_configs'
    )
    brake_config = models.ForeignKey(
        BrakeConfig,
        on_delete=models.PROTECT,
        related_name='vehicles'
    )
    source = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'vcdb_vehicle_to_brake_config'
        ordering = ['vehicle']
        verbose_name = _('Vehicle to Brake Config')
        verbose_name_plural = _('Vehicle to Brake Configs')
        indexes = [
            models.Index(fields=['vehicle']),
            models.Index(fields=['brake_config']),
        ]

    def __str__(self):
        return f"{self.vehicle} -> {self.brake_config}"


class VehicleToDriveType(AuditMixin, models.Model):
    """Links vehicles to their drive types."""
    vehicle_to_drive_type_id = models.IntegerField(primary_key=True)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='drive_types'
    )
    drive_type = models.ForeignKey(
        DriveType,
        on_delete=models.PROTECT,
        related_name='vehicles'
    )
    source = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'vcdb_vehicle_to_drive_type'
        ordering = ['vehicle']
        verbose_name = _('Vehicle to Drive Type')
        verbose_name_plural = _('Vehicle to Drive Types')
        indexes = [
            models.Index(fields=['vehicle']),
            models.Index(fields=['drive_type']),
        ]

    def __str__(self):
        return f"{self.vehicle} -> {self.drive_type}"


class VehicleToSteeringConfig(AuditMixin, models.Model):
    """Links vehicles to their steering configurations."""
    vehicle_to_steering_config_id = models.IntegerField(primary_key=True)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='steering_configs'
    )
    steering_config = models.ForeignKey(
        SteeringConfig,
        on_delete=models.PROTECT,
        related_name='vehicles'
    )
    source = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'vcdb_vehicle_to_steering_config'
        ordering = ['vehicle']
        verbose_name = _('Vehicle to Steering Config')
        verbose_name_plural = _('Vehicle to Steering Configs')
        indexes = [
            models.Index(fields=['vehicle']),
            models.Index(fields=['steering_config']),
        ]

    def __str__(self):
        return f"{self.vehicle} -> {self.steering_config}"


class VehicleToSpringTypeConfig(AuditMixin, models.Model):
    """Links vehicles to their spring/suspension configurations."""
    vehicle_to_spring_type_config_id = models.IntegerField(primary_key=True)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='spring_type_configs'
    )
    spring_type_config = models.ForeignKey(
        SpringTypeConfig,
        on_delete=models.PROTECT,
        related_name='vehicles'
    )
    source = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'vcdb_vehicle_to_spring_type_config'
        ordering = ['vehicle']
        verbose_name = _('Vehicle to Spring Type Config')
        verbose_name_plural = _('Vehicle to Spring Type Configs')
        indexes = [
            models.Index(fields=['vehicle']),
            models.Index(fields=['spring_type_config']),
        ]

    def __str__(self):
        return f"{self.vehicle} -> {self.spring_type_config}"


class VehicleToBedConfig(AuditMixin, models.Model):
    """Links vehicles to their bed configurations (for trucks)."""
    vehicle_to_bed_config_id = models.IntegerField(primary_key=True)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='bed_configs'
    )
    bed_config = models.ForeignKey(
        BedConfig,
        on_delete=models.PROTECT,
        related_name='vehicles'
    )
    source = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'vcdb_vehicle_to_bed_config'
        ordering = ['vehicle']
        verbose_name = _('Vehicle to Bed Config')
        verbose_name_plural = _('Vehicle to Bed Configs')
        indexes = [
            models.Index(fields=['vehicle']),
            models.Index(fields=['bed_config']),
        ]

    def __str__(self):
        return f"{self.vehicle} -> {self.bed_config}"


class VehicleToClass(AuditMixin, models.Model):
    """Links vehicles to their classifications."""
    vehicle_to_class_id = models.IntegerField(primary_key=True)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='classes'
    )
    vehicle_class = models.ForeignKey(
        Class,
        on_delete=models.PROTECT,
        related_name='vehicles'
    )
    source = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'vcdb_vehicle_to_class'
        ordering = ['vehicle']
        verbose_name = _('Vehicle to Class')
        verbose_name_plural = _('Vehicle to Classes')
        indexes = [
            models.Index(fields=['vehicle']),
            models.Index(fields=['vehicle_class']),
        ]

    def __str__(self):
        return f"{self.vehicle} -> {self.vehicle_class}"


class VehicleToMfrBodyCode(AuditMixin, models.Model):
    """Links vehicles to manufacturer body codes."""
    vehicle_to_mfr_body_code_id = models.IntegerField(primary_key=True)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='mfr_body_codes'
    )
    mfr_body_code = models.ForeignKey(
        MfrBodyCode,
        on_delete=models.PROTECT,
        related_name='vehicles'
    )
    source = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'vcdb_vehicle_to_mfr_body_code'
        ordering = ['vehicle']
        verbose_name = _('Vehicle to Mfr Body Code')
        verbose_name_plural = _('Vehicle to Mfr Body Codes')
        indexes = [
            models.Index(fields=['vehicle']),
            models.Index(fields=['mfr_body_code']),
        ]

    def __str__(self):
        return f"{self.vehicle} -> {self.mfr_body_code}"


class VehicleToWheelbase(AuditMixin, models.Model):
    """Links vehicles to their wheelbase specifications."""
    vehicle_to_wheelbase_id = models.IntegerField(primary_key=True)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='wheelbases'
    )
    wheelbase = models.ForeignKey(
        WheelBase,
        on_delete=models.PROTECT,
        related_name='vehicles'
    )
    source = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'vcdb_vehicle_to_wheelbase'
        ordering = ['vehicle']
        verbose_name = _('Vehicle to Wheelbase')
        verbose_name_plural = _('Vehicle to Wheelbases')
        indexes = [
            models.Index(fields=['vehicle']),
            models.Index(fields=['wheelbase']),
        ]

    def __str__(self):
        return f"{self.vehicle} -> {self.wheelbase}"


# Audit and Change Tracking Models
class ChangeReason(AuditMixin, models.Model):
    """Reasons for data changes."""
    change_reason_id = models.IntegerField(primary_key=True)
    change_reason = models.CharField(max_length=255)

    class Meta:
        db_table = 'vcdb_change_reasons'
        ordering = ['change_reason']
        verbose_name = _('Change Reason')
        verbose_name_plural = _('Change Reasons')

    def __str__(self):
        return self.change_reason


class Change(AuditMixin, models.Model):
    """Change tracking records."""
    change_id = models.AutoField(primary_key=True)
    request_id = models.IntegerField()
    change_reason = models.ForeignKey(
        ChangeReason,
        on_delete=models.PROTECT,
        related_name='changes'
    )
    rev_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'vcdb_changes'
        ordering = ['-rev_date']
        verbose_name = _('Change')
        verbose_name_plural = _('Changes')
        indexes = [
            models.Index(fields=['change_reason']),
            models.Index(fields=['rev_date']),
            models.Index(fields=['request_id']),
        ]

    def __str__(self):
        return f"Change {self.change_id}: {self.change_reason}"


class ChangeAttributeState(AuditMixin, models.Model):
    """Change attribute states."""
    change_attribute_state_id = models.IntegerField(primary_key=True)
    change_attribute_state = models.CharField(max_length=255)

    class Meta:
        db_table = 'vcdb_change_attribute_states'
        ordering = ['change_attribute_state']
        verbose_name = _('Change Attribute State')
        verbose_name_plural = _('Change Attribute States')

    def __str__(self):
        return self.change_attribute_state


class ChangeTableName(AuditMixin, models.Model):
    """Table names for change tracking."""
    table_name_id = models.IntegerField(primary_key=True)
    table_name = models.CharField(max_length=255)
    table_description = models.CharField(max_length=1000, null=True, blank=True)

    class Meta:
        db_table = 'vcdb_change_table_names'
        ordering = ['table_name']
        verbose_name = _('Change Table Name')
        verbose_name_plural = _('Change Table Names')

    def __str__(self):
        return self.table_name


class ChangeDetail(AuditMixin, models.Model):
    """Detailed change tracking information."""
    change_detail_id = models.AutoField(primary_key=True)
    change = models.ForeignKey(
        Change,
        on_delete=models.CASCADE,
        related_name='details'
    )
    change_attribute_state = models.ForeignKey(
        ChangeAttributeState,
        on_delete=models.PROTECT,
        related_name='details'
    )
    table_name = models.ForeignKey(
        ChangeTableName,
        on_delete=models.PROTECT,
        related_name='details'
    )
    primary_key_column_name = models.CharField(max_length=255, null=True, blank=True)
    primary_key_before = models.IntegerField(null=True, blank=True)
    primary_key_after = models.IntegerField(null=True, blank=True)
    column_name = models.CharField(max_length=255, null=True, blank=True)
    column_value_before = models.CharField(max_length=1000, null=True, blank=True)
    column_value_after = models.CharField(max_length=1000, null=True, blank=True)

    class Meta:
        db_table = 'vcdb_change_details'
        ordering = ['change', 'change_detail_id']
        verbose_name = _('Change Detail')
        verbose_name_plural = _('Change Details')
        indexes = [
            models.Index(fields=['change']),
            models.Index(fields=['change_attribute_state']),
            models.Index(fields=['table_name']),
            models.Index(fields=['column_name']),
        ]

    def __str__(self):
        return f"Detail {self.change_detail_id}: {self.column_name}"


# Internationalization Models
class Language(AuditMixin, models.Model):
    """Supported languages for internationalization."""
    language_name = models.CharField(max_length=20)
    dialect_name = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = 'vcdb_language'
        ordering = ['language_name']
        verbose_name = _('Language')
        verbose_name_plural = _('Languages')

    def __str__(self):
        if self.dialect_name:
            return f"{self.language_name} ({self.dialect_name})"
        return self.language_name


class EnglishPhrase(AuditMixin, models.Model):
    """English phrases for translation."""
    english_phrase = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'vcdb_english_phrase'
        ordering = ['english_phrase']
        verbose_name = _('English Phrase')
        verbose_name_plural = _('English Phrases')
        indexes = [
            models.Index(fields=['english_phrase']),
        ]

    def __str__(self):
        return self.english_phrase


class LanguageTranslation(AuditMixin, models.Model):
    """Translations of English phrases to other languages."""
    english_phrase = models.ForeignKey(
        EnglishPhrase,
        on_delete=models.CASCADE,
        related_name='translations'
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.CASCADE,
        related_name='translations'
    )
    translation = models.CharField(max_length=150)

    class Meta:
        db_table = 'vcdb_language_translation'
        ordering = ['english_phrase', 'language']
        verbose_name = _('Language Translation')
        verbose_name_plural = _('Language Translations')
        unique_together = [['english_phrase', 'language']]
        indexes = [
            models.Index(fields=['english_phrase']),
            models.Index(fields=['language']),
        ]

    def __str__(self):
        return f"{self.english_phrase} -> {self.translation} ({self.language})"


class LanguageTranslationAttachment(AuditMixin, models.Model):
    """Attachments for language translations."""
    language_translation = models.ForeignKey(
        LanguageTranslation,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    attachment = models.ForeignKey(
        Attachment,
        on_delete=models.CASCADE,
        related_name='language_translation_attachments'
    )

    class Meta:
        db_table = 'vcdb_language_translation_attachment'
        ordering = ['language_translation']
        verbose_name = _('Language Translation Attachment')
        verbose_name_plural = _('Language Translation Attachments')

    def __str__(self):
        return f"{self.language_translation} -> {self.attachment}"


# Version tracking
class Version(AuditMixin, models.Model):
    """System version tracking."""
    version_date = models.DateField(primary_key=True)

    class Meta:
        db_table = 'vcdb_version'
        ordering = ['-version_date']
        verbose_name = _('Version')
        verbose_name_plural = _('Versions')

    def __str__(self):
        return str(self.version_date)


class VcdbChange(models.Model):
    """VCDB change tracking (legacy)."""
    version_date = models.DateTimeField()
    table_name = models.CharField(max_length=30)
    record_id = models.IntegerField()
    action = models.CharField(max_length=1)

    class Meta:
        db_table = 'vcdb_vcdb_changes'
        ordering = ['-version_date']
        verbose_name = _('VCDB Change')
        verbose_name_plural = _('VCDB Changes')
        indexes = [
            models.Index(fields=['version_date']),
            models.Index(fields=['table_name']),
            models.Index(fields=['record_id']),
            models.Index(fields=['action']),
        ]

    def __str__(self):
        return f"{self.table_name}:{self.record_id} ({self.action})"