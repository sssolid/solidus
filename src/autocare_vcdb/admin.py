# src/autocare/admin/vcdb.py
"""
Django admin configuration for automotive models.
"""

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db.models import Count

from autocare_vcdb.models import (
    # Basic reference models
    Abbreviation, Aspiration, AttachmentType, Attachment,
    Make, VehicleTypeGroup, VehicleType, Model, Year, BaseVehicle,
    SubModel, Region, PublicationStage, Vehicle,

    # Engine models
    EngineBase, CylinderHeadType, FuelType, FuelDeliveryType,
    FuelDeliverySubType, FuelSystemControlType, FuelSystemDesign,
    FuelDeliveryConfig, IgnitionSystemType, Mfr, EngineDesignation,
    EngineVIN, EngineVersion, Valves, PowerOutput, EngineConfig,

    # Transmission models
    TransmissionType, TransmissionNumSpeeds, TransmissionControlType,
    TransmissionBase, TransmissionMfrCode, ElecControlled, Transmission,

    # Body/styling models
    BodyType, BodyNumDoors, BodyStyleConfig, MfrBodyCode, WheelBase,

    # Brake system models
    BrakeType, BrakeSystem, BrakeABS, BrakeConfig,

    # Other systems
    DriveType, SteeringType, SteeringSystem, SteeringConfig,
    SpringType, SpringTypeConfig, BedType, BedLength, BedConfig,
    Class,

    # Vehicle relationship models
    VehicleToEngineConfig, VehicleToTransmission, VehicleToBodyStyleConfig,
    VehicleToBrakeConfig, VehicleToDriveType, VehicleToSteeringConfig,
    VehicleToSpringTypeConfig, VehicleToBedConfig, VehicleToClass,
    VehicleToMfrBodyCode, VehicleToWheelbase,

    # Audit models
    ChangeReasons, Changes, ChangeAttributeStates, ChangeTableNames, ChangeDetails,

    # Internationalization
    Language, EnglishPhrase, LanguageTranslation, LanguageTranslationAttachment,

    # Version
    Version, VCdbChanges, EngineConfig2, EngineBase2,
)


class SearchableMixin:
    """Mixin for common search functionality."""

    def get_search_fields(self, request):
        """Override to add dynamic search fields."""
        search_fields = getattr(self, 'search_fields', ())
        return search_fields


# Base reference model admins
@admin.register(Abbreviation)
class AbbreviationAdmin(admin.ModelAdmin):
    list_display = ['abbreviation', 'description', 'long_description']
    search_fields = ['abbreviation', 'description', 'long_description']
    ordering = ['abbreviation']


@admin.register(Aspiration)
class AspirationAdmin(admin.ModelAdmin):
    list_display = ['aspiration_id', 'aspiration_name']
    search_fields = ['aspiration_name']
    ordering = ['aspiration_name']


@admin.register(AttachmentType)
class AttachmentTypeAdmin(admin.ModelAdmin):
    list_display = ['attachment_type_id', 'attachment_type_name']
    search_fields = ['attachment_type_name']
    ordering = ['attachment_type_name']


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['attachment_id', 'attachment_file_name', 'attachment_type', 'attachment_description']
    list_filter = ['attachment_type', ]
    search_fields = ['attachment_file_name', 'attachment_description']
    autocomplete_fields = ['attachment_type']


@admin.register(Make)
class MakeAdmin(admin.ModelAdmin):
    list_display = ['make_id', 'make_name', 'vehicle_count']
    search_fields = ['make_name']
    ordering = ['make_name']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            vehicle_count=Count('base_vehicles__vehicles')
        )

    def vehicle_count(self, obj):
        return obj.vehicle_count

    vehicle_count.short_description = _('Vehicles')
    vehicle_count.admin_order_field = 'vehicle_count'


@admin.register(VehicleTypeGroup)
class VehicleTypeGroupAdmin(admin.ModelAdmin):
    list_display = ['vehicle_type_group_id', 'vehicle_type_group_name']
    search_fields = ['vehicle_type_group_name']
    ordering = ['vehicle_type_group_name']


@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display = ['vehicle_type_id', 'vehicle_type_name', 'vehicle_type_group']
    list_filter = ['vehicle_type_group']
    search_fields = ['vehicle_type_name']
    autocomplete_fields = ['vehicle_type_group']
    ordering = ['vehicle_type_name']


