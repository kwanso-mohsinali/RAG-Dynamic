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
from apps.api.app.ai.dependencies import VectorServiceDep
from apps.api.app.schemas.document import (
    IngestFileRequest,
    IngestFileResponse,
    RemoveFileRequest,
    RemoveFileResponse,
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
    except Exception as e:
        logger.error(f"[DOCUMENT_ENDPOINT] Error ingesting file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest file",
        )


# @router.delete(
#     "/remove",
#     response_model=RemoveFileResponse,
#     status_code=status.HTTP_200_OK,
#     summary="Remove file from vector database",
#     description="Remove file from vector database.",
# )
# async def remove_file(
#     request: RemoveFileRequest,
#     vector_service: VectorServiceDep,
#     user_id: UUID = Depends(get_current_user_id),
# ) -> RemoveFileResponse:
#     """
#     Remove file from vector database.

#     This endpoint removes a file from the vector database.

#     Args:
#         request (RemoveFileRequest): Request schema for removing a file
#         vector_service (VectorServiceDep): Vector service dependency
#         user_id (UUID, optional): User ID dependency

#     Returns:
#         RemoveFileResponse: Response schema for removing a file
#     """
#     try:
#         resource_id = request.resource_id
#         file_key = request.file_key

#         logger.info(f"[DOCUMENT_ENDPOINT] Resource ID: {resource_id}")
#         logger.info(f"[DOCUMENT_ENDPOINT] User ID: {user_id}")
#         logger.info(f"[DOCUMENT_ENDPOINT] File Key: {file_key}")

#         # Remove file from vector database
#         vector_service.remove_documents(str(resource_id), str(file_key))
#         logger.info(
#             f"[DOCUMENT_ENDPOINT] Successfully removed file from resource: {resource_id}"
#         )

#         return RemoveFileResponse(message="File removed successfully", status="success")
#     except Exception as e:
#         logger.error(f"[DOCUMENT_ENDPOINT] Error removing file: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to remove file",
#         )
