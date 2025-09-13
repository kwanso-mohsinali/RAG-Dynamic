"""
Chat service for AI chat operations and streaming.

This service handles RAG-based chat functionality with conversation
persistence using LangGraph workflows.
"""

from typing import Dict, Any, Optional, AsyncGenerator
from uuid import UUID
from langchain_core.messages import HumanMessage, AIMessage
from app.ai.workflows.create_rag_chat_workflow import (
    create_rag_chat_workflow,
    validate_rag_chat_input,
    prepare_rag_chat_config,
)
from app.ai.services.checkpointer_service import CheckpointerService
from app.ai.services.vector_service import VectorService
import logging

logger = logging.getLogger(__name__)


class ChatService:
    """
    Service for AI chat operations and streaming.

    Handles RAG-based chat functionality with conversation persistence
    using LangGraph workflows for proper state management.
    """

    def __init__(self, vector_service: VectorService):
        """
        Initialize ChatService with required dependencies.

        Args:
            vector_service: Optional VectorService instance. If not provided, creates new one.
        """

        # Use singleton pattern for checkpointer service
        self._checkpointer_service = CheckpointerService()

        # Initialize vector service
        self.vector_service = vector_service

    async def _get_workflow(self, resource_id: UUID, async_mode: bool = False):
        """
        Get or create RAG chat workflow for the resource.

        Args:
            resource_id: Resource UUID
            async_mode: If True, create async workflow for streaming

        Returns:
            Compiled LangGraph workflow
        """
        try:
            logger.info(
                f"[CHAT_SERVICE] Creating {'async' if async_mode else 'sync'} workflow for resource {resource_id}"
            )

            # Reuse existing checkpointer service (singleton pattern)
            # This prevents creating multiple connection pools
            checkpointer_service = self._checkpointer_service

            # Create workflow with proper async/sync mode
            workflow = await create_rag_chat_workflow(
                resource_id=resource_id,
                checkpointer_service=checkpointer_service,
                async_mode=async_mode,  # Use proper async/sync mode
            )

            logger.info(
                f"[CHAT_SERVICE] Workflow created successfully for resource {resource_id}"
            )
            return workflow

        except Exception as e:
            logger.error(
                f"[CHAT_SERVICE] Failed to create workflow for resource {resource_id}: {str(e)}"
            )
            raise RuntimeError(f"Failed to create workflow: {str(e)}")

    async def send_message(
        self, resource_id: UUID, message: str, thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a chat message and get AI response using RAG workflow.

        Args:
            resource_id: Resource UUID
            message: User message
            thread_id: Optional thread ID for conversation persistence

        Returns:
            AI response with context

        Raises:
            RuntimeError: If processing fails
        """
        try:
            logger.info(
                f"[CHAT_SERVICE] Processing chat message for resource {resource_id}, thread {thread_id}"
            )

            # Prepare workflow input
            input_data = {
                "message": message,
                "resource_id": str(resource_id),
                "thread_id": thread_id or "default",
            }

            # Debug: Log what we're preparing
            logger.info(f"[CHAT_SERVICE] Input data: {input_data}")

            # Validate input
            validated_input = validate_rag_chat_input(input_data)
            config = prepare_rag_chat_config(thread_id or "default")

            # Debug: Log what we're passing to the workflow
            logger.info(f"[CHAT_SERVICE] Validated input: {validated_input}")
            logger.info(f"[CHAT_SERVICE] Config: {config}")

            # Get async workflow for regular chat (consistent with ainvoke)
            workflow = await self._get_workflow(resource_id, async_mode=True)

            # Execute workflow
            logger.info(
                f"[CHAT_SERVICE] Executing async workflow for resource {resource_id}"
            )
            result = await workflow.ainvoke(validated_input, config=config)

            # Extract response
            answer = result.get("answer", "")
            context = result.get("context", "")
            messages = result.get("messages", [])

            # Get AI message from result
            ai_message = None
            if messages:
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage):
                        ai_message = msg
                        break

            if not ai_message:
                ai_message = AIMessage(content=answer)

            logger.info(
                f"[CHAT_SERVICE] Successfully processed message for resource {resource_id}"
            )
            logger.info(
                f"[CHAT_SERVICE] Generated response length: {len(answer)} characters"
            )

            return {
                "answer": answer,
                "context": context,
                "thread_id": thread_id or "default",
                "resource_id": str(resource_id),
            }

        except Exception as e:
            logger.error(
                f"[CHAT_SERVICE] Failed to process chat message for resource {resource_id}: {str(e)}"
            )
            raise RuntimeError(f"Failed to process chat message: {str(e)}")

    async def send_message_non_streaming(
        self, resource_id: UUID, message: str, thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a chat message using LangGraph workflow (non-streaming).

        This approach uses LangGraph workflow directly without streaming:
        1. Single workflow handles everything (conversation, processing, state)
        2. Automatic state management and persistence
        3. Returns complete response at once

        Args:
            resource_id: Resource UUID
            message: User message
            thread_id: Optional thread ID for conversation persistence

        Returns:
            Complete response with conversation state

        Raises:
            RuntimeError: If processing fails
        """
        try:
            logger.info(
                f"[CHAT_SERVICE] Processing non-streaming message for resource {resource_id}, thread {thread_id}"
            )

            # Get workflow for processing
            workflow = await self._get_workflow(resource_id, async_mode=True)

            # Prepare input for workflow
            input_data = {
                "message": message,
                "resource_id": str(resource_id),
                "thread_id": thread_id or "default",
            }

            # Prepare config for conversation persistence
            from app.ai.workflows.create_rag_chat_workflow import (
                prepare_rag_chat_config,
            )

            config = prepare_rag_chat_config(thread_id or "default")

            logger.info(
                f"[CHAT_SERVICE] Starting workflow processing for resource {resource_id}"
            )

            # Use workflow directly for non-streaming processing
            # This handles conversation state, persistence, and processing automatically
            result = await workflow.ainvoke(input_data, config=config)

            logger.info(
                f"[CHAT_SERVICE] Successfully processed message for resource {resource_id}"
            )

            # Extract response from workflow result
            if hasattr(result, "values") and "messages" in result.values:
                messages = result.values["messages"]
                if messages and hasattr(messages[-1], "content"):
                    response = messages[-1].content
                else:
                    response = "No response generated"
            else:
                response = "No response generated"

            return {
                "content": response,
                "context": "",
                "thread_id": thread_id or "default",
                "conversation_state": result,
            }

        except Exception as e:
            logger.error(
                f"[CHAT_SERVICE] Failed to process message for resource {resource_id}: {str(e)}"
            )
            raise RuntimeError(f"Failed to process message: {str(e)}")

    async def stream_message(
        self, resource_id: UUID, message: str, thread_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream a chat message response using hybrid approach.

        This approach:
        1. Uses LangGraph workflow for conversation management and persistence
        2. Uses direct RAG chain streaming for real-time content generation
        3. Maintains conversation history through workflow state

        Args:
            resource_id: Resource UUID
            message: User message
            thread_id: Optional thread ID for conversation persistence

        Yields:
            Streaming response chunks

        Raises:
            RuntimeError: If processing fails
        """
        import asyncio

        try:

            logger.info(
                f"[CHAT_SERVICE] Processing streaming message for resource {resource_id}, thread {thread_id}"
            )

            # Step 1: Update workflow state FIRST to save the user message
            # This ensures conversation history is saved even if streaming fails
            workflow = await self._get_workflow(resource_id, async_mode=True)

            # Prepare input for workflow state update
            workflow_input = {
                "message": message,
                "resource_id": str(resource_id),
                "thread_id": thread_id or "default",
            }

            # Validate input
            from app.ai.workflows.create_rag_chat_workflow import (
                validate_rag_chat_input,
                prepare_rag_chat_config,
            )

            validated_input = validate_rag_chat_input(workflow_input)
            config = prepare_rag_chat_config(thread_id or "default")

            # Update workflow state to save user message
            logger.info(f"[CHAT_SERVICE] Updating workflow state with user message")
            await workflow.ainvoke(validated_input, config=config)

            # Step 2: Get conversation history from updated workflow state
            conversation_history = []
            try:
                # Get current state to extract conversation history
                current_state = await workflow.aget_state(config)
                if (
                    current_state
                    and hasattr(current_state, "values")
                    and "messages" in current_state.values
                ):
                    conversation_history = current_state.values["messages"]
                    logger.info(
                        f"[CHAT_SERVICE] Loaded {len(conversation_history)} messages from conversation history"
                    )
            except Exception as e:
                logger.error(
                    f"[CHAT_SERVICE] Could not load conversation history: {str(e)}"
                )

            # Step 3: Stream response using RAG chain
            from app.ai.chains.rag_chain import RAGChain

            rag_chain = RAGChain(resource_id, self.vector_service)

            # Prepare input for streaming
            input_data = {"input": message, "chat_history": conversation_history}

            logger.info(
                f"[CHAT_SERVICE] Starting RAG chain streaming for resource {resource_id}"
            )

            # Stream directly from the RAG chain with timeout protection
            chunk_count = 0
            context = ""
            start_time = asyncio.get_event_loop().time()
            timeout_seconds = 60
            source_documents = []
            complete_response = ""  # Store complete response during streaming

            try:
                async for chunk in rag_chain.astream(input_data):
                    # Check timeout
                    current_time = asyncio.get_event_loop().time()
                    if current_time - start_time > timeout_seconds:
                        logger.error(
                            f"[CHAT_SERVICE] Streaming timeout after {timeout_seconds} seconds"
                        )
                        break

                    chunk_count += 1

                    # Extract content and context from chunk
                    content = chunk.get("answer", "")
                    context = chunk.get("context", "")
                    source_docs = chunk.get("source_documents", [])

                    if content:
                        # Accumulate complete response for workflow update
                        complete_response += content

                        yield {
                            "content": content,
                            "context": context,
                            "thread_id": thread_id or "default",
                            "is_final": False,
                        }

                        # Store source documents for final chunk
                        if source_docs and not source_documents:
                            source_documents = source_docs

            except asyncio.TimeoutError:
                logger.error(
                    f"[CHAT_SERVICE] Streaming timeout for resource {resource_id}"
                )
                yield {
                    "content": "Streaming timeout - response incomplete",
                    "context": "",
                    "thread_id": thread_id or "default",
                    "is_final": True,
                }
                return

            # Step 4: Update workflow state with the complete AI response
            if thread_id and complete_response:
                try:
                    # Create AI message for workflow state update
                    from langchain_core.messages import AIMessage

                    ai_message = AIMessage(content=complete_response)

                    # Add AI message to conversation history
                    conversation_history.append(ai_message)

                    # Update workflow state with the complete conversation
                    logger.info(
                        f"[CHAT_SERVICE] Updating workflow state with AI response (length: {len(complete_response)})"
                    )

                    # The workflow state is already updated with user message,
                    # so we just need to ensure the AI response is also saved
                    # This is handled automatically by the workflow's state management

                    logger.info(
                        f"[CHAT_SERVICE] Workflow state update completed for thread_id: {thread_id}"
                    )
                except Exception as e:
                    logger.error(
                        f"[CHAT_SERVICE] Could not update workflow state: {str(e)}"
                    )
                    # Don't fail the streaming if workflow update fails

            # Send final chunk with full context
            final_chunk = {
                "content": "",
                "context": context,
                "thread_id": thread_id or "default",
                "is_final": True,
            }

            logger.info(f"[CHAT_SERVICE] Yielding final chunk...")
            yield final_chunk

        except Exception as e:
            logger.error(
                f"[CHAT_SERVICE] Failed to process chat message for resource {resource_id}: {str(e)}"
            )
            raise RuntimeError(f"Failed to process chat message: {str(e)}")

    async def get_conversation_history(
        self,
        resource_id: UUID,
        thread_id: str,
    ) -> list[dict[str, Any]]:
        """
        Get conversation history from LangGraph workflow state.

        Args:
            resource_id: Resource UUID
            thread_id: Conversation thread ID

        Returns:
            List of conversation messages with role and content
        """
        try:
            # Get workflow to access conversation history
            workflow = await self._get_workflow(resource_id, async_mode=True)

            # Prepare config to get current state
            config = prepare_rag_chat_config(thread_id)

            # Get current state (this will load existing conversation)
            current_state = await workflow.aget_state(config)

            if current_state:
                # Check if messages are in state.values
                if (
                    hasattr(current_state, "values")
                    and "messages" in current_state.values
                ):
                    messages = current_state.values["messages"]

                    # Convert LangGraph messages to simple format
                    history = []
                    for message in messages:

                        # Get message content
                        content = getattr(message, "content", "")
                        if not content:
                            logger.info(
                                f"[CHAT_SERVICE] Message has no content: {message}"
                            )
                            continue

                        # Determine message role
                        if isinstance(message, HumanMessage):
                            role = "human"
                        elif isinstance(message, AIMessage):
                            role = "assistant"
                        elif hasattr(message, "type"):
                            role = "human" if message.type == "human" else "assistant"
                        else:
                            role = "unknown"
                            logger.info(
                                f"[CHAT_SERVICE] Unknown message type: {type(message)}"
                            )

                        history.append(
                            {
                                "role": role,
                                "content": content,
                                "timestamp": getattr(message, "additional_kwargs", {}).get("timestamp", None),
                            }
                        )
                    return history
                elif hasattr(current_state, "messages"):
                    # Fallback to direct messages attribute
                    messages = current_state.messages

                    # Convert LangGraph messages to simple format
                    history = []
                    for message in messages:

                        # Get message content
                        content = getattr(message, "content", "")
                        if not content:
                            logger.info(
                                f"[CHAT_SERVICE] Message has no content: {message}"
                            )
                            continue

                        # Determine message role
                        if isinstance(message, HumanMessage):
                            role = "human"
                        elif isinstance(message, AIMessage):
                            role = "assistant"
                        elif hasattr(message, "type"):
                            role = "human" if message.type == "human" else "assistant"
                        else:
                            role = "unknown"
                            logger.info(
                                f"[CHAT_SERVICE] Unknown message type: {type(message)}"
                            )
                        history.append(
                            {
                                "role": role,
                                "content": content,
                                "timestamp": getattr(message, "additional_kwargs", {}).get("timestamp", None),
                            }
                        )
                    return history
                else:
                    logger.info(
                        f"[CHAT_SERVICE] No 'messages' found in state.values or direct attribute"
                    )
                    logger.info(
                        f"[CHAT_SERVICE] Available keys in state.values: {list(current_state.values.keys()) if hasattr(current_state, 'values') else 'No values attribute'}"
                    )
            else:
                logger.info(
                    f"[CHAT_SERVICE] No current state found for thread {thread_id}"
                )

            logger.info(
                f"[CHAT_SERVICE] No conversation history found for thread {thread_id}"
            )
            return []

        except Exception as e:
            logger.error(f"[CHAT_SERVICE] Failed to get conversation history: {str(e)}")
            return []

    async def clear_conversation_history(self, thread_id: str) -> None:
        """
        Clear persisted conversation for a given thread by deleting checkpoints.

        Returns True on success, False otherwise.
        """
        try:
            return await self._checkpointer_service.delete_postgres_checkpointer(
                thread_id
            )
        except Exception as e:
            logger.error(
                f"[CHAT_SERVICE] Failed to clear conversation for thread {thread_id}: {str(e)}"
            )
            raise RuntimeError(f"Failed to clear conversation history: {str(e)}")
