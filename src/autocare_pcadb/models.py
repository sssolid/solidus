from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.validators import MinLengthValidator, MaxLengthValidator


class ACESCodedValues(models.Model):
    """ACES coded values for standardized automotive data"""
    element = models.CharField(max_length=255, null=True, blank=True, verbose_name="Element", db_column="Element")
    attribute = models.CharField(max_length=255, null=True, blank=True, verbose_name="Attribute", db_column="Attribute")
    coded_value = models.CharField(max_length=255, null=True, blank=True, verbose_name="Coded Value", db_column="CodedValue")
    code_description = models.CharField(max_length=255, null=True, blank=True, verbose_name="Code Description", db_column="CodeDescription")

    class Meta:
        db_table = 'pcadb_aces_coded_values'
        verbose_name = "ACES Coded Value"
        verbose_name_plural = "ACES Coded Values"
        ordering = ['element', 'attribute']
        indexes = [
            models.Index(fields=['element', 'attribute'], name='aces_element_attr_idx'),
            models.Index(fields=['coded_value'], name='aces_coded_value_idx'),
        ]

    def __str__(self):
        return f"{self.element} - {self.attribute}: {self.coded_value}"


class Alias(models.Model):
    """Part aliases for alternative naming"""
    alias_id = models.IntegerField(primary_key=True, verbose_name="Alias ID", db_column="AliasID")
    alias_name = models.CharField(max_length=100, verbose_name="Alias Name", db_column="AliasName")

    class Meta:
        db_table = 'pcadb_alias'
        verbose_name = "Alias"
        verbose_name_plural = "Aliases"
        ordering = ['alias_name']
        indexes = [
            models.Index(fields=['alias_name'], name='alias_name_idx'),
        ]

    def __str__(self):
        return self.alias_name


class Categories(models.Model):
    """Product categories"""
    category_id = models.IntegerField(primary_key=True, verbose_name="Category ID", db_column="CategoryID")
    category_name = models.CharField(max_length=100, verbose_name="Category Name", db_column="CategoryName")

    class Meta:
        db_table = 'pcadb_categories'
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['category_name']
        indexes = [
            models.Index(fields=['category_name'], name='category_name_idx'),
        ]

    def __str__(self):
        return self.category_name


class Subcategories(models.Model):
    """Product subcategories"""
    sub_category_id = models.IntegerField(primary_key=True, verbose_name="Subcategory ID", db_column="SubCategoryID")
    sub_category_name = models.CharField(max_length=100, verbose_name="Subcategory Name", db_column="SubCategoryName")

    class Meta:
        db_table = 'pcadb_subcategories'
        verbose_name = "Subcategory"
        verbose_name_plural = "Subcategories"
        ordering = ['sub_category_name']
        indexes = [
            models.Index(fields=['sub_category_name'], name='subcategory_name_idx'),
        ]

    def __str__(self):
        return self.sub_category_name


class Positions(models.Model):
    """Part positions"""
    position_id = models.IntegerField(primary_key=True, verbose_name="Position ID", db_column="PositionID")
    position = models.CharField(max_length=100, verbose_name="Position", db_column="Position")

    class Meta:
        db_table = 'pcadb_positions'
        verbose_name = "Position"
        verbose_name_plural = "Positions"
        ordering = ['position']
        indexes = [
            models.Index(fields=['position'], name='position_idx'),
        ]

    def __str__(self):
        return self.position


class Use(models.Model):
    """Part usage descriptions"""
    use_id = models.IntegerField(primary_key=True, verbose_name="Use ID", db_column="UseID")
    use_description = models.CharField(max_length=100, verbose_name="Use Description", db_column="UseDescription")

    class Meta:
        db_table = 'pcadb_use'
        verbose_name = "Use"
        verbose_name_plural = "Uses"
        ordering = ['use_description']
        indexes = [
            models.Index(fields=['use_description'], name='use_description_idx'),
        ]

    def __str__(self):
        return self.use_description


class PartsDescription(models.Model):
    """Detailed descriptions for parts"""
    parts_description_id = models.IntegerField(primary_key=True, verbose_name="Parts Description ID", db_column="PartsDescriptionID")
    parts_description = models.CharField(max_length=500, verbose_name="Parts Description", db_column="PartsDescription")

    class Meta:
        db_table = 'pcadb_parts_description'
        verbose_name = "Parts Description"
        verbose_name_plural = "Parts Descriptions"
        ordering = ['parts_description']
        indexes = [
            models.Index(fields=['parts_description'], name='parts_desc_idx'),
        ]

    def __str__(self):
        return self.parts_description[:50] + "..." if len(self.parts_description) > 50 else self.parts_description


