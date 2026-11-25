"""Smoke tests for production API, cache, and durable workflow runs."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ApiAndCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.TemporaryDirectory()
        os.environ["SQLITE_PATH"] = str(Path(cls._tmpdir.name) / "test.db")
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("GOVERNED_API_KEY", None)
        # Fresh cache/module state for isolated DB path
        import cache.result_cache as rc
        import db.connection as dbc

        rc._CACHE = None
        dbc.init_db()

        from fastapi.testclient import TestClient

        from api.app import app

        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmpdir.cleanup()

    def test_health_and_ready(self) -> None:
        h = self.client.get("/health")
        self.assertEqual(h.status_code, 200)
        self.assertEqual(h.json()["status"], "ok")
        r = self.client.get("/ready")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ready")
        self.assertEqual(r.json()["database"], "sqlite")

    def test_reconcile_and_cache_hit(self) -> None:
        body = {"left_source": "sample_bank", "right_source": "sample_ledger"}
        first = self.client.post("/v1/workflows/reconcile", json=body)
        self.assertEqual(first.status_code, 200, first.text)
        payload = first.json()
        self.assertFalse(payload["cache_hit"])
        self.assertEqual(payload["result"]["matched_count"], 5)
        self.assertIn("lineage", payload)
        run_id = payload["run_id"]

        second = self.client.post("/v1/workflows/reconcile", json=body)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["cache_hit"])

        run = self.client.get(f"/v1/runs/{run_id}")
        self.assertEqual(run.status_code, 200)
        self.assertEqual(run.json()["workflow"], "reconcile_transactions")

    def test_variance_endpoint(self) -> None:
        body = {
            "actuals_source": "sample_actuals",
            "budget_source": "sample_budget",
            "threshold_pct": 5.0,
        }
        resp = self.client.post("/v1/workflows/variance", json=body)
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data["result"]["flagged_count"], 6)
        self.assertEqual(data["lineage"]["version"], "1.0.1")

    def test_list_runs(self) -> None:
        resp = self.client.get("/v1/runs?limit=10")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.json()["count"], 1)

    def test_api_key_enforced_when_configured(self) -> None:
        os.environ["GOVERNED_API_KEY"] = "secret-test-key"
        try:
            denied = self.client.post(
                "/v1/workflows/variance",
                json={
                    "actuals_source": "sample_actuals",
                    "budget_source": "sample_budget",
                },
            )
            self.assertEqual(denied.status_code, 401)
            ok = self.client.post(
                "/v1/workflows/variance",
                json={
                    "actuals_source": "sample_actuals",
                    "budget_source": "sample_budget",
                },
                headers={"X-API-Key": "secret-test-key"},
            )
            self.assertEqual(ok.status_code, 200)
        finally:
            os.environ.pop("GOVERNED_API_KEY", None)


if __name__ == "__main__":
    unittest.main()
