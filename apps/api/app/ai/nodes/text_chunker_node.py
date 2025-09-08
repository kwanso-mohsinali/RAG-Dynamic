import logging
from typing import Dict, Any
from app.ai.schemas.workflow_states import FileIngestionState
from apps.api.app.ai.tools.chunking_tools import TextChunkingTool

logger = logging.getLogger(__name__)

def text_chunker_node(state: FileIngestionState) -> Dict[str, Any]:
    """
    Lightweight LangGraph node container for text chunking.
    This node delegates all text chunking logic to the TextChunkingTool.

    Args:
        state: FileIngestionState containing documents and file type

    Returns:
        Updated state with text chunking results
    """
    logger.info(
        f"[TEXT_CHUNKER_NODE] Starting text chunker for file path: {state.file_path}"
    )
    try:
        parsed_documents = state.documents
        content_type = state.document_type
        
        logger.info(f"[TEXT_CHUNKER_NODE] Chunking {len(parsed_documents)} documents for {content_type} content")
        
        text_chunking_tool = TextChunkingTool()
        chunked_documents = text_chunking_tool.adaptive_chunk(parsed_documents, content_type)
        
        logger.info(f"[TEXT_CHUNKER_NODE] Chunking resulted in {len(chunked_documents)} documents for {content_type} content")
        
        return {
            "documents": chunked_documents,
        }
    except Exception as e:
        logger.error(f"[TEXT_CHUNKER_NODE] Text chunking failed: {str(e)}")
        return {
            "error_message": f"Text chunking failed: {str(e)}",
            "documents": [],
        }