@admin.register(Model)
class ModelAdmin(admin.ModelAdmin):
    list_display = ['model_id', 'model_name', 'vehicle_type']
    list_filter = ['vehicle_type']
    search_fields = ['model_name']
    autocomplete_fields = ['vehicle_type']
    ordering = ['model_name']


@admin.register(Year)
class YearAdmin(admin.ModelAdmin):
    search_fields = ['year_id']
    list_display = ['year_id']
    ordering = ['-year_id']


@admin.register(BaseVehicle)
class BaseVehicleAdmin(admin.ModelAdmin):
    list_display = ['base_vehicle_id', 'year', 'make', 'model', 'vehicle_count']
    list_filter = ['year', 'make']
    search_fields = ['make__make_name', 'model__model_name']
    autocomplete_fields = ['year', 'make', 'model']
    ordering = ['-year__year_id', 'make__make_name', 'model__model_name']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'year', 'make', 'model'
        ).annotate(vehicle_count=Count('vehicles'))

    def vehicle_count(self, obj):
        count = obj.vehicle_count
        if count > 0:
            url = reverse('admin:automotive_vehicle_changelist')
            return format_html(
                '<a href="{}?base_vehicle__exact={}">{}</a>',
                url, obj.base_vehicle_id, count
            )
        return count

    vehicle_count.short_description = _('Vehicles')
    vehicle_count.admin_order_field = 'vehicle_count'


@admin.register(SubModel)
class SubModelAdmin(admin.ModelAdmin):
    list_display = ['sub_model_id', 'sub_model_name']
    search_fields = ['sub_model_name']
    ordering = ['sub_model_name']


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['region_id', 'region_name', 'region_abbr', 'parent']
    list_filter = ['parent']
    search_fields = ['region_name', 'region_abbr']
    autocomplete_fields = ['parent']
    ordering = ['region_name']


@admin.register(PublicationStage)
class PublicationStageAdmin(admin.ModelAdmin):
    list_display = ['publication_stage_id', 'publication_stage_name']
    search_fields = ['publication_stage_name']
    ordering = ['publication_stage_name']


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = [
        'vehicle_id', 'base_vehicle_display', 'submodel', 'region',
        'publication_stage', 'publication_stage_date'
    ]
    list_filter = [
        'base_vehicle__year', 'base_vehicle__make', 'region',
        'publication_stage', 'publication_stage_date'
    ]
    search_fields = [
        'base_vehicle__make__make_name',
        'base_vehicle__model__model_name',
        'submodel__sub_model_name'
    ]
    autocomplete_fields = ['base_vehicle', 'submodel', 'region', 'publication_stage']
    ordering = ['-base_vehicle__year__year_id', 'base_vehicle__make__make_name']
    date_hierarchy = 'publication_stage_date'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'base_vehicle__year', 'base_vehicle__make', 'base_vehicle__model',
            'submodel', 'region', 'publication_stage'
        )

    def base_vehicle_display(self, obj):
        return str(obj.base_vehicle)

    base_vehicle_display.short_description = _('Base Vehicle')
    base_vehicle_display.admin_order_field = 'base_vehicle'


# Engine-related admins
@admin.register(EngineBase)
class EngineBaseAdmin(admin.ModelAdmin):
    list_display = [
        'engine_base_id', 'liter', 'cylinders', 'cc', 'cid',
        'block_type', 'eng_bore_in', 'eng_stroke_in'
    ]
    list_filter = ['liter', 'cylinders', 'block_type']
    search_fields = ['liter', 'cc', 'cid']
    ordering = ['liter', 'cylinders']


@admin.register(EngineBase2)
class EngineBaseAdmin(admin.ModelAdmin):
    list_display = [
        'engine_base_id'
    ]
    list_filter = ['engine_block']
    search_fields = ['engine_block__liter']
    ordering = ['engine_block__liter']


@admin.register(CylinderHeadType)
class CylinderHeadTypeAdmin(admin.ModelAdmin):
    list_display = ['cylinder_head_type_id', 'cylinder_head_type_name']
    search_fields = ['cylinder_head_type_name']
    ordering = ['cylinder_head_type_name']


@admin.register(FuelType)
class FuelTypeAdmin(admin.ModelAdmin):
    list_display = ['fuel_type_id', 'fuel_type_name']
    search_fields = ['fuel_type_name']
    ordering = ['fuel_type_name']


