"""
Chat endpoints for RAG-based conversational AI.

This module provides FastAPI endpoints for resource-specific chat functionality
with streaming support and conversation management.
"""

import logging
from typing import Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_conversation_service, get_current_user_id
from app.ai.dependencies import ChatServiceDep
from app.services.conversation_service import ConversationService
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatStreamChunk,
    ConversationHistoryResponse,
    ConversationListResponse,
    ConversationDeactivateResponse,
    ResourceChatStatsResponse,
    ConversationSummary,
    ConversationMessage,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/resources/{resource_id}/chat/message",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send chat message",
    description="Send a message to the resource's RAG chat system and get an AI response.",
)
async def send_chat_message(
    resource_id: UUID,
    request: ChatMessageRequest,
    chat_service: ChatServiceDep,
    user_id: UUID = Depends(get_current_user_id),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ChatMessageResponse:
    """
    Send a message to the resource's RAG chat system.

    This endpoint:
    - Creates or uses existing conversation
    - Processes the message through the RAG pipeline
    - Returns the AI response with context
    """
    try:
        logger.info(
            f"[CHAT_ENDPOINT] User {user_id} sending message to resource {resource_id}"
        )

        # Step 1: Get or create conversation through business service
        conversation = conversation_service.get_or_create_conversation(
            resource_id=resource_id, user_id=user_id
        )

        # Step 2: Send message through AI service
        ai_response = await chat_service.send_message(
            resource_id=resource_id,
            message=request.message,
            thread_id=conversation.thread_id,
        )

        # Step 3: Update conversation metadata
        updated_conversation = conversation_service.update_conversation_metadata(
            conversation_id=conversation.id,
            user_id=user_id,
            message_count_increment=2,  # User message + AI response
        )

        return ChatMessageResponse(
            answer=ai_response.get("answer", ""),
            context=ai_response.get("context", ""),
            conversation_id=updated_conversation.id,
            thread_id=ai_response.get("thread_id", conversation.thread_id),
            message_count=updated_conversation.message_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CHAT_ENDPOINT] Error sending message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message",
        )


@router.post(
    "/resources/{resource_id}/chat/stream",
    response_class=StreamingResponse,
    summary="Stream chat message",
    description="Send a message and receive streaming AI response.",
)
async def stream_chat_message(
    resource_id: UUID,
    request: ChatMessageRequest,
    chat_service: ChatServiceDep,
    user_id: UUID = Depends(get_current_user_id),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> StreamingResponse:
    """
    Send a message and receive streaming AI response.

    This endpoint:
    - Creates or uses existing conversation
    - Streams the AI response in real-time
    - Returns Server-Sent Events (SSE) format
    """
    try:
        logger.info(
            f"[CHAT_ENDPOINT] User {user_id} streaming message to resource {resource_id}"
        )

        # Get or create conversation through business service
        conversation = conversation_service.get_or_create_conversation(
            resource_id=resource_id, user_id=user_id
        )

        async def generate_stream():
            """Generate streaming response."""
            try:
                # Validate input
                if not request.message or not request.message.strip():
                    raise ValueError("Message cannot be empty")

                logger.info(
                    f"[CHAT_ENDPOINT] Starting stream for resource {resource_id}, thread {conversation.thread_id}"
                )

                chunk_count = 0
                async for chunk in chat_service.stream_message(
                    resource_id=resource_id,
                    message=request.message,
                    thread_id=conversation.thread_id,
                ):
                    chunk_count += 1

                    # Validate chunk structure
                    if not isinstance(chunk, dict):
                        logger.warning(
                            f"[CHAT_ENDPOINT] Invalid chunk format: {type(chunk)}"
                        )
                        continue

                    # Format as Server-Sent Events
                    stream_chunk = ChatStreamChunk(
                        content=chunk.get("content", ""),
                        context=chunk.get("context", ""),
                        conversation_id=conversation.id,
                        thread_id=chunk.get("thread_id", conversation.thread_id),
                        is_final=chunk.get("is_final", False),
                    )

                    yield f"data: {stream_chunk.model_dump_json()}\n\n"

                    # Log final chunk
                    if chunk.get("is_final", False):
                        logger.info(
                            f"[CHAT_ENDPOINT] Stream completed with {chunk_count} chunks"
                        )

                # Update conversation metadata after streaming completes
                conversation_service.update_conversation_metadata(
                    conversation_id=conversation.id,
                    user_id=user_id,  # Pass user_id instead of current_user object
                    message_count_increment=2,  # User message + AI response
                )

            except Exception as e:
                logger.error(f"[CHAT_ENDPOINT] Error in stream generation: {str(e)}")
                error_chunk = ChatStreamChunk(
                    content=f"Error: {str(e)}",
                    context="",
                    conversation_id=conversation.id,
                    thread_id=conversation.thread_id or "error",
                    is_final=True,
                )
                yield f"data: {error_chunk.model_dump_json()}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CHAT_ENDPOINT] Error setting up stream: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup streaming response",
        )


