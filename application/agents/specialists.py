"""
Specialist agents (Engineer) — execute governed workflows via WorkflowService.
"""

from __future__ import annotations

from typing import Any

from application.workflow_service import WorkflowService


class ReconcileAgent:
    name = "reconcile"

    def __init__(self, workflows: WorkflowService | None = None) -> None:
        self.workflows = workflows or WorkflowService()

    def run(self, tool_args: dict[str, Any]) -> dict[str, Any]:
        return self.workflows.reconcile(
            left_source=tool_args["left_source"],
            right_source=tool_args["right_source"],
            amount_tolerance=float(tool_args.get("amount_tolerance", 0.01)),
            left_label=tool_args.get("left_label", "bank"),
            right_label=tool_args.get("right_label", "ledger"),
            include_details=bool(tool_args.get("include_details", True)),
            conversation_id=tool_args.get("conversation_id"),
        )


class VarianceAgent:
    name = "variance"

    def __init__(self, workflows: WorkflowService | None = None) -> None:
        self.workflows = workflows or WorkflowService()

    def run(self, tool_args: dict[str, Any]) -> dict[str, Any]:
        threshold_abs = tool_args.get("threshold_abs")
        return self.workflows.variance(
            actuals_source=tool_args["actuals_source"],
            budget_source=tool_args["budget_source"],
            threshold_pct=float(tool_args.get("threshold_pct", 5.0)),
            threshold_abs=None if threshold_abs is None else float(threshold_abs),
            include_details=bool(tool_args.get("include_details", True)),
            conversation_id=tool_args.get("conversation_id"),
        )
