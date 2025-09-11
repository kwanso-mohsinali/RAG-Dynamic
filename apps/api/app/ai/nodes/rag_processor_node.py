"""
RAG processor node - lightweight container for RAG query processing.

This node delegates all RAG processing logic to the RAGChain.
"""

from typing import Dict, Any
from uuid import UUID
from langchain_core.messages import HumanMessage, AIMessage
from app.ai.schemas.workflow_states import RAGChatState
from app.ai.chains.rag_chain import RAGChain
from app.ai.services.vector_service import VectorService
import logging

logger = logging.getLogger(__name__)

def rag_processor_node(state: RAGChatState) -> Dict[str, Any]:
    """
    Lightweight LangGraph node container for RAG processing.

    This node delegates all RAG processing logic to the RAGChain.

    With RAGChatState and add_messages annotation, LangGraph automatically
    handles conversation history - we just need to return the AI response.

    Args:
        state: RAGChatState containing messages and resource context

    Returns:
        Updated state with RAG processing results
    """
    resource_id = (
        state.resource_id
        if hasattr(state, "resource_id")
        else state.get("resource_id", "unknown")
    )
    logger.info(f"[RAG_PROCESSOR_NODE] Starting RAG processing for resource {resource_id}")

    try:
        # Extract messages from state (LangGraph already merged conversation history)
        messages = (
            state.messages if hasattr(state, "messages") else state.get("messages", [])
        )
        if not messages:
            logger.info(
                f"[RAG_PROCESSOR_NODE] No messages provided for resource {resource_id}"
            )
            return {
                "answer": "No message to process",
                "messages": [AIMessage(content="No message to process")],
            }

        # Get the last human message (the current user input)
        last_message = messages[-1]
        if not isinstance(last_message, HumanMessage):
            logger.info(
                f"[RAG_PROCESSOR_NODE] Expected human message for resource {resource_id}"
            )
            return {
                "answer": "Expected human message",
                "messages": [AIMessage(content="Expected human message")],
            }

        user_input = last_message.content
        logger.info(
            f"[RAG_PROCESSOR_NODE] Processing query: {user_input[:50]}... for resource {resource_id}"
        )

        # Prepare chat history (exclude the current message)
        # LangGraph has already provided us with the full conversation history
        chat_history = messages[:-1] if len(messages) > 1 else []

        # Initialize RAG processing chain
        logger.info(f"[RAG_PROCESSOR_NODE] Initializing RAGChain for resource {resource_id}")

        # IMPORTANT: Use shared VectorService from the workflow instead of creating new one
        # The vector_service should be passed through the workflow state or we need to modify
        # the workflow to pass it to the node. For now, we'll create a new one but this
        # should be optimized to use the shared instance.
        vector_service = VectorService()  # This will use the shared engine

        # Create RAG chain with resource context
        rag_chain = RAGChain(UUID(resource_id), vector_service)

        # Process through chain
        logger.info(f"[RAG_PROCESSOR_NODE] Delegating to RAGChain for resource {resource_id}")

        # Use invoke method for consistent processing
        chain_result = rag_chain.invoke(
            {"input": user_input, "chat_history": chat_history}
        )

        # Extract results
        answer = chain_result.get("answer", "")
        context = chain_result.get("context", "")

        # Create AI response message
        ai_message = {"role": "assistant", "content": answer}

        logger.info(
            f"[RAG_PROCESSOR_NODE] RAG processing completed successfully for resource {resource_id}"
        )
        logger.info(
            f"[RAG_PROCESSOR_NODE] Generated response length: {len(answer)} characters"
        )

        # SIMPLIFIED: With add_messages annotation, we just return the AI message
        # LangGraph will automatically append it to the conversation history
        return {
            # ← add_messages will append this automatically
            "messages": [ai_message],
            "context": context,
            "answer": answer,
        }

    except Exception as e:
        logger.error(
            f"[RAG_PROCESSOR_NODE] RAG processor node failed for resource {resource_id}: {str(e)}"
        )

        error_message = AIMessage(
            content=f"I apologize, but I encountered an error: {str(e)}"
        )

        # Even for errors, let add_messages handle history
        return {
            "error_message": f"RAG processor node failed: {str(e)}",
            # ← add_messages will append this automatically
            "messages": [error_message],
            "answer": str(e),
        }


