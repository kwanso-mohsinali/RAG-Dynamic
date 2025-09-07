"""
Conversation model for managing RAG chat sessions.

This model stores conversation metadata only. LangGraph's PostgreSQL checkpointer
handles the actual message persistence automatically using thread_id.
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

from app.models.base import BaseModel


class Conversation(BaseModel):
    """
    Conversation model for RAG chat sessions.

    Stores only business metadata - LangGraph handles message persistence
    via PostgreSQL checkpointer using thread_id as the key.
    """

    __tablename__ = "conversations"

    # Core identification
    resource_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # LangGraph integration
    thread_id = Column(
        String(255), nullable=False, unique=True, index=True
    )  # LangGraph thread identifier

    # Conversation metadata
    # Auto-generated from first message
    title = Column(String(255), nullable=False)

    # Statistics (for business logic)
    message_count = Column(Integer, default=0)  # Track conversation length
    last_message_at = Column(DateTime, default=datetime.utcnow)  # For sorting/cleanup

    # Status management
    is_active = Column(Boolean, default=True)  # For archiving conversations

    def __repr__(self):
        return f"<Conversation(id={self.id}, thread_id='{self.thread_id}', resource_id={self.resource_id})>"

    @classmethod
    def generate_thread_id(cls, resource_id: str, user_id: str) -> str:
        """
        Generate unique thread ID for LangGraph.

        Format: resource_{resource_id}_user_{user_id}_{timestamp}

        This ensures thread isolation per resource-user combination.
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"resource_{resource_id}_user_{user_id}_{timestamp}"
