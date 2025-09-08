"""
File ingestion workflow definition using function-based approach.

This follows the established pattern where workflows are pure functions
that define the graph structure and return compiled applications.
"""

import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from app.ai.schemas.workflow_states import FileIngestionState
from app.ai.nodes.pdf_parser_node import pdf_parser_node
from app.ai.nodes.docx_parser_node import docx_parser_node
from app.ai.nodes.image_parser_node import image_parser_node
from app.ai.nodes.text_chunker_node import text_chunker_node
from app.ai.nodes.store_documents_node import store_documents_node


logger = logging.getLogger(__name__)


def create_file_ingestion_workflow() -> StateGraph:
    """
    Create file ingestion workflow for file ingestion functionality.
    """

    # Create workflow with proper state schema
    workflow = StateGraph(FileIngestionState)

    # Add nodes
    workflow.add_node("start", lambda state: state)
    workflow.add_node("pdf_parser", pdf_parser_node)
    workflow.add_node("docx_parser", docx_parser_node)
    workflow.add_node("image_parser", image_parser_node)
    workflow.add_node("text_chunker", text_chunker_node)
    workflow.add_node("store_documents", store_documents_node)

    def document_router(
        state: FileIngestionState,
    ) -> str:
        """Routes to the appropriate handler based on file extension."""
        logger.info(f"[FILE_INGESTION_WORKFLOW] Received file path: {state.file_path}")
        
        # Extract extension from file path
        ext = state.file_path.split(".")[-1].lower()

        logger.info(f"[FILE_INGESTION_WORKFLOW] Received file extension: {ext}")

        if ext in {"pdf"}:
            document_type = "pdf"
        elif ext in {"docx", "doc"}:
            document_type = "docx"
        elif ext in {"jpg", "jpeg", "png"}:
            document_type = "img"
        else:
            logger.error(f"[FILE_INGESTION_WORKFLOW] Unknown file extension: {ext}")
            document_type = "unknown"

        logger.info(f"[FILE_INGESTION_WORKFLOW] Document type: {document_type}")
        return document_type

    # Conditional edge
    workflow.add_conditional_edges(
        "start",
        document_router,
        {
            "pdf": "pdf_parser",
            "docx": "docx_parser",
            "img": "image_parser",
            "unknown": END,
        },
    )

    # Add edges
    workflow.add_edge(START, "start")
    workflow.add_edge("pdf_parser", "text_chunker")
    workflow.add_edge("docx_parser", "text_chunker")
    workflow.add_edge("image_parser", "text_chunker")
    workflow.add_edge("text_chunker", "store_documents")
    workflow.add_edge("store_documents", END)

    app = workflow.compile()

    logger.info(f"[FILE_INGESTION_WORKFLOW] Workflow compiled successfully")

    return app


def validate_file_ingestion_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and prepare input for file ingestion workflow.

    This function prepares the input for LangGraph.

    Args:
        input_data: Raw input data

    Returns:
        Validated and formatted state dict

    Raises:
        ValueError: If input validation fails
    """
    logger.info(f"[FILE_INGESTION_WORKFLOW] Validating input data: {input_data}")

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
        f"[FILE_INGESTION_WORKFLOW] Prepared input state with file path: {file_path} and resource ID: {resource_id}"
    )

    return state
