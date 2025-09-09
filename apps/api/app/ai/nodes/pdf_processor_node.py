import logging
from typing import Dict, Any
from apps.api.app.ai.tools.pdf_tools import PDFExtractionTool

logger = logging.getLogger(__name__)


def pdf_processor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lightweight LangGraph node container for PDF parsing.
    This node delegates all PDF parsing logic to the PDFExtractionTool.

    Args:
        state: DocumentProcessingState containing file path

    Returns:
        Updated state with PDF parsing results
    """
    try:
        file_path = state.get("file_path")
        logger.info(f"[PDF_PARSER_NODE] Starting PDF parser for file path: {file_path}")

        pdf_tool = PDFExtractionTool()
        parsed_documents = pdf_tool.extract_text(file_path)
        logger.info(
            f"[PDF_PARSER_NODE] Extracted {len(parsed_documents)} documents from {file_path}"
        )
        return {
            **state,
            "documents": parsed_documents,
            "status": "pdf_processed",
        }
    except Exception as e:
        logger.error(f"[PDF_PARSER_NODE] PDF extraction failed: {str(e)}")
        return {
            **state,
            "error_message": f"PDF extraction failed: {str(e)}",
            "status": "failed",
        }
