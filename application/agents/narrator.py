"""
Narrator — produce a user-facing answer that cites lineage (no invented math).
"""

from __future__ import annotations

from typing import Any

from application.agents.models import ReviewReport, RouteDecision


def narrate(
    question: str,
    decision: RouteDecision,
    outcome: dict[str, Any] | None,
    review: ReviewReport,
) -> str:
    if decision.intent == "unknown":
        return (
            "I can help with bank↔ledger reconciliation or budget-vs-actual variance "
            "on the sample datasets. Try asking to reconcile sample bank/ledger or "
            "analyze sample actuals vs budget."
        )

    if not review.passed:
        issues = "; ".join(review.issues) or "quality checks failed"
        return f"I could not produce a governed answer ({issues})."

    assert outcome is not None
    result = outcome["result"]
    lineage = result.get("lineage") or {}
    wf = lineage.get("workflow", "unknown_workflow")
    ver = lineage.get("version", "?")
    cite = f"via {wf} v{ver}"

    if decision.intent == "reconcile":
        totals = result.get("totals") or {}
        parts = [
            f"Reconciliation complete ({cite}).",
            f"Matched: {result.get('matched_count')}; "
            f"unmatched bank: {result.get('unmatched_left_count')}; "
            f"unmatched ledger: {result.get('unmatched_right_count')}.",
            f"Total variance: {totals.get('total_variance')}.",
        ]
        if result.get("unmatched_left") and "which" in question.lower():
            refs = [t.get("reference") for t in result["unmatched_left"][:10]]
            parts.append(f"Unmatched bank refs: {', '.join(refs)}.")
        return " ".join(parts)

    if decision.intent == "variance":
        totals = result.get("totals") or {}
        parts = [
            f"Variance analysis complete ({cite}).",
            f"Accounts: {result.get('item_count')}; flagged: {result.get('flagged_count')}.",
            f"Overall absolute variance: {totals.get('absolute_variance')}; "
            f"percent: {totals.get('percent_variance')}.",
        ]
        flagged = result.get("flagged") or []
        if flagged and ("which" in question.lower() or "flag" in question.lower()):
            names = [i.get("account") for i in flagged]
            parts.append(f"Flagged accounts: {', '.join(names)}.")
        return " ".join(parts)

    return f"Done ({cite})."
