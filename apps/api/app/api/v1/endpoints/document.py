"""
Document endpoints for document processing.

This module provides FastAPI endpoints for resource-specific document processing functionality
with streaming support and conversation management.
"""

import logging
from typing import Any
from uuid import UUID
from fastapi import APIRouter
from pydantic import BaseModel
from celery_app.tasks.document_processing_tasks import process_document_task

logger = logging.getLogger(__name__)

router = APIRouter()

class UploadFileRequest(BaseModel):
    resource_id: UUID
    file_key: str
    user_id: UUID

@router.post("/upload", response_model=Any)
async def upload_file(
    request: UploadFileRequest,
):
    """
    Upload a file and create a document record.
    """

    print(f"[DOCUMENT_ENDPOINT] Resource ID: {request.resource_id}")
    print(f"[DOCUMENT_ENDPOINT] User ID: {request.user_id}")
    print(f"[DOCUMENT_ENDPOINT] File Key: {request.file_key}")

    # Auto-trigger document processing for resource documents
    if request.resource_id and request.user_id:
        if request.file_key:
            # Queue Celery task instead of background task
            process_document_task.delay(str(request.resource_id), str(request.user_id), str(request.file_key))
            return {"message": "Document processing queued"}
        else:
            print(f"[DOCUMENT_ENDPOINT] No File Key found")
            return {"message": "No File Key found"}
    else:
        print(f"[DOCUMENT_ENDPOINT] Resource ID or User ID  is missing")
        return {"message": "Resource ID or User ID is missing"}