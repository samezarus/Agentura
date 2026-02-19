# MODELS & HANDLERS

from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


class HistoryItem(BaseModel):
    from_: str = Field(alias="from")
    message: str
    timestamp: Optional[str] = None
    model: Optional[str] = None

    model_config = {"populate_by_name": True}


class ChatRequest(BaseModel):
    session_id: str
    prompt: str


class ChatResponse(BaseModel):
    response: str
    tool_used: Optional[str] = None
    tool_result: Optional[str] = None
    response_time: Optional[float] = None  # Время генерации в секундах


class ToolDetectionRequest(BaseModel):
    prompt: str


class ToolDetectionResponse(BaseModel):
    use_tool: bool
    tool_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None