"""
Storage tools for file operations and metadata detection.

These tools handle file downloads, uploads, and metadata extraction
without requiring service instances in workflow state.
"""

import logging
import os
import tempfile
import mimetypes
from pathlib import Path
from typing import Dict, Any
from uuid import uuid4
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class FileStorageTool:
    """
    Tool for file storage operations.

    Creates its own storage service instance instead of receiving it through state.
    This follows proper tool patterns and avoids service coupling in workflows.
    """

    def __init__(self):
        """Initialize with self-contained storage service."""
        self.storage_service = StorageService()

    def download_from_gcs(self, gcs_path: str) -> str:
        """
        Download file from Google Cloud Storage to local temporary file.

        Args:
            gcs_path: GCS blob path (e.g., "projects/123/attachments/file.pdf")

        Returns:
            Local file path of downloaded file

        Raises:
            RuntimeError: If download fails
        """
        logger.info(f"[FILE_STORAGE_TOOL] Downloading file from GCS: {gcs_path}")

        try:
            # Create temporary file with proper extension
            file_extension = Path(gcs_path).suffix
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=file_extension,
                prefix=f"ai_processing_{uuid4().hex[:8]}_",
            )
            temp_path = temp_file.name
            temp_file.close()

            logger.info(f"[FILE_STORAGE_TOOL] Created temporary file: {temp_path}")

            # Download using storage service (returns local path on success)
            downloaded_path = self.storage_service.download_file(gcs_path, temp_path)

            if not downloaded_path or downloaded_path != temp_path:
                logger.error(f"[FILE_STORAGE_TOOL] Failed to download {gcs_path}")
                # Clean up temp file on failure
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise RuntimeError(f"Failed to download file from GCS: {gcs_path}")

            # Verify file was downloaded
            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                logger.error(
                    f"[FILE_STORAGE_TOOL] Downloaded file is empty or missing: {temp_path}"
                )
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise RuntimeError(f"Downloaded file is empty or missing: {gcs_path}")

            file_size = os.path.getsize(temp_path)
            logger.info(
                f"[FILE_STORAGE_TOOL] Successfully downloaded {file_size} bytes to {temp_path}"
            )
            return temp_path

        except Exception as e:
            logger.error(
                f"[FILE_STORAGE_TOOL] Download failed for {gcs_path}: {str(e)}",
                exc_info=True,
            )
            raise RuntimeError(f"File download failed: {str(e)}")

    def cleanup_temp_file(self, file_path: str) -> bool:
        """
        Clean up temporary file.

        Args:
            file_path: Path to temporary file

        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(
                    f"[FILE_STORAGE_TOOL] Cleaned up temporary file: {file_path}"
                )
                return True
            return True  # File doesn't exist, consider it cleaned up
        except Exception as e:
            logger.error(f"[FILE_STORAGE_TOOL] Failed to cleanup {file_path}: {str(e)}")
            return False


class FileMetadataTool:
    """Tool for file metadata detection and analysis."""

    # Supported file types for processing
    SUPPORTED_TYPES = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/msword": "doc",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "application/vnd.ms-excel": "xls",
        "text/csv": "csv",  # Added CSV support
        "text/plain": "txt",
        "text/markdown": "md",
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/tiff": "tiff",
    }

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get comprehensive file information.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file metadata
        """
        logger.info(f"[FILE_METADATA_TOOL] Getting file info for: {file_path}")

        try:
            file_stat = os.stat(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)

            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "file_size": file_stat.st_size,
                "mime_type": mime_type,
                "extension": Path(file_path).suffix.lower(),
                "created_time": file_stat.st_ctime,
                "modified_time": file_stat.st_mtime,
                "is_readable": os.access(file_path, os.R_OK),
            }
        except Exception as e:
            logger.error(
                f"[FILE_METADATA_TOOL] Failed to get file info for {file_path}: {str(e)}"
            )
            return {"file_path": file_path, "error": str(e)}

    def detect_file_type(self, file_path: str) -> str:
        """
        Detect file type from file path and content.

        Args:
            file_path: Path to file

        Returns:
            File type string (pdf, docx, txt, etc.)
        """
        try:
            mime_type, _ = mimetypes.guess_type(file_path)

            if mime_type in self.SUPPORTED_TYPES:
                file_type = self.SUPPORTED_TYPES[mime_type]
                logger.info(
                    f"[FILE_METADATA_TOOL] Detected file type: {file_type} (mime: {mime_type})"
                )
                return file_type

            # Fallback to extension-based detection
            extension = Path(file_path).suffix.lower()
            extension_map = {
                ".pdf": "pdf",
                ".docx": "docx",
                ".doc": "doc",
                ".xlsx": "xlsx",
                ".xls": "xls",
                ".csv": "csv",  # Added CSV extension mapping
                ".txt": "txt",
                ".md": "md",
                ".jpg": "jpg",
                ".jpeg": "jpg",
                ".png": "png",
                ".tiff": "tiff",
            }

            if extension in extension_map:
                file_type = extension_map[extension]
                logger.info(
                    f"[FILE_METADATA_TOOL] Detected file type by extension: {file_type}"
                )
                return file_type

            logger.warning(
                f"[FILE_METADATA_TOOL] Unknown file type for {file_path}, mime: {mime_type}"
            )
            return "unknown"

        except Exception as e:
            logger.error(
                f"[FILE_METADATA_TOOL] File type detection failed for {file_path}: {str(e)}"
            )
            return "unknown"

    def is_supported_format(self, file_path: str) -> bool:
        """
        Check if file format is supported for processing.

        Args:
            file_path: Path to file

        Returns:
            True if format is supported, False otherwise
        """
        file_type = self.detect_file_type(file_path)
        supported = file_type in [
            "pdf",
            "docx",
            "doc",
            "xlsx",
            "xls",
            "csv",
            "txt",
            "md",
            "jpg",
            "png",
            "tiff",
        ]
        logger.info(
            f"[FILE_METADATA_TOOL] File format supported: {supported} (type: {file_type})"
        )
        return supported

    def estimate_processing_time(self, file_path: str) -> Dict[str, Any]:
        """
        Estimate processing time based on file characteristics.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with time estimates
        """
        try:
            file_size = os.path.getsize(file_path)
            file_type = self.detect_file_type(file_path)

            # Base estimates in seconds (rough approximations)
            base_times = {
                "pdf": 2.0,  # 2 seconds per MB
                "docx": 1.5,  # 1.5 seconds per MB
                "doc": 1.5,
                # 3 seconds per MB (complex financial analysis)
                "xlsx": 3.0,
                "xls": 3.5,  # 3.5 seconds per MB (legacy format overhead)
                "csv": 2.5,  # 2.5 seconds per MB (tabular data analysis)
                "txt": 0.5,  # 0.5 seconds per MB
                "md": 0.5,
                "jpg": 3.0,  # 3 seconds per MB (OCR)
                "png": 3.0,
                "tiff": 3.0,
                "unknown": 5.0,  # Conservative estimate
            }

            size_mb = file_size / (1024 * 1024)
            base_time = base_times.get(file_type, 5.0)
            estimated_seconds = max(1.0, size_mb * base_time)

            return {
                "estimated_seconds": estimated_seconds,
                "estimated_minutes": estimated_seconds / 60,
                "file_size_mb": size_mb,
                "processing_complexity": (
                    "high"
                    if file_type in ["jpg", "png", "tiff"]
                    else "medium" if file_type == "pdf" else "low"
                ),
            }

        except Exception as e:
            logger.error(
                f"[FILE_METADATA_TOOL] Time estimation failed for {file_path}: {str(e)}"
            )
            return {
                "estimated_seconds": 30.0,  # Default fallback
                "estimated_minutes": 0.5,
                "error": str(e),
            }
