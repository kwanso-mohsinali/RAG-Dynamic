"""
Conversation service for managing conversation CRUD operations.

This service handles all business logic related to conversations,
including creation, updates, and authorization checks.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.conversation import Conversation

logger = logging.getLogger(__name__)

class ConversationService:
    """
    Service for managing conversation business logic and CRUD operations.

    Handles all database operations and business rules for conversations
    while delegating AI processing to the AI module.
    """

    def __init__(self, db: Session):
        """
        Initialize conversation service with dependencies.

        Args:
            db: Database session
        """
        self.db = db

    def get_or_create_conversation(
        self,
        resource_id: UUID,
        user_id: UUID ,
        title: Optional[str] = None,
        resource_details: Optional[str] = None
    ) -> Conversation:
        """
        Get existing conversation or create a new one for the user and resource.

        Args:
            resource_id: Resource UUID
            user_id: User UUID
            title: Optional conversation title
            resource_details: Optional resource details

        Returns:
            Conversation object with thread_id

        Raises:
            HTTPException: If resource access is denied or operation fails
        """
        try:
            # Verify resource access through resource service
            if not resource_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Resource not found or access denied"
                )

            # Look for active conversation for this user/resource
            existing_conversation = (
                self.db.query(Conversation)
                .filter(
                    Conversation.resource_id == resource_id,
                    Conversation.user_id == user_id,
                    Conversation.is_active == True
                )
                .first()
            )

            if existing_conversation:
                logger.info(
                    f"[CONVERSATION_SERVICE] Using existing conversation {existing_conversation.id}")
                return existing_conversation

            # Create new conversation with unique thread ID
            conversation = Conversation(
                resource_id=resource_id,
                user_id=user_id,
                thread_id=str(uuid4()),  # Unique thread ID for LangGraph
                title=title or f"Chat - {resource_id}",
                message_count=0,
                last_message_at=datetime.utcnow(),
                is_active=True,
                resource_details=resource_details
            )

            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)

            logger.info(
                f"[CONVERSATION_SERVICE] Created new conversation {conversation.id}")

            return conversation

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"[CONVERSATION_SERVICE] Error creating conversation: {str(e)}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create conversation"
            )

    def get_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID
    ) -> Optional[Conversation]:
        """
        Get a conversation by ID with user authorization.

        Args:
            conversation_id: Conversation UUID
            current_user: Current user making the request

        Returns:
            Conversation object if found and accessible, None otherwise

        Raises:
            HTTPException: If user doesn't have permission to access the conversation
        """
        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )

        if not conversation:
            return None

        # Check if user owns the conversation
        if conversation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this conversation"
            )

        return conversation

    def update_conversation_metadata(
        self,
        conversation_id: UUID,
        user_id: UUID,  # Changed from current_user: User to user_id: UUID
        message_count_increment: int = 2,  # User message + AI response
        update_last_message: bool = True
    ) -> Conversation:
        """
        Update conversation metadata after message exchange.

        Args:
            conversation_id: Conversation UUID
            user_id: User ID making the request (UUID instead of User object to avoid session issues)
            message_count_increment: Number to increment message count by
            update_last_message: Whether to update last_message_at timestamp

        Returns:
            Updated conversation object

        Raises:
            HTTPException: If conversation not found or access denied
        """
        # Get conversation directly without passing user object
        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Check if user owns the conversation using user_id
        if conversation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this conversation"
            )

        # Update metadata
        conversation.message_count += message_count_increment
        if update_last_message:
            conversation.last_message_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(conversation)

        logger.info(
            f"[CONVERSATION_SERVICE] Updated conversation {conversation_id} metadata")
        return conversation

    def get_user_conversations(
        self,
        user_id: UUID,
        resource_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Conversation]:
        """
        Get conversations for a user, optionally filtered by resource.

        Args:
            user_id: User ID making the request
            resource_id: Optional resource filter
            skip: Number of conversations to skip (pagination)
            limit: Maximum number of conversations to return

        Returns:
            List of conversation objects
        """
        query = (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
        )

        # Filter by resource if provided
        if resource_id:
            query = query.filter(Conversation.resource_id == resource_id)

        conversations = (
            query.order_by(Conversation.last_message_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        logger.info(
            f"[CONVERSATION_SERVICE] Retrieved {len(conversations)} conversations for user {user_id}")
        return conversations

    def deactivate_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Deactivate a conversation (end the chat session).

        Args:
            conversation_id: Conversation UUID
            current_user: Current user making the request

        Returns:
            True if conversation was deactivated, False if not found

        Raises:
            HTTPException: If user doesn't have permission to deactivate the conversation
        """
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            return False

        conversation.is_active = False
        self.db.commit()

        logger.info(
            f"[CONVERSATION_SERVICE] Deactivated conversation {conversation_id}")
        return True

    def get_conversation_history(
        self,
        conversation_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get conversation history and metadata.

        Args:
            conversation_id: Conversation UUID
            current_user: Current user making the request

        Returns:
            Dictionary with conversation metadata

        Raises:
            HTTPException: If conversation not found or access denied
        """
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        return {
            'conversation_id': conversation.id,
            'thread_id': conversation.thread_id,
            'resource_id': conversation.resource_id,
            'title': conversation.title,
            'message_count': conversation.message_count,
            'last_message_at': conversation.last_message_at,
            'is_active': conversation.is_active,
            'created_at': conversation.created_at
        }