class Parts(models.Model):
    """Main parts/terminology table"""
    part_terminology_id = models.IntegerField(primary_key=True, verbose_name="Part Terminology ID", db_column="PartTerminologyID")
    part_terminology_name = models.CharField(max_length=256, verbose_name="Part Terminology Name", db_column="PartTerminologyName")
    parts_description = models.ForeignKey(
        PartsDescription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Parts Description",
        db_column="PartsDescriptionID"
    )
    rev_date = models.DateField(null=True, blank=True, verbose_name="Revision Date", db_column="RevDate")

    class Meta:
        db_table = 'pcadb_parts'
        verbose_name = "Part"
        verbose_name_plural = "Parts"
        ordering = ['part_terminology_name']
        indexes = [
            models.Index(fields=['part_terminology_name'], name='part_name_idx'),
            models.Index(fields=['rev_date'], name='part_rev_date_idx'),
        ]

    def __str__(self):
        return self.part_terminology_name

    def get_absolute_url(self):
        return reverse('part-detail', kwargs={'pk': self.pk})


class MeasurementGroup(models.Model):
    """Groups for measurement units"""
    measurement_group_id = models.IntegerField(primary_key=True, verbose_name="Measurement Group ID", db_column="MeasurementGroupID")
    measurement_group_name = models.CharField(max_length=80, null=True, blank=True, verbose_name="Measurement Group Name", db_column="MeasurementGroupName")

    class Meta:
        db_table = 'pcadb_measurement_group'
        verbose_name = "Measurement Group"
        verbose_name_plural = "Measurement Groups"
        ordering = ['measurement_group_name']
        indexes = [
            models.Index(fields=['measurement_group_name'], name='measurement_group_name_idx'),
        ]

    def __str__(self):
        return self.measurement_group_name or f"Group {self.measurement_group_id}"


class MetaData(models.Model):
    """Metadata definitions for part attributes"""
    meta_id = models.IntegerField(primary_key=True, verbose_name="Meta ID", db_column="MetaID")
    meta_name = models.CharField(max_length=80, null=True, blank=True, verbose_name="Meta Name", db_column="MetaName")
    meta_description = models.CharField(max_length=512, null=True, blank=True, verbose_name="Meta Description", db_column="MetaDescr")
    meta_format = models.CharField(max_length=10, null=True, blank=True, verbose_name="Meta Format", db_column="MetaFormat")
    data_type = models.CharField(max_length=50, null=True, blank=True, verbose_name="Data Type", db_column="DataType")
    min_length = models.IntegerField(null=True, blank=True, verbose_name="Minimum Length", db_column="MinLength")
    max_length = models.IntegerField(null=True, blank=True, verbose_name="Maximum Length", db_column="MaxLength")

    class Meta:
        db_table = 'pcadb_meta_data'
        verbose_name = "Meta Data"
        verbose_name_plural = "Meta Data"
        ordering = ['meta_name']
        indexes = [
            models.Index(fields=['meta_name'], name='meta_name_idx'),
            models.Index(fields=['data_type'], name='meta_data_type_idx'),
        ]

    def __str__(self):
        return self.meta_name or f"Meta {self.meta_id}"


class MetaUOMCodes(models.Model):
    """Unit of measure codes"""
    meta_uom_id = models.IntegerField(primary_key=True, verbose_name="Meta UOM ID", db_column="MetaUOMID")
    uom_code = models.CharField(max_length=10, null=True, blank=True, verbose_name="UOM Code", db_column="UOMCode")
    uom_description = models.CharField(max_length=512, null=True, blank=True, verbose_name="UOM Description", db_column="UOMDescription")
    uom_label = models.CharField(max_length=10, null=True, blank=True, verbose_name="UOM Label", db_column="UOMLabel")
    measurement_group = models.ForeignKey(
        MeasurementGroup,
        on_delete=models.CASCADE,
        verbose_name="Measurement Group",
        db_column="MeasurementGroupID"
    )

    class Meta:
        db_table = 'pcadb_meta_uom_codes'
        verbose_name = "Meta UOM Code"
        verbose_name_plural = "Meta UOM Codes"
        ordering = ['uom_code']
        indexes = [
            models.Index(fields=['uom_code'], name='uom_code_idx'),
            models.Index(fields=['measurement_group'], name='uom_measurement_group_idx'),
        ]

    def __str__(self):
        return f"{self.uom_code} - {self.uom_description}" if self.uom_code and self.uom_description else str(self.meta_uom_id)


class PartAttributes(models.Model):
    """Part attributes definitions"""
    pa_id = models.IntegerField(primary_key=True, verbose_name="Part Attribute ID", db_column="PAID")
    pa_name = models.CharField(max_length=80, null=True, blank=True, verbose_name="Attribute Name", db_column="PAName")
    pa_description = models.CharField(max_length=512, null=True, blank=True, verbose_name="Attribute Description", db_column="PADescr")

    class Meta:
        db_table = 'pcadb_part_attributes'
        verbose_name = "Part Attribute"
        verbose_name_plural = "Part Attributes"
        ordering = ['pa_name']
        indexes = [
            models.Index(fields=['pa_name'], name='part_attr_name_idx'),
        ]

    def __str__(self):
        return self.pa_name or f"Attribute {self.pa_id}"


