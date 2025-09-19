from typing import Annotated
from fastapi import Depends
from app.ai.services.chat_service import ChatService
from app.ai.services.vector_service import VectorService


def get_vector_service() -> VectorService:
    """Get VectorService instance."""
    return VectorService()

def get_chat_service(vector_service: VectorService = Depends(get_vector_service)) -> ChatService:
    """Get ChatService instance with dependencies."""
    return ChatService(vector_service)


# Type aliases for clean injection
VectorServiceDep = Annotated[VectorService, Depends(get_vector_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
