"""
OptimizerAgent — tune specialist args for latency/memory without changing answers.
"""

from __future__ import annotations

from typing import Any

from application.agents.models import RouteDecision

_SUMMARY_HINTS = (
    "how many",
    "summary",
    "overview",
    "total variance",
    "overall",
    "totals",
    "count",
)
_DETAIL_HINTS = (
    "which",
    "list",
    "show me",
    "unmatched",
    "flagged accounts",
    "detail",
    "items",
)


class OptimizerAgent:
    name = "optimizer"

    def tune(self, question: str, decision: RouteDecision) -> tuple[RouteDecision, dict[str, Any]]:
        """
        Prefer include_details=False for overview questions (smaller payloads / faster JSON).
        Keep details when the user asks which/list/flagged items.
        """
        text = (question or "").lower()
        args = dict(decision.tool_args)
        notes: dict[str, Any] = {"before": dict(args)}

        wants_detail = any(h in text for h in _DETAIL_HINTS)
        wants_summary = any(h in text for h in _SUMMARY_HINTS)

        if decision.intent in {"reconcile", "variance"}:
            if wants_detail:
                args["include_details"] = True
                notes["choice"] = "force_details"
            elif wants_summary and not wants_detail:
                args["include_details"] = False
                notes["choice"] = "summary_mode"
            else:
                # Default: summary for variance overviews, details for reconcile matching lists
                if decision.intent == "variance" and "flag" not in text and "which" not in text:
                    args["include_details"] = False
                    notes["choice"] = "variance_default_summary"
                else:
                    notes["choice"] = "keep_default"

        tuned = RouteDecision(
            intent=decision.intent,
            specialist=decision.specialist,
            tool_args=args,
            rationale=decision.rationale + f"; optimizer={notes.get('choice')}",
        )
        notes["after"] = dict(args)
        return tuned, notes