class PartAttributeAssignment(models.Model):
    """Assignment of attributes to parts with metadata"""
    papt_id = models.IntegerField(primary_key=True, verbose_name="Part Attribute Assignment ID", db_column="PAPTID")
    meta_data = models.ForeignKey(MetaData, on_delete=models.CASCADE, verbose_name="Meta Data", db_column="MetaID")
    part = models.ForeignKey(Parts, on_delete=models.CASCADE, verbose_name="Part", db_column="PartTerminologyID")
    part_attribute = models.ForeignKey(PartAttributes, on_delete=models.CASCADE, verbose_name="Part Attribute", db_column="PAID")

    class Meta:
        db_table = 'pcadb_part_attribute_assignment'
        verbose_name = "Part Attribute Assignment"
        verbose_name_plural = "Part Attribute Assignments"
        ordering = ['part', 'part_attribute']
        indexes = [
            models.Index(fields=['part', 'part_attribute'], name='part_attr_assignment_idx'),
            models.Index(fields=['meta_data'], name='part_attr_meta_idx'),
        ]
        unique_together = [['part', 'part_attribute', 'meta_data']]

    def __str__(self):
        return f"{self.part} - {self.part_attribute}"


class MetaUOMCodeAssignment(models.Model):
    """Assignment of UOM codes to part attribute assignments"""
    meta_uom_code_assignment_id = models.IntegerField(primary_key=True, verbose_name="Meta UOM Code Assignment ID", db_column="MetaUOMCodeAssignmentID")
    part_attribute_assignment = models.ForeignKey(
        PartAttributeAssignment,
        on_delete=models.CASCADE,
        verbose_name="Part Attribute Assignment",
        db_column="PAPTID"
    )
    meta_uom = models.ForeignKey(MetaUOMCodes, on_delete=models.CASCADE, verbose_name="Meta UOM", db_column="MetaUOMID")

    class Meta:
        db_table = 'pcadb_meta_uom_code_assignment'
        verbose_name = "Meta UOM Code Assignment"
        verbose_name_plural = "Meta UOM Code Assignments"
        ordering = ['part_attribute_assignment']
        indexes = [
            models.Index(fields=['part_attribute_assignment'], name='meta_uom_assignment_idx'),
            models.Index(fields=['meta_uom'], name='meta_uom_idx'),
        ]

    def __str__(self):
        return f"{self.part_attribute_assignment} - {self.meta_uom}"


class PartPosition(models.Model):
    """Part positions"""
    part_position_id = models.IntegerField(primary_key=True, verbose_name="Part Position ID", db_column="PartPositionID")
    part = models.ForeignKey(Parts, on_delete=models.CASCADE, verbose_name="Part", db_column="PartTerminologyID")
    position = models.ForeignKey(Positions, on_delete=models.CASCADE, verbose_name="Position", db_column="PositionID")
    rev_date = models.DateField(null=True, blank=True, verbose_name="Revision Date", db_column="RevDate")

    class Meta:
        db_table = 'pcadb_part_position'
        verbose_name = "Part Position"
        verbose_name_plural = "Part Positions"
        ordering = ['part', 'position']
        indexes = [
            models.Index(fields=['part'], name='part_position_part_idx'),
            models.Index(fields=['position'], name='part_position_pos_idx'),
            models.Index(fields=['rev_date'], name='part_position_rev_date_idx'),
        ]

    def __str__(self):
        return f"{self.part} - {self.position}"


class PartCategory(models.Model):
    """Part category assignments"""
    part_category_id = models.IntegerField(primary_key=True, verbose_name="Part Category ID", db_column="PartCategoryID")
    part = models.ForeignKey(Parts, on_delete=models.CASCADE, verbose_name="Part", db_column="PartTerminologyID")
    subcategory = models.ForeignKey(Subcategories, on_delete=models.CASCADE, verbose_name="Subcategory", db_column="SubCategoryID")
    category = models.ForeignKey(Categories, on_delete=models.CASCADE, verbose_name="Category", db_column="CategoryID")

    class Meta:
        db_table = 'pcadb_part_category'
        verbose_name = "Part Category"
        verbose_name_plural = "Part Categories"
        ordering = ['category', 'subcategory', 'part']
        indexes = [
            models.Index(fields=['part'], name='part_category_part_idx'),
            models.Index(fields=['category'], name='part_category_cat_idx'),
            models.Index(fields=['subcategory'], name='part_category_subcat_idx'),
        ]

    def __str__(self):
        return f"{self.part} - {self.category}/{self.subcategory}"


