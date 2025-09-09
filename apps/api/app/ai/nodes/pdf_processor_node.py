import logging
from typing import Dict, Any
from app.ai.schemas.workflow_states import DocumentProcessingState
from apps.api.app.ai.tools.pdf_tools import PDFExtractionTool

logger = logging.getLogger(__name__)


def pdf_processor_node(state: DocumentProcessingState) -> Dict[str, Any]:
    """
    Lightweight LangGraph node container for PDF parsing.
    This node delegates all PDF parsing logic to the PDFExtractionTool.

    Args:
        state: DocumentProcessingState containing file path

    Returns:
        Updated state with PDF parsing results
    """
    logger.info(
        f"[PDF_PARSER_NODE] Starting PDF parser for file path: {state.file_path}"
    )
    try:
        pdf_tool = PDFExtractionTool()
        parsed_documents = pdf_tool.extract_text(state.file_path)
        logger.info(
            f"[PDF_PARSER_NODE] Extracted {len(parsed_documents)} documents from {state.file_path}"
        )
        return {
            "documents": parsed_documents,
            "status": "pdf_processed",
        }
    except Exception as e:
        logger.error(f"[PDF_PARSER_NODE] PDF extraction failed: {str(e)}")
        return {
            "error_message": f"PDF extraction failed: {str(e)}",
            "status": "failed",
        }
