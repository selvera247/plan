"""Persistence for conversations, messages, workflow runs, and tool calls."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _ph(driver: str) -> str:
    return "%s" if driver == "postgres" else "?"


class AuditRepository:
    def __init__(self, conn: Any, *, driver: str = "sqlite") -> None:
        self.conn = conn
        self.driver = driver
        self.q = _ph(driver)

    def create_conversation(self, *, api_key_hash: str | None = None, metadata: dict | None = None) -> str:
        cid = _new_id()
        now = _utcnow()
        self.conn.execute(
            f"""
            INSERT INTO conversations (id, created_at, updated_at, api_key_hash, metadata_json)
            VALUES ({self.q}, {self.q}, {self.q}, {self.q}, {self.q})
            """,
            (cid, now, now, api_key_hash, json.dumps(metadata or {})),
        )
        return cid

    def touch_conversation(self, conversation_id: str) -> None:
        self.conn.execute(
            f"UPDATE conversations SET updated_at = {self.q} WHERE id = {self.q}",
            (_utcnow(), conversation_id),
        )

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        cur = self.conn.execute(
            f"SELECT * FROM conversations WHERE id = {self.q}",
            (conversation_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def add_message(self, conversation_id: str, role: str, content: str) -> str:
        mid = _new_id()
        self.conn.execute(
            f"""
            INSERT INTO messages (id, conversation_id, role, content, created_at)
            VALUES ({self.q}, {self.q}, {self.q}, {self.q}, {self.q})
            """,
            (mid, conversation_id, role, content, _utcnow()),
        )
        self.touch_conversation(conversation_id)
        return mid

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            f"""
            SELECT id, role, content, created_at
            FROM messages
            WHERE conversation_id = {self.q}
            ORDER BY created_at ASC
            """,
            (conversation_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    def record_workflow_run(
        self,
        *,
        workflow: str,
        version: str,
        input_hash: str,
        inputs: dict[str, Any],
        result: dict[str, Any],
        lineage: dict[str, Any],
        cache_hit: bool,
        duration_ms: float,
        conversation_id: str | None = None,
    ) -> str:
        rid = _new_id()
        self.conn.execute(
            f"""
            INSERT INTO workflow_runs (
                id, workflow, version, input_hash, inputs_json, result_json,
                lineage_json, cache_hit, duration_ms, conversation_id, created_at
            ) VALUES (
                {self.q}, {self.q}, {self.q}, {self.q}, {self.q}, {self.q},
                {self.q}, {self.q}, {self.q}, {self.q}, {self.q}
            )
            """,
            (
                rid,
                workflow,
                version,
                input_hash,
                json.dumps(inputs, default=str),
                json.dumps(result, default=str),
                json.dumps(lineage, default=str),
                1 if cache_hit else 0,
                duration_ms,
                conversation_id,
                _utcnow(),
            ),
        )
        return rid

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        cur = self.conn.execute(
            f"SELECT * FROM workflow_runs WHERE id = {self.q}",
            (run_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        data = dict(row)
        for key in ("inputs_json", "result_json", "lineage_json"):
            if key in data and isinstance(data[key], str):
                data[key.replace("_json", "")] = json.loads(data[key])
        return data

    def list_runs(self, *, limit: int = 50) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            f"""
            SELECT id, workflow, version, input_hash, cache_hit, duration_ms,
                   lineage_json, created_at, conversation_id
            FROM workflow_runs
            ORDER BY created_at DESC
            LIMIT {self.q}
            """,
            (limit,),
        )
        rows = []
        for row in cur.fetchall():
            item = dict(row)
            if isinstance(item.get("lineage_json"), str):
                item["lineage"] = json.loads(item["lineage_json"])
            rows.append(item)
        return rows

    def record_tool_call(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        status: str,
        conversation_id: str | None = None,
        message_id: str | None = None,
        run_id: str | None = None,
        error: str | None = None,
    ) -> str:
        tid = _new_id()
        self.conn.execute(
            f"""
            INSERT INTO tool_calls (
                id, conversation_id, message_id, run_id, tool_name,
                arguments_json, status, error, created_at
            ) VALUES (
                {self.q}, {self.q}, {self.q}, {self.q}, {self.q},
                {self.q}, {self.q}, {self.q}, {self.q}
            )
            """,
            (
                tid,
                conversation_id,
                message_id,
                run_id,
                tool_name,
                json.dumps(arguments, default=str),
                status,
                error,
                _utcnow(),
            ),
        )
        return tid
