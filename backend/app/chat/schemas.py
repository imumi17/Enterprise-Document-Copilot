from typing import Any

from pydantic import BaseModel, Field


class UiMessagePart(BaseModel):
    type: str
    text: str | None = None


class UiMessage(BaseModel):
    id: str
    role: str
    parts: list[UiMessagePart] = Field(default_factory=list)
    content: str | None = None


class ChatStreamRequest(BaseModel):
    id: str
    messages: list[dict[str, Any]]


class ChatThreadResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class ThreadMessagesResponse(BaseModel):
    messages: list[UiMessage]