@admin.register(FuelDeliveryType)
class FuelDeliveryTypeAdmin(admin.ModelAdmin):
    list_display = ['fuel_delivery_type_id', 'fuel_delivery_type_name']
    search_fields = ['fuel_delivery_type_name']
    ordering = ['fuel_delivery_type_name']


@admin.register(FuelDeliverySubType)
class FuelDeliverySubTypeAdmin(admin.ModelAdmin):
    list_display = ['fuel_delivery_sub_type_id', 'fuel_delivery_sub_type_name']
    search_fields = ['fuel_delivery_sub_type_name']
    ordering = ['fuel_delivery_sub_type_name']


@admin.register(FuelSystemControlType)
class FuelSystemControlTypeAdmin(admin.ModelAdmin):
    list_display = ['fuel_system_control_type_id', 'fuel_system_control_type_name']
    search_fields = ['fuel_system_control_type_name']
    ordering = ['fuel_system_control_type_name']


@admin.register(FuelSystemDesign)
class FuelSystemDesignAdmin(admin.ModelAdmin):
    list_display = ['fuel_system_design_id', 'fuel_system_design_name']
    search_fields = ['fuel_system_design_name']
    ordering = ['fuel_system_design_name']


@admin.register(FuelDeliveryConfig)
class FuelDeliveryConfigAdmin(admin.ModelAdmin):
    search_fields = ['fuel_delivery_type__fuel_delivery_type_name',
                     'fuel_delivery_sub_type__fuel_delivery_sub_type_name',
                     'fuel_system_control_type__fuel_system_control_type_name',
                     'fuel_system_design__fuel_system_design_name']
    list_display = [
        'fuel_delivery_config_id', 'fuel_delivery_type',
        'fuel_delivery_sub_type', 'fuel_system_control_type', 'fuel_system_design'
    ]
    list_filter = [
        'fuel_delivery_type', 'fuel_delivery_sub_type',
        'fuel_system_control_type', 'fuel_system_design'
    ]
    autocomplete_fields = [
        'fuel_delivery_type', 'fuel_delivery_sub_type',
        'fuel_system_control_type', 'fuel_system_design'
    ]


@admin.register(IgnitionSystemType)
class IgnitionSystemTypeAdmin(admin.ModelAdmin):
    list_display = ['ignition_system_type_id', 'ignition_system_type_name']
    search_fields = ['ignition_system_type_name']
    ordering = ['ignition_system_type_name']


@admin.register(Mfr)
class MfrAdmin(admin.ModelAdmin):
    list_display = ['mfr_id', 'mfr_name']
    search_fields = ['mfr_name']
    ordering = ['mfr_name']


@admin.register(EngineDesignation)
class EngineDesignationAdmin(admin.ModelAdmin):
    list_display = ['engine_designation_id', 'engine_designation_name']
    search_fields = ['engine_designation_name']
    ordering = ['engine_designation_name']


@admin.register(EngineVIN)
class EngineVINAdmin(admin.ModelAdmin):
    list_display = ['engine_vin_id', 'engine_vin_name']
    search_fields = ['engine_vin_name']
    ordering = ['engine_vin_name']


@admin.register(EngineVersion)
class EngineVersionAdmin(admin.ModelAdmin):
    list_display = ['engine_version_id', 'engine_version']
    search_fields = ['engine_version']
    ordering = ['engine_version']


@admin.register(Valves)
class ValvesAdmin(admin.ModelAdmin):
    list_display = ['valves_id', 'valves_per_engine']
    search_fields = ['valves_per_engine']
    ordering = ['valves_per_engine']


@admin.register(PowerOutput)
class PowerOutputAdmin(admin.ModelAdmin):
    list_display = ['power_output_id', 'horse_power', 'kilowatt_power']
    search_fields = ['horse_power', 'kilowatt_power']
    ordering = ['-horse_power']


@admin.register(EngineConfig)
class EngineConfigAdmin(admin.ModelAdmin):
    list_display = [
        'engine_config_id', 'engine_base_display', 'engine_designation',
        'fuel_type', 'aspiration', 'power_output'
    ]
    list_filter = [
        'engine_base__liter', 'engine_base__cylinders', 'fuel_type',
        'aspiration', 'cylinder_head_type', 'ignition_system_type'
    ]
    search_fields = [
        'engine_designation__engine_designation_name',
        'engine_base__liter', 'engine_base__cylinders'
    ]
    autocomplete_fields = [
        'engine_designation', 'engine_vin', 'valves', 'engine_base',
        'fuel_delivery_config', 'aspiration', 'cylinder_head_type',
        'fuel_type', 'ignition_system_type', 'engine_mfr',
        'engine_version', 'power_output'
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'engine_base', 'engine_designation', 'fuel_type', 'aspiration', 'power_output'
        )

    def engine_base_display(self, obj):
        return str(obj.engine_base)

    engine_base_display.short_description = _('Engine Base')
    engine_base_display.admin_order_field = 'engine_base'


