from typing import Annotated, List, Optional, Sequence
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class RAGChatState(BaseModel):
    """
    State schema for RAG chat workflow.

    Follows LangGraph documentation pattern with message history and RAG context.
    Used for conversational RAG with persistent message history.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages] = Field(
        default_factory=list
    )
    resource_id: str = Field(..., description="ID of the resource being queried")
    answer: Optional[str] = Field(default=None, description="Generated answer from RAG")
    error_message: Optional[str] = Field(
        default=None, description="Error message if processing fails"
    )


class DocumentProcessingState(BaseModel):
    """
    State schema for document processing workflow.

    This state is passed between nodes in the LangGraph workflow
    and tracks the complete document processing pipeline.
    """

    file_path: str = Field(..., description="Path to the file to be processed")
    resource_id: str = Field(
        ..., description="ID of the resource to store the documents"
    )
    file_format: Optional[str] = Field(
        None, description="Detected file format (pdf, docx, image, text)"
    )
    status: str = Field(default="pending", description="Overall processing status")
    documents: List[Document] = Field(
        default_factory=list, description="Processed documents"
    )
    embeddings_stored: Optional[int] = Field(
        default=0, description="Number of embeddings stored"
    )
    storage_metadata: Optional[dict] = Field(None, description="Storage metadata")
    error_message: Optional[str] = Field(
        default=None, description="Error message if processing fails"
    )
    file_metadata: Optional[dict] = Field(None, description="File metadata")
    is_supported_format: Optional[bool] = Field(None, description="Is supported format")
    processing_estimate: Optional[dict] = Field(None, description="Processing estimate")
