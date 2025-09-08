"""
Celery tasks package for distributed task processing.

This package contains all Celery task definitions for background processing.
"""

from .document_processing_tasks import process_document_task

__all__ = ["process_document_task"]
