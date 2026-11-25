"""Tests for the multi-agent Router → Optimizer → Specialist → Reviewer pipeline."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class MultiAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.TemporaryDirectory()
        os.environ["SQLITE_PATH"] = str(Path(cls._tmpdir.name) / "agents.db")
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("GOVERNED_API_KEY", None)
        import cache.result_cache as rc
        import infrastructure.cache.result_cache as irc
        import infrastructure.persistence.connection as dbc

        rc._CACHE = None
        irc._CACHE = None
        dbc.reset_sqlite_pool()
        dbc.init_db()

        from application.agents.orchestrator import AgentOrchestrator
        from application.workflow_service import WorkflowService
        from fastapi.testclient import TestClient
        from interfaces.api.app import app

        cls.orch = AgentOrchestrator(WorkflowService())
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmpdir.cleanup()

    def test_router_reconcile_intent(self) -> None:
        from application.agents.router_agent import RouterAgent

        d = RouterAgent().route(
            "Please reconcile sample bank and ledger. How many matched?"
        )
        self.assertEqual(d.intent, "reconcile")
        self.assertEqual(d.tool_args["left_source"], "sample_bank")

    def test_router_variance_intent(self) -> None:
        from application.agents.router_agent import RouterAgent

        d = RouterAgent().route(
            "Which accounts are flagged in sample actuals vs budget?"
        )
        self.assertEqual(d.intent, "variance")

    def test_optimizer_summary_mode(self) -> None:
        from application.agents.optimizer_agent import OptimizerAgent
        from application.agents.router_agent import RouterAgent

        decision = RouterAgent().route(
            "What is the overall absolute variance for sample actuals vs budget?"
        )
        tuned, notes = OptimizerAgent().tune(
            "What is the overall absolute variance?", decision
        )
        self.assertFalse(tuned.tool_args["include_details"])
        self.assertIn(notes["choice"], {"summary_mode", "variance_default_summary"})

    def test_orchestrator_reconcile_end_to_end(self) -> None:
        result = self.orch.run(
            "Reconcile the sample bank and ledger. How many matched?"
        )
        self.assertEqual(result.intent, "reconcile")
        self.assertTrue(result.review.passed)
        self.assertIsNotNone(result.lineage)
        self.assertEqual(result.lineage["workflow"], "reconcile_transactions")
        self.assertIn("Matched:", result.answer)
        self.assertIn("via reconcile_transactions", result.answer)
        agents = [s.agent for s in result.trace]
        self.assertEqual(agents[0], "router")
        self.assertIn("reviewer", agents)
        self.assertIn("narrator", agents)

    def test_orchestrator_variance_end_to_end(self) -> None:
        result = self.orch.run(
            "Using sample actuals and budget, what is the overall variance?"
        )
        self.assertEqual(result.intent, "variance")
        self.assertTrue(result.review.passed)
        self.assertEqual(result.lineage["workflow"], "analyze_variance")
        self.assertIn("flagged", result.answer.lower())

    def test_reviewer_rejects_unknown(self) -> None:
        result = self.orch.run("What is the weather in Chicago?")
        self.assertEqual(result.intent, "unknown")
        self.assertFalse(result.review.passed)
        self.assertIn("reconcil", result.answer.lower() + "budget")

    def test_api_agents_run(self) -> None:
        resp = self.client.post(
            "/v1/agents/run",
            json={"question": "Match bank feed to ledger using sample CSVs"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["intent"], "reconcile")
        self.assertTrue(body["review"]["passed"])
        self.assertEqual(body["result"]["matched_count"], 5)


if __name__ == "__main__":
    unittest.main()
