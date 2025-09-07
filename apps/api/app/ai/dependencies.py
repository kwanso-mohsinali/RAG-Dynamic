from typing import Annotated
from fastapi import Depends
from app.ai.services.chat_service import ChatService
from app.ai.services.vector_service import VectorService


def get_chat_service() -> ChatService:
    """Get ChatService instance with dependencies."""
    vector_service = VectorService()
    return ChatService(vector_service)


# Type aliases for clean injection
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
