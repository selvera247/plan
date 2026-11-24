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

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.audit import (
    clear_tool_call_log,
    get_tool_call_log,
    logger,
    record_tool_call,
)
from tools.registry import HANDLERS, TOOL_DEFINITIONS


__all__ = [
    "TOOL_DEFINITIONS",
    "execute_tool",
    "get_tool_call_log",
    "clear_tool_call_log",
]


def execute_tool(name: str, arguments: dict[str, Any] | str) -> dict[str, Any]:
    """Execute a named tool and record the call for auditability."""
    if isinstance(arguments, str):
        arguments = json.loads(arguments) if arguments.strip() else {}

    started = datetime.now(timezone.utc)
    if name not in HANDLERS:
        error = f"Unknown tool: {name}"
        record_tool_call(
            tool=name,
            arguments=arguments,
            status="error",
            started_at=started,
            error=error,
        )
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
        logger.exception("TOOL_CALL_FAILED name=%s args=%s", name, arguments)
        return {"error": str(exc), "lineage": None}
