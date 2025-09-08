import logging
from typing import Dict, Any
from app.ai.schemas.workflow_states import FileIngestionState
from apps.api.app.ai.tools.pdf_tools import PDFExtractionTool

logger = logging.getLogger(__name__)


def pdf_parser_node(state: FileIngestionState) -> Dict[str, Any]:
    """
    Lightweight LangGraph node container for PDF parsing.
    This node delegates all PDF parsing logic to the PDFExtractionTool.

    Args:
        state: FileIngestionState containing file path

    Returns:
        Updated state with PDF parsing results
    """
    logger.info(
        f"[PDF_PARSER_NODE] Starting PDF parser for file path: {state.file_path}"
    )
    try:
        pdf_tool = PDFExtractionTool()
        parsed_documents = pdf_tool.extract_text(state.file_path)
        logger.info(f"[PDF_PARSER_NODE] Extracted {len(parsed_documents)} documents from {state.file_path}")
        return {
            "documents": parsed_documents,
            "document_type": "pdf",
        }
    except Exception as e:
        logger.error(f"[PDF_PARSER_NODE] PDF extraction failed: {str(e)}")
        return {
            "error_message": f"PDF extraction failed: {str(e)}",
            "documents": [],
        }
