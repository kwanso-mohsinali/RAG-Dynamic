"""
Document endpoints for document processing.

This module provides FastAPI endpoints for resource-specific document processing functionality
with streaming support and conversation management.
"""

import logging
from uuid import UUID
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from apps.api.app.schemas.document import UploadFileRequest
from apps.api.app.core.dependencies import get_current_user_id
from celery_app.tasks.document_processing_tasks import process_document_task

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=dict)
async def upload_file(
    request: UploadFileRequest,
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    """
    Upload a file and create a document record.
    """
    try:

        resource_id = request.resource_id
        file_key = request.file_key

        logger.info(f"[DOCUMENT_ENDPOINT] Resource ID: {resource_id}")
        logger.info(f"[DOCUMENT_ENDPOINT] User ID: {user_id}")
        logger.info(f"[DOCUMENT_ENDPOINT] File Key: {file_key}")

        # Auto-trigger document processing for resource documents
        if resource_id:
            if file_key:
                # Queue Celery task instead of background task
                process_document_task.delay(
                    str(resource_id), str(user_id), str(file_key)
                )
                logger.info(f"[DOCUMENT_ENDPOINT] Document processing queued")
                return {"message": "Document processing  queued "}
            else:
                logger.error(f"[DOCUMENT_ENDPOINT] No File Key found")
                return {"message": "No File Key found"}
        else:
            logger.error(f"[DOCUMENT_ENDPOINT] Resource ID is missing")
            return {"message": "Resource ID is missing"}
    except Exception as e:
        logger.error(f"[DOCUMENT_ENDPOINT] Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file",
        )
