"""Shared DTOs for the multi-agent pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Intent = Literal["reconcile", "variance", "unknown"]


@dataclass
class RouteDecision:
    intent: Intent
    specialist: str
    tool_args: dict[str, Any]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewReport:
    passed: bool
    checks: list[dict[str, Any]] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentStep:
    agent: str
    status: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentRunResult:
    answer: str
    intent: Intent
    lineage: dict[str, Any] | None
    run_id: str | None
    cache_hit: bool
    review: ReviewReport
    trace: list[AgentStep]
    workflow_result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "intent": self.intent,
            "lineage": self.lineage,
            "run_id": self.run_id,
            "cache_hit": self.cache_hit,
            "review": self.review.to_dict(),
            "trace": [s.to_dict() for s in self.trace],
            "result": self.workflow_result,
        }
