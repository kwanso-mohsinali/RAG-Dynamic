from typing import Annotated
from uuid import UUID
from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.services.conversation_service import ConversationService
from apps.api.app.core.config import settings


def get_secret_key(request: Request) -> str:
    """Get the secret key from the Authorization header."""

    # Extract secret key from Authorization header
    authorization = request.headers.get("authorization")
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
        )

    # Check if it's a Bearer token
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be a Bearer token",
        )

    # Extract the secret key from Bearer token
    secret_key = authorization.split(" ")[1]

    # Validate the secret key
    if not secret_key or secret_key != settings.SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or Missing Secret Key",
        )

    return secret_key


def get_current_user_id(
    request: Request, secret_key: str = Depends(get_secret_key)
) -> UUID:
    """
    Extract current user ID from request body and validate secret key from Authorization header.

    This dependency reads the request body and extracts the user_id field,
    while validating the secret key from the Authorization Bearer token.

    Args:
        request: FastAPI Request object

    Returns:
        UUID: The current user's ID

    Raises:
        HTTPException: If user_id is missing or invalid
    """
    # Extract user_id from header
    user_id = request.headers.get("user")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User Not Found",
        )

    # Convert to UUID if it's a string
    if isinstance(user_id, str):
        try:
            user_id = UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID must be a valid UUID",
            )
    elif not isinstance(user_id, UUID):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid User ID",
        )

    return user_id


def get_conversation_service(
    db: Annotated[Session, Depends(get_db)],
) -> ConversationService:
    return ConversationService(db)
