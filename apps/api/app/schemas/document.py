from pydantic import BaseModel, Field
from typing import Optional


class BaseFileResponse(BaseModel):
    """Base response schema with common fields."""

    message: str = Field(..., description="Response message describing the result")
    status: str = Field(..., description="Status of the operation")


class BaseFileRequest(BaseModel):
    """Base request schema with common fields."""

    resource_id: str = Field(
        ..., description="ID of the resource to associate the file with"
    )
    file_key: str = Field(..., description="S3 file key for the uploaded file")


class IngestFileRequest(BaseFileRequest):
    """Request schema for ingesting a file."""

    pass


class IngestFileResponse(BaseFileResponse):
    """Response schema for file ingestion endpoint."""

    resource_id: Optional[str] = Field(
        None, description="Resource ID (included on success)"
    )
    task_id: Optional[str] = Field(
        None, description="Celery task ID for document processing"
    )


class RemoveFileRequest(BaseFileRequest):
    """Request schema for removing a file."""

    pass


class RemoveFileResponse(BaseFileResponse):
    """Response schema for removing a file."""

    pass