class PartsToAlias(models.Model):
    """Many-to-many relationship between parts and aliases"""
    part = models.ForeignKey(Parts, on_delete=models.CASCADE, verbose_name="Part", db_column="PartTerminologyID")
    alias = models.ForeignKey(Alias, on_delete=models.CASCADE, verbose_name="Alias", db_column="AliasID")

    class Meta:
        db_table = 'pcadb_parts_to_alias'
        verbose_name = "Parts to Alias"
        verbose_name_plural = "Parts to Aliases"
        ordering = ['part', 'alias']
        unique_together = [['part', 'alias']]
        indexes = [
            models.Index(fields=['part'], name='parts_to_alias_part_idx'),
            models.Index(fields=['alias'], name='parts_to_alias_alias_idx'),
        ]

    def __str__(self):
        return f"{self.part} -> {self.alias}"


class PartsToUse(models.Model):
    """Many-to-many relationship between parts and uses"""
    part = models.ForeignKey(Parts, on_delete=models.CASCADE, verbose_name="Part", db_column="PartTerminologyID")
    use = models.ForeignKey(Use, on_delete=models.CASCADE, verbose_name="Use", db_column="UseID")

    class Meta:
        db_table = 'pcadb_parts_to_use'
        verbose_name = "Parts to Use"
        verbose_name_plural = "Parts to Uses"
        ordering = ['part', 'use']
        unique_together = [['part', 'use']]
        indexes = [
            models.Index(fields=['part'], name='parts_to_use_part_idx'),
            models.Index(fields=['use'], name='parts_to_use_use_idx'),
        ]

    def __str__(self):
        return f"{self.part} -> {self.use}"


class PartsRelationship(models.Model):
    """Relationships between parts"""
    part = models.ForeignKey(
        Parts,
        on_delete=models.CASCADE,
        related_name='part_relationships',
        verbose_name="Part",
        db_column="PartTerminologyID"
    )
    related_part = models.ForeignKey(
        Parts,
        on_delete=models.CASCADE,
        related_name='related_to_parts',
        verbose_name="Related Part",
        db_column="RelatedPartTerminologyID"
    )

    class Meta:
        db_table = 'pcadb_parts_relationship'
        verbose_name = "Parts Relationship"
        verbose_name_plural = "Parts Relationships"
        ordering = ['part', 'related_part']
        unique_together = [['part', 'related_part']]
        indexes = [
            models.Index(fields=['part'], name='parts_rel_part_idx'),
            models.Index(fields=['related_part'], name='parts_rel_related_idx'),
        ]

    def __str__(self):
        return f"{self.part} -> {self.related_part}"


class PartsSupersession(models.Model):
    """Part supersession tracking"""
    parts_supersession_id = models.IntegerField(primary_key=True, verbose_name="Parts Supersession ID", db_column="PartsSupersessionId")
    old_part_terminology_id = models.IntegerField(verbose_name="Old Part Terminology ID", db_column="OldPartTerminologyID")
    old_part_terminology_name = models.CharField(max_length=256, verbose_name="Old Part Terminology Name", db_column="OldPartTerminologyName")
    new_part_terminology_id = models.IntegerField(verbose_name="New Part Terminology ID", db_column="NewPartTerminologyID")
    new_part_terminology_name = models.CharField(max_length=256, verbose_name="New Part Terminology Name", db_column="NewPartTerminologyName")
    rev_date = models.DateField(null=True, blank=True, verbose_name="Revision Date", db_column="RevDate")
    note = models.CharField(max_length=1000, null=True, blank=True, verbose_name="Note", db_column="Note")

    class Meta:
        db_table = 'pcadb_parts_supersession'
        verbose_name = "Parts Supersession"
        verbose_name_plural = "Parts Supersessions"
        ordering = ['-rev_date', 'old_part_terminology_name']
        indexes = [
            models.Index(fields=['old_part_terminology_id'], name='supersession_old_part_idx'),
            models.Index(fields=['new_part_terminology_id'], name='supersession_new_part_idx'),
            models.Index(fields=['rev_date'], name='supersession_rev_date_idx'),
        ]

    def __str__(self):
        return f"{self.old_part_terminology_name} -> {self.new_part_terminology_name}"


class ValidValues(models.Model):
    """Valid values for attributes"""
    valid_value_id = models.IntegerField(primary_key=True, verbose_name="Valid Value ID", db_column="ValidValueID")
    valid_value = models.CharField(max_length=100, verbose_name="Valid Value", db_column="ValidValue")

    class Meta:
        db_table = 'pcadb_valid_values'
        verbose_name = "Valid Value"
        verbose_name_plural = "Valid Values"
        ordering = ['valid_value']
        indexes = [
            models.Index(fields=['valid_value'], name='valid_value_idx'),
        ]

    def __str__(self):
        return self.valid_value


