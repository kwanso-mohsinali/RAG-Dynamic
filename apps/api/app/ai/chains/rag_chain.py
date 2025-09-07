from typing import Any, Dict, List
from uuid import UUID
from langchain_core.documents import Document
from langchain_core.runnables import RunnableParallel
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.ai.services.vector_service import VectorService
from app.core.config import settings
from app.ai.prompts.rag_prompts import RAG_SYSTEM_PROMPT
import logging

logger = logging.getLogger(__name__)

class RAGChain:
    """Complete RAG system implementation using LangChain, pgvector, and OpenAI."""

    def __init__(self, resource_id: UUID, vector_service: VectorService):
        """
        Initialize RAG chain for a specific resource.

        Args:
            resource_id: Resource UUID for namespace isolation
            vector_service: Existing VectorService instance
        """
        self.resource_id = resource_id
        self.vector_service = vector_service

        # Initialize LLM with streaming support
        self.llm = ChatOpenAI(
            model=settings.MODEL, streaming=True, openai_api_key=settings.OPENAI_API_KEY
        )

        # Create resource-specific retriever using existing VectorService
        self.retriever = self.vector_service.create_retriever(
            resource_id=resource_id,
            search_kwargs={"k": 10},  # Retrieve top 10 relevant chunks
        )

        # Build the RAG chain
        self.chain = self._build_rag_chain()

    def _build_rag_chain(self):
        """
        Build the RAG chain following LangChain patterns.

        Returns:
            Configured RAG chain with context retrieval and response generation
        """
        # RAG prompt template with conversation history support
        # Using centralized prompt constant for consistency and maintainability
        rag_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", RAG_SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ]
        )

        # Build the chain using proper retrieval and formatting
        def retrieve_and_format(query: str) -> str:
            """Retrieve documents and format them for context."""
            docs = self.retriever.invoke(query)
            return self._format_docs(docs)

        rag_chain = (
            RunnableParallel(
                {
                    "context": lambda x: retrieve_and_format(x["input"]),
                    "chat_history": lambda x: x.get("chat_history", []),
                    "input": lambda x: x["input"],
                }
            )
            | rag_prompt
            | self.llm
            | StrOutputParser()
        )

        return rag_chain

    def _format_docs(self, docs: List[Document]) -> str:
        """
        Format retrieved documents for context.

        Args:
            docs: List of retrieved documents

        Returns:
            Formatted context string with source attribution
        """
        if not docs:
            return "No relevant documents found in the resource."

        formatted_docs = []
        for i, doc in enumerate(docs, 1):
            # Extract metadata for source attribution
            metadata = doc.metadata
            # Try to get the actual filename from various metadata fields
            source_file = (
                metadata.get("source_file") or metadata.get("file_type") or "Unknown"
            )

            page = metadata.get("page") or metadata.get("page_number", "N/A")
            chunk_index = metadata.get("chunk_index", "")

            # Create a more informative source reference
            if chunk_index:
                source_ref = f"File: {source_file}, Page: {page}, Chunk: {chunk_index}"
            else:
                source_ref = f"File: {source_file}, Page: {page}"

            formatted_doc = f"""
               Document {i} ({source_ref}):
               {doc.page_content}
            """
            formatted_docs.append(formatted_doc)

        return "\n".join(formatted_docs)

    def invoke(self, input_data: Dict[str, Any], callbacks=None) -> str:
        """
        Invoke the RAG chain with input data.

        Args:
            input_data: Dictionary containing:
                - input: User question
                - chat_history: List of previous messages

        Returns:
            Dictionary with answer and context
        """
        try:
            # Extract input components
            user_input = input_data.get("input", "")
            chat_history = input_data.get("chat_history", [])

            # Prepare chain input
            chain_input = {
                "chat_history": chat_history,
                "input": user_input,
            }

            # Generate response (pass callbacks for tracking)
            config = {"callbacks": callbacks} if callbacks else None
            answer = self.chain.invoke(chain_input, config=config)

            return answer

        except Exception as e:
            logger.error(f"[RAG_CHAIN] Error processing query: {str(e)}")
            raise

    async def astream(self, input_data: Dict[str, Any]):
        """
        Stream the RAG chain response.

        Args:
            input_data: Dictionary containing input and chat_history

        Yields:
            Streaming response chunks with context information
        """
        try:
            # Validate input
            if not isinstance(input_data, dict):
                raise ValueError("Input data must be a dictionary")

            # Extract input components
            user_input = input_data.get("input", "")
            chat_history = input_data.get("chat_history", [])

            if not user_input or not user_input.strip():
                raise ValueError("User input cannot be empty")

            logger.info(
                f"[RAG_CHAIN] Starting streaming for query: {user_input[:50]}..."
            )

            # Retrieve relevant documents
            relevant_docs = self.retriever.invoke(user_input)
            logger.info(
                f"[RAG_CHAIN] Retrieved {len(relevant_docs)} relevant documents"
            )

            # Format context
            context = self._format_docs(relevant_docs)

            # Use the LLM's astream method directly for better streaming
            # Create the system message with context
            from langchain_core.messages import SystemMessage, HumanMessage

            system_content = f"""You are a helpful AI assistant. Answer questions based on the provided context.

            Context:
            {context}

            Please provide a helpful and accurate response based on the context above."""

            # Create messages for the LLM
            messages = [SystemMessage(content=system_content)]

            # Add chat history if any
            if chat_history:
                messages.extend(chat_history)

            # Add the current user message
            messages.append(HumanMessage(content=user_input))

            # Stream directly from the LLM
            chunk_count = 0
            async for chunk in self.llm.astream(messages):
                chunk_count += 1
                if hasattr(chunk, "content") and chunk.content:
                    yield {
                        "answer": chunk.content,
                        "context": context,  # Include context in each chunk
                        "source_documents": relevant_docs,
                    }
                else:
                    logger.info(f"[RAG_CHAIN] Empty chunk {chunk_count}")

            logger.info(f"[RAG_CHAIN] Streaming completed with {chunk_count} chunks")

        except Exception as e:
            logger.error(f"[RAG_CHAIN] Error streaming query: {str(e)}")
            # Yield error chunk instead of raising
            yield {"answer": f"Error: {str(e)}", "context": "", "source_documents": []}
