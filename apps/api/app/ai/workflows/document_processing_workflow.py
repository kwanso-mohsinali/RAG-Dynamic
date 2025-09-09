"""
Document processing workflow definition using function-based approach.

This follows the established pattern where workflows are pure functions
that define the graph structure and return compiled applications.
"""

import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from app.ai.nodes.pdf_processor_node import pdf_processor_node
from app.ai.nodes.docx_processor_node import docx_processor_node
from app.ai.nodes.image_processor_node import image_processor_node
from app.ai.nodes.chunker_node import chunker_node
from app.ai.nodes.embedder_node import embedder_node
from app.ai.nodes.file_fetcher_node import file_fetcher_node

logger = logging.getLogger(__name__)


def create_document_processing_workflow() -> StateGraph:
    """
    Create document processing workflow for document processing functionality.
    """

    logger.info(f"[DOCUMENT_PROCESSING_WORKFLOW] Creating document processing workflow")

    # Create the state graph with dict for flexibility while maintaining validation
    # We'll validate state using DocumentProcessingState schema in the service layer
    workflow = StateGraph(dict)

    # Add nodes
    workflow.add_node("file_fetcher", file_fetcher_node)
    workflow.add_node("document_router", lambda state: state)
    workflow.add_node("pdf_processor", pdf_processor_node)
    workflow.add_node("docx_processor", docx_processor_node)
    workflow.add_node("image_processor", image_processor_node)
    workflow.add_node("chunker", chunker_node)
    workflow.add_node("embedder", embedder_node)
    workflow.add_node("error_handler", error_handler_node)

    # Set entry point
    workflow.set_entry_point("file_fetcher")

    # Add conditional edge from file_fetcher to check if download was successful
    workflow.add_conditional_edges(
        "file_fetcher",
        check_file_fetcher_status,
        {"document_router": "document_router", "error_handler": "error_handler"},
    )

    # Conditional edge from document_router to appropriate processor
    workflow.add_conditional_edges(
        "document_router",
        route_after_analysis,
        {
            "pdf_processor": "pdf_processor",
            "docx_processor": "docx_processor",
            "image_processor": "image_processor",
            "error_handler": "error_handler",
        },
    )

    # All processors go to chunker
    workflow.add_edge("pdf_processor", "chunker")
    workflow.add_edge("docx_processor", "chunker")
    workflow.add_edge("image_processor", "chunker")
    
    # Chunker goes to embedder
    workflow.add_edge("chunker", "embedder")
    
    # Final Steps
    workflow.add_edge("embedder", END)
    workflow.add_edge("error_handler", END)

    # Compile the workflow
    app = workflow.compile()

    logger.info(f"[DOCUMENT_PROCESSING_WORKFLOW] Workflow compiled successfully")

    return app


def route_after_analysis(
    state: Dict[str, Any],
) -> str:
    """
    Route to the appropriate processor based on document analysis.

    This function examines the state after document routing
    and determines which specialized processor should handle the file.

    Args:
        state: Current workflow state

    Returns:
        Next node name
    """
    status = state.get("status", "pending")
    file_path = state.get("file_path")
    file_type = state.get("file_type", "unknown")
    is_supported_format = state.get("is_supported_format", False)
    
    logger.info(
        f"[DOCUMENT_PROCESSING_WORKFLOW] Routing decision for file {file_path}: status={status}"
    )

    # If there's an error or unsupported file, go to error handler
    if status == "failed" or not is_supported_format:
        logger.info(
            f"[DOCUMENT_PROCESSING_WORKFLOW] Routing to error_handler for file {file_path} (status={status})"
        )
        return "error_handler"

    # Route to appropriate processor
    route_mapping = {
        "pdf": "pdf_processor",
        "docx": "docx_processor",
        "image": "image_processor",
    }

    next_node = route_mapping.get(file_type, "error_handler")
    logger.info(
        f"[DOCUMENT_PROCESSING_WORKFLOW] Routing file {file_path} with file type '{file_type}' to node '{next_node}'"
    )

    return next_node


def check_file_fetcher_status(state: Dict[str, Any]) -> str:
    """
    Check if file fetching was successful and route accordingly.

    Args:
        state: Current workflow state

    Returns:
        Next node name based on file fetcher status
    """
    status = state.get("status", "pending")
    file_path = state.get("file_path")
    
    logger.info(f"[DOCUMENT_PROCESSING_WORKFLOW] File path from file fetcher: {file_path}")
    logger.info(f"[DOCUMENT_PROCESSING_WORKFLOW] Status from file fetcher: {status}")

    # If file fetching failed or no file path was set, go to error handler
    if status == "failed" or not file_path:
        return "error_handler"

    # If successful, continue to document router
    return "document_router"


def error_handler_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle errors and unsupported file types.

    This node provides graceful error handling and cleanup
    for failed processing attempts.

    Args:
        state: Current workflow state

    Returns:
        Updated state with error handling
    """

    try:
        # Work directly with state dictionary instead of creating Pydantic object
        error_message = state.get("error_message", "Unknown processing error")
        is_supported_format = state.get("is_supported_format", False)
        file_format = state.get("file_type", "unknown")

        # Create appropriate error response
        if not is_supported_format:
            final_message = f"File type not supported for AI processing: {file_format}"
            final_status = "skipped"
        else:
            final_message = f"Processing failed: {error_message}"
            final_status = "failed"

        # Update state for final result
        updated_state = {
            "status": final_status,
            "error_message": final_message,
        }

        return updated_state

    except Exception as e:
        return {
            "status": "failed",
            "error_message": f"Error handler failed: {str(e)}",
        }


def validate_document_processing_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and prepare input for document processing workflow.

    This function prepares the input for LangGraph.

    Args:
        input_data: Raw input data

    Returns:
        Validated and formatted state dict

    Raises:
        ValueError: If input validation fails
    """
    logger.info(f"[DOCUMENT_PROCESSING_WORKFLOW] Validating input data: {input_data}")

    # Extract required fields
    file_key = input_data.get("file_key", "") 
    resource_id = input_data.get("resource_id", "")
    status = input_data.get("status", "pending")

    if not file_key:
        raise ValueError("File key is required")

    if not resource_id:
        raise ValueError("Resource ID is required")

    # Prepare state with current file path
    state = {
        "file_key": file_key,
        "resource_id": str(resource_id),
        "status":status
    }

    logger.info(
        f"[DOCUMENT_PROCESSING_WORKFLOW] Prepared input state with file key: {file_key} and resource ID: {resource_id}"
    )

    return state


# Create a singleton workflow instance for reuse
_workflow_instance = None


def get_document_processing_workflow_instance() -> StateGraph:
    """
    Get a singleton instance of the document processing workflow.

    Returns:
        Compiled workflow instance
    """
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = create_document_processing_workflow()
    return _workflow_instance