@admin.register(EngineConfig2)
class EngineConfig2Admin(admin.ModelAdmin):
    list_display = [
        'engine_config_id', 'engine_base_display', 'engine_designation',
        'fuel_type', 'aspiration', 'power_output'
    ]
    list_filter = [
        'fuel_type',
        'aspiration', 'cylinder_head_type', 'ignition_system_type'
    ]
    search_fields = [
        'engine_designation__engine_designation_name',
    ]
    autocomplete_fields = [
        'engine_designation', 'engine_vin', 'valves', 'engine_base',
        'fuel_delivery_config', 'aspiration', 'cylinder_head_type',
        'fuel_type', 'ignition_system_type', 'engine_mfr',
        'engine_version', 'power_output'
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'engine_base', 'engine_designation', 'fuel_type', 'aspiration', 'power_output'
        )

    def engine_base_display(self, obj):
        return str(obj.engine_base)

    engine_base_display.short_description = _('Engine Base')
    engine_base_display.admin_order_field = 'engine_base'


# Transmission admins
@admin.register(TransmissionType)
class TransmissionTypeAdmin(admin.ModelAdmin):
    list_display = ['transmission_type_id', 'transmission_type_name']
    search_fields = ['transmission_type_name']
    ordering = ['transmission_type_name']


@admin.register(TransmissionNumSpeeds)
class TransmissionNumSpeedsAdmin(admin.ModelAdmin):
    list_display = ['transmission_num_speeds_id', 'transmission_num_speeds']
    search_fields = ['transmission_num_speeds']
    ordering = ['transmission_num_speeds']


@admin.register(TransmissionControlType)
class TransmissionControlTypeAdmin(admin.ModelAdmin):
    list_display = ['transmission_control_type_id', 'transmission_control_type_name']
    search_fields = ['transmission_control_type_name']
    ordering = ['transmission_control_type_name']


@admin.register(TransmissionBase)
class TransmissionBaseAdmin(admin.ModelAdmin):
    search_fields = ['transmission_type__transmission_type_name',
                     'transmission_control_type__transmission_control_type_name',
                     'transmission_num_speeds__transmission_num_speeds']
    list_display = [
        'transmission_base_id', 'transmission_type',
        'transmission_num_speeds', 'transmission_control_type'
    ]
    list_filter = ['transmission_type', 'transmission_control_type']
    autocomplete_fields = [
        'transmission_type', 'transmission_num_speeds', 'transmission_control_type'
    ]


@admin.register(TransmissionMfrCode)
class TransmissionMfrCodeAdmin(admin.ModelAdmin):
    list_display = ['transmission_mfr_code_id', 'transmission_mfr_code']
    search_fields = ['transmission_mfr_code']
    ordering = ['transmission_mfr_code']


@admin.register(ElecControlled)
class ElecControlledAdmin(admin.ModelAdmin):
    list_display = ['elec_controlled_id', 'elec_controlled']
    search_fields = ['elec_controlled']
    ordering = ['elec_controlled']


@admin.register(Transmission)
class TransmissionAdmin(admin.ModelAdmin):
    search_fields = ['transmission_base__transmission_num_speeds__transmission_num_speeds', 'transmission_mfr_code__transmission_mfr_code',
                     'transmission_elec_controlled__elec_controlled']
    list_display = [
        'transmission_id', 'transmission_base', 'transmission_mfr_code',
        'transmission_elec_controlled', 'transmission_mfr'
    ]
    list_filter = ['transmission_mfr', 'transmission_elec_controlled']
    autocomplete_fields = [
        'transmission_base', 'transmission_mfr_code',
        'transmission_elec_controlled', 'transmission_mfr'
    ]


# Body/styling admins
@admin.register(BodyType)
class BodyTypeAdmin(admin.ModelAdmin):
    list_display = ['body_type_id', 'body_type_name']
    search_fields = ['body_type_name']
    ordering = ['body_type_name']


