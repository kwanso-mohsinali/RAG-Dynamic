import logging
from typing import Dict, Any
from app.ai.schemas.workflow_states import DocumentProcessingState
from apps.api.app.ai.services.vector_service import VectorService

logger = logging.getLogger(__name__)


def embedder_node(state: DocumentProcessingState) -> Dict[str, Any]:
    """
    Lightweight LangGraph node container for storing documents in vector database.
    This node delegates all storing documents logic to the VectorService.

    Args:
        state: DocumentProcessingState containing documents and resource id

    Returns:
        Updated state with storing documents results in vector database
    """
    logger.info(f"[STORE_DOCUMENTS_NODE] Starting storing documents in vector database")
    try:
        chunked_documents = state.documents
        resource_id = state.resource_id

        logger.info(
            f"[STORE_DOCUMENTS_NODE] Storing {len(chunked_documents)} documents in vector database for resource {resource_id}"
        )

        vector_service = VectorService()
        result = vector_service.store_documents(chunked_documents, resource_id)

        logger.info(
            f"[STORE_DOCUMENTS_NODE] Successfully stored {len(result['document_count'])} documents in vector database"
        )
        return state
    except Exception as e:
        logger.error(
            f"[STORE_DOCUMENTS_NODE] Failed to store documents in vector database: {str(e)}"
        )
        return {
            "error_message": f"Failed to store documents in vector database: {str(e)}",
            "documents": [],
        }
