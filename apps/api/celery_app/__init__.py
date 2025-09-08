"""
Celery application package for distributed task processing.

This package contains the Celery application configuration and task definitions
for handling document processing and other background operations.
"""

from .celery import celery_app

__all__ = ["celery_app"]
