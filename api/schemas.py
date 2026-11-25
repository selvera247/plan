"""Pydantic request/response models for the v1 API."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"


class ReadyResponse(BaseModel):
    status: str
    database: str
    cache: dict[str, Any]


class ReconcileRequest(BaseModel):
    left_source: str = Field(..., examples=["sample_bank"])
    right_source: str = Field(..., examples=["sample_ledger"])
    amount_tolerance: float = 0.01
    left_label: str = "bank"
    right_label: str = "ledger"
    conversation_id: Optional[str] = None


class VarianceRequest(BaseModel):
    actuals_source: str = Field(..., examples=["sample_actuals"])
    budget_source: str = Field(..., examples=["sample_budget"])
    threshold_pct: float = 5.0
    threshold_abs: Optional[float] = None
    conversation_id: Optional[str] = None


class WorkflowResponse(BaseModel):
    run_id: str
    cache_hit: bool
    duration_ms: Optional[float] = None
    lineage: Optional[dict[str, Any]] = None
    result: dict[str, Any]


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    run_ids: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    lineage: Optional[dict[str, Any]] = None


class ConversationResponse(BaseModel):
    conversation_id: str
    messages: list[dict[str, Any]]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
