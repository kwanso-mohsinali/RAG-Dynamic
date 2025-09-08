"""
Service factory for creating service instances with proper dependencies.

This module provides factory functions to create service instances
with proper database sessions and dependency injection for various contexts
including Celery tasks, API endpoints, and background jobs.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.ai.services.document_processing_service import DocumentProcessingService

# Ensure environment variables are loaded
from dotenv import load_dotenv
load_dotenv()


def create_database_session():
    """
    Create a fresh database session.

    Returns:
        SQLAlchemy session
    """
    # Get DATABASE_URL from environment or settings
    database_url = os.getenv('DATABASE_URL') or getattr(
        settings, 'DATABASE_URL', None)

    if not database_url:
        raise ValueError(
            "DATABASE_URL not found. Please ensure DATABASE_URL environment variable is set. "
            "You can set it in your .env file or export it in your shell."
        )

    # Apply the same URL conversion logic as in session.py
    # Convert postgres:// or postgresql:// to postgresql+psycopg:// for psycopg3 compatibility
    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://", "postgresql+psycopg://", 1)

    # Create engine with proper configuration
    engine_kwargs = {}
    if "postgresql" in database_url:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 300
        # Ensure proper SSL handling for Heroku
        if os.getenv("ENVIRONMENT") == "development":
            engine_kwargs["connect_args"] = {"sslmode": "disable"}
        else:
            engine_kwargs["connect_args"] = {"sslmode": "require"}

    engine = create_engine(database_url, **engine_kwargs)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def create_document_processing_service() -> DocumentProcessingService:
    """
    Create DocumentProcessingService with all dependencies for Celery tasks.
    """
    return DocumentProcessingService()