@router.get(
    "/resources/{resource_id}/chat/history",
    response_model=ConversationHistoryResponse,
    summary="Get conversation history for a resource",
    description="Get conversation history for the current user in this resource.",
)
async def get_resource_chat_history(
    resource_id: UUID,
    chat_service: ChatServiceDep,
    user_id: UUID = Depends(get_current_user_id),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationHistoryResponse:
    """
    Get conversation history for the current user in this resource.
    """
    try:
        # First, get conversation metadata and verify access
        conversation = conversation_service.get_or_create_conversation(
            resource_id=resource_id, user_id=user_id
        )
        
        # Then get the actual message history from the AI service
        message_history = await chat_service.get_conversation_history(
            resource_id=conversation.resource_id,
            thread_id=conversation.thread_id,
        )

        # Convert to ConversationMessage format
        messages = [
            ConversationMessage(
                role=msg.get("role", "unknown"),
                content=msg.get("content", ""),
                timestamp=msg.get("timestamp") or datetime.utcnow(),
                metadata=None,
            )
            for msg in message_history  # message_history is already a list
        ]

        return ConversationHistoryResponse(
            conversation_id=conversation.id,
            messages=messages,
            total_messages=len(messages),
        )

    except HTTPException:
        raise
 
    except Exception as e:
        logger.error(f"[CHAT_ENDPOINT] Error getting resource chat history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resource chat history",
        )


@router.get(
    "/resources/{resource_id}/chat/conversations",
    response_model=ConversationListResponse,
    summary="List resource conversations",
    description="Get list of conversations for the current user in this resource.",
)
async def list_conversations(
    resource_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationListResponse:
    """
    Get list of conversations for the current user in this resource.
    """
    try:
        conversations = conversation_service.get_user_conversations(
            user_id=user_id, resource_id=resource_id
        )

        conversation_summaries = [
            ConversationSummary.model_validate(conv) for conv in conversations
        ]

        return ConversationListResponse(
            conversations=conversation_summaries,
            total_count=len(conversation_summaries),
        )

    except Exception as e:
        logger.error(f"[CHAT_ENDPOINT] Error listing conversations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations",
        )


@router.get(
    "/conversations/{conversation_id}/history",
    response_model=ConversationHistoryResponse,
    summary="Get conversation history",
    description="Get the message history for a specific conversation.",
)
async def get_conversation_history(
    conversation_id: UUID,
    chat_service: ChatServiceDep,
    user_id: UUID = Depends(get_current_user_id),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationHistoryResponse:
    """
    Get the message history for a specific conversation.

    Note: This endpoint doesn't require resource guard since conversation
    access is verified by user ownership in the service layer.
    """
    try:
        # First, get conversation metadata and verify access
        conversation_metadata = conversation_service.get_conversation_history(
            conversation_id=conversation_id, user_id=user_id
        )

        # Then get the actual message history from the AI service
        message_history = await chat_service.get_conversation_history(
            resource_id=conversation_metadata["resource_id"],
            thread_id=conversation_metadata["thread_id"],
        )

        # Convert to ConversationMessage format
        messages = [
            ConversationMessage(
                role=msg.get("role", "unknown"),
                content=msg.get("content", ""),
                timestamp=msg.get("timestamp") or datetime.utcnow(),
                metadata=None,
            )
            for msg in message_history  # message_history is already a list
        ]

        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            messages=messages,
            total_messages=len(messages),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CHAT_ENDPOINT] Error getting conversation history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation history",
        )



@router.post(
    "/conversations/{conversation_id}/deactivate",
    response_model=ConversationDeactivateResponse,
    summary="Deactivate conversation",
    description="Deactivate a conversation (end the chat session).",
)
async def deactivate_conversation(
    conversation_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationDeactivateResponse:
    """
    Deactivate a conversation (end the chat session).

    Note: This endpoint doesn't require resource guard since conversation
    access is verified by user ownership in the service layer.
    """
    try:
        success = conversation_service.deactivate_conversation(
            conversation_id=conversation_id, user_id=user_id
        )

        if success:
            return ConversationDeactivateResponse(
                conversation_id=conversation_id,
                message="Conversation deactivated successfully",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to deactivate conversation",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CHAT_ENDPOINT] Error deactivating conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate conversation",
        )


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List all user conversations",
    description="Get list of all conversations for the current user across all resources.",
)
async def list_all_conversations(
    user_id: UUID = Depends(get_current_user_id),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationListResponse:
    """
    Get list of all conversations for the current user across all resources.
    """
    try:
        conversations = conversation_service.get_user_conversations(user_id=user_id)

        conversation_summaries = [
            ConversationSummary.model_validate(conv) for conv in conversations
        ]

        return ConversationListResponse(
            conversations=conversation_summaries,
            total_count=len(conversation_summaries),
        )

    except Exception as e:
        logger.error(f"[CHAT_ENDPOINT] Error listing all conversations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations",
        )


@router.get(
    "/resources/{resource_id}/chat/stats",
    response_model=ResourceChatStatsResponse,
    summary="Get resource chat statistics",
    description="Get chat statistics for a resource.",
)
async def get_resource_chat_stats(
    resource_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ResourceChatStatsResponse:
    """
    Get chat statistics for a resource.
    """
    try:
        conversations = conversation_service.get_user_conversations(
            user_id=user_id, resource_id=resource_id
        )

        total_conversations = len(conversations)
        active_conversations = len([conv for conv in conversations if conv.is_active])
        total_messages = sum(conv.message_count for conv in conversations)

        # Calculate average messages per conversation
        average_messages_per_conversation = (
            total_messages / total_conversations if total_conversations > 0 else 0.0
        )

        # Get last activity timestamp
        last_activity = max(
            (conv.last_message_at for conv in conversations), default=None
        )

        return ResourceChatStatsResponse(
            resource_id=resource_id,
            total_conversations=total_conversations,
            active_conversations=active_conversations,
            total_messages=total_messages,
            total_users=1,  # Currently only the requesting user
            average_messages_per_conversation=average_messages_per_conversation,
            last_activity=last_activity,
        )

    except Exception as e:
        logger.error(f"[CHAT_ENDPOINT] Error getting resource stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resource statistics",
        )


@router.get(
    "/pool/stats",
    summary="Get shared pool statistics",
    description="Get statistics about the shared connection pool used by checkpointers.",
)
async def get_pool_stats() -> Dict[str, Any]:
    """
    Get shared pool statistics for monitoring connection pool health.

    This endpoint provides insights into the shared connection pool
    used by LangGraph checkpointers.
    """
    try:
        from app.ai.services.shared_pool_service import get_pool_stats

        stats = get_pool_stats()

        return {"pool_stats": stats, "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        logger.error(f"[CHAT_ENDPOINT] Error getting pool stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pool statistics",
        )
