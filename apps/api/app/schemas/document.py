from pydantic import BaseModel, Field
from typing import Optional

class IngestFileRequest(BaseModel):
    """Request schema for ingesting a file."""

    resource_id: str = Field(
        ..., description="ID of the resource to associate the file with"
    )
    file_key: str = Field(..., description="S3 file key for the uploaded file")
    secret_key: str = Field(..., description="Secret key for authentication")


class IngestFileResponse(BaseModel):
    """Response schema for file ingestion endpoint."""

    message: str = Field(..., description="Response message describing the result")
    status: str = Field(..., description="Status of the file ingestion operation")
    resource_id: Optional[str] = Field(
        None, description="Resource ID (included on success)"
    )
    task_id: Optional[str] = Field(
        None, description="Celery task ID for document processing"
    )
