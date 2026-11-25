"""
Minimal production HTTP API for the governed finance assistant.

Run:
  uvicorn api.app:app --reload --port 8000
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from project_paths import ENV_FILE

load_dotenv(ENV_FILE)

from api.deps import get_chat_service, get_workflow_service, require_api_key
from api.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    HealthResponse,
    ReadyResponse,
    ReconcileRequest,
    VarianceRequest,
    WorkflowResponse,
)
from cache.result_cache import get_result_cache
from db.connection import _database_url, get_connection, init_db
from db.repository import AuditRepository
from services.chat_service import GovernedChatService
from services.workflow_service import WorkflowService

APP_VERSION = "1.0.0"

app = FastAPI(
    title="Governed Finance Assistant API",
    version=APP_VERSION,
    description=(
        "Production-shaped API: deterministic workflows with lineage, "
        "result caching, and durable audit storage."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health", response_model=HealthResponse, tags=["ops"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=APP_VERSION)


@app.get("/ready", response_model=ReadyResponse, tags=["ops"])
def ready() -> ReadyResponse:
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        db = "postgres" if _database_url().startswith(("postgres",)) else "sqlite"
        return ReadyResponse(status="ready", database=db, cache=get_result_cache().stats())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"not ready: {exc}") from exc


@app.post(
    "/v1/workflows/reconcile",
    response_model=WorkflowResponse,
    tags=["workflows"],
)
def reconcile(
    body: ReconcileRequest,
    _: str | None = Depends(require_api_key),
    workflows: WorkflowService = Depends(get_workflow_service),
) -> WorkflowResponse:
    try:
        outcome = workflows.reconcile(
            left_source=body.left_source,
            right_source=body.right_source,
            amount_tolerance=body.amount_tolerance,
            left_label=body.left_label,
            right_label=body.right_label,
            conversation_id=body.conversation_id,
        )
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WorkflowResponse(**outcome)


@app.post(
    "/v1/workflows/variance",
    response_model=WorkflowResponse,
    tags=["workflows"],
)
def variance(
    body: VarianceRequest,
    _: str | None = Depends(require_api_key),
    workflows: WorkflowService = Depends(get_workflow_service),
) -> WorkflowResponse:
    try:
        outcome = workflows.variance(
            actuals_source=body.actuals_source,
            budget_source=body.budget_source,
            threshold_pct=body.threshold_pct,
            threshold_abs=body.threshold_abs,
            conversation_id=body.conversation_id,
        )
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WorkflowResponse(**outcome)


@app.post("/v1/chat", response_model=ChatResponse, tags=["chat"])
def chat(
    body: ChatRequest,
    api_key: str | None = Depends(require_api_key),
    chat_svc: GovernedChatService = Depends(get_chat_service),
) -> ChatResponse:
    try:
        outcome = chat_svc.ask(
            body.message,
            conversation_id=body.conversation_id,
            api_key=api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ChatResponse(
        conversation_id=outcome["conversation_id"],
        reply=outcome["reply"],
        run_ids=outcome.get("run_ids") or [],
        tool_calls=outcome.get("tool_calls") or [],
        lineage=outcome.get("lineage"),
    )


@app.get(
    "/v1/conversations/{conversation_id}",
    response_model=ConversationResponse,
    tags=["chat"],
)
def get_conversation(
    conversation_id: str,
    _: str | None = Depends(require_api_key),
) -> ConversationResponse:
    driver = "postgres" if _database_url().startswith(("postgres",)) else "sqlite"
    with get_connection() as conn:
        repo = AuditRepository(conn, driver=driver)
        if not repo.get_conversation(conversation_id):
            raise HTTPException(status_code=404, detail="conversation not found")
        messages = repo.list_messages(conversation_id)
    return ConversationResponse(conversation_id=conversation_id, messages=messages)


@app.get("/v1/runs/{run_id}", tags=["audit"])
def get_run(run_id: str, _: str | None = Depends(require_api_key)) -> dict:
    driver = "postgres" if _database_url().startswith(("postgres",)) else "sqlite"
    with get_connection() as conn:
        repo = AuditRepository(conn, driver=driver)
        run = repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.get("/v1/runs", tags=["audit"])
def list_runs(
    limit: int = Query(50, ge=1, le=200),
    _: str | None = Depends(require_api_key),
) -> dict:
    driver = "postgres" if _database_url().startswith(("postgres",)) else "sqlite"
    with get_connection() as conn:
        repo = AuditRepository(conn, driver=driver)
        runs = repo.list_runs(limit=limit)
    return {"runs": runs, "count": len(runs)}
