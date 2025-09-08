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
from celery_app.tasks.document_processing_tasks import process_document_task

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=Any)
async def upload_file(
    resource_id: UUID,
):
    """
    Upload a file and create a document record.
    """

    print(f"[DOCUMENT_ENDPOINT] Resource ID: {resource_id}")

    # Auto-trigger document processing for resource documents
    if resource_id:
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
                f"[DOCUMENT_ENDPOINT] Auto-triggering document processing for resource {resource_id} and file {file_path}"
            )

            # Queue Celery task instead of background task
            process_document_task.delay(str(resource_id), str(file_path))
        else:
            print(f"[DOCUMENT_ENDPOINT] No PDF files found in {knowledge_base_folder}")
            return {"message": "No PDF files found in knowledge base folder"}

    return {"message": "Document processing queued"}
