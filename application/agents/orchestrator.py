"""
Orchestrator — runs Router → Optimizer → Specialist → Reviewer → Narrator.
"""

from __future__ import annotations

from typing import Any

from application.agents.models import AgentRunResult, AgentStep
from application.agents.narrator import narrate
from application.agents.optimizer_agent import OptimizerAgent
from application.agents.reviewer_agent import ReviewerAgent
from application.agents.router_agent import RouterAgent
from application.agents.specialists import ReconcileAgent, VarianceAgent
from application.workflow_service import WorkflowService


class AgentOrchestrator:
    def __init__(self, workflows: WorkflowService | None = None) -> None:
        self.workflows = workflows or WorkflowService()
        self.router = RouterAgent()
        self.optimizer = OptimizerAgent()
        self.reviewer = ReviewerAgent()
        self.reconcile_agent = ReconcileAgent(self.workflows)
        self.variance_agent = VarianceAgent(self.workflows)

    def run(self, question: str, *, conversation_id: str | None = None) -> AgentRunResult:
        trace: list[AgentStep] = []

        decision = self.router.route(question)
        trace.append(
            AgentStep(
                agent=self.router.name,
                status="ok",
                detail=decision.to_dict(),
            )
        )

        decision, opt_notes = self.optimizer.tune(question, decision)
        if conversation_id:
            decision.tool_args["conversation_id"] = conversation_id
        trace.append(
            AgentStep(agent=self.optimizer.name, status="ok", detail=opt_notes)
        )

        outcome: dict[str, Any] | None = None
        if decision.intent == "reconcile":
            outcome = self.reconcile_agent.run(decision.tool_args)
            trace.append(
                AgentStep(
                    agent=self.reconcile_agent.name,
                    status="ok",
                    detail={
                        "run_id": outcome.get("run_id"),
                        "cache_hit": outcome.get("cache_hit"),
                    },
                )
            )
        elif decision.intent == "variance":
            outcome = self.variance_agent.run(decision.tool_args)
            trace.append(
                AgentStep(
                    agent=self.variance_agent.name,
                    status="ok",
                    detail={
                        "run_id": outcome.get("run_id"),
                        "cache_hit": outcome.get("cache_hit"),
                    },
                )
            )
        else:
            trace.append(
                AgentStep(
                    agent="specialist",
                    status="skipped",
                    detail={"reason": "unknown_intent"},
                )
            )

        review = self.reviewer.review(decision, outcome)
        trace.append(
            AgentStep(
                agent=self.reviewer.name,
                status="ok" if review.passed else "failed",
                detail=review.to_dict(),
            )
        )

        # One retry: if summary mode failed field checks that need details, flip details on.
        if (
            not review.passed
            and outcome
            and decision.tool_args.get("include_details") is False
            and any("missing" in i.lower() for i in review.issues)
        ):
            decision.tool_args["include_details"] = True
            if decision.intent == "reconcile":
                outcome = self.reconcile_agent.run(decision.tool_args)
            elif decision.intent == "variance":
                outcome = self.variance_agent.run(decision.tool_args)
            review = self.reviewer.review(decision, outcome)
            trace.append(
                AgentStep(
                    agent="optimizer_retry",
                    status="ok" if review.passed else "failed",
                    detail={"include_details": True, "review": review.to_dict()},
                )
            )

        answer = narrate(question, decision, outcome, review)
        trace.append(
            AgentStep(agent="narrator", status="ok", detail={"chars": len(answer)})
        )

        lineage = None
        run_id = None
        cache_hit = False
        result = None
        if outcome:
            result = outcome.get("result")
            lineage = (result or {}).get("lineage") or outcome.get("lineage")
            run_id = outcome.get("run_id")
            cache_hit = bool(outcome.get("cache_hit"))

        return AgentRunResult(
            answer=answer,
            intent=decision.intent,
            lineage=lineage,
            run_id=run_id,
            cache_hit=cache_hit,
            review=review,
            trace=trace,
            workflow_result=result,
        )


def run_multi_agent(question: str, **kwargs: Any) -> dict[str, Any]:
    return AgentOrchestrator().run(question, **kwargs).to_dict()
