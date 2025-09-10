"""
Celery tasks for document processing operations.

This module contains Celery task definitions for handling document processing
with proper database session management and error handling.
"""

import time
import logging
import gc
import psutil
import os
from uuid import UUID
from celery_app.celery import celery_app
from app.factories.service_factory import create_document_processing_service


logger = logging.getLogger(__name__)


def log_memory_usage(stage: str):
    """Log current memory usage for monitoring."""
    try:
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        logger.info(f"[MEMORY] {stage}: {memory_mb:.1f}MB")
    except Exception as e:
        logger.warning(f"[MEMORY] Could not log memory usage: {str(e)}")


def force_garbage_collection():
    """Force garbage collection and log memory before/after."""
    try:
        before_mb = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        logger.info(f"[GC] Before GC: {before_mb:.1f}MB")

        gc.collect()

        after_mb = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        logger.info(
            f"[GC] After GC: {after_mb:.1f}MB (freed: {before_mb - after_mb:.1f}MB)"
        )
    except Exception as e:
        logger.warning(f"[GC] Could not perform garbage collection: {str(e)}")


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    name="process_document_task",
    retry_kwargs={"max_retries": 3, "countdown": 60},
    retry_backoff=True,
    soft_time_limit=600,  # 10 minutes soft limit
    time_limit=900,  # 15 minutes hard limit
    max_memory_per_child=300000,  # 300MB per child process
    # Removed rate_limit to allow unlimited queuing
)
def process_document_task(self, resource_id: str, user_id: str, file_key: str):
    """
    Celery task for processing documents using the AI WorkflowService.

    This task replaces the FastAPI background task and provides:
    - Proper database session management
    - Task progress tracking with structured updates
    - Automatic retry logic with exponential backoff
    - Rate limiting for resource control
    - Concurrency control via Celery worker settings

    Args:
        resource_id: Resource UUID as string
        user_id: User UUID as string
        file_path: File path as string

    Returns:
        Dictionary with processing results
    """
    start_time = time.time()
    task_id = self.request.id

    logger.info(f"[CELERY_TASK] Starting document processing task {task_id}")
    logger.info(f"[CELERY_TASK] Processing file {file_key} for resource {resource_id}")

    # Log initial memory usage
    log_memory_usage("Task Start")

    try:
        # Update task status with structured progress
        self.update_state(
            state="PROGRESS",
            meta={
                "file_key": file_key,
                "progress": 0,
                "status": "initializing",
                "current_step": "initializing_document_processing_service",
                "task_id": task_id,
            },
        )

  
        # Create fresh service dependencies
        document_processing_service = create_document_processing_service()
        log_memory_usage("Services Created")

        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={
                "file_key": file_key,
                "progress": 10,
                "status": "services_created",
                "current_step": "document_processing_service_initialized",
                "task_id": task_id,
            },
        )

        # Process document using workflow service
        logger.info(f"[CELERY_TASK] Invoking workflow service for file {file_key}")
        log_memory_usage("Before Workflow")

        result = document_processing_service.process_document_sync(
            resource_id=UUID(resource_id), user_id=UUID(user_id), file_key=str(file_key)
        )

        log_memory_usage("After Workflow")
        force_garbage_collection()

        duration = time.time() - start_time
        logger.info(
            f"[CELERY_TASK] Document processing completed in {duration:.2f}s for file {file_key}"
        )

        # Return success result with structured data
        return {
            "file_key": file_key,
            "resource_id": resource_id,
            "status": "completed",
            "result": result,
            "duration": duration,
            "task_id": task_id,
            "completed_at": time.time(),
        }

    except Exception as exc:
        logger.error(f"[CELERY_TASK] Document processing failed: {str(exc)}")
        
        duration = time.time() - start_time
        error_msg = f"Document processing failed after {duration:.2f}s: {str(exc)}"
        logger.error(f"[CELERY_TASK] {error_msg}")

        # Force garbage collection on error
        force_garbage_collection()

        # Create a simple, serializable error response
        error_info = {
            "file_key": file_key,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "duration": duration,
            "task_id": task_id,
            "failed_at": time.time(),
            "status": "failed",
        }

        # Update task state to failure with detailed error info
        try:
            self.update_state(state="FAILURE", meta=error_info)
        except Exception as update_exc:
            logger.warning(
                f"[CELERY_TASK] Could not update task state: {str(update_exc)}"
            )

        # Instead of re-raising, return the error info to avoid serialization issues
        # This prevents the KeyError: 'exc_type' issue in Celery backend
        return error_info


@celery_app.task(bind=True, name="health_check_task")
def health_check_task(self):
    """
    Simple health check task for monitoring Celery worker status.

    Returns:
        Dictionary with health status
    """
    return {"status": "healthy", "worker_id": self.request.id, "timestamp": time.time()}
