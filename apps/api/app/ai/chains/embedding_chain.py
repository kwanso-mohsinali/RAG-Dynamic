"""
Embedding chain using embedding tools for vector generation and storage.
"""

import logging
from typing import Dict, Any, List, Optional
from langchain_core.documents import Document

from app.ai.tools.embedding_tools import EmbeddingGenerationTool, EmbeddingAnalysisTool
from app.ai.services.vector_service import VectorService

logger = logging.getLogger(__name__)


class EmbeddingChain:
    """Chain for generating and storing embeddings using embedding tools."""

    def __init__(self, model: str = "text-embedding-3-small"):
        """
        Initialize the embedding chain with hybrid approach.

        HYBRID APPROACH: Uses both tools and services appropriately.

        Args:
            model: OpenAI embedding model to use
        """
        # TOOLS: For simple, stateless operations
        self.embedding_tool = EmbeddingGenerationTool(model)
        self.analysis_tool = EmbeddingAnalysisTool()

        # SERVICE: For complex, stateful infrastructure (now with tool delegation)
        self.vector_service = VectorService()

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process chunks through embedding generation and storage.

        Args:
            state: Processing state containing chunks and project information

        Returns:
            Updated state with embedding results
        """
        file_path = state.get("file_path", "unknown")
        resource_id = state.get("resource_id", "unknown")
        logger.info(
            f"[EMBEDDING_CHAIN] Starting embedding processing for file {file_path}, resource {resource_id}"
        )

        try:
            chunks = state.get("documents", [])

            logger.info(
                f"[EMBEDDING_CHAIN] Processing {len(chunks)} documents for embedding"
            )

            if not chunks:
                logger.error(
                    f"[EMBEDDING_CHAIN] No chunks provided for embedding file {file_path}"
                )
                return {
                    "success": False,
                    "error": "No chunks provided for embedding",
                    "embeddings_stored": 0,
                }

            if not file_path:
                logger.error(f"[EMBEDDING_CHAIN] No file_path provided")
                return {
                    "success": False,
                    "error": "No file_path provided",
                    "embeddings_stored": 0,
                }

            # Enhance chunk metadata with resource and file info
            logger.info(
                f"[EMBEDDING_CHAIN] Enhancing chunk metadata for file {file_path}"
            )
            original_filename = state.get("file_metadata", {}).get("file_name", "unknown")
            enhanced_chunks = self._enhance_chunk_metadata(
                chunks, resource_id, original_filename
            )

            # Store documents in vector database using VectorService (with proper table tracking)
            logger.info(
                f"[EMBEDDING_CHAIN] Storing {len(enhanced_chunks)} documents in vector database via VectorService"
            )
            storage_result = self.vector_service.store_documents(
                enhanced_chunks, resource_id
            )

            if not storage_result["success"]:
                logger.error(
                    f"[EMBEDDING_CHAIN] Failed to store embeddings for file {file_path}: {storage_result['error'] or 'Unknown error'}"
                )
                return {
                    "success": False,
                    "error": f"Failed to store documents in vector database: {storage_result['error'] or 'Unknown error'}",
                    "embeddings_stored": 0,
                }

            logger.info(
                f"[EMBEDDING_CHAIN] Successfully stored {storage_result['document_count']} embeddings"
            )

            # TOOL USAGE: Generate embeddings for analysis (sample)
            logger.info(
                f"[EMBEDDING_CHAIN] Generating sample embeddings for analysis using EmbeddingGenerationTool"
            )
            sample_texts = [chunk.page_content for chunk in enhanced_chunks[:5]]
            sample_embeddings = self.embedding_tool.generate_embeddings(sample_texts)

            # TOOL USAGE: Analyze embedding quality
            logger.info(
                f"[EMBEDDING_CHAIN] Analyzing embedding quality using EmbeddingAnalysisTool"
            )
            embedding_analysis = self.analysis_tool.analyze_embedding_quality(
                sample_embeddings
            )

            logger.info(
                f"[EMBEDDING_CHAIN] Embedding processing completed for file {file_path}"
            )
            return {
                "success": True,
                "embeddings_stored": storage_result.get("document_count", 0),
                "document_ids": storage_result.get("document_ids", []),
                "embedding_analysis": embedding_analysis,
                "collection_name": storage_result.get("collection_name", "unknown"),
                "storage_metadata": {
                    "embedding_model": storage_result.get("embedding_model", "unknown"),
                    "total_chunks": len(enhanced_chunks),
                    "resource_id": resource_id,
                    "file_path": file_path,
                },
            }

        except Exception as e:
            logger.error(
                f"[EMBEDDING_CHAIN] Embedding processing failed for file {file_path}: {str(e)}",
                exc_info=True,
            )
            return {"success": False, "error": str(e), "embeddings_stored": 0}

    def _enhance_chunk_metadata(
        self,
        chunks: List[Document],
        resource_id: Optional[str] = None,
        original_filename: Optional[str] = None,
    ) -> List[Document]:
        """
        Enhance chunk metadata with project and attachment information.

        Args:
            chunks: List of document chunks
            resource_id: Resource identifier
            original_filename: Original filename of the document

        Returns:
            Enhanced chunks with additional metadata
        """
        enhanced_chunks = []

        # Ensure resource_id is a string (convert from UUID if needed)
        resource_id_str = str(resource_id) if resource_id else None

        for chunk in chunks:
            # Sanitize existing metadata to ensure JSON serialization
            sanitized_metadata = self._sanitize_metadata(chunk.metadata)

            # Create a copy of the chunk with enhanced metadata
            enhanced_metadata = {
                **sanitized_metadata,
                "resource_id": resource_id_str,
                "original_filename": original_filename or "unknown",
                "source_file": original_filename
                or "unknown",  # For backward compatibility
                "chunk_id": f"{original_filename}_{chunk.metadata.get('chunk_index', 0)}",
                "embedding_timestamp": str(int(__import__("time").time())),
            }

            enhanced_chunk = Document(
                page_content=chunk.page_content, metadata=enhanced_metadata
            )
            enhanced_chunks.append(enhanced_chunk)

        return enhanced_chunks

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize metadata to ensure JSON serialization compatibility.

        Args:
            metadata: Original metadata dictionary

        Returns:
            Sanitized metadata with all values converted to JSON-serializable types
        """
        sanitized = {}
        for key, value in metadata.items():
            if value is None:
                sanitized[key] = None
            elif hasattr(value, "__str__"):
                # Convert UUID objects and other non-serializable types to strings
                sanitized[key] = str(value)
            else:
                sanitized[key] = value
        return sanitized
