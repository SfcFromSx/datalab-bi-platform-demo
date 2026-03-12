"""Pydantic schemas for LLM log API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class LLMLogResponse(BaseModel):
    id: str
    feature: str
    model: str
    messages: Optional[list[dict[str, Any]]] = None
    response: Optional[str] = None
    tokens_prompt: int = 0
    tokens_completion: int = 0
    duration_ms: int = 0
    status: str = "success"
    error: Optional[str] = None
    cell_id: Optional[str] = None
    notebook_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LLMLogListResponse(BaseModel):
    logs: list[LLMLogResponse]
    total: int


class LLMLogStatsResponse(BaseModel):
    total_calls: int = 0
    success_count: int = 0
    error_count: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    avg_duration_ms: float = 0.0
    by_feature: dict[str, int] = {}
    by_model: dict[str, int] = {}