class ValidValueAssignment(models.Model):
    """Assignment of valid values to part attribute assignments"""
    valid_value_assignment_id = models.IntegerField(primary_key=True, verbose_name="Valid Value Assignment ID", db_column="ValidValueAssignmentID")
    part_attribute_assignment = models.ForeignKey(
        PartAttributeAssignment,
        on_delete=models.CASCADE,
        verbose_name="Part Attribute Assignment",
        db_column="PAPTID"
    )
    valid_value = models.ForeignKey(ValidValues, on_delete=models.CASCADE, verbose_name="Valid Value", db_column="ValidValueID")

    class Meta:
        db_table = 'pcadb_valid_value_assignment'
        verbose_name = "Valid Value Assignment"
        verbose_name_plural = "Valid Value Assignments"
        ordering = ['part_attribute_assignment', 'valid_value']
        indexes = [
            models.Index(fields=['part_attribute_assignment'], name='valid_value_assignment_idx'),
            models.Index(fields=['valid_value'], name='valid_value_assignment_val_idx'),
        ]

    def __str__(self):
        return f"{self.part_attribute_assignment} - {self.valid_value}"


# PIES-related models
class PIESSegment(models.Model):
    """PIES segments"""
    pies_segment_id = models.IntegerField(primary_key=True, verbose_name="PIES Segment ID", db_column="PIESSegmentId")
    segment_abb = models.CharField(max_length=50, verbose_name="Segment Abbreviation", db_column="SegmentAbb")
    segment_name = models.CharField(max_length=50, verbose_name="Segment Name", db_column="SegmentName")
    segment_description = models.CharField(max_length=250, verbose_name="Segment Description", db_column="SegmentDescription")

    class Meta:
        db_table = 'pcadb_pies_segment'
        verbose_name = "PIES Segment"
        verbose_name_plural = "PIES Segments"
        ordering = ['segment_name']
        indexes = [
            models.Index(fields=['segment_abb'], name='pies_segment_abb_idx'),
            models.Index(fields=['segment_name'], name='pies_segment_name_idx'),
        ]

    def __str__(self):
        return f"{self.segment_abb} - {self.segment_name}"


class PIESCode(models.Model):
    """PIES codes"""
    pies_code_id = models.IntegerField(primary_key=True, verbose_name="PIES Code ID", db_column="PIESCodeId")
    code_value = models.CharField(max_length=255, verbose_name="Code Value", db_column="CodeValue")
    code_format = models.CharField(max_length=255, verbose_name="Code Format", db_column="CodeFormat")
    field_format = models.CharField(max_length=255, null=True, blank=True, verbose_name="Field Format", db_column="FieldFormat")
    code_description = models.CharField(max_length=255, verbose_name="Code Description", db_column="CodeDescription")
    source = models.CharField(max_length=255, null=True, blank=True, verbose_name="Source", db_column="Source")

    class Meta:
        db_table = 'pcadb_pies_code'
        verbose_name = "PIES Code"
        verbose_name_plural = "PIES Codes"
        ordering = ['code_value']
        indexes = [
            models.Index(fields=['code_value'], name='pies_code_value_idx'),
            models.Index(fields=['source'], name='pies_code_source_idx'),
        ]

    def __str__(self):
        return f"{self.code_value} - {self.code_description}"


class PIESExpiGroup(models.Model):
    """PIES expiration groups"""
    pies_expi_group_id = models.IntegerField(primary_key=True, verbose_name="PIES Expi Group ID", db_column="PIESExpiGroupId")
    expi_group_code = models.CharField(max_length=255, verbose_name="Expi Group Code", db_column="ExpiGroupCode")
    expi_group_description = models.CharField(max_length=255, verbose_name="Expi Group Description", db_column="ExpiGroupDescription")

    class Meta:
        db_table = 'pcadb_pies_expi_group'
        verbose_name = "PIES Expi Group"
        verbose_name_plural = "PIES Expi Groups"
        ordering = ['expi_group_code']
        indexes = [
            models.Index(fields=['expi_group_code'], name='pies_expi_group_code_idx'),
        ]

    def __str__(self):
        return f"{self.expi_group_code} - {self.expi_group_description}"


class PIESExpiCode(models.Model):
    """PIES expiration codes"""
    pies_expi_code_id = models.IntegerField(primary_key=True, verbose_name="PIES Expi Code ID", db_column="PIESExpiCodeId")
    expi_code = models.CharField(max_length=50, verbose_name="Expi Code", db_column="ExpiCode")
    expi_code_description = models.CharField(max_length=255, verbose_name="Expi Code Description", db_column="ExpiCodeDescription")
    pies_expi_group = models.ForeignKey(
        PIESExpiGroup,
        on_delete=models.CASCADE,
        verbose_name="PIES Expi Group",
        db_column="PIESExpiGroupId"
    )

    class Meta:
        db_table = 'pcadb_pies_expi_code'
        verbose_name = "PIES Expi Code"
        verbose_name_plural = "PIES Expi Codes"
        ordering = ['expi_code']
        indexes = [
            models.Index(fields=['expi_code'], name='pies_expi_code_idx'),
            models.Index(fields=['pies_expi_group'], name='pies_expi_group_idx'),
        ]

    def __str__(self):
        return f"{self.expi_code} - {self.expi_code_description}"


