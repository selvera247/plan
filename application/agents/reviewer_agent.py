"""
ReviewerAgent — quality gate on specialist output (lineage + required fields).
"""

from __future__ import annotations

from typing import Any

from application.agents.models import ReviewReport, RouteDecision


class ReviewerAgent:
    name = "reviewer"

    def review(
        self,
        decision: RouteDecision,
        outcome: dict[str, Any] | None,
    ) -> ReviewReport:
        checks: list[dict[str, Any]] = []
        issues: list[str] = []

        if decision.intent == "unknown":
            return ReviewReport(
                passed=False,
                checks=[{"name": "intent", "ok": False}],
                issues=["Router could not classify a finance workflow intent"],
            )

        if not outcome or "result" not in outcome:
            return ReviewReport(
                passed=False,
                checks=[{"name": "outcome_present", "ok": False}],
                issues=["Specialist returned no outcome"],
            )

        result = outcome["result"] or {}
        lineage = result.get("lineage") or outcome.get("lineage") or {}

        lineage_ok = bool(lineage.get("workflow") and lineage.get("version"))
        checks.append({"name": "lineage", "ok": lineage_ok, "lineage": lineage})
        if not lineage_ok:
            issues.append("Missing workflow lineage (name/version)")

        if "error" in result:
            checks.append({"name": "no_error", "ok": False, "error": result["error"]})
            issues.append(f"Workflow error: {result['error']}")

        if decision.intent == "reconcile":
            for field in ("matched_count", "unmatched_left_count", "unmatched_right_count", "totals"):
                ok = field in result
                checks.append({"name": f"field:{field}", "ok": ok})
                if not ok:
                    issues.append(f"Reconcile result missing '{field}'")
            if lineage_ok and lineage.get("workflow") != "reconcile_transactions":
                issues.append(
                    f"Lineage workflow mismatch: {lineage.get('workflow')}"
                )
                checks.append({"name": "workflow_match", "ok": False})
            else:
                checks.append({"name": "workflow_match", "ok": True})

        if decision.intent == "variance":
            for field in ("item_count", "flagged_count", "totals"):
                ok = field in result
                checks.append({"name": f"field:{field}", "ok": ok})
                if not ok:
                    issues.append(f"Variance result missing '{field}'")
            if lineage_ok and lineage.get("workflow") != "analyze_variance":
                issues.append(
                    f"Lineage workflow mismatch: {lineage.get('workflow')}"
                )
                checks.append({"name": "workflow_match", "ok": False})
            else:
                checks.append({"name": "workflow_match", "ok": True})

        return ReviewReport(passed=not issues, checks=checks, issues=issues)
