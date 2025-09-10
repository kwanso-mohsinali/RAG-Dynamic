"""
Document ingestion endpoints for AI-powered RAG processing.

This module provides FastAPI endpoints for asynchronous document ingestion and processing
through the AI pipeline. Documents are processed via Celery tasks for scalability,
with support for multiple file types, OCR extraction, embedding generation, and
vector storage for RAG-based conversational AI.
"""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from apps.api.app.schemas.document import (
    IngestFileRequest,
    IngestFileResponse,
)
from apps.api.app.core.dependencies import get_current_user_id
from celery_app.tasks.document_processing_tasks import process_document_task

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/ingest",
    response_model=IngestFileResponse,
    status_code=status.HTTP_200_OK,
    summary="Enqueue file for document processing using celery task",
    description="Process files through document processing workflow.",
)
async def ingest_file(
    request: IngestFileRequest,
    user_id: UUID = Depends(get_current_user_id),
) -> IngestFileResponse:
    """
    Queue file for asynchronous document processing through document processing workflow.
    Args: request (IngestFileRequest), user_id (UUID)
    Returns: IngestFileResponse with task_id for tracking processing status
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
                # Queue Celery task and capture task ID
                task = process_document_task.delay(
                    str(resource_id), str(user_id), str(file_key)
                )
                logger.info(
                    f"[DOCUMENT_ENDPOINT] Document processing successfully queued with task ID: {task.id}"
                )

                return IngestFileResponse(
                    message="Document processing successfully queued",
                    status="success",
                    resource_id=str(resource_id),
                    task_id=task.id,
                )
            else:
                logger.error(f"[DOCUMENT_ENDPOINT] No File Key found")
                return IngestFileResponse(message="No File Key found", status="error")
        else:
            logger.error(f"[DOCUMENT_ENDPOINT] Resource ID is missing")
            return IngestFileResponse(message="Resource ID is missing", status="error")
    except Exception as e:
        logger.error(f"[DOCUMENT_ENDPOINT] Error ingesting file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest file",
        )
