"""API dependencies: auth, services."""

from __future__ import annotations

import os
from typing import Annotated, Optional

from fastapi import Header, HTTPException, status

from services.chat_service import GovernedChatService
from services.workflow_service import WorkflowService

_workflow_service: WorkflowService | None = None
_chat_service: GovernedChatService | None = None


def get_workflow_service() -> WorkflowService:
    global _workflow_service
    if _workflow_service is None:
        _workflow_service = WorkflowService()
    return _workflow_service


def get_chat_service() -> GovernedChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = GovernedChatService(get_workflow_service())
    return _chat_service


def require_api_key(
    x_api_key: Annotated[Optional[str], Header()] = None,
) -> Optional[str]:
    """
    MVP auth: if GOVERNED_API_KEY is set, require matching X-API-Key.
    If unset, allow open local access (dev mode).
    """
    expected = (os.getenv("GOVERNED_API_KEY") or "").strip()
    if not expected:
        return x_api_key
    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )
    return x_api_key
