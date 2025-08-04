# src/assets/utils.py
import hashlib
import json
import logging
import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image

logger = logging.getLogger("solidus.assets")


class ImageProcessor:
    """Handle image processing with ImageMagick"""

    @staticmethod
    def process_image(
        input_path, output_path, max_width=None, max_height=None, quality=85
    ):
        """Process image using ImageMagick"""
        try:
            cmd = [settings.IMAGEMAGICK_PATH, input_path]

            # Auto-orient based on EXIF data
            cmd.extend(["-auto-orient"])

            # Strip metadata but preserve color profile
            cmd.extend(["-strip"])

            # Resize if dimensions provided
            if max_width and max_height:
                cmd.extend(["-resize", f"{max_width}x{max_height}>"])

            # Set quality
            cmd.extend(["-quality", str(quality)])

            # Output path
            cmd.append(output_path)

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"ImageMagick error: {result.stderr}")
                return False

            return True

        except Exception as e:
            logger.error(f"Image processing error: {str(e)}")
            return False

    @staticmethod
    def generate_thumbnail(input_path, output_path, size=(150, 150)):
        """Generate thumbnail using ImageMagick"""
        try:
            width, height = size

            cmd = [
                settings.IMAGEMAGICK_PATH,
                input_path,
                "-auto-orient",
                "-strip",
                "-thumbnail",
                f"{width}x{height}^",
                "-gravity",
                "center",
                "-extent",
                f"{width}x{height}",
                "-quality",
                "80",
                output_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Thumbnail generation error: {str(e)}")
            return False

    @staticmethod
    def get_image_info(image_path):
        """Get image dimensions and format"""
        try:
            with Image.open(image_path) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                }
        except Exception as e:
            logger.error(f"Error getting image info: {str(e)}")
            return None


class ExifProcessor:
    """Handle EXIF metadata extraction and manipulation"""

    @staticmethod
    def extract_metadata(file_path):
        """Extract metadata using ExifTool"""
        try:
            cmd = [settings.EXIFTOOL_PATH, "-json", "-all", file_path]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                metadata = json.loads(result.stdout)[0]

                # Clean up metadata
                cleaned = {}
                for key, value in metadata.items():
                    if key.startswith("File:") or key.startswith("ExifTool:"):
                        continue
                    cleaned[key] = value

                return cleaned

            return {}

        except Exception as e:
            logger.error(f"EXIF extraction error: {str(e)}")
            return {}

    @staticmethod
    def write_metadata(file_path, metadata):
        """Write metadata to file using ExifTool"""
        try:
            cmd = [settings.EXIFTOOL_PATH, "-overwrite_original"]

            # Add metadata arguments
            for key, value in metadata.items():
                cmd.extend([f"-{key}={value}"])

            cmd.append(file_path)

            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0

        except Exception as e:
            logger.error(f"EXIF write error: {str(e)}")
            return False

    @staticmethod
    def extract_tags_from_metadata(metadata):
        """Extract useful tags from metadata"""
        tags = set()

        # Keywords
        if "Keywords" in metadata:
            if isinstance(metadata["Keywords"], list):
                tags.update(metadata["Keywords"])
            else:
                tags.add(metadata["Keywords"])

        # Camera info
        if "Make" in metadata:
            tags.add(metadata["Make"])
        if "Model" in metadata:
            tags.add(metadata["Model"])

        # Location
        if "City" in metadata:
            tags.add(metadata["City"])
        if "Country" in metadata:
            tags.add(metadata["Country"])

        # Clean tags
        tags = {tag.strip().lower() for tag in tags if tag and isinstance(tag, str)}

        return list(tags)


