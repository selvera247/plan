"""
RouterAgent (Architect) — classify finance intent and propose tool args.

Deterministic keyword routing; no LLM required.
"""

from __future__ import annotations

import re
from typing import Any

from application.agents.models import RouteDecision

_RECON_HINTS = (
    "reconcil",
    "match",
    "unmatched",
    "bank",
    "ledger",
    "gl ",
    "general ledger",
    "transaction",
    "clearing",
)
_VARIANCE_HINTS = (
    "variance",
    "budget",
    "actual",
    "overspend",
    "underspend",
    "flagged",
    "account",
    "p&l",
    "pnl",
)


class RouterAgent:
    name = "router"

    def route(self, question: str) -> RouteDecision:
        text = (question or "").strip().lower()
        recon_score = sum(1 for h in _RECON_HINTS if h in text)
        var_score = sum(1 for h in _VARIANCE_HINTS if h in text)

        # Explicit overrides
        if "reconcil" in text or "bank" in text and "ledger" in text:
            recon_score += 2
        if "budget" in text or "variance" in text or "actual" in text:
            var_score += 2

        if recon_score == 0 and var_score == 0:
            return RouteDecision(
                intent="unknown",
                specialist="none",
                tool_args={},
                rationale="No finance workflow keywords detected",
            )

        if recon_score >= var_score:
            args: dict[str, Any] = {
                "left_source": "sample_bank",
                "right_source": "sample_ledger",
                "amount_tolerance": 0.01,
                "include_details": True,
            }
            # Detect tolerance like 1.00 / $1
            m = re.search(r"tolerance\s*(?:of\s*)?(\d+(?:\.\d+)?)", text)
            if m:
                args["amount_tolerance"] = float(m.group(1))
            elif "1.00" in text or "tolerance 1" in text:
                args["amount_tolerance"] = 1.0
            return RouteDecision(
                intent="reconcile",
                specialist="reconcile",
                tool_args=args,
                rationale=f"recon_score={recon_score} >?= var_score={var_score}",
            )

        return RouteDecision(
            intent="variance",
            specialist="variance",
            tool_args={
                "actuals_source": "sample_actuals",
                "budget_source": "sample_budget",
                "threshold_pct": 5.0,
                "include_details": True,
            },
            rationale=f"var_score={var_score} > recon_score={recon_score}",
        )
