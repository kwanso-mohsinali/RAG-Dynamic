"""
Chat schemas for RAG-based conversational AI.

Pydantic models for chat request/response validation.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """Request schema for sending a chat message."""

    message: str = Field(..., description="The user's message")
    conversation_id: Optional[UUID] = Field(
        None, description="Existing conversation ID (optional)")


class ChatMessageResponse(BaseModel):
    """Response schema for chat message."""

    answer: str = Field(..., description="AI assistant's response")
    conversation_id: UUID = Field(..., description="Conversation ID")
    thread_id: str = Field(..., description="LangGraph thread ID")
    message_count: int = Field(...,
                               description="Total messages in conversation")


class ChatStreamChunk(BaseModel):
    """Schema for streaming chat response chunks."""

    content: str = Field(..., description="Chunk of the response")
    conversation_id: UUID = Field(..., description="Conversation ID")
    thread_id: str = Field(..., description="LangGraph thread ID")
    is_final: bool = Field(..., description="Whether this is the final chunk")


class ConversationSummary(BaseModel):
    """Summary information about a conversation."""

    id: UUID = Field(..., description="Conversation ID")
    resource_id: UUID = Field(..., description="Resource ID")
    user_id: UUID = Field(..., description="User ID")
    title: str = Field(..., description="Conversation title")
    message_count: int = Field(..., description="Number of messages")
    last_message_at: datetime = Field(...,
                                      description="Timestamp of last message")
    is_active: bool = Field(..., description="Whether conversation is active")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """Response schema for listing conversations."""

    conversations: List[ConversationSummary] = Field(
        ..., description="List of conversations")
    total_count: int = Field(..., description="Total number of conversations")


class ConversationMessage(BaseModel):
    """Schema for individual conversation messages."""

    role: str = Field(..., description="Message role (human/ai)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata")


class ConversationHistoryResponse(BaseModel):
    """Response schema for conversation history."""

    conversation_id: UUID = Field(..., description="Conversation ID")
    messages: List[ConversationMessage] = Field(
        ..., description="Conversation messages")
    total_messages: int = Field(..., description="Total number of messages")


class ConversationCreateResponse(BaseModel):
    """Response schema for creating a new conversation."""

    conversation_id: UUID = Field(..., description="New conversation ID")
    thread_id: str = Field(..., description="LangGraph thread ID")
    message: str = Field(..., description="Success message")


class ConversationDeactivateResponse(BaseModel):
    """Response schema for deactivating a conversation."""

    conversation_id: UUID = Field(...,
                                  description="Deactivated conversation ID")
    message: str = Field(..., description="Success message")


class ResourceChatStatsResponse(BaseModel):
    """Response schema for resource chat statistics."""

    resource_id: UUID = Field(..., description="Resource ID")
    total_conversations: int = Field(..., description="Total conversations")
    active_conversations: int = Field(..., description="Active conversations")
    total_messages: int = Field(..., description="Total messages")
    total_users: int = Field(..., description="Total users who have chatted")
    average_messages_per_conversation: float = Field(
        ..., description="Average messages per conversation")
    last_activity: Optional[datetime] = Field(
        None, description="Last chat activity")