class AssetFileHandler:
    """Handle asset file operations"""

    @staticmethod
    def calculate_file_hash(file_obj):
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()

        # Reset file position
        file_obj.seek(0)

        # Read in chunks
        for chunk in iter(lambda: file_obj.read(4096), b""):
            sha256_hash.update(chunk)

        # Reset file position
        file_obj.seek(0)

        return sha256_hash.hexdigest()

    @staticmethod
    def organize_file_path(asset, filename):
        """Generate organized file path based on asset type and date"""
        from datetime import datetime

        # Get file extension
        ext = os.path.splitext(filename)[1].lower()

        # Build path components
        date = datetime.now()
        path_components = [
            settings.ASSET_UPLOAD_PATH,
            asset.asset_type,
            str(date.year),
            f"{date.month:02d}",
            f"{date.day:02d}",
            f"{asset.file_hash[:2]}",  # First 2 chars of hash for distribution
            f"{asset.file_hash}{ext}",
        ]

        return os.path.join(*path_components)

    @staticmethod
    def save_processed_versions(asset_file, original_path):
        """Generate and save processed versions of the asset"""
        if asset_file.asset.asset_type != "image":
            return True

        try:
            # Paths for processed versions
            base_path = os.path.splitext(original_path)[0]
            ext = os.path.splitext(original_path)[1]

            # Generate main processed version
            processed_path = f"{base_path}_processed{ext}"
            temp_processed = Path(f"/tmp/{os.path.basename(processed_path)}")

            # Download original for processing
            with default_storage.open(original_path, "rb") as f:
                temp_original = Path(f"/tmp/{os.path.basename(original_path)}")
                temp_original.write_bytes(f.read())

            # Process main image
            if ImageProcessor.process_image(
                str(temp_original),
                str(temp_processed),
                max_width=2048,
                max_height=2048,
                quality=90,
            ):
                # Save processed version
                with open(temp_processed, "rb") as f:
                    asset_file.processed_path = default_storage.save(
                        processed_path, ContentFile(f.read())
                    )

            # Generate thumbnails
            for size_name, dimensions in settings.ASSET_THUMBNAIL_SIZES.items():
                thumb_path = f"{base_path}_thumb_{size_name}{ext}"
                temp_thumb = Path(f"/tmp/{os.path.basename(thumb_path)}")

                if ImageProcessor.generate_thumbnail(
                    str(temp_original), str(temp_thumb), size=dimensions
                ):
                    with open(temp_thumb, "rb") as f:
                        if size_name == "small":
                            asset_file.thumbnail_path = default_storage.save(
                                thumb_path, ContentFile(f.read())
                            )

                    # Clean up temp file
                    temp_thumb.unlink(missing_ok=True)

            # Get image info
            info = ImageProcessor.get_image_info(str(temp_original))
            if info:
                asset_file.width = info["width"]
                asset_file.height = info["height"]

            # Clean up temp files
            temp_original.unlink(missing_ok=True)
            temp_processed.unlink(missing_ok=True)

            asset_file.is_processed = True
            asset_file.processing_status = "completed"
            asset_file.save()

            return True

        except Exception as e:
            logger.error(f"Error processing asset versions: {str(e)}")
            asset_file.processing_status = "failed"
            asset_file.processing_error = str(e)
            asset_file.save()
            return False


class BulkAssetProcessor:
    """Handle bulk asset operations"""

    @staticmethod
    def process_upload_batch(files, user, category=None, tags=None):
        """Process multiple file uploads"""
        from .models import Asset, AssetFile

        results = {"success": [], "failed": [], "duplicates": []}

        for file_obj in files:
            try:
                # Calculate hash
                file_hash = AssetFileHandler.calculate_file_hash(file_obj)

                # Check for duplicates
                if Asset.objects.filter(file_hash=file_hash).exists():
                    results["duplicates"].append(
                        {
                            "filename": file_obj.name,
                            "reason": "File already exists in system",
                        }
                    )
                    continue

                # Determine asset type
                mime_type = file_obj.content_type
                if mime_type.startswith("image/"):
                    asset_type = "image"
                elif mime_type.startswith("video/"):
                    asset_type = "video"
                elif mime_type == "application/pdf":
                    asset_type = "document"
                elif mime_type in ["application/zip", "application/x-rar"]:
                    asset_type = "archive"
                else:
                    asset_type = "other"

                # Create asset
                asset = Asset.objects.create(
                    title=os.path.splitext(file_obj.name)[0],
                    asset_type=asset_type,
                    original_filename=file_obj.name,
                    file_size=file_obj.size,
                    file_hash=file_hash,
                    mime_type=mime_type,
                    created_by=user,
                )

                # Add category and tags
                if category:
                    asset.categories.add(category)
                if tags:
                    asset.tags.add(*tags)

                # Save file
                file_path = AssetFileHandler.organize_file_path(asset, file_obj.name)
                saved_path = default_storage.save(file_path, file_obj)

                # Create asset file record
                asset_file = AssetFile.objects.create(
                    asset=asset, file_path=saved_path, version=1, is_current=True
                )

                # Extract metadata
                if asset_type == "image":
                    with default_storage.open(saved_path, "rb") as f:
                        temp_path = Path(f"/tmp/{file_hash}")
                        temp_path.write_bytes(f.read())

                    metadata = ExifProcessor.extract_metadata(str(temp_path))
                    asset.metadata = metadata

                    # Extract tags from metadata
                    auto_tags = ExifProcessor.extract_tags_from_metadata(metadata)
                    if auto_tags:
                        asset.tags.add(*auto_tags)

                    asset.save()
                    temp_path.unlink(missing_ok=True)

                # Queue for processing
                from core.models import TaskQueue

                TaskQueue.objects.create(
                    task_type="asset_processing",
                    task_data={"asset_file_id": asset_file.id, "asset_id": asset.id},
                    created_by=user,
                )

                results["success"].append(
                    {"id": asset.id, "filename": file_obj.name, "title": asset.title}
                )

            except Exception as e:
                logger.error(f"Error processing file {file_obj.name}: {str(e)}")
                results["failed"].append({"filename": file_obj.name, "error": str(e)})

        return results
