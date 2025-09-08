import logging
from typing import Dict, Any
from app.ai.schemas.workflow_states import DocumentProcessingState
from apps.api.app.ai.tools.chunking_tools import TextChunkingTool
from langchain_community.vectorstores.utils import filter_complex_metadata

logger = logging.getLogger(__name__)


def chunker_node(state: DocumentProcessingState) -> Dict[str, Any]:
    """
    Lightweight LangGraph node container for text chunking.
    This node delegates all text chunking logic to the TextChunkingTool.

    Args:
        state: DocumentProcessingState containing documents and file format

    Returns:
        Updated state with text chunking results
    """
    logger.info(
        f"[CHUNKER_NODE] Starting text chunker for file path: {state.file_path}"
    )
    try:
        filtered_documents = filter_complex_metadata(state.documents)
        content_type = state.file_format

        logger.info(
            f"[CHUNKER_NODE] Chunking {len(filtered_documents)} documents for {content_type} content"
        )

        text_chunking_tool = TextChunkingTool()
        chunked_documents = text_chunking_tool.adaptive_chunk(
            filtered_documents, content_type
        )

        logger.info(
            f"[CHUNKER_NODE] Chunking resulted in {len(chunked_documents)} documents for {content_type} content"
        )

        return {
            **state,
            "documents": chunked_documents,
            "status": "documents_chunked",
        }
    except Exception as e:
        logger.error(f"[CHUNKER_NODE] Text chunking failed: {str(e)}")
        return {
            "error_message": f"Text chunking failed: {str(e)}",
            "documents": [],
            "status": "failed",
        }
