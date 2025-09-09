import logging
from typing import Dict, Any
from app.ai.schemas.workflow_states import DocumentProcessingState
from apps.api.app.ai.chains.embedding_chain import EmbeddingChain

logger = logging.getLogger(__name__)


def embedder_node(state: DocumentProcessingState) -> Dict[str, Any]:
    """
    Lightweight LangGraph node container for storing documents in vector database.
    This node delegates all storing documents logic to the VectorService.

    Args:
        state: DocumentProcessingState containing file path and resource id and documents

    Returns:
        Updated state with storing documents results in vector database
    """
    logger.info(f"[EMBEDDER_NODE] Starting storing documents in vector database")

    try:
        chunks = state.documents or []
        file_path = state.file_path or "unknown"
        resource_id = state.resource_id or "unknown"
        logger.info(
            f"[EMBEDDER_NODE] Processing {len(chunks)} chunks for file {resource_id}"
        )

        # Initialize embedding chain
        logger.info(
            f"[EMBEDDER_NODE] Initializing embedding chain for file {file_path}"
        )
        embedding_chain = EmbeddingChain()

        # Process chunks through embedding chain
        logger.info(
            f"[EMBEDDER_NODE] Delegating to embedding chain for file {file_path}"
        )
        chain_result = embedding_chain.process(state)

        logger.info(f"[EMBEDDER_NODE] Chain result: {chain_result}")
        
        # Convert chain result to state updates
        if chain_result["success"]:
            logger.info(
                f"[EMBEDDER_NODE] Embedding completed successfully for file {file_path}"
            )
            # logger.info(
            #     f"[EMBEDDER_NODE] Stored {chain_result['embeddings_stored']} embeddings in collection {chain_result['collection_name']}"
            # )
            return {
                "status": "embeddings_stored",
                "embeddings_stored": chain_result["embeddings_stored"],
                "storage_metadata": chain_result["storage_metadata"],
            }
        else:
            logger.error(
                f"[EMBEDDER_NODE] Embedding failed for file {file_path}: {chain_result['error']}"
            )
            return {
                "status": "failed",
                "error_message": f"Embedding failed: {chain_result['error']}",
                "embeddings_stored": 0,
            }
    except Exception as e:
        logger.error(
            f"[EMBEDDER_NODE] Failed to store documents in vector database: {str(e)}"
        )
        return {
            "error_message": f"Failed to store documents in vector database: {str(e)}",
            "status": "failed",
            "embeddings_stored": 0,
        }
