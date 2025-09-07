from typing import Annotated
from fastapi import Depends
from app.ai.services.chat_service import ChatService

def get_chat_service(
) -> ChatService:
    """Get ChatService instance with dependencies."""
    return ChatService()


# Type aliases for clean injection
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]