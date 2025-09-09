"""
Document processing service for managing document processing workflows.

This service handles workflow execution, status tracking, and error management
while integrating with existing business services.
"""

import logging
from typing import Dict, Any
from uuid import UUID
import asyncio

from apps.api.app.ai.schemas.workflow_states import DocumentProcessingState

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """
    Service for managing AI document processing workflows.

    Handles document processing workflow execution, status tracking, and integration with
    existing business services while maintaining clean separation of concerns.
    """

    async def process_document_async(
        self, resource_id: UUID, user_id: UUID, file_key: str
    ) -> Dict[str, Any]:
        """
        Process a document asynchronously using the AI workflow.

        Args:
            resource_id: ID of the resource to store the documents
            user_id: ID of the user requesting processing
            file_key: Key of the file to process

        Returns:
            Processing result with status and metadata

        Raises:
            ValueError: If file path or resource id not found
            RuntimeError: If workflow execution fails
        """
        try:
            if not user_id:
                logger.error(f"[DOCUMENT_PROCESSING_SERVICE] User id not found")
                raise ValueError(f"User id not found")
            
            logger.info(
                f"[DOCUMENT_PROCESSING_SERVICE] Fetching file {file_key}")
            if not file_key:
                logger.error(
                    f"[DOCUMENT_PROCESSING_SERVICE] File key not found or not authorized")
                raise ValueError(
                    f"File key not found or not authorized")
                
            logger.info(
                f"[DOCUMENT_PROCESSING_SERVICE] Starting document processing for file {file_key}"
            )

            # Create the LangGraph workflow (lazy import to avoid circular dependency)
            logger.info(
                f"[DOCUMENT_PROCESSING_SERVICE] Creating document processing workflow"
            )
            from app.ai.workflows.document_processing_workflow import (
                create_document_processing_workflow,
                validate_document_processing_input,
            )

            workflow = create_document_processing_workflow()

            # Initialize state with all required fields
            logger.info(
                f"[DOCUMENT_PROCESSING_SERVICE] Initializing workflow state for file {file_key}"
            )

            # Prepare workflow input
            initial_state = DocumentProcessingState(
                resource_id=resource_id,
                file_key=file_key,
                status="pending",
            )

            # Convert to dict and add only data (no service instances)
            state_dict = initial_state.model_dump()

            # Debug: Log what we're preparing
            logger.info(f"[DOCUMENT_PROCESSING_SERVICE] Input data: {state_dict}")

            # Validate input
            validated_input = validate_document_processing_input(state_dict)

            # Debug: Log what we're passing to the workflow
            logger.info(
                f"[DOCUMENT_PROCESSING_SERVICE] Validated input: {validated_input}"
            )

            # Run the LangGraph workflow directly
            logger.info(
                f"[DOCUMENT_PROCESSING_SERVICE] Invoking LangGraph workflow for file {file_key}"
            )
            final_state = workflow.invoke(validated_input)
            logger.info(
                f"[DOCUMENT_PROCESSING_SERVICE] Workflow completed with status: {final_state.get('status')}"
            )
            
            # Update final status based on result
            if final_state.get("status") == "embeddings_stored":
                # Successful completion - embeddings were stored
                return {
                    "success": True,
                    "resource_id": resource_id,
                    "status": "completed",
                    "message": "Document processing completed successfully",
                    "file_type": final_state.get("file_type"),
                }
            else:
                # Processing failed
                return {
                    "success": False,
                    "resource_id": resource_id,
                    "status": "failed",
                    "message": final_state.get("error_message", "Document processing failed"),
                    "file_type": final_state.get("file_type"),
                }

        except Exception as e:
            raise RuntimeError(f"Document processing failed: {str(e)}")

    def process_document_sync(
        self, resource_id: UUID, user_id: UUID, file_key: str
    ) -> Dict[str, Any]:
        """
        Process a document synchronously (blocking).

        Args:
            resource_id: ID of the resource to store the documents
            user_id: ID of the user requesting processing
            file_key: Key of the file to process

        Returns:
            Processing result with status and metadata
        """
        return asyncio.run(self.process_document_async(resource_id, user_id, file_key))
