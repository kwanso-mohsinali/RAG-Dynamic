from typing import Annotated
from uuid import UUID
from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.services.conversation_service import ConversationService


async def get_current_user_id(request: Request) -> UUID:
    """
    Extract current user ID from request body.

    This dependency reads the request body and extracts the user_id field.
    Can be used with any endpoint that includes user_id in the request body.

    Args:
        request: FastAPI Request object

    Returns:
        UUID: The current user's ID

    Raises:
        HTTPException: If user_id is missing or invalid
    """
    try:
        # Get the request body as JSON
        body = await request.json()

        # Extract user_id from body
        user_id = body.get("user_id")

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

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse request body: {str(e)}",
        )


def get_conversation_service(
    db: Annotated[Session, Depends(get_db)],
) -> ConversationService:
    return ConversationService(db)