class PIESField(models.Model):
    """PIES fields"""
    pies_field_id = models.IntegerField(primary_key=True, verbose_name="PIES Field ID", db_column="PIESFieldId")
    field_name = models.CharField(max_length=255, verbose_name="Field Name", db_column="FieldName")
    reference_field_number = models.CharField(max_length=255, verbose_name="Reference Field Number", db_column="ReferenceFieldNumber")
    pies_segment = models.ForeignKey(PIESSegment, on_delete=models.CASCADE, verbose_name="PIES Segment", db_column="PIESSegmentId")

    class Meta:
        db_table = 'pcadb_pies_field'
        verbose_name = "PIES Field"
        verbose_name_plural = "PIES Fields"
        ordering = ['field_name']
        indexes = [
            models.Index(fields=['field_name'], name='pies_field_name_idx'),
            models.Index(fields=['reference_field_number'], name='pies_field_ref_num_idx'),
            models.Index(fields=['pies_segment'], name='pies_field_segment_idx'),
        ]

    def __str__(self):
        return f"{self.field_name} ({self.reference_field_number})"


class PIESReferenceFieldCode(models.Model):
    """PIES reference field codes"""
    pies_reference_field_code_id = models.IntegerField(primary_key=True, verbose_name="PIES Reference Field Code ID", db_column="PIESReferenceFieldCodeId")
    pies_field = models.ForeignKey(PIESField, on_delete=models.CASCADE, verbose_name="PIES Field", db_column="PIESFieldId")
    pies_code = models.ForeignKey(PIESCode, on_delete=models.CASCADE, verbose_name="PIES Code", db_column="PIESCodeId")
    pies_expi_code = models.ForeignKey(
        PIESExpiCode,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="PIES Expi Code",
        db_column="PIESExpiCodeId"
    )
    reference_notes = models.CharField(max_length=2000, null=True, blank=True, verbose_name="Reference Notes", db_column="ReferenceNotes")

    class Meta:
        db_table = 'pcadb_pies_reference_field_code'
        verbose_name = "PIES Reference Field Code"
        verbose_name_plural = "PIES Reference Field Codes"
        ordering = ['pies_field', 'pies_code']
        indexes = [
            models.Index(fields=['pies_field'], name='pies_ref_field_idx'),
            models.Index(fields=['pies_code'], name='pies_ref_code_idx'),
            models.Index(fields=['pies_expi_code'], name='pies_ref_expi_idx'),
        ]

    def __str__(self):
        return f"{self.pies_field} - {self.pies_code}"


# Audit/Change tracking models
class ChangeReasons(models.Model):
    """Reasons for changes"""
    change_reason_id = models.IntegerField(primary_key=True, verbose_name="Change Reason ID", db_column="ChangeReasonID")
    change_reason = models.CharField(max_length=255, verbose_name="Change Reason", db_column="ChangeReason")

    class Meta:
        db_table = 'pcadb_change_reasons'
        verbose_name = "Change Reason"
        verbose_name_plural = "Change Reasons"
        ordering = ['change_reason']
        indexes = [
            models.Index(fields=['change_reason'], name='change_reason_idx'),
        ]

    def __str__(self):
        return self.change_reason


class ChangeTableNames(models.Model):
    """Table names for change tracking"""
    table_name_id = models.IntegerField(primary_key=True, verbose_name="Table Name ID", db_column="TableNameID")
    table_name = models.CharField(max_length=255, verbose_name="Table Name", db_column="TableName")
    table_description = models.CharField(max_length=1000, null=True, blank=True, verbose_name="Table Description", db_column="TableDescription")

    class Meta:
        db_table = 'pcadb_change_table_names'
        verbose_name = "Change Table Name"
        verbose_name_plural = "Change Table Names"
        ordering = ['table_name']
        indexes = [
            models.Index(fields=['table_name'], name='change_table_name_idx'),
        ]

    def __str__(self):
        return self.table_name


class ChangeAttributeStates(models.Model):
    """States for change attributes"""
    change_attribute_state_id = models.IntegerField(primary_key=True, verbose_name="Change Attribute State ID", db_column="ChangeAttributeStateID")
    change_attribute_state = models.CharField(max_length=255, verbose_name="Change Attribute State", db_column="ChangeAttributeState")

    class Meta:
        db_table = 'pcadb_change_attribute_states'
        verbose_name = "Change Attribute State"
        verbose_name_plural = "Change Attribute States"
        ordering = ['change_attribute_state']
        indexes = [
            models.Index(fields=['change_attribute_state'], name='change_attr_state_idx'),
        ]

    def __str__(self):
        return self.change_attribute_state