async def rag_processor_node_streaming_async(state: RAGChatState) -> Dict[str, Any]:
    """
    Async streaming version of RAG processor node for LangGraph workflow streaming.

    This node uses async LLM streaming to enable LangGraph workflow streaming.
    The LLM calls inside this node will stream, which allows LangGraph to stream the tokens.

    Args:
        state: RAGChatState containing messages and resource context

    Returns:
        Updated state with RAG processing results
    """
    from langchain_openai import ChatOpenAI
    from app.core.config import settings

    resource_id = (
        state.resource_id
        if hasattr(state, "resource_id")
        else state.get("resource_id", "unknown")
    )
    logger.info(
        f"[RAG_PROCESSOR_NODE_STREAMING_ASYNC] Starting async streaming RAG processing for resource {resource_id}"
    )

    try:
        # Extract messages from state (LangGraph already merged conversation history)
        messages = (
            state.messages if hasattr(state, "messages") else state.get("messages", [])
        )
        if not messages:
            logger.info(
                f"[RAG_PROCESSOR_NODE_STREAMING_ASYNC] No messages provided for resource {resource_id}"
            )
            return {
                "answer": "No message to process",
                "messages": [AIMessage(content="No message to process")],
            }

        # Get the last human message (the current user input)
        last_message = messages[-1]
        logger.info(
            f"[RAG_PROCESSOR_NODE_STREAMING_ASYNC] Last message type: {type(last_message)}, content: {getattr(last_message, 'content', '')[:50]}..."
        )

        # Debug: Log all messages to understand the conversation state
        logger.info(
            f"[RAG_PROCESSOR_NODE_STREAMING_ASYNC] Total messages in conversation: {len(messages)}"
        )
        for i, msg in enumerate(messages):
            logger.info(
                f"[RAG_PROCESSOR_NODE_STREAMING_ASYNC] Message {i}: {type(msg)} - {getattr(msg, 'content', '')[:50]}..."
            )

        if not isinstance(last_message, HumanMessage):
            logger.info(
                f"[RAG_PROCESSOR_NODE_STREAMING_ASYNC] Expected human message for resource {resource_id}, got {type(last_message)}"
            )
            # Instead of returning an error, try to find the last human message
            human_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
            if human_messages:
                last_human_message = human_messages[-1]
                logger.info(
                    f"[RAG_PROCESSOR_NODE_STREAMING_ASYNC] Found last human message: {last_human_message.content[:50]}..."
                )
                user_input = last_human_message.content
            else:
                logger.info(
                    f"[RAG_PROCESSOR_NODE_STREAMING_ASYNC] No human messages found in conversation"
                )
                return {
                    "answer": "No human message found in conversation",
                    "messages": [
                        AIMessage(content="No human message found in conversation")
                    ],
                }
        else:
            user_input = last_message.content
        logger.info(
            f"[RAG_PROCESSOR_NODE_STREAMING_ASYNC] Processing query: {user_input[:50]}... for resource {resource_id}"
        )

        # Prepare chat history (exclude the current message)
        chat_history = messages[:-1] if len(messages) > 1 else []

        # Initialize vector service for document retrieval
        logger.info(
            f"[RAG_PROCESSOR_NODE_STREAMING_ASYNC] Initializing VectorService for resource {resource_id}"
        )

        vector_service = VectorService()  # This will use the shared engine

        # Retrieve relevant documents
        retriever = vector_service.create_retriever(
            resource_id=UUID(resource_id), search_kwargs={"k": 10}
        )

        relevant_docs = retriever.invoke(user_input)
        logger.info(
            f"[RAG_PROCESSOR_NODE_STREAMING_ASYNC] Retrieved {len(relevant_docs)} relevant documents"
        )

        # Format context from documents
        context = ""
        if relevant_docs:
            formatted_docs = []
            for i, doc in enumerate(relevant_docs, 1):
                metadata = doc.metadata
                source_file = (
                    metadata.get("source_file")
                    or metadata.get("file_name")
                    or metadata.get("original_filename")
                )
                page = metadata.get("page") or metadata.get("page_number", "N/A")
                chunk_index = metadata.get("chunk_index", "")

                formatted_docs.append(
                    f"Document {i} (File: {source_file}, Page: {page}, Chunk: {chunk_index}):\n"
                    f"Text Content:\n{doc.page_content}\n"
                )
            context = "\n\n".join(formatted_docs)
        else:
            context = "No relevant documents found in the resource."

        # Initialize LLM with streaming support
        llm = ChatOpenAI(
            model=settings.MODEL,
            streaming=True,  # This enables streaming
            openai_api_key=settings.OPENAI_API_KEY,
        )

        # Create system message with context
        from langchain_core.messages import SystemMessage

        system_content = f"""You are a helpful AI assistant. Answer questions based on the provided context.

        Context:
        {context}

        Please provide a helpful and accurate response based on the context above."""

        # Create messages for the LLM
        llm_messages = [SystemMessage(content=system_content)]

        # Add chat history if any
        if chat_history:
            llm_messages.extend(chat_history)

        # Add the current user message
        llm_messages.append(HumanMessage(content=user_input))

        # Use the LLM with async streaming
        # This allows LangGraph to stream the tokens
        logger.info(
            f"[RAG_PROCESSOR_NODE_STREAMING_ASYNC] Calling LLM with async streaming for resource {resource_id}"
        )

        # Use ainvoke for async streaming - this is what enables LangGraph workflow streaming
        response = await llm.ainvoke(llm_messages)
        answer = response.content
        
        # Create AI response message
        ai_message = {"role": "assistant", "content": answer}

        logger.info(
            f"[RAG_PROCESSOR_NODE_STREAMING_ASYNC] RAG processing completed successfully for resource {resource_id}"
        )
        logger.info(
            f"[RAG_PROCESSOR_NODE_STREAMING_ASYNC] Generated response length: {len(answer)} characters"
        )

        # Return the final state for LangGraph
        # IMPORTANT: We return the AI message to be appended to the conversation
        # LangGraph will automatically merge this with existing messages
        return {
            # This will be appended to existing messages
            "messages": [ai_message],
            "context": context,
            "answer": answer,
        }

    except Exception as e:
        logger.error(
            f"[RAG_PROCESSOR_NODE_STREAMING_ASYNC] RAG processor node failed for resource {resource_id}: {str(e)}"
        )

        error_message = AIMessage(
            content=f"I apologize, but I encountered an error: {str(e)}"
        )

        return {
            "error_message": f"RAG processor node failed: {str(e)}",
            "messages": [error_message],
            "answer": str(e),
        }
