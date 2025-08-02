# src/feeds/generators.py
import csv
import io
import json
import logging
from xml.etree import ElementTree as ET

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Prefetch

from assets.models import Asset
from products.models import CustomerPricing, Product, ProductFitment

logger = logging.getLogger("solidus.feeds")


class BaseFeedGenerator:
    """Base class for feed generators"""

    def __init__(self, feed):
        self.feed = feed
        self.temp_file = None

    def generate(self, generation):
        """Generate the feed file"""
        raise NotImplementedError

    def get_queryset(self):
        """Get the base queryset for the feed"""
        if self.feed.feed_type == "product_catalog":
            queryset = Product.objects.filter(is_active=True)

            # Apply filters
            if self.feed.categories.exists():
                queryset = queryset.filter(categories__in=self.feed.categories.all())
            if self.feed.brands.exists():
                queryset = queryset.filter(brand__in=self.feed.brands.all())
            if self.feed.product_tags:
                queryset = queryset.filter(tags__name__in=self.feed.product_tags)

            # Prefetch related data
            queryset = queryset.select_related("brand").prefetch_related(
                "categories",
                "tags",
                Prefetch(
                    "customer_prices",
                    queryset=CustomerPricing.objects.filter(
                        customer=self.feed.customer
                    ),
                    to_attr="customer_pricing",
                ),
            )

            return queryset.distinct()

        elif self.feed.feed_type == "assets":
            queryset = Asset.objects.filter(is_active=True)

            # Filter by categories accessible to customer
            if self.feed.customer.is_customer:
                if self.feed.customer.allowed_asset_categories:
                    queryset = queryset.filter(
                        categories__slug__in=self.feed.customer.allowed_asset_categories
                    )

            return queryset.prefetch_related("categories", "tags", "files")

        elif self.feed.feed_type == "fitment":
            queryset = ProductFitment.objects.select_related("product", "make", "model")

            # Apply product filters
            if self.feed.categories.exists():
                queryset = queryset.filter(
                    product__categories__in=self.feed.categories.all()
                )
            if self.feed.brands.exists():
                queryset = queryset.filter(product__brand__in=self.feed.brands.all())

            return queryset.distinct()

        return None

    def get_field_value(self, obj, field_name):
        """Get field value with custom mapping support"""
        # Check custom mapping first
        if field_name in self.feed.custom_field_mapping:
            mapped_field = self.feed.custom_field_mapping[field_name]
            if "." in mapped_field:
                # Handle related fields
                parts = mapped_field.split(".")
                value = obj
                for part in parts:
                    value = getattr(value, part, None)
                    if value is None:
                        break
                return value
            return getattr(obj, mapped_field, None)

        # Default field access
        return getattr(obj, field_name, None)

    def save_file(self, generation, content, filename):
        """Save the generated file"""
        try:
            # Create file path
            file_path = (
                f"feeds/{self.feed.customer.id}/{generation.generation_id}/{filename}"
            )

            # Save to storage
            saved_path = default_storage.save(file_path, ContentFile(content))

            # Get file size
            file_size = default_storage.size(saved_path)

            return {"success": True, "file_path": saved_path, "file_size": file_size}

        except Exception as e:
            logger.error(f"Error saving feed file: {str(e)}")
            return {"success": False, "error": str(e)}