class Changes(models.Model):
    """Main change tracking table"""
    change_id = models.IntegerField(primary_key=True, verbose_name="Change ID", db_column="ChangeID")
    request_id = models.IntegerField(verbose_name="Request ID", db_column="RequestID")
    change_reason = models.ForeignKey(ChangeReasons, on_delete=models.CASCADE, verbose_name="Change Reason", db_column="ChangeReasonID")
    rev_date = models.DateField(null=True, blank=True, verbose_name="Revision Date", db_column="RevDate")

    class Meta:
        db_table = 'pcadb_changes'
        verbose_name = "Change"
        verbose_name_plural = "Changes"
        ordering = ['-rev_date', '-change_id']
        indexes = [
            models.Index(fields=['request_id'], name='change_request_id_idx'),
            models.Index(fields=['rev_date'], name='change_rev_date_idx'),
            models.Index(fields=['change_reason'], name='change_reason_fk_idx'),
        ]

    def __str__(self):
        return f"Change {self.change_id} - {self.change_reason}"


class ChangeDetails(models.Model):
    """Detailed change tracking"""
    change_detail_id = models.IntegerField(primary_key=True, verbose_name="Change Detail ID", db_column="ChangeDetailID")
    change = models.ForeignKey(Changes, on_delete=models.CASCADE, verbose_name="Change", db_column="ChangeID")
    change_attribute_state = models.ForeignKey(
        ChangeAttributeStates,
        on_delete=models.CASCADE,
        verbose_name="Change Attribute State",
        db_column="ChangeAttributeStateID"
    )
    table_name = models.ForeignKey(ChangeTableNames, on_delete=models.CASCADE, verbose_name="Table Name", db_column="TableNameID")
    primary_key_column_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Primary Key Column Name", db_column="PrimaryKeyColumnName")
    primary_key_before = models.IntegerField(null=True, blank=True, verbose_name="Primary Key Before", db_column="PrimaryKeyBefore")
    primary_key_after = models.IntegerField(null=True, blank=True, verbose_name="Primary Key After", db_column="PrimaryKeyAfter")
    column_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Column Name", db_column="ColumnName")
    column_value_before = models.CharField(max_length=1000, null=True, blank=True, verbose_name="Column Value Before", db_column="ColumnValueBefore")
    column_value_after = models.CharField(max_length=1000, null=True, blank=True, verbose_name="Column Value After", db_column="ColumnValueAfter")

    class Meta:
        db_table = 'pcadb_change_details'
        verbose_name = "Change Detail"
        verbose_name_plural = "Change Details"
        ordering = ['change', 'change_detail_id']
        indexes = [
            models.Index(fields=['change'], name='change_detail_change_idx'),
            models.Index(fields=['table_name'], name='change_detail_table_idx'),
            models.Index(fields=['primary_key_before'], name='change_detail_pk_before_idx'),
            models.Index(fields=['primary_key_after'], name='change_detail_pk_after_idx'),
        ]

    def __str__(self):
        return f"Change Detail {self.change_detail_id} - {self.change}"


# Lookup/Style tables
class Style(models.Model):
    """Styling information"""
    style_id = models.IntegerField(primary_key=True, verbose_name="Style ID", db_column="StyleID")
    style_name = models.CharField(max_length=80, null=True, blank=True, verbose_name="Style Name", db_column="StyleName")

    class Meta:
        db_table = 'pcadb_style'
        verbose_name = "Style"
        verbose_name_plural = "Styles"
        ordering = ['style_name']
        indexes = [
            models.Index(fields=['style_name'], name='style_name_idx'),
        ]

    def __str__(self):
        return self.style_name or f"Style {self.style_id}"


