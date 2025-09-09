import logging
from typing import Dict, Any
from apps.api.app.ai.tools.image_tools import ImageExtractionTool

logger = logging.getLogger(__name__)


def image_processor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lightweight LangGraph node container for image parsing.
    This node delegates all image parsing logic to the ImageExtractionTool.

    Args:
        state: DocumentProcessingState containing file path

    Returns:
        Updated state with image parsing results
    """
    try:
        file_path = state.get("file_path")
        logger.info(f"[IMAGE_PARSER_NODE] Starting image parser for file path: {file_path}")
        
        image_tool = ImageExtractionTool()
        parsed_documents = image_tool.extract_with_tesseract(file_path)
        logger.info(
            f"[IMAGE_PARSER_NODE] Extracted {len(parsed_documents)} documents from {file_path}"
        )
        return {
            **state,
            "documents": parsed_documents,
            "status": "image_processed",
        }
    except Exception as e:
        logger.error(f"[IMAGE_PARSER_NODE] Image extraction failed: {str(e)}")
        return {
            **state,
            "error_message": f"Image extraction failed: {str(e)}",
            "status": "failed",
        }