@admin.register(BodyNumDoors)
class BodyNumDoorsAdmin(admin.ModelAdmin):
    list_display = ['body_num_doors_id', 'body_num_doors']
    search_fields = ['body_num_doors']
    ordering = ['body_num_doors']


@admin.register(BodyStyleConfig)
class BodyStyleConfigAdmin(admin.ModelAdmin):
    search_fields = ['body_type__body_type_name', 'body_num_doors__body_num_doors']
    list_display = ['body_style_config_id', 'body_type', 'body_num_doors']
    list_filter = ['body_type', 'body_num_doors']
    autocomplete_fields = ['body_type', 'body_num_doors']


@admin.register(MfrBodyCode)
class MfrBodyCodeAdmin(admin.ModelAdmin):
    list_display = ['mfr_body_code_id', 'mfr_body_code_name']
    search_fields = ['mfr_body_code_name']
    ordering = ['mfr_body_code_name']


@admin.register(WheelBase)
class WheelBaseAdmin(admin.ModelAdmin):
    list_display = ['wheel_base_id', 'wheel_base', 'wheel_base_metric']
    search_fields = ['wheel_base', 'wheel_base_metric']
    ordering = ['wheel_base']


# Brake system admins
@admin.register(BrakeType)
class BrakeTypeAdmin(admin.ModelAdmin):
    list_display = ['brake_type_id', 'brake_type_name']
    search_fields = ['brake_type_name']
    ordering = ['brake_type_name']


@admin.register(BrakeSystem)
class BrakeSystemAdmin(admin.ModelAdmin):
    list_display = ['brake_system_id', 'brake_system_name']
    search_fields = ['brake_system_name']
    ordering = ['brake_system_name']


@admin.register(BrakeABS)
class BrakeABSAdmin(admin.ModelAdmin):
    list_display = ['brake_abs_id', 'brake_abs_name']
    search_fields = ['brake_abs_name']
    ordering = ['brake_abs_name']


@admin.register(BrakeConfig)
class BrakeConfigAdmin(admin.ModelAdmin):
    search_fields = ['front_brake_type__brake_type_name', 'rear_brake_type__brake_type_name',
                     'brake_system__brake_system_name', 'brake_abs__brake_abs_name']
    list_display = [
        'brake_config_id', 'front_brake_type', 'rear_brake_type',
        'brake_system', 'brake_abs'
    ]
    list_filter = ['brake_system', 'brake_abs', 'front_brake_type', 'rear_brake_type']
    autocomplete_fields = ['front_brake_type', 'rear_brake_type', 'brake_system', 'brake_abs']


# Other system admins
@admin.register(DriveType)
class DriveTypeAdmin(admin.ModelAdmin):
    list_display = ['drive_type_id', 'drive_type_name']
    search_fields = ['drive_type_name']
    ordering = ['drive_type_name']


@admin.register(SteeringType)
class SteeringTypeAdmin(admin.ModelAdmin):
    list_display = ['steering_type_id', 'steering_type_name']
    search_fields = ['steering_type_name']
    ordering = ['steering_type_name']


@admin.register(SteeringSystem)
class SteeringSystemAdmin(admin.ModelAdmin):
    list_display = ['steering_system_id', 'steering_system_name']
    search_fields = ['steering_system_name']
    ordering = ['steering_system_name']


@admin.register(SteeringConfig)
class SteeringConfigAdmin(admin.ModelAdmin):
    search_fields = ['steering_type__steering_type_name', 'steering_system__steering_system_name']
    list_display = ['steering_config_id', 'steering_type', 'steering_system']
    list_filter = ['steering_type', 'steering_system']
    autocomplete_fields = ['steering_type', 'steering_system']


@admin.register(SpringType)
class SpringTypeAdmin(admin.ModelAdmin):
    list_display = ['spring_type_id', 'spring_type_name']
    search_fields = ['spring_type_name']
    ordering = ['spring_type_name']


@admin.register(SpringTypeConfig)
class SpringTypeConfigAdmin(admin.ModelAdmin):
    search_fields = ['front_spring_type__spring_type_name', 'rear_spring_type__spring_type_name']
    list_display = ['spring_type_config_id', 'front_spring_type', 'rear_spring_type']
    list_filter = ['front_spring_type', 'rear_spring_type']
    autocomplete_fields = ['front_spring_type', 'rear_spring_type']


