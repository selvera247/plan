"""Lightweight performance regression checks (not flaky wall-clock gates)."""

from __future__ import annotations

import sys
import time
import unittest
from datetime import date, timedelta
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cache.result_cache import ResultCache, cache_key
from logic.common import amounts_within_tolerance
from logic.reconcile import reconcile_transactions


def _txns(n: int, seed: int = 1) -> list[dict]:
    rng = random.Random(seed)
    base = date(2024, 1, 1)
    rows = []
    for i in range(n):
        d = base + timedelta(days=i % 28)
        rows.append(
            {
                "date": d.isoformat(),
                "amount": round(10 + (i % 100) + rng.random(), 2),
                "reference": f"REF-{i}",
                "description": "perf",
            }
        )
    return rows


class PerfRegressionTests(unittest.TestCase):
    def test_tolerance_hot_path_is_fast(self) -> None:
        t0 = time.perf_counter()
        for _ in range(100_000):
            amounts_within_tolerance(10.0, 10.005, 0.01)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        # Loose ceiling — catches accidental Decimal regression (~300ms+).
        self.assertLess(elapsed_ms, 150.0, f"tolerance loop too slow: {elapsed_ms:.1f}ms")

    def test_reconcile_5k_and_summary_mode(self) -> None:
        left = _txns(5000)
        right = [dict(r) for r in left]
        t0 = time.perf_counter()
        full = reconcile_transactions(left, right)
        full_ms = (time.perf_counter() - t0) * 1000
        self.assertEqual(full["matched_count"], 5000)
        self.assertIn("matched", full)

        t0 = time.perf_counter()
        summary = reconcile_transactions(left, right, include_details=False)
        summary_ms = (time.perf_counter() - t0) * 1000
        self.assertEqual(summary["matched_count"], 5000)
        self.assertNotIn("matched", summary)
        # Summary should not be dramatically slower than full (no detail alloc).
        self.assertLess(full_ms, 2000.0, f"full reconcile too slow: {full_ms:.1f}ms")
        self.assertLess(summary_ms, 2000.0, f"summary reconcile too slow: {summary_ms:.1f}ms")

    def test_cache_get_is_near_constant_time(self) -> None:
        left = _txns(2000)
        right = [dict(r) for r in left]
        payload = reconcile_transactions(left, right)
        cache = ResultCache(max_entries=8, ttl_seconds=60)
        key = cache_key("reconcile_transactions", "1.0.2", {"n": 2000})
        cache.set(key, payload)
        t0 = time.perf_counter()
        for _ in range(1000):
            got = cache.get(key)
            self.assertEqual(got["matched_count"], 2000)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        # Immutable no-copy gets should be sub-ms each even for large payloads.
        self.assertLess(elapsed_ms, 100.0, f"cache get loop too slow: {elapsed_ms:.1f}ms")



if __name__ == "__main__":
    unittest.main()
