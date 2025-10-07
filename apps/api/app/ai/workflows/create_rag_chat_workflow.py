"""
RAG chat workflow definition using function-based approach.

This follows the established pattern where workflows are pure functions
that define the graph structure and return compiled applications.
"""

from datetime import datetime
from typing import Dict, Any
from uuid import UUID
from langgraph.graph import StateGraph, START, END
from app.ai.nodes.rag_processor_node import rag_processor_node_streaming_async
from app.ai.services.checkpointer_service import CheckpointerService
from app.ai.schemas.workflow_states import RAGChatState
import logging

logger = logging.getLogger(__name__)


async def create_rag_chat_workflow(
    resource_id: UUID,
    checkpointer_service=None,
    async_mode: bool = False,
) -> StateGraph:
    """
    Create RAG chat workflow for resource-specific document querying.

    Uses proper PostgreSQL checkpointer context manager pattern.
    """

    # Create workflow with proper state schema
    workflow = StateGraph(RAGChatState)
    # Use streaming version
    workflow.add_node("rag_processor", rag_processor_node_streaming_async)
    workflow.add_edge(START, "rag_processor")
    workflow.add_edge("rag_processor", END)

    # Use provided checkpointer service or create new one
    if checkpointer_service is None:
        checkpointer_service = CheckpointerService()
        logger.info("[RAG_CHAT_WORKFLOW] Created new CheckpointerService")
    else:
        logger.info(
            "[RAG_CHAT_WORKFLOW] Using provided CheckpointerService with shared connection"
        )

    # Create checkpointer based on mode
    if async_mode:
        logger.info("[RAG_CHAT_WORKFLOW] Using async checkpointer for streaming")
    else:
        logger.info("[RAG_CHAT_WORKFLOW] Using sync checkpointer for regular execution")

    checkpointer = await checkpointer_service.create_checkpointer(async_mode)

    # Log checkpointer type
    checkpointer_type = checkpointer_service.get_checkpointer_type(checkpointer)
    logger.info(
        f"[RAG_CHAT_WORKFLOW] Using {checkpointer_type} checkpointer for resource {resource_id}"
    )

    # Compile workflow with checkpointer
    # Note: For PostgreSQL checkpointers, LangGraph will handle the context manager
    app = workflow.compile(checkpointer=checkpointer)

    logger.info(
        f"[RAG_CHAT_WORKFLOW] Workflow compiled successfully for resource {resource_id}"
    )

    return app


def validate_rag_chat_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and prepare input for RAG chat workflow.

    This function prepares the input for LangGraph. The checkpointer will automatically
    handle conversation history by appending the current message to existing messages.

    Args:
        input_data: Raw input data

    Returns:
        Validated and formatted state dict

    Raises:
        ValueError: If input validation fails
    """

    # Extract required fields
    message = input_data.get("message", "")
    resource_id = input_data.get("resource_id")
    thread_id = input_data.get("thread_id", "default")
    resource_details = input_data.get("resource_details", "")

    if not message:
        raise ValueError("Message is required")

    if not resource_id:
        raise ValueError("Resource ID is required")

    # Create human message as a serializable dictionary
    # This avoids JSON serialization issues with LangChain objects in the checkpointer
    human_message_dict = {
        "type": "human",
        "content": message,
        "additional_kwargs": {"timestamp": datetime.utcnow()},
        "response_metadata": {},
    }

    # Prepare state with current message
    # LangGraph's checkpointer will automatically:
    # 1. Retrieve existing conversation state using thread_id
    # 2. Append this new message to the existing messages (thanks to add_messages annotation)
    # 3. Pass the complete conversation history to the workflow
    state = {
        # This will be appended to existing messages
        "messages": [human_message_dict],
        "resource_id": str(resource_id),
        "resource_details": str(resource_details),
        "context": "",  # Initialize empty context
        "answer": "",  # Initialize empty answer
    }

    logger.info(
        f"[RAG_CHAT_WORKFLOW] Prepared input state with {len(state['messages'])} messages for thread_id: {thread_id}"
    )
    logger.info(
        f"[RAG_CHAT_WORKFLOW] Human message content: {human_message_dict['content'][:50]}..."
    )

    return state


def prepare_rag_chat_config(thread_id: str) -> Dict[str, Any]:
    """
    Prepare configuration for RAG chat workflow execution.

    Args:
        thread_id: Thread identifier for conversation persistence

    Returns:
        Configuration dict for workflow execution
    """
    return {
        "configurable": {"thread_id": thread_id},
        "metadata": {"thread_id": thread_id},     # Used for making thread id in langsmith
        "run_name": "rag_chat_workflow",          # specify trace name in langsmith
    }
