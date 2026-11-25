"""
OpenAI function-calling facade around the tool registry.

Each tool returns the deterministic result (including lineage).
Every invocation is audited via ``tools.audit``.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from infrastructure.tools.audit_log import (
    clear_tool_call_log,
    get_tool_call_log,
    logger,
    record_tool_call,
)
from infrastructure.tools.registry import HANDLERS, TOOL_DEFINITIONS


__all__ = [
    "TOOL_DEFINITIONS",
    "execute_tool",
    "get_tool_call_log",
    "clear_tool_call_log",
]


def _parse_arguments(arguments: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    if not isinstance(arguments, str):
        raise TypeError(f"Tool arguments must be dict or JSON string, got {type(arguments)}")
    if not arguments.strip():
        return {}
    try:
        parsed = json.loads(arguments)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid tool arguments JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Tool arguments JSON must be an object")
    return parsed


def execute_tool(name: str, arguments: dict[str, Any] | str) -> dict[str, Any]:
    """Execute a named tool and record the call for auditability."""
    started = datetime.now(timezone.utc)
    try:
        arguments = _parse_arguments(arguments)
    except (TypeError, ValueError) as exc:
        record_tool_call(
            tool=name,
            arguments={"raw": arguments} if not isinstance(arguments, dict) else arguments,
            status="error",
            started_at=started,
            error=str(exc),
        )
        logger.error("TOOL_CALL_FAILED name=%s error=%s", name, exc)
        return {"error": str(exc), "lineage": None}

    if name not in HANDLERS:
        error = f"Unknown tool: {name}"
        record_tool_call(
            tool=name,
            arguments=arguments,
            status="error",
            started_at=started,
            error=error,
        )
        logger.error("TOOL_CALL_FAILED name=%s error=%s", name, error)
        return {"error": error, "lineage": None}

    try:
        result = HANDLERS[name](arguments)
        record_tool_call(
            tool=name,
            arguments=arguments,
            status="ok",
            started_at=started,
            lineage=result.get("lineage"),
        )
        return result
    except Exception as exc:  # noqa: BLE001 — surface cleanly to the assistant
        record_tool_call(
            tool=name,
            arguments=arguments,
            status="error",
            started_at=started,
            error=str(exc),
        )
        # Validation / missing-file errors are expected in production traffic;
        # reserve stack traces for unexpected failures.
        if isinstance(exc, (ValueError, TypeError, FileNotFoundError, OSError)):
            logger.error("TOOL_CALL_FAILED name=%s args=%s error=%s", name, arguments, exc)
        else:
            logger.exception("TOOL_CALL_FAILED name=%s args=%s", name, arguments)
        return {"error": str(exc), "lineage": None}
