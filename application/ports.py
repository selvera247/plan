"""
Outbound ports (interfaces) that infrastructure adapters implement.

Keeps application use cases free of FastAPI, SQLite, OpenAI, and filesystem details.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol


class ResultCachePort(Protocol):
    def get(self, key: str) -> dict[str, Any] | None: ...
    def set(self, key: str, value: dict[str, Any]) -> None: ...
    def stats(self) -> dict[str, Any]: ...


class AuditRepositoryPort(Protocol):
    def create_conversation(
        self, *, api_key_hash: str | None = None, metadata: dict | None = None
    ) -> str: ...

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None: ...

    def add_message(self, conversation_id: str, role: str, content: str) -> str: ...

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]: ...

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
    ) -> str: ...

    def get_run(self, run_id: str) -> dict[str, Any] | None: ...

    def list_runs(self, *, limit: int = 50) -> list[dict[str, Any]]: ...

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
    ) -> str: ...


class DataPathResolverPort(Protocol):
    def resolve(self, source: str | None) -> Any: ...