@admin.register(BedType)
class BedTypeAdmin(admin.ModelAdmin):
    list_display = ['bed_type_id', 'bed_type_name']
    search_fields = ['bed_type_name']
    ordering = ['bed_type_name']


@admin.register(BedLength)
class BedLengthAdmin(admin.ModelAdmin):
    list_display = ['bed_length_id', 'bed_length', 'bed_length_metric']
    search_fields = ['bed_length', 'bed_length_metric']
    ordering = ['bed_length']


@admin.register(BedConfig)
class BedConfigAdmin(admin.ModelAdmin):
    search_fields = ['bed_type__bed_type_name', 'bed_length__bed_length']
    list_display = ['bed_config_id', 'bed_type', 'bed_length']
    list_filter = ['bed_type']
    autocomplete_fields = ['bed_type', 'bed_length']


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ['class_id', 'class_name']
    search_fields = ['class_name']
    ordering = ['class_name']


# Vehicle relationship admins - using tabular inlines for better UX
class VehicleToEngineConfigInline(admin.TabularInline):
    model = VehicleToEngineConfig
    extra = 0
    autocomplete_fields = ['engine_config']


class VehicleToTransmissionInline(admin.TabularInline):
    model = VehicleToTransmission
    extra = 0
    autocomplete_fields = ['transmission']


class VehicleToBodyStyleConfigInline(admin.TabularInline):
    model = VehicleToBodyStyleConfig
    extra = 0
    autocomplete_fields = ['body_style_config']


class VehicleToBrakeConfigInline(admin.TabularInline):
    model = VehicleToBrakeConfig
    extra = 0
    autocomplete_fields = ['brake_config']


class VehicleToDriveTypeInline(admin.TabularInline):
    model = VehicleToDriveType
    extra = 0
    autocomplete_fields = ['drive_type']


# Add inlines to Vehicle admin
VehicleAdmin.inlines = [
    VehicleToEngineConfigInline,
    VehicleToTransmissionInline,
    VehicleToBodyStyleConfigInline,
    VehicleToBrakeConfigInline,
    VehicleToDriveTypeInline,
]


# Audit and change tracking admins
@admin.register(ChangeReasons)
class ChangeReasonsAdmin(admin.ModelAdmin):
    list_display = ['change_reason_id', 'change_reason']
    search_fields = ['change_reason']
    ordering = ['change_reason']


class ChangeDetailInline(admin.TabularInline):
    model = ChangeDetails
    extra = 0
    readonly_fields = ['change_detail_id']


@admin.register(Changes)
class ChangeAdmin(admin.ModelAdmin):
    list_display = ['change_id', 'request_id', 'change_reason', 'rev_date']
    list_filter = ['change_reason', 'rev_date']
    search_fields = ['request_id']
    autocomplete_fields = ['change_reason']
    date_hierarchy = 'rev_date'
    inlines = [ChangeDetailInline]


@admin.register(ChangeAttributeStates)
class ChangeAttributeStateAdmin(admin.ModelAdmin):
    list_display = ['change_attribute_state_id', 'change_attribute_state']
    search_fields = ['change_attribute_state']
    ordering = ['change_attribute_state']


@admin.register(ChangeTableNames)
class ChangeTableNameAdmin(admin.ModelAdmin):
    list_display = ['table_name_id', 'table_name', 'table_description']
    search_fields = ['table_name', 'table_description']
    ordering = ['table_name']


@admin.register(ChangeDetails)
class ChangeDetailAdmin(admin.ModelAdmin):
    list_display = [
        'change_detail_id', 'change', 'table_name', 'column_name',
        'change_attribute_state'
    ]
    list_filter = ['change_attribute_state', 'table_name']
    search_fields = ['column_name', 'column_value_before', 'column_value_after']
    autocomplete_fields = ['change', 'change_attribute_state', 'table_name']


# Internationalization admins
@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ['language_id', 'language_name', 'dialect_name']
    search_fields = ['language_name', 'dialect_name']
    ordering = ['language_name']


@admin.register(EnglishPhrase)
class EnglishPhraseAdmin(admin.ModelAdmin):
    list_display = ['english_phrase_id', 'english_phrase']
    search_fields = ['english_phrase']
    ordering = ['english_phrase']


class LanguageTranslationAttachmentInline(admin.TabularInline):
    model = LanguageTranslationAttachment
    extra = 0


