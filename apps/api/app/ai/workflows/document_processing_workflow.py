"""
Document processing workflow definition using function-based approach.

This follows the established pattern where workflows are pure functions
that define the graph structure and return compiled applications.
"""

import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from app.ai.schemas.workflow_states import DocumentProcessingState
from app.ai.nodes.pdf_processor_node import pdf_processor_node
from app.ai.nodes.docx_processor_node import docx_processor_node
from app.ai.nodes.image_processor_node import image_processor_node
from app.ai.nodes.chunker_node import chunker_node
from app.ai.nodes.embedder_node import embedder_node


logger = logging.getLogger(__name__)


def create_document_processing_workflow() -> StateGraph:
    """
    Create document processing workflow for document processing functionality.
    """

    # Create workflow with proper state schema
    workflow = StateGraph(DocumentProcessingState)

    # Add nodes
    workflow.add_node("start", lambda state: state)
    workflow.add_node("pdf_processor", pdf_processor_node)
    workflow.add_node("docx_processor", docx_processor_node)
    workflow.add_node("image_processor", image_processor_node)
    workflow.add_node("chunker", chunker_node)
    workflow.add_node("embedder", embedder_node)

    # Conditional edge
    workflow.add_conditional_edges(
        "start",
        document_router,
        {
            "pdf": "pdf_processor",
            "docx": "docx_processor",
            "image": "image_processor",
            "unknown": END,
        },
    )

    # Add edges
    workflow.add_edge(START, "start")
    workflow.add_edge("pdf_processor", "chunker")
    workflow.add_edge("docx_processor", "chunker")
    workflow.add_edge("image_processor", "chunker")
    workflow.add_edge("chunker", "embedder")
    workflow.add_edge("embedder", END)

    app = workflow.compile()

    logger.info(f"[DOCUMENT_PROCESSING_WORKFLOW] Workflow compiled successfully")

    return app


def document_router(
    state: DocumentProcessingState,
) -> str:
    """Routes to the appropriate handler based on file extension."""
    logger.info(f"[DOCUMENT_PROCESSING_WORKFLOW] Received file path: {state.file_path}")

    # Extract extension from file path
    ext = state.file_path.split(".")[-1].lower()

    logger.info(f"[DOCUMENT_PROCESSING_WORKFLOW] Received file extension: {ext}")

    if ext in {"pdf"}:
        file_format = "pdf"
    elif ext in {"docx", "doc"}:
        file_format = "docx"
    elif ext in {"jpg", "jpeg", "png"}:
        file_format = "image"
    else:
        logger.error(f"[DOCUMENT_PROCESSING_WORKFLOW] Unknown file extension: {ext}")
        file_format = "unknown"

    logger.info(f"[DOCUMENT_PROCESSING_WORKFLOW] Document type: {file_format}")
    return file_format


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
    file_path = input_data.get("file_path", "")
    resource_id = input_data.get("resource_id")

    if not file_path:
        raise ValueError("File path is required")

    if not resource_id:
        raise ValueError("Resource ID is required")

    # Prepare state with current file path
    state = {
        "file_path": file_path,
        "resource_id": str(resource_id),
    }

    logger.info(
        f"[DOCUMENT_PROCESSING_WORKFLOW] Prepared input state with file path: {file_path} and resource ID: {resource_id}"
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
