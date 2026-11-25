"""Regression tests for production edge cases found in debugging."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from logic.common import parse_amount
from logic.reconcile import reconcile_transactions
from logic.variance import analyze_variance
from tools.openai_tools import clear_tool_call_log, execute_tool


class EdgeCaseTests(unittest.TestCase):
    def test_null_optional_tolerance_uses_default(self) -> None:
        clear_tool_call_log()
        result = execute_tool(
            "reconcile_transactions",
            {
                "left_source": "sample_bank",
                "right_source": "sample_ledger",
                "amount_tolerance": None,
            },
        )
        self.assertNotIn("error", result)
        self.assertEqual(result["matched_count"], 5)
        self.assertEqual(result["lineage"]["inputs_used"]["amount_tolerance"], 0.01)

    def test_null_threshold_pct_uses_default(self) -> None:
        clear_tool_call_log()
        result = execute_tool(
            "analyze_variance",
            {
                "actuals_source": "sample_actuals",
                "budget_source": "sample_budget",
                "threshold_pct": None,
            },
        )
        self.assertNotIn("error", result)
        self.assertEqual(result["flagged_count"], 6)

    def test_malformed_json_args_do_not_crash(self) -> None:
        clear_tool_call_log()
        result = execute_tool("reconcile_transactions", "{not-json")
        self.assertIn("error", result)
        self.assertIn("Invalid tool arguments JSON", result["error"])

    def test_utf8_bom_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bom.csv"
            path.write_bytes(b"\xef\xbb\xbfaccount,amount\nSales,100\n")
            result = analyze_variance(path, {"Sales": 90})
            self.assertEqual(result["item_count"], 1)
            self.assertEqual(result["items"][0]["absolute_variance"], 10.0)

    def test_accounting_parentheses_amount(self) -> None:
        self.assertEqual(parse_amount("(1,250.00)"), -1250.0)
        self.assertEqual(parse_amount("$1,250.50"), 1250.5)

    def test_negative_tolerance_rejected(self) -> None:
        with self.assertRaises(ValueError):
            reconcile_transactions(
                [{"date": "2024-01-01", "amount": 10, "reference": "A"}],
                [{"date": "2024-01-01", "amount": 10, "reference": "A"}],
                amount_tolerance=-0.01,
            )

    def test_negative_threshold_rejected(self) -> None:
        with self.assertRaises(ValueError):
            analyze_variance({"A": 100}, {"A": 100}, threshold_pct=-1)

    def test_float_precision_zero_tolerance_match(self) -> None:
        result = reconcile_transactions(
            [{"date": "2024-01-01", "amount": 0.1 + 0.2, "reference": "X"}],
            [{"date": "2024-01-01", "amount": 0.3, "reference": "X"}],
            amount_tolerance=0.0,
        )
        self.assertEqual(result["matched_count"], 1)

    def test_empty_source_is_clear_error(self) -> None:
        clear_tool_call_log()
        result = execute_tool(
            "analyze_variance",
            {"actuals_source": "", "budget_source": "sample_budget"},
        )
        self.assertIn("error", result)
        self.assertIn("Empty data source", result["error"])

    def test_missing_file_lists_aliases(self) -> None:
        clear_tool_call_log()
        result = execute_tool(
            "reconcile_transactions",
            {"left_source": "nope.csv", "right_source": "sample_ledger"},
        )
        self.assertIn("error", result)
        self.assertIn("sample_bank", result["error"])

    def test_sample_parity_unchanged(self) -> None:
        clear_tool_call_log()
        recon = execute_tool(
            "reconcile_transactions",
            {"left_source": "sample_bank", "right_source": "sample_ledger"},
        )
        var = execute_tool(
            "analyze_variance",
            {"actuals_source": "sample_actuals", "budget_source": "sample_budget"},
        )
        self.assertEqual(recon["matched_count"], 5)
        self.assertEqual(recon["totals"]["total_variance"], 250.75)
        self.assertEqual(var["flagged_count"], 6)
        self.assertEqual(var["totals"]["absolute_variance"], 9550.0)
        self.assertEqual(recon["lineage"]["version"], "1.0.2")
        self.assertEqual(var["lineage"]["version"], "1.0.2")


if __name__ == "__main__":
    unittest.main()