class PartAttributeStyle(models.Model):
    """Styling for part attributes"""
    style = models.ForeignKey(Style, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Style", db_column="StyleID")
    part_attribute_assignment = models.ForeignKey(
        PartAttributeAssignment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Part Attribute Assignment",
        db_column="PAPTID"
    )

    class Meta:
        db_table = 'pcadb_part_attribute_style'
        verbose_name = "Part Attribute Style"
        verbose_name_plural = "Part Attribute Styles"
        ordering = ['style', 'part_attribute_assignment']
        indexes = [
            models.Index(fields=['style'], name='part_attr_style_style_idx'),
            models.Index(fields=['part_attribute_assignment'], name='part_attr_style_papt_idx'),
        ]

    def __str__(self):
        return f"{self.style} - {self.part_attribute_assignment}"


class PartTypeStyle(models.Model):
    """Styling for part types"""
    style = models.ForeignKey(Style, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Style", db_column="StyleID")
    part = models.ForeignKey(Parts, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Part", db_column="PartTerminologyID")

    class Meta:
        db_table = 'pcadb_part_type_style'
        verbose_name = "Part Type Style"
        verbose_name_plural = "Part Type Styles"
        ordering = ['style', 'part']
        indexes = [
            models.Index(fields=['style'], name='part_type_style_style_idx'),
            models.Index(fields=['part'], name='part_type_style_part_idx'),
        ]

    def __str__(self):
        return f"{self.style} - {self.part}"


class CodeMaster(models.Model):
    """Master codes linking parts to categories and positions"""
    code_master_id = models.IntegerField(primary_key=True, verbose_name="Code Master ID", db_column="CodeMasterID")
    part = models.ForeignKey(Parts, on_delete=models.CASCADE, verbose_name="Part", db_column="PartTerminologyID")
    category = models.ForeignKey(Categories, on_delete=models.CASCADE, verbose_name="Category", db_column="CategoryID")
    subcategory = models.ForeignKey(Subcategories, on_delete=models.CASCADE, verbose_name="Subcategory", db_column="SubCategoryID")
    position = models.ForeignKey(Positions, on_delete=models.CASCADE, verbose_name="Position", db_column="PositionID")
    rev_date = models.DateField(null=True, blank=True, verbose_name="Revision Date", db_column="RevDate")

    class Meta:
        db_table = 'pcadb_code_master'
        verbose_name = "Code Master"
        verbose_name_plural = "Code Masters"
        ordering = ['category', 'subcategory', 'part']
        indexes = [
            models.Index(fields=['part'], name='code_master_part_idx'),
            models.Index(fields=['category'], name='code_master_category_idx'),
            models.Index(fields=['subcategory'], name='code_master_subcategory_idx'),
            models.Index(fields=['position'], name='code_master_position_idx'),
            models.Index(fields=['rev_date'], name='code_master_rev_date_idx'),
        ]

    def __str__(self):
        return f"{self.part} - {self.category}/{self.subcategory}"


class PCdbChanges(models.Model):
    """PCdb change tracking"""
    code_master_id = models.IntegerField(null=True, blank=True, verbose_name="Code Master ID", db_column="CodeMasterID")
    category_id = models.IntegerField(null=True, blank=True, verbose_name="Category ID", db_column="CategoryID")
    category_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Category Name", db_column="CategoryName")
    sub_category_id = models.IntegerField(null=True, blank=True, verbose_name="Sub Category ID", db_column="SubCategoryID")
    sub_category_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Sub Category Name", db_column="SubCategoryName")
    part_terminology_id = models.IntegerField(null=True, blank=True, verbose_name="Part Terminology ID", db_column="PartTerminologyID")
    part_terminology_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Part Terminology Name", db_column="PartTerminologyName")
    use_id = models.IntegerField(null=True, blank=True, verbose_name="Use ID", db_column="UseID")
    use_description = models.CharField(max_length=100, null=True, blank=True, verbose_name="Use Description", db_column="UseDescription")
    position_id = models.IntegerField(null=True, blank=True, verbose_name="Position ID", db_column="PositionID")
    position = models.CharField(max_length=100, null=True, blank=True, verbose_name="Position", db_column="Position")
    rev_date = models.DateField(null=True, blank=True, verbose_name="Revision Date", db_column="RevDate")
    action = models.CharField(max_length=20, null=True, blank=True, verbose_name="Action", db_column="Action")

    class Meta:
        db_table = 'pcadb_pcdb_changes'
        verbose_name = "PCdb Change"
        verbose_name_plural = "PCdb Changes"
        ordering = ['-rev_date', '-id']
        indexes = [
            models.Index(fields=['code_master_id'], name='pcdb_code_master_idx'),
            models.Index(fields=['part_terminology_id'], name='pcdb_part_terminology_idx'),
            models.Index(fields=['rev_date'], name='pcdb_rev_date_idx'),
            models.Index(fields=['action'], name='pcdb_action_idx'),
        ]

    def __str__(self):
        return f"PCdb Change {self.id} - {self.action}"


class RetiredTerms(models.Model):
    """Retired terminology tracking"""
    part_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Part Name", db_column="PartName")
    part_id_code = models.IntegerField(null=True, blank=True, verbose_name="Part ID Code", db_column="PartIDCode")

    class Meta:
        db_table = 'pcadb_retired_terms'
        verbose_name = "Retired Term"
        verbose_name_plural = "Retired Terms"
        ordering = ['part_name']
        indexes = [
            models.Index(fields=['part_name'], name='retired_term_name_idx'),
            models.Index(fields=['part_id_code'], name='retired_term_id_idx'),
        ]

    def __str__(self):
        return self.part_name or f"Retired Term {self.id}"


class Version(models.Model):
    """Version tracking"""
    version_date = models.DateField(null=True, blank=True, verbose_name="Version Date", db_column="VersionDate")

    class Meta:
        db_table = 'pcadb_version'
        verbose_name = "Version"
        verbose_name_plural = "Versions"
        ordering = ['-version_date']
        indexes = [
            models.Index(fields=['version_date'], name='version_date_idx'),
        ]

    def __str__(self):
        return f"Version {self.version_date}" if self.version_date else f"Version {self.id}"