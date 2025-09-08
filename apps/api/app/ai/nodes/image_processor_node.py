import logging
from typing import Dict, Any
from app.ai.schemas.workflow_states import DocumentProcessingState
from apps.api.app.ai.tools.image_tools import ImageExtractionTool

logger = logging.getLogger(__name__)


def image_processor_node(state: DocumentProcessingState) -> Dict[str, Any]:
    """
    Lightweight LangGraph node container for image parsing.
    This node delegates all image parsing logic to the ImageExtractionTool.

    Args:
        state: DocumentProcessingState containing file path

    Returns:
        Updated state with image parsing results
    """
    logger.info(
        f"[IMAGE_PARSER_NODE] Starting image parser for file path: {state.file_path}"
    )
    try:
        image_tool = ImageExtractionTool()
        parsed_documents = image_tool.extract_with_tesseract(state.file_path)
        logger.info(
            f"[IMAGE_PARSER_NODE] Extracted {len(parsed_documents)} documents from {state.file_path}"
        )
        return {
            "documents": parsed_documents,
            "file_format": "image",
        }
    except Exception as e:
        logger.error(f"[IMAGE_PARSER_NODE] Image extraction failed: {str(e)}")
        return {
            "error_message": f"Image extraction failed: {str(e)}",
            "documents": [],
        }
