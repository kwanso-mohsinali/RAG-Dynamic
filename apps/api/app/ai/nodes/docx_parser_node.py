import logging
from typing import Dict, Any
from app.ai.schemas.workflow_states import FileIngestionState
from apps.api.app.ai.tools.docx_tools import DOCXExtractionTool

logger = logging.getLogger(__name__)


def docx_parser_node(state: FileIngestionState) -> Dict[str, Any]:
    """
    Lightweight LangGraph node container for DOCX parsing.
    This node delegates all DOCX parsing logic to the DOCXExtractionTool.

    Args:
        state: FileIngestionState containing file path

    Returns:
        Updated state with DOCX parsing results
    """
    logger.info(
        f"[DOCX_PARSER_NODE] Starting DOCX parser for file path: {state.file_path}"
    )
    try:
        docx_tool = DOCXExtractionTool()
        parsed_documents = docx_tool.extract_text(state.file_path)
        logger.info(f"[DOCX_PARSER_NODE] Extracted {len(parsed_documents)} documents from {state.file_path}")
        return {
            "documents": parsed_documents,
            "document_type": "docx",
        }
    except Exception as e:
        logger.error(f"[DOCX_PARSER_NODE] DOCX extraction failed: {str(e)}")
        return {
            "error_message": f"DOCX extraction failed: {str(e)}",
            "documents": [],
        }