class CSVFeedGenerator(BaseFeedGenerator):
    """Generate CSV format feeds"""

    def generate(self, generation):
        try:
            queryset = self.get_queryset()
            if queryset is None:
                raise ValueError(f"Unsupported feed type: {self.feed.feed_type}")

            # Get fields
            fields = self.feed.included_fields or self.get_default_fields()

            # Use in-memory CSV stream
            buffer = io.StringIO()
            writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL)

            # Write header
            writer.writerow(fields)

            row_count = 0
            for obj in queryset:
                row = []
                for field in fields:
                    value = self.get_field_value(obj, field)

                    if value is None:
                        value = ""
                    elif isinstance(value, list):
                        value = "|".join(str(v) for v in value)
                    elif hasattr(value, "all"):  # ManyToMany
                        value = "|".join(str(v) for v in value.all())
                    else:
                        value = str(value)

                    row.append(value)

                writer.writerow(row)
                row_count += 1

            content = buffer.getvalue().encode("utf-8")
            filename = f"{self.feed.slug}_{generation.generation_id}.csv"

            result = self.save_file(generation, content, filename)
            if result["success"]:
                result["row_count"] = row_count

            return result

        except Exception as e:
            logger.error(f"Error generating CSV feed: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_default_fields(self):
        """Get default fields based on feed type"""
        if self.feed.feed_type == "product_catalog":
            return [
                "sku",
                "name",
                "brand",
                "categories",
                "short_description",
                "msrp",
                "customer_price",
                "part_numbers",
                "oem_numbers",
                "length",
                "width",
                "height",
                "weight",
            ]
        elif self.feed.feed_type == "assets":
            return [
                "id",
                "title",
                "description",
                "asset_type",
                "categories",
                "tags",
                "file_url",
                "thumbnail_url",
                "file_size",
                "created_at",
            ]
        elif self.feed.feed_type == "fitment":
            return [
                "sku",
                "make",
                "model",
                "year_start",
                "year_end",
                "submodel",
                "engine",
                "position",
                "notes",
            ]
        return []


class XMLFeedGenerator(BaseFeedGenerator):
    """Generate XML format feeds"""

    def generate(self, generation):
        try:
            queryset = self.get_queryset()
            if queryset is None:
                raise ValueError(f"Unsupported feed type: {self.feed.feed_type}")

            # Create root element
            root = ET.Element("feed")
            root.set("type", self.feed.feed_type)
            root.set("generated", generation.started_at.isoformat())

            # Add metadata
            metadata = ET.SubElement(root, "metadata")
            ET.SubElement(metadata, "customer").text = str(
                self.feed.customer.company_name or self.feed.customer.username
            )
            ET.SubElement(metadata, "feed_name").text = self.feed.name
            ET.SubElement(metadata, "generation_id").text = str(
                generation.generation_id
            )

            # Add items
            items = ET.SubElement(root, "items")
            fields = self.feed.included_fields or self.get_default_fields()

            row_count = 0
            for obj in queryset:
                item = ET.SubElement(items, "item")

                for field in fields:
                    value = self.get_field_value(obj, field)

                    if value is not None:
                        field_elem = ET.SubElement(item, field.replace("_", "-"))

                        if isinstance(value, list):
                            for v in value:
                                ET.SubElement(field_elem, "value").text = str(v)
                        elif hasattr(value, "all"):  # ManyToMany
                            for v in value.all():
                                ET.SubElement(field_elem, "value").text = str(v)
                        else:
                            field_elem.text = str(value)

                row_count += 1

            # Convert to string
            xml_string = ET.tostring(root, encoding="unicode", method="xml")

            # Pretty print
            from xml.dom import minidom

            dom = minidom.parseString(xml_string)
            pretty_xml = dom.toprettyxml(indent="  ")

            # Save file
            content = pretty_xml.encode("utf-8")
            filename = f"{self.feed.slug}_{generation.generation_id}.xml"

            result = self.save_file(generation, content, filename)
            if result["success"]:
                result["row_count"] = row_count

            return result

        except Exception as e:
            logger.error(f"Error generating XML feed: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_default_fields(self):
        """Get default fields - same as CSV"""
        csv_gen = CSVFeedGenerator(self.feed)
        return csv_gen.get_default_fields()


class JSONFeedGenerator(BaseFeedGenerator):
    """Generate JSON format feeds"""

    def generate(self, generation):
        try:
            queryset = self.get_queryset()
            if queryset is None:
                raise ValueError(f"Unsupported feed type: {self.feed.feed_type}")

            # Build JSON structure
            data = {
                "feed": {
                    "type": self.feed.feed_type,
                    "name": self.feed.name,
                    "generated": generation.started_at.isoformat(),
                    "generation_id": str(generation.generation_id),
                    "customer": self.feed.customer.company_name
                    or self.feed.customer.username,
                },
                "items": [],
            }

            fields = self.feed.included_fields or self.get_default_fields()

            for obj in queryset:
                item = {}

                for field in fields:
                    value = self.get_field_value(obj, field)

                    if value is not None:
                        if hasattr(value, "all"):  # ManyToMany
                            value = [str(v) for v in value.all()]
                        elif hasattr(value, "isoformat"):  # DateTime
                            value = value.isoformat()
                        elif isinstance(value, list):
                            value = [str(v) for v in value]
                        else:
                            value = str(value)

                        item[field] = value

                data["items"].append(item)

            # Save file
            content = json.dumps(data, indent=2).encode("utf-8")
            filename = f"{self.feed.slug}_{generation.generation_id}.json"

            result = self.save_file(generation, content, filename)
            if result["success"]:
                result["row_count"] = len(data["items"])

            return result

        except Exception as e:
            logger.error(f"Error generating JSON feed: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_default_fields(self):
        """Get default fields - same as CSV"""
        csv_gen = CSVFeedGenerator(self.feed)
        return csv_gen.get_default_fields()


class FeedGeneratorFactory:
    """Factory to get appropriate feed generator"""

    generators = {
        "csv": CSVFeedGenerator,
        "xml": XMLFeedGenerator,
        "json": JSONFeedGenerator,
        "txt": CSVFeedGenerator,  # Tab-delimited can use CSV generator with modifications
    }

    @classmethod
    def get_generator(cls, feed):
        """Get generator instance for feed"""
        generator_class = cls.generators.get(feed.format)
        if not generator_class:
            raise ValueError(f"Unsupported feed format: {feed.format}")

        return generator_class(feed)
