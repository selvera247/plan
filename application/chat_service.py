"""
Application use case: governed chat — LLM routes to WorkflowService tools.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from application.workflow_service import WorkflowService
from infrastructure.llm.assistant import FinanceAssistant
from infrastructure.persistence.connection import _database_url, get_connection
from infrastructure.persistence.repository import AuditRepository
from infrastructure.tools.openai_tools import TOOL_DEFINITIONS


def _driver() -> str:
    url = _database_url()
    return "postgres" if url.startswith(("postgres://", "postgresql://")) else "sqlite"


def _hash_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:32]


class GovernedChatService:
    """Chat path that executes tools via WorkflowService (cache + DB)."""

    def __init__(self, workflows: WorkflowService | None = None) -> None:
        self.workflows = workflows or WorkflowService()

    def _execute_governed_tool(
        self, name: str, args: dict[str, Any], conversation_id: str
    ) -> tuple[dict[str, Any], str | None]:
        if name == "reconcile_transactions":
            outcome = self.workflows.reconcile(
                left_source=args["left_source"],
                right_source=args["right_source"],
                amount_tolerance=float(args.get("amount_tolerance") or 0.01),
                left_label=args.get("left_label") or "bank",
                right_label=args.get("right_label") or "ledger",
                conversation_id=conversation_id,
            )
            return outcome["result"], outcome["run_id"]
        if name == "analyze_variance":
            threshold_abs = args.get("threshold_abs")
            outcome = self.workflows.variance(
                actuals_source=args["actuals_source"],
                budget_source=args["budget_source"],
                threshold_pct=float(args.get("threshold_pct") or 5.0),
                threshold_abs=None if threshold_abs is None else float(threshold_abs),
                conversation_id=conversation_id,
            )
            return outcome["result"], outcome["run_id"]
        return {"error": f"Unknown tool: {name}", "lineage": None}, None

    def ask(
        self,
        message: str,
        *,
        conversation_id: str | None = None,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required for /v1/chat")

        with get_connection() as conn:
            repo = AuditRepository(conn, driver=_driver())
            if conversation_id:
                existing = repo.get_conversation(conversation_id)
                if not existing:
                    raise ValueError(f"Unknown conversation_id: {conversation_id}")
            else:
                conversation_id = repo.create_conversation(
                    api_key_hash=_hash_key(api_key)
                )
            repo.add_message(conversation_id, "user", message)

        from infrastructure.llm.assistant import (
            _assistant_message_dict,
            _parse_tool_arguments,
        )

        assistant = FinanceAssistant()
        run_ids: list[str] = []
        tool_trace: list[dict[str, Any]] = []

        assistant.messages.append({"role": "user", "content": message})
        for _ in range(assistant.max_tool_rounds):
            response = assistant.client.chat.completions.create(
                model=assistant.model,
                messages=assistant.messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )
            msg = response.choices[0].message
            assistant.messages.append(_assistant_message_dict(msg))
            if not msg.tool_calls:
                reply = msg.content or ""
                break
            for tc in msg.tool_calls:
                name = tc.function.name
                args = _parse_tool_arguments(tc.function.arguments)
                result, run_id = self._execute_governed_tool(name, args, conversation_id)
                if run_id:
                    run_ids.append(run_id)
                status = "error" if "error" in result else "ok"
                tool_trace.append(
                    {"name": name, "arguments": args, "run_id": run_id, "status": status}
                )
                with get_connection() as conn:
                    repo = AuditRepository(conn, driver=_driver())
                    repo.record_tool_call(
                        tool_name=name,
                        arguments=args,
                        status=status,
                        conversation_id=conversation_id,
                        run_id=run_id,
                        error=result.get("error") if status == "error" else None,
                    )
                assistant.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, default=str),
                    }
                )
        else:
            final = assistant.client.chat.completions.create(
                model=assistant.model,
                messages=assistant.messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="none",
            )
            reply = final.choices[0].message.content or ""

        lineage = None
        if tool_trace:
            for tc in reversed(tool_trace):
                if tc["status"] == "ok" and tc.get("run_id"):
                    with get_connection() as conn:
                        repo = AuditRepository(conn, driver=_driver())
                        run = repo.get_run(tc["run_id"])
                        if run:
                            lineage = run.get("lineage") or (
                                json.loads(run["lineage_json"])
                                if isinstance(run.get("lineage_json"), str)
                                else None
                            )
                    break

        with get_connection() as conn:
            repo = AuditRepository(conn, driver=_driver())
            repo.add_message(conversation_id, "assistant", reply)

        return {
            "conversation_id": conversation_id,
            "reply": reply,
            "run_ids": run_ids,
            "tool_calls": tool_trace,
            "lineage": lineage,
            "system_prompt_version": "governed-v1",
        }
