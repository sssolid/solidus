from django.contrib import admin
from autocare.models import *


@admin.register(ACESCodedValue)
class ACESCodedValueAdmin(admin.ModelAdmin):
    list_display = ['element', 'attribute', 'coded_value', 'code_description']
    list_filter = ['element', 'attribute']
    search_fields = ['element', 'attribute', 'coded_value', 'code_description']
    list_per_page = 50


@admin.register(Alias)
class AliasAdmin(admin.ModelAdmin):
    list_display = ['alias_id', 'alias_name']
    search_fields = ['alias_name']
    list_per_page = 50


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['category_id', 'category_name']
    search_fields = ['category_name']
    list_per_page = 50


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ['sub_category_id', 'sub_category_name']
    search_fields = ['sub_category_name']
    list_per_page = 50


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['position_id', 'position']
    search_fields = ['position']
    list_per_page = 50


@admin.register(Use)
class UseAdmin(admin.ModelAdmin):
    list_display = ['use_id', 'use_description']
    search_fields = ['use_description']
    list_per_page = 50


@admin.register(PartsDescription)
class PartsDescriptionAdmin(admin.ModelAdmin):
    list_display = ['parts_description_id', 'get_short_description']
    search_fields = ['parts_description']
    list_per_page = 50

    def get_short_description(self, obj):
        return obj.parts_description[:50] + "..." if len(obj.parts_description) > 50 else obj.parts_description
    get_short_description.short_description = 'Description'


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ['part_terminology_id', 'part_terminology_name', 'parts_description', 'rev_date']
    list_filter = ['rev_date']
    search_fields = ['part_terminology_name', 'parts_description__parts_description']
    date_hierarchy = 'rev_date'
    list_per_page = 50
    raw_id_fields = ['parts_description']


@admin.register(MeasurementGroup)
class MeasurementGroupAdmin(admin.ModelAdmin):
    list_display = ['measurement_group_id', 'measurement_group_name']
    search_fields = ['measurement_group_name']
    list_per_page = 50


@admin.register(MetaData)
class MetaDataAdmin(admin.ModelAdmin):
    list_display = ['meta_id', 'meta_name', 'data_type', 'min_length', 'max_length']
    list_filter = ['data_type', 'meta_format']
    search_fields = ['meta_name', 'meta_description']
    list_per_page = 50


@admin.register(MetaUOMCode)
class MetaUOMCodeAdmin(admin.ModelAdmin):
    list_display = ['meta_uom_id', 'uom_code', 'uom_description', 'measurement_group']
    list_filter = ['measurement_group']
    search_fields = ['uom_code', 'uom_description']
    raw_id_fields = ['measurement_group']
    list_per_page = 50


@admin.register(PartAttribute)
class PartAttributeAdmin(admin.ModelAdmin):
    list_display = ['pa_id', 'pa_name', 'get_short_description']
    search_fields = ['pa_name', 'pa_description']
    list_per_page = 50

    def get_short_description(self, obj):
        if obj.pa_description:
            return obj.pa_description[:50] + "..." if len(obj.pa_description) > 50 else obj.pa_description
        return "-"
    get_short_description.short_description = 'Description'


@admin.register(PartAttributeAssignment)
class PartAttributeAssignmentAdmin(admin.ModelAdmin):
    list_display = ['papt_id', 'part', 'part_attribute', 'meta_data']
    list_filter = ['part_attribute', 'meta_data']
    search_fields = ['part__part_terminology_name', 'part_attribute__pa_name']
    raw_id_fields = ['part', 'part_attribute', 'meta_data']
    list_per_page = 50


@admin.register(PIESSegment)
class PIESSegmentAdmin(admin.ModelAdmin):
    list_display = ['pies_segment_id', 'segment_abb', 'segment_name', 'get_short_description']
    search_fields = ['segment_abb', 'segment_name', 'segment_description']
    list_per_page = 50

    def get_short_description(self, obj):
        return obj.segment_description[:50] + "..." if len(obj.segment_description) > 50 else obj.segment_description
    get_short_description.short_description = 'Description'


@admin.register(PIESCode)
class PIESCodeAdmin(admin.ModelAdmin):
    list_display = ['pies_code_id', 'code_value', 'code_format', 'get_short_description']
    list_filter = ['code_format', 'source']
    search_fields = ['code_value', 'code_description']
    list_per_page = 50

    def get_short_description(self, obj):
        return obj.code_description[:50] + "..." if len(obj.code_description) > 50 else obj.code_description
    get_short_description.short_description = 'Description'


@admin.register(Change)
class ChangeAdmin(admin.ModelAdmin):
    list_display = ['change_id', 'request_id', 'change_reason', 'rev_date']
    list_filter = ['change_reason', 'rev_date']
    search_fields = ['request_id']
    date_hierarchy = 'rev_date'
    raw_id_fields = ['change_reason']
    list_per_page = 50


@admin.register(ChangeDetail)
class ChangeDetailAdmin(admin.ModelAdmin):
    list_display = ['change_detail_id', 'change', 'table_name', 'column_name', 'get_short_before', 'get_short_after']
    list_filter = ['change_attribute_state', 'table_name']
    search_fields = ['column_name', 'column_value_before', 'column_value_after']
    raw_id_fields = ['change', 'change_attribute_state', 'table_name']
    list_per_page = 50

    def get_short_before(self, obj):
        if obj.column_value_before:
            return obj.column_value_before[:30] + "..." if len(obj.column_value_before) > 30 else obj.column_value_before
        return "-"
    get_short_before.short_description = 'Before'

    def get_short_after(self, obj):
        if obj.column_value_after:
            return obj.column_value_after[:30] + "..." if len(obj.column_value_after) > 30 else obj.column_value_after
        return "-"
    get_short_after.short_description = 'After'


# Register remaining models with basic admin
admin.site.register(ChangeReason)
admin.site.register(ChangeTableName)
admin.site.register(ChangeAttributeState)
admin.site.register(MetaUOMCodeAssignment)
admin.site.register(PartPosition)
admin.site.register(PartCategory)
admin.site.register(PartsToAlias)
admin.site.register(PartsToUse)
admin.site.register(PartsRelationship)
admin.site.register(PartsSupersession)
admin.site.register(ValidValue)
admin.site.register(ValidValueAssignment)
admin.site.register(PIESExpiGroup)
admin.site.register(PIESExpiCode)
admin.site.register(PIESField)
admin.site.register(PIESReferenceFieldCode)
admin.site.register(Style)
admin.site.register(PartAttributeStyle)
admin.site.register(PartTypeStyle)
admin.site.register(CodeMaster)
admin.site.register(PCdbChange)
admin.site.register(RetiredTerm)
admin.site.register(Version)