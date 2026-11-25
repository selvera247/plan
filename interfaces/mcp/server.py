"""
Optional FastMCP server exposing the same governed finance workflows.

Run:
    python3 -m interfaces.mcp.server
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from infrastructure.tools.openai_tools import execute_tool


try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    from fastmcp import FastMCP

mcp = FastMCP(
    name="governed-finance",
    instructions=(
        "Deterministic finance workflows. Call these tools for any numeric "
        "or rule-based finance question; do not compute numbers yourself."
    ),
)


@mcp.tool()
def reconcile_transactions(
    left_source: str,
    right_source: str,
    amount_tolerance: float = 0.01,
    left_label: str = "bank",
    right_label: str = "ledger",
) -> dict[str, Any]:
    """Reconcile two transaction CSVs on amount + date + reference."""
    return execute_tool(
        "reconcile_transactions",
        {
            "left_source": left_source,
            "right_source": right_source,
            "amount_tolerance": amount_tolerance,
            "left_label": left_label,
            "right_label": right_label,
        },
    )


@mcp.tool()
def analyze_variance(
    actuals_source: str,
    budget_source: str,
    threshold_pct: float = 5.0,
    threshold_abs: Optional[float] = None,
) -> dict[str, Any]:
    """Compare actuals vs budget and flag variances above threshold."""
    return execute_tool(
        "analyze_variance",
        {
            "actuals_source": actuals_source,
            "budget_source": budget_source,
            "threshold_pct": threshold_pct,
            "threshold_abs": threshold_abs,
        },
    )


if __name__ == "__main__":
    mcp.run()
