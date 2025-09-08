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

    messages: Annotated[Sequence[BaseMessage], add_messages]
    resource_id: str
    answer: str
    error_message: str


class DocumentProcessingState(BaseModel):
    """
    State schema for document processing workflow.

    This state is passed between nodes in the LangGraph workflow
    and tracks the complete document processing pipeline.
    """

    file_path: Field(..., description="Path to the file to be processed")
    resource_id: Field(..., description="ID of the resource to store the documents")
    file_format: Optional[str] = Field(
        None, description="Detected file format (pdf, docx, image, text)"
    )
    status: str = Field(default="pending", description="Overall processing status")
    documents: List[Document]
    error_message: str
