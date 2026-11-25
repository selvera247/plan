"""
Orchestrates deterministic workflows with caching + durable audit runs.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from cache.result_cache import ResultCache, cache_key, get_result_cache
from db.connection import _database_url, get_connection
from db.repository import AuditRepository
from logic.reconcile import WORKFLOW_NAME as RECON_NAME
from logic.reconcile import WORKFLOW_VERSION as RECON_VERSION
from logic.reconcile import reconcile_transactions
from logic.variance import WORKFLOW_NAME as VAR_NAME
from logic.variance import WORKFLOW_VERSION as VAR_VERSION
from logic.variance import analyze_variance
from tools.registry import resolve_data_path


def _driver() -> str:
    url = _database_url()
    return "postgres" if url.startswith(("postgres://", "postgresql://")) else "sqlite"


class WorkflowService:
    def __init__(self, cache: ResultCache | None = None) -> None:
        self.cache = cache or get_result_cache()

    def _run(
        self,
        *,
        workflow: str,
        version: str,
        inputs: dict[str, Any],
        runner: Callable[[], dict[str, Any]],
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        key = cache_key(workflow, version, inputs)
        cached = self.cache.get(key)
        if cached is not None:
            with get_connection() as conn:
                repo = AuditRepository(conn, driver=_driver())
                run_id = repo.record_workflow_run(
                    workflow=workflow,
                    version=version,
                    input_hash=key,
                    inputs=inputs,
                    result=cached,
                    lineage=cached.get("lineage") or {},
                    cache_hit=True,
                    duration_ms=0.0,
                    conversation_id=conversation_id,
                )
            return {
                "run_id": run_id,
                "cache_hit": True,
                "result": cached,
                "lineage": cached.get("lineage"),
            }

        started = time.perf_counter()
        result = runner()
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        lineage = result.get("lineage") or {}
        self.cache.set(key, result)

        with get_connection() as conn:
            repo = AuditRepository(conn, driver=_driver())
            run_id = repo.record_workflow_run(
                workflow=workflow,
                version=version,
                input_hash=key,
                inputs=inputs,
                result=result,
                lineage=lineage,
                cache_hit=False,
                duration_ms=duration_ms,
                conversation_id=conversation_id,
            )

        return {
            "run_id": run_id,
            "cache_hit": False,
            "duration_ms": duration_ms,
            "result": result,
            "lineage": lineage,
        }

    def reconcile(
        self,
        *,
        left_source: str,
        right_source: str,
        amount_tolerance: float = 0.01,
        left_label: str = "bank",
        right_label: str = "ledger",
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        left = resolve_data_path(left_source)
        right = resolve_data_path(right_source)
        inputs = {
            "left_source": str(left),
            "right_source": str(right),
            "amount_tolerance": amount_tolerance,
            "left_label": left_label,
            "right_label": right_label,
        }
        return self._run(
            workflow=RECON_NAME,
            version=RECON_VERSION,
            inputs=inputs,
            runner=lambda: reconcile_transactions(
                left,
                right,
                amount_tolerance=amount_tolerance,
                left_label=left_label,
                right_label=right_label,
            ),
            conversation_id=conversation_id,
        )

    def variance(
        self,
        *,
        actuals_source: str,
        budget_source: str,
        threshold_pct: float = 5.0,
        threshold_abs: float | None = None,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        actuals = resolve_data_path(actuals_source)
        budget = resolve_data_path(budget_source)
        inputs = {
            "actuals_source": str(actuals),
            "budget_source": str(budget),
            "threshold_pct": threshold_pct,
            "threshold_abs": threshold_abs,
        }
        return self._run(
            workflow=VAR_NAME,
            version=VAR_VERSION,
            inputs=inputs,
            runner=lambda: analyze_variance(
                actuals,
                budget,
                threshold_pct=threshold_pct,
                threshold_abs=threshold_abs,
            ),
            conversation_id=conversation_id,
        )
