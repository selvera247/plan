"""
Tool registry: OpenAI schemas, demo aliases, and handlers into logic workflows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from logic.common import coerce_float
from logic.reconcile import reconcile_transactions
from logic.variance import analyze_variance
from project_paths import DATA_DIR, ROOT

SOURCE_ALIASES: dict[str, Path] = {
    "sample_bank": DATA_DIR / "sample_transactions_bank.csv",
    "sample_ledger": DATA_DIR / "sample_transactions_ledger.csv",
    "sample_actuals": DATA_DIR / "sample_actuals.csv",
    "sample_budget": DATA_DIR / "sample_budget.csv",
}


def resolve_data_path(source: str | None) -> Path:
    if source is None or not str(source).strip():
        raise ValueError(
            "Empty data source. Pass a CSV path or one of: "
            + ", ".join(sorted(SOURCE_ALIASES))
        )

    key = str(source).strip().lower()
    if key in SOURCE_ALIASES:
        path = SOURCE_ALIASES[key]
    else:
        path = Path(source)
        if not path.is_absolute():
            path = ROOT / path

    if path.is_dir():
        raise ValueError(
            f"Data source resolves to a directory, not a file: {path}. "
            f"Known aliases: {', '.join(sorted(SOURCE_ALIASES))}"
        )
    if not path.is_file():
        raise FileNotFoundError(
            f"Data file not found: {path}. "
            f"Known aliases: {', '.join(sorted(SOURCE_ALIASES))}"
        )
    return path


def _run_reconcile(args: dict[str, Any]) -> dict[str, Any]:
    if "left_source" not in args or "right_source" not in args:
        raise ValueError("reconcile_transactions requires left_source and right_source")
    return reconcile_transactions(
        resolve_data_path(args.get("left_source")),
        resolve_data_path(args.get("right_source")),
        amount_tolerance=coerce_float(
            args.get("amount_tolerance"), default=0.01, name="amount_tolerance"
        ),
        left_label=str(args.get("left_label") or "bank"),
        right_label=str(args.get("right_label") or "ledger"),
    )


def _run_variance(args: dict[str, Any]) -> dict[str, Any]:
    if "actuals_source" not in args or "budget_source" not in args:
        raise ValueError("analyze_variance requires actuals_source and budget_source")
    threshold_abs_raw = args.get("threshold_abs")
    threshold_abs = (
        None
        if threshold_abs_raw is None or threshold_abs_raw == ""
        else float(threshold_abs_raw)
    )
    return analyze_variance(
        resolve_data_path(args.get("actuals_source")),
        resolve_data_path(args.get("budget_source")),
        threshold_pct=coerce_float(
            args.get("threshold_pct"), default=5.0, name="threshold_pct"
        ),
        threshold_abs=threshold_abs,
    )


HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "reconcile_transactions": _run_reconcile,
    "analyze_variance": _run_variance,
}

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
                    "left_label": {"type": "string", "default": "bank"},
                    "right_label": {"type": "string", "default": "ledger"},
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
