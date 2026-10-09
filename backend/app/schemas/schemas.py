
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    status: str
    chunk_count: int
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