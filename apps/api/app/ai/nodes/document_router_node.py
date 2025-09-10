"""
Document router node - lightweight container for routing documents by type.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def document_router_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lightweight LangGraph node container for document routing.

    This node makes routing decisions based on file metadata already
    computed by the file fetcher node.

    Args:
        state: LangGraph state containing file_path and metadata from file fetcher

    Returns:
        Updated state with routing decision
    """
    filename = state.get("file_metadata", {}).get("file_name", "unknown")
    logger.info(f"[DOCUMENT_ROUTER_NODE] Starting document routing for file {filename}")

    try:
        # Extract required state (already computed by file fetcher)
        file_path = state.get("file_path")
        file_type = state.get("file_type")
        is_supported = state.get("is_supported_format", False)

        logger.info(
            f"[DOCUMENT_ROUTER_NODE] Using file fetcher results - Path: {file_path}, Type: {file_type}, Supported: {is_supported}"
        )

        # Validate that file fetcher completed successfully
        if not file_path:
            logger.error(
                f"[DOCUMENT_ROUTER_NODE] No file path provided by file fetcher for  file {filename}"
            )
            return {
                **state,
                "status": "failed",
                "error_message": "No file path provided by file fetcher",
            }

        if not file_type:
            logger.error(
                f"[DOCUMENT_ROUTER_NODE] No file type detected by file fetcher for file {filename}"
            )
            return {
                **state,
                "status": "failed",
                "error_message": "File type could not be determined by file fetcher",
            }

        logger.info(
            f"[DOCUMENT_ROUTER_NODE] Making routing decision for file {filename}"
        )

        # Use switch pattern for routing decision
        processing_route = _get_routing_decision(file_type, is_supported)

        # Log the routing decision
        if processing_route == "unsupported":
            logger.warning(
                f"[DOCUMENT_ROUTER_NODE] File format not supported for file {filename}"
            )
        elif processing_route == "unknown":
            logger.warning(
                f"[DOCUMENT_ROUTER_NODE] Unknown file type '{file_type}' for file {filename}"
            )
        else:
            logger.info(
                f"[DOCUMENT_ROUTER_NODE] Routing to {processing_route.upper()} processor for file {filename}"
            )

        logger.info(
            f"[DOCUMENT_ROUTER_NODE] Document routing completed for file {filename}: route={processing_route}"
        )

        return {
            **state,
            "status": "routed",
            "processing_route": processing_route,
        }

    except Exception as e:
        logger.error(
            f"[DOCUMENT_ROUTER_NODE] Document routing failed for file {filename}: {str(e)}",
            exc_info=True,
        )
        return {
            **state,
            "status": "failed",
            "error_message": f"Document routing failed: {str(e)}",
        }


def _get_routing_decision(file_type: str, is_supported: bool) -> str:
    """
    Switch-style routing decision logic.

    Args:
        file_type: File type detected by file fetcher
        is_supported: Whether format is supported

    Returns:
        Tuple of (processing_route, next_processor)
    """
    # Check support first
    if not is_supported:
        return "unsupported"

    # Switch pattern for file type routing
    routing_switch = {
        "pdf": "pdf",
        "docx": "docx",
        # Handle .doc files with docx processor
        "doc": "docx",
        "xlsx": "excel",
        "xls": "excel",
        # Route CSV files to excel processor
        "csv": "excel",
        "txt": "text",
        # Handle markdown with text processor
        "md": "text",
        "jpg": "image",
        "jpeg": "image",  # Handle .jpeg extension
        "png": "image",
        "tiff": "image",
    }

    # Get routing decision from switch
    return routing_switch.get(file_type, "unknown")
