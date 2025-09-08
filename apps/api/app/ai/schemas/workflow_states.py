from typing import Annotated, List, Sequence
from langchain_core.documents import Document
from pydantic import BaseModel
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

class FileIngestionState(BaseModel):
    """
    State schema for file ingestion workflow.
    """
    file_path: str
    document_type: str
    resource_id: str
    documents: List[Document]
    error_message: str
    
    