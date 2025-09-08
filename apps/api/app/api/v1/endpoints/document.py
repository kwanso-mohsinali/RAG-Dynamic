"""
Document endpoints for document processing.

This module provides FastAPI endpoints for resource-specific document processing functionality
with streaming support and conversation management.
"""

import logging
import glob
import os
from typing import Any
from uuid import UUID
from fastapi import APIRouter
from pydantic import BaseModel
from celery_app.tasks.document_processing_tasks import process_document_task

logger = logging.getLogger(__name__)

router = APIRouter()

class UploadFileRequest(BaseModel):
    resource_id: UUID
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

    # Auto-trigger document processing for resource documents
    if request.resource_id and request.user_id:
        # Get the knowledge base folder path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        knowledge_base_folder = os.path.join(current_dir, "knowledge_base")

        # Use glob to find PDF files in the knowledge base folder
        pdf_pattern = os.path.join(knowledge_base_folder, "*.pdf")
        pdf_files = glob.glob(pdf_pattern)

        if pdf_files:
            # Use the first PDF file found
            file_path = pdf_files[0]
            print(f"[DOCUMENT_ENDPOINT] Found PDF file: {file_path}")

            print(
                f"[DOCUMENT_ENDPOINT] Auto-triggering document processing for resource {request.resource_id} and file {file_path}"
            )

            # Queue Celery task instead of background task
            process_document_task.delay(str(request.resource_id), str(request.user_id), str(file_path))
        else:
            print(f"[DOCUMENT_ENDPOINT] No PDF files found in {knowledge_base_folder}")
            return {"message": "No PDF files found in knowledge base folder"}

        return {"message": "Document processing queued"}
    
    else:
        print(f"[DOCUMENT_ENDPOINT] Resource ID or User ID is missing")
        return {"message": "Resource ID or User ID is missing"}