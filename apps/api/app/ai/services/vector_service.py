from typing import Any, List, Optional, Dict
from uuid import UUID
from langchain_core.documents import Document
from app.ai.services.engine_service import get_shared_pg_engine
from app.ai.tools.embedding_tools import EmbeddingGenerationTool
from app.core.config import settings
from langchain_postgres import PGVectorStore


class VectorService:
    """
    Service for managing vector database operations.

    Handles embedding generation, vector storage, and retrieval with RAG.

    Uses shared PGEngine to eliminate connection pool proliferation.
    """

    def __init__(self):
        """
        Initialize vector service.
        """

        # Parse DATABASE_URL for PGVector connection
        if not settings.DATABASE_URL:
            raise ValueError("DATABASE_URL is required for vector operations")

        # Initialize tools for stateless operations
        self.embedding_tool = EmbeddingGenerationTool(model="text-embedding-3-small")

        self.embeddings = self.embedding_tool.embeddings

        # Always use shared engine to eliminate connection proliferation
        self.engine = get_shared_pg_engine()
        print("[VECTOR_SERVICE] Using shared PGEngine for vector operations")

    def get_collection_name(self, resource_id: UUID) -> str:
        """
        Get resource-specific collection name for namespace isolation.

        Args:
            resource_id: UUID

        Returns:
            Collection name
        """
        # Convert UUID to string and replace hyphens with underscores
        resource_id_str = str(resource_id)
        resource_part = f"resource_{resource_id_str.replace('-', '_')}"

        # One table per resource (current/recommended)
        return f"{resource_part}_documents"

    def _create_vector_store(self, collection_name: str) -> "PGVectorStore":
        """
        Create a vector store instance using shared engine.

        Uses the shared PGEngine instance instead of creating new ones.

        Args:
            collection_name: Name of the collection/table

        Returns:
            PGVectorStore instance

        Raises:
            RuntimeError: If vector store creation fails
        """
        print(
            f"[VECTOR_SERVICE] Creating vector store for collection: {collection_name}"
        )

        try:
            # Use shared engine instead of creating new one
            vector_store = PGVectorStore.create_sync(
                engine=self.engine,  # REUSE SHARED ENGINE
                table_name=collection_name,
                embedding_service=self.embeddings,
            )

            print(
                f"[VECTOR_SERVICE] Successfully created vector store for {collection_name}"
            )
            return vector_store

        except Exception as e:
            print(
                f"[VECTOR_SERVICE] Failed to create vector store for {collection_name}: {str(e)}"
            )
            raise RuntimeError(f"Failed to create vector store: {str(e)}")

    def _get_vector_store(self, collection_name: str) -> "PGVectorStore":
        """
        Get or create a vector store instance for the given collection.

        Uses shared engine instead of creating new ones.

        Args:
            collection_name: Name of the collection/table

        Returns:
            PGVectorStore instance

        Raises:
            RuntimeError: If vector store creation fails
        """
        print(
            f"[VECTOR_SERVICE] Getting vector store for collection: {collection_name}"
        )

        try:
            # Ensure table exists first
            print(f"[VECTOR_SERVICE] Ensuring {collection_name} table exists ")
            self._ensure_table_exists(collection_name)

            # Use shared engine instead of creating new one
            vector_store = PGVectorStore.create_sync(
                engine=self.engine,  # REUSE SHARED ENGINE
                table_name=collection_name,
                embedding_service=self.embeddings,
            )

            print(
                f"[VECTOR_SERVICE] Successfully got vector store for {collection_name}"
            )
            return vector_store

        except Exception as e:
            print(
                f"[VECTOR_SERVICE] Failed to get vector store for {collection_name}: {str(e)}"
            )
            raise RuntimeError(f"Failed to get vector store: {str(e)}")

    def _ensure_table_exists(self, collection_name: str) -> None:
        """
        Ensure that the vector table exists for the collection.

        Uses shared engine for table initialization.

        Args:
            collection_name: Name of the collection/table

        Raises:
            RuntimeError: If table creation fails for reasons other than existing table
        """

        print(f"[VECTOR_SERVICE] Ensuring table exists: {collection_name}")

        try:
            # Use shared engine for table initialization
            vector_size = self.embedding_tool.get_embedding_dimension()
            print(f"[VECTOR_SERVICE] Vector size: {vector_size}")

            # Try to initialize table, but handle DuplicateTable gracefully
            try:
                self.engine.init_vectorstore_table(  # REUSE SHARED ENGINE
                    table_name=collection_name,
                    vector_size=vector_size,
                )
                print(
                    f"[VECTOR_SERVICE] Successfully created new table: {collection_name}"
                )
            except Exception as table_error:
                # Check if it's a DuplicateTable error (table already exists)
                if "already exists" in str(table_error) or "DuplicateTable" in str(
                    table_error
                ):
                    print(
                        f"[VECTOR_SERVICE] Table already exists (expected): {collection_name}"
                    )
                else:
                    # Re-raise if it's a different error
                    raise table_error

            print(f"[VECTOR_SERVICE] Table ready for use: {collection_name}")

        except Exception as e:
            print(f"[VECTOR_SERVICE] Failed to ensure table exists: {str(e)}")
            raise RuntimeError(f"Failed to ensure table exists: {str(e)}")

    def create_retriever(
        self, resource_id: UUID, search_kwargs: Optional[Dict[str, Any]] = None
    ):
        """
        Create a retriever for document search.

        Args:
            resource_id: UUID
            search_kwargs: Optional search parameters

        Returns:
            Configured retriever for the resource

        Raises:
            RuntimeError: If retriever creation fails
        """
        try:
            collection_name = self.get_collection_name(resource_id)
            print(
                f"[VECTOR_SERVICE] Creating retriever for collection: {collection_name}"
            )

            # SERVICE RESPONSIBILITY: Prepare resource-specific search parameters
            # Note: No resource_id filter needed since table name provides isolation
            default_search_kwargs = {"search_type": "similarity", "k": 5}

            # Merge with provided search kwargs
            if search_kwargs:
                default_search_kwargs.update(search_kwargs)

            # SERVICE RESPONSIBILITY: Create retriever using pre-created vector store
            print(f"[VECTOR_SERVICE] Creating retriever using existing vector store")
            vector_store = self._get_vector_store(collection_name)
            retriever = vector_store.as_retriever(search_kwargs=default_search_kwargs)

            print(f"[VECTOR_SERVICE] Successfully created retriever")
            return retriever

        except Exception as e:
            print(f"[VECTOR_SERVICE] Failed to create retriever: {str(e)}")
            raise RuntimeError(f"Failed to create retriever: {str(e)}")

    def similarity_search(
        self,
        query: str,
        resource_id: UUID,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        Perform similarity search.

        Args:
            query: Search query
            resource_id: UUID
            k: Number of results to return
            filter_dict: Additional filters

        Returns:
            List of similar documents

        Raises:
            RuntimeError: If search operation fails
        """
        try:
            collection_name = self.get_collection_name(resource_id)
            print(
                f"[VECTOR_SERVICE] Performing similarity search in collection: {collection_name}"
            )

            # SERVICE RESPONSIBILITY: Prepare search filter (no resource_id needed due to table isolation)
            search_filter = filter_dict if filter_dict else None

            # SERVICE RESPONSIBILITY: Perform search using pre-created vector store
            print(f"[VECTOR_SERVICE] Performing search using existing vector store")
            vector_store = self._get_vector_store(collection_name)
            results = vector_store.similarity_search(query, k=k, filter=search_filter)

            print(f"[VECTOR_SERVICE] Found {len(results)} similar documents")
            return results

        except Exception as e:
            print(f"[VECTOR_SERVICE] Similarity search failed: {str(e)}")
            raise RuntimeError(f"Similarity search failed: {str(e)}")

    def store_documents(
        self,
        documents: List[Document],
        resource_id: UUID,
    ) -> Dict[str, Any]:
        """
        Store documents in vector database.

        Args:
            documents: List of documents to store
            resource_id: UUID

        Returns:
            Storage result with metadata

        Raises:
            RuntimeError: If storage operation fails
        """
        print(
            f"Storing documents in vector database {len(documents)}",
        )

        try:
            collection_name = self.get_collection_name(resource_id)
            print(f"[VECTOR_SERVICE] Using collection name: {collection_name}")

            # SERVICE RESPONSIBILITY: Add metadata
            print(f"[VECTOR_SERVICE] Adding metadata to {len(documents)} documents")
            for doc in documents:
                doc.metadata.update({"collection": collection_name})

            # SERVICE RESPONSIBILITY: Store documents using pre-created vector store
            print(f"[VECTOR_SERVICE] Storing documents using existing vector store")
            vector_store = self._get_vector_store(collection_name)
            document_ids = vector_store.add_documents(documents)

            # SERVICE RESPONSIBILITY: Create result with service-level metadata
            enhanced_result = {
                "success": True,
                "collection_name": collection_name,
                "document_count": len(documents),
                "document_ids": document_ids,
                "embedding_model": "text-embedding-3-small",
            }

            print(
                f"[VECTOR_SERVICE] Successfully stored {enhanced_result['document_count']} documents in vector database",
            )
            return enhanced_result

        except Exception as e:
            print(
                f"[VECTOR_SERVICE] Failed to store documents in vector database: {str(e)}"
            )
            raise RuntimeError(
                f"[VECTOR_SERVICE] Failed to store documents in vector database: {str(e)}"
            )
