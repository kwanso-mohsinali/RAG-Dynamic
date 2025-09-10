from typing import Dict, Any
from app.ai.tools.storage_tools import FileStorageTool, FileMetadataTool
import gc
import logging


logger = logging.getLogger(__name__)


def file_fetcher_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lightweight LangGraph node container for file fetching.

    This node downloads files from s3 bucket by file key and prepares them for processing.
    All business logic is delegated to storage tools which are self-contained.

    Args:
        state: LangGraph state containing file_key

    Returns:
        Updated state with local file path and metadata
    """
    logger.info(f"[FILE_FETCHER_NODE] Starting file fetching process")
    try:
        
        # Extract required state
        file_key = state.get("file_key")
        
        logger.info(f"[FILE_FETCHER_NODE] File key: {file_key}")

        if not file_key:
            logger.error(f"[FILE_FETCHER_NODE] No file key provided")
            return {
                **state,
                "status": "failed",
                "error_message": "No file key provided",
            }

        logger.info(
            f"[FILE_FETCHER_NODE] Initializing storage tools for file {file_key}"
        )
        # Initialize self-contained storage tools (no service dependency)
        storage_tool = FileStorageTool()
        metadata_tool = FileMetadataTool()

        logger.info(
            f"[FILE_FETCHER_NODE] Downloading file from S3 with key: {file_key}"
        )
        # Download file from S3 to local temp file
        local_path = storage_tool.download_from_s3(file_key)
        logger.info(f"[FILE_FETCHER_NODE] File downloaded to: {local_path}")

        # Force garbage collection after file download
        gc.collect()

        logger.info(f"[FILE_FETCHER_NODE] Getting file metadata for file {file_key}")
        # Get file metadata
        file_info = metadata_tool.get_file_info(local_path)

        # Detect file type
        file_type = metadata_tool.detect_file_type(local_path)
        logger.info(f"[FILE_FETCHER_NODE] Detected file type: {file_type}")

        # Check if format is supported
        is_supported = metadata_tool.is_supported_format(local_path)
        logger.info(f"[FILE_FETCHER_NODE] File format supported: {is_supported}")

        # Estimate processing time
        time_estimate = metadata_tool.estimate_processing_time(local_path)
        logger.info(f"[FILE_FETCHER_NODE] Processing time estimate: {time_estimate}")

        logger.info(
            f"[FILE_FETCHER_NODE] File fetch completed successfully for file {file_key}"
        )
        return {
            **state,
            "status": "file_fetched",
            "file_path": local_path,
            "file_key": file_key,
            "file_type": file_type,
            "is_supported_format": is_supported,
            "file_metadata": file_info,
            "processing_estimate": time_estimate,
        }

    except Exception as e:
        logger.error(
            f"[FILE_FETCHER_NODE] File fetching failed for file {file_key}: {str(e)}",
            exc_info=True,
        )
        return {
            **state,
            "status": "failed",
            "error_message": f"File fetching failed: {str(e)}",
        }
