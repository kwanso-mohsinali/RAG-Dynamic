from typing import Annotated, Sequence
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