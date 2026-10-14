
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    status: str
    chunk_count: int
    error_message: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SourceResponse(BaseModel):
    document_id: UUID
    document: str
    page: int
    text: str
    score: float


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: UUID | None = None


class ChatResponse(BaseModel):
    conversation_id: UUID
    answer: str
    sources: list[SourceResponse]
    agent_trace: list[dict] | None = None


class ConversationResponse(BaseModel):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    sources: list
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)