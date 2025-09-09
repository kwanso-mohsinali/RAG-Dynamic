import logging
from typing import Dict, Any
from apps.api.app.ai.tools.docx_tools import DOCXExtractionTool

logger = logging.getLogger(__name__)


def docx_processor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lightweight LangGraph node container for DOCX parsing.
    This node delegates all DOCX parsing logic to the DOCXExtractionTool.

    Args:
        state: DocumentProcessingState containing file path

    Returns:
        Updated state with DOCX parsing results
    """
    try:
        file_path = state.get('file_path')
        logger.info(f"[DOCX_PARSER_NODE] Starting DOCX parser for file path: {file_path}")
        
        docx_tool = DOCXExtractionTool()
        parsed_documents = docx_tool.extract_text(file_path)
        logger.info(
            f"[DOCX_PARSER_NODE] Extracted {len(parsed_documents)} documents from {file_path}"
        )
        return {
            **state,
            "documents": parsed_documents,
            "status": "docx_processed",
            "current_step": "docx_processed",
        }
    except Exception as e:
        logger.error(f"[DOCX_PARSER_NODE] DOCX extraction failed: {str(e)}")
        return {
            **state,
            "error_message": f"DOCX extraction failed: {str(e)}",
            "documents": [],
            "status": "failed",
        }
