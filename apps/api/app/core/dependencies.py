from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.dependencies import get_db
from app.services.conversation_service import ConversationService


def get_conversation_service(
    db: Annotated[Session, Depends(get_db)],
) -> ConversationService:
    return ConversationService(db)
