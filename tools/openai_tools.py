"""
OpenAI function-calling wrapper around governed finance workflows.

Each tool returns both the deterministic result and lineage metadata.
Every invocation is logged for auditability.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Allow running from repo root without installing as a package.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from logic.reconcile import reconcile_transactions
from logic.variance import analyze_variance

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("governed_finance.tools")
if not logger.handlers:
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

_TOOL_CALL_LOG: list[dict[str, Any]] = []

DATA_DIR = ROOT / "data"

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "reconcile_transactions",
            "description": (
                "Reconcile two transaction sets (bank vs ledger) by matching "
                "on amount, date, and reference. Returns matched/unmatched "
                "counts, variance totals, and lineage metadata. "
                "ALWAYS use this tool for reconciliation or matching questions — "
                "never calculate matches yourself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "left_source": {
                        "type": "string",
                        "description": (
                            "Path to left (e.g. bank) CSV relative to repo, "
                            "or the keyword 'sample_bank' for demo data."
                        ),
                    },
                    "right_source": {
                        "type": "string",
                        "description": (
                            "Path to right (e.g. ledger) CSV relative to repo, "
                            "or the keyword 'sample_ledger' for demo data."
                        ),
                    },
                    "amount_tolerance": {
                        "type": "number",
                        "description": "Absolute amount tolerance for matching (default 0.01).",
                        "default": 0.01,
                    },
                    "left_label": {
                        "type": "string",
                        "default": "bank",
                    },
                    "right_label": {
                        "type": "string",
                        "default": "ledger",
                    },
                },
                "required": ["left_source", "right_source"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_variance",
            "description": (
                "Compare actuals vs budget by account/category. Returns "
                "absolute and percent variance, flagged items above threshold, "
                "and lineage metadata. ALWAYS use this tool for variance, "
                "budget-vs-actual, or overspend questions — never calculate yourself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "actuals_source": {
                        "type": "string",
                        "description": (
                            "Path to actuals CSV relative to repo, "
                            "or the keyword 'sample_actuals' for demo data."
                        ),
                    },
                    "budget_source": {
                        "type": "string",
                        "description": (
                            "Path to budget CSV relative to repo, "
                            "or the keyword 'sample_budget' for demo data."
                        ),
                    },
                    "threshold_pct": {
                        "type": "number",
                        "description": "Flag items with |% variance| >= this value (default 5.0).",
                        "default": 5.0,
                    },
                    "threshold_abs": {
                        "type": ["number", "null"],
                        "description": "Optional absolute variance flag threshold.",
                        "default": None,
                    },
                },
                "required": ["actuals_source", "budget_source"],
            },
        },
    },
]


def _resolve_data_path(source: str, aliases: dict[str, Path]) -> str | Path:
    key = source.strip().lower()
    if key in aliases:
        return aliases[key]
    path = Path(source)
    if not path.is_absolute():
        path = ROOT / path
    return path


def _run_reconcile(args: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "sample_bank": DATA_DIR / "sample_transactions_bank.csv",
        "sample_ledger": DATA_DIR / "sample_transactions_ledger.csv",
    }
    left = _resolve_data_path(args["left_source"], aliases)
    right = _resolve_data_path(args["right_source"], aliases)
    return reconcile_transactions(
        left,
        right,
        amount_tolerance=float(args.get("amount_tolerance", 0.01)),
        left_label=args.get("left_label", "bank"),
        right_label=args.get("right_label", "ledger"),
    )


def _run_variance(args: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "sample_actuals": DATA_DIR / "sample_actuals.csv",
        "sample_budget": DATA_DIR / "sample_budget.csv",
    }
    actuals = _resolve_data_path(args["actuals_source"], aliases)
    budget = _resolve_data_path(args["budget_source"], aliases)
    threshold_abs = args.get("threshold_abs")
    return analyze_variance(
        actuals,
        budget,
        threshold_pct=float(args.get("threshold_pct", 5.0)),
        threshold_abs=None if threshold_abs is None else float(threshold_abs),
    )


_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "reconcile_transactions": _run_reconcile,
    "analyze_variance": _run_variance,
}


def get_tool_call_log() -> list[dict[str, Any]]:
    """Return a copy of in-memory tool call records for this process."""
    return list(_TOOL_CALL_LOG)


def clear_tool_call_log() -> None:
    _TOOL_CALL_LOG.clear()


def execute_tool(name: str, arguments: dict[str, Any] | str) -> dict[str, Any]:
    """
    Execute a named tool and log the call.

    Returns a dict with ``result`` (workflow output including lineage)
    and ``tool_meta`` (call timing / name).
    """
    if isinstance(arguments, str):
        arguments = json.loads(arguments) if arguments.strip() else {}

    started = datetime.now(timezone.utc)
    if name not in _HANDLERS:
        error = {"error": f"Unknown tool: {name}", "lineage": None}
        record = {
            "tool": name,
            "arguments": arguments,
            "status": "error",
            "error": error["error"],
            "started_at": started.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        _TOOL_CALL_LOG.append(record)
        logger.error("TOOL_CALL_FAILED name=%s args=%s error=%s", name, arguments, error["error"])
        return error

    try:
        result = _HANDLERS[name](arguments)
        finished = datetime.now(timezone.utc)
        lineage = result.get("lineage")
        record = {
            "tool": name,
            "arguments": arguments,
            "status": "ok",
            "lineage": lineage,
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "duration_ms": round((finished - started).total_seconds() * 1000, 2),
        }
        _TOOL_CALL_LOG.append(record)
        logger.info(
            "TOOL_CALL tool=%s status=ok lineage=%s args=%s duration_ms=%s",
            name,
            json.dumps(lineage),
            json.dumps(arguments),
            record["duration_ms"],
        )
        return result
    except Exception as exc:  # noqa: BLE001 — surface cleanly to the assistant
        finished = datetime.now(timezone.utc)
        record = {
            "tool": name,
            "arguments": arguments,
            "status": "error",
            "error": str(exc),
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
        }
        _TOOL_CALL_LOG.append(record)
        logger.exception("TOOL_CALL_FAILED name=%s args=%s", name, arguments)
        return {"error": str(exc), "lineage": None}
