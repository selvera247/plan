"""Tool-call audit log (in-memory + file). Lazy handler setup."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from project_paths import LOG_DIR

logger = logging.getLogger("governed_finance.tools")
_TOOL_CALL_LOG: list[dict[str, Any]] = []
_CONFIGURED = False


def configure_logging() -> None:
    """Attach stream + file handlers once (idempotent)."""
    global _CONFIGURED
    if _CONFIGURED or logger.handlers:
        _CONFIGURED = True
        return

    LOG_DIR.mkdir(exist_ok=True)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(LOG_DIR / "tool_calls.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    _CONFIGURED = True


def get_tool_call_log() -> list[dict[str, Any]]:
    return list(_TOOL_CALL_LOG)


def clear_tool_call_log() -> None:
    _TOOL_CALL_LOG.clear()


def record_tool_call(
    *,
    tool: str,
    arguments: dict[str, Any],
    status: str,
    started_at: datetime,
    finished_at: datetime | None = None,
    lineage: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    configure_logging()
    finished = finished_at or datetime.now(timezone.utc)
    record: dict[str, Any] = {
        "tool": tool,
        "arguments": arguments,
        "status": status,
        "started_at": started_at.isoformat(),
        "finished_at": finished.isoformat(),
    }
    if lineage is not None:
        record["lineage"] = lineage
    if error is not None:
        record["error"] = error
    if status == "ok":
        record["duration_ms"] = round((finished - started_at).total_seconds() * 1000, 2)
        logger.info(
            "TOOL_CALL tool=%s status=ok lineage=%s args=%s duration_ms=%s",
            tool,
            json.dumps(lineage),
            json.dumps(arguments),
            record["duration_ms"],
        )
    # Error logging is owned by execute_tool so validation failures are not double-logged.

    _TOOL_CALL_LOG.append(record)
    return record