@admin.register(LanguageTranslation)
class LanguageTranslationAdmin(admin.ModelAdmin):
    list_display = ['language_translation_id', 'english_phrase', 'language', 'translation']
    list_filter = ['language']
    search_fields = ['english_phrase__english_phrase', 'translation']
    autocomplete_fields = ['english_phrase', 'language']
    inlines = [LanguageTranslationAttachmentInline]


# Version tracking admins
@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = ['version_date']
    ordering = ['-version_date']


@admin.register(VCdbChanges)
class VcdbChangeAdmin(admin.ModelAdmin):
    list_display = ['version_date', 'table_name', 'record_id', 'action']
    list_filter = ['table_name', 'action', 'version_date']
    search_fields = ['table_name', 'record_id']
    date_hierarchy = 'version_date'
    ordering = ['-version_date']


# Register remaining relationship models
@admin.register(VehicleToEngineConfig)
class VehicleToEngineConfigAdmin(admin.ModelAdmin):
    list_display = ['vehicle_to_engine_config_id', 'vehicle', 'engine_config', 'source']
    list_filter = ['source']
    autocomplete_fields = ['vehicle', 'engine_config']


@admin.register(VehicleToTransmission)
class VehicleToTransmissionAdmin(admin.ModelAdmin):
    list_display = ['vehicle_to_transmission_id', 'vehicle', 'transmission', 'source']
    list_filter = ['source']
    autocomplete_fields = ['vehicle', 'transmission']


@admin.register(VehicleToBodyStyleConfig)
class VehicleToBodyStyleConfigAdmin(admin.ModelAdmin):
    list_display = ['vehicle_to_body_style_config_id', 'vehicle', 'body_style_config', 'source']
    list_filter = ['source']
    autocomplete_fields = ['vehicle', 'body_style_config']


@admin.register(VehicleToBrakeConfig)
class VehicleToBrakeConfigAdmin(admin.ModelAdmin):
    list_display = ['vehicle_to_brake_config_id', 'vehicle', 'brake_config', 'source']
    list_filter = ['source']
    autocomplete_fields = ['vehicle', 'brake_config']


@admin.register(VehicleToDriveType)
class VehicleToDriveTypeAdmin(admin.ModelAdmin):
    list_display = ['vehicle_to_drive_type_id', 'vehicle', 'drive_type', 'source']
    list_filter = ['source', 'drive_type']
    autocomplete_fields = ['vehicle', 'drive_type']


@admin.register(VehicleToSteeringConfig)
class VehicleToSteeringConfigAdmin(admin.ModelAdmin):
    list_display = ['vehicle_to_steering_config_id', 'vehicle', 'steering_config', 'source']
    list_filter = ['source']
    autocomplete_fields = ['vehicle', 'steering_config']


@admin.register(VehicleToSpringTypeConfig)
class VehicleToSpringTypeConfigAdmin(admin.ModelAdmin):
    list_display = ['vehicle_to_spring_type_config_id', 'vehicle', 'spring_type_config', 'source']
    list_filter = ['source']
    autocomplete_fields = ['vehicle', 'spring_type_config']


@admin.register(VehicleToBedConfig)
class VehicleToBedConfigAdmin(admin.ModelAdmin):
    list_display = ['vehicle_to_bed_config_id', 'vehicle', 'bed_config', 'source']
    list_filter = ['source']
    autocomplete_fields = ['vehicle', 'bed_config']


@admin.register(VehicleToClass)
class VehicleToClassAdmin(admin.ModelAdmin):
    list_display = ['vehicle_to_class_id', 'vehicle', 'vehicle_class', 'source']
    list_filter = ['source', 'vehicle_class']
    autocomplete_fields = ['vehicle', 'vehicle_class']


@admin.register(VehicleToMfrBodyCode)
class VehicleToMfrBodyCodeAdmin(admin.ModelAdmin):
    list_display = ['vehicle_to_mfr_body_code_id', 'vehicle', 'mfr_body_code', 'source']
    list_filter = ['source', 'mfr_body_code']
    autocomplete_fields = ['vehicle', 'mfr_body_code']


@admin.register(VehicleToWheelbase)
class VehicleToWheelbaseAdmin(admin.ModelAdmin):
    list_display = ['vehicle_to_wheelbase_id', 'vehicle', 'wheelbase', 'source']
    list_filter = ['source']
    autocomplete_fields = ['vehicle', 'wheelbase']
