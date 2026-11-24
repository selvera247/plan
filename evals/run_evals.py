"""
Simple evaluation harness for the governed finance assistant.

Scores:
  1. Correct tool called
  2. Numerical accuracy (within tolerance) against golden expected_values
  3. Whether lineage was surfaced in the tool result and/or assistant reply

Modes:
  --logic-only   Skip the LLM; run expected tools deterministically (CI-friendly)
  (default)      Call the OpenAI assistant for each golden question

Usage:
  python evals/run_evals.py --logic-only
  OPENAI_API_KEY=... python evals/run_evals.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from tools.openai_tools import clear_tool_call_log, execute_tool

load_dotenv(ROOT / ".env")

GOLDEN_PATH = Path(__file__).with_name("golden.json")
DEFAULT_TOLERANCE = 0.01


def _dig(obj: dict[str, Any], dotted: str) -> Any:
    cur: Any = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _near(actual: Any, expected: Any, tol: float) -> bool:
    if expected is None:
        return actual is None
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return abs(float(actual) - float(expected)) <= tol
    return actual == expected


def _default_tool_args(tool_name: str, case: dict[str, Any]) -> dict[str, Any]:
    """Deterministic args for logic-only mode based on the golden case."""
    if tool_name == "reconcile_transactions":
        args: dict[str, Any] = {
            "left_source": "sample_bank",
            "right_source": "sample_ledger",
        }
        # Heuristic: cases that mention tolerance 1.00
        if "1.00" in case.get("question", "") or "tolerance 1" in case.get("question", "").lower():
            args["amount_tolerance"] = 1.0
        return args
    if tool_name == "analyze_variance":
        return {
            "actuals_source": "sample_actuals",
            "budget_source": "sample_budget",
        }
    raise ValueError(f"No default args for tool {tool_name}")


def score_result(
    case: dict[str, Any],
    *,
    tool_name: str | None,
    result: dict[str, Any] | None,
    reply: str = "",
    tol: float = DEFAULT_TOLERANCE,
) -> dict[str, Any]:
    expected_tool = case["expected_tool"]
    tool_ok = tool_name == expected_tool

    numeric_checks: list[dict[str, Any]] = []
    numeric_ok = True
    if result and "error" not in result:
        for key, expected in case.get("expected_values", {}).items():
            actual = _dig(result, key)
            ok = _near(actual, expected, tol)
            numeric_checks.append(
                {"field": key, "expected": expected, "actual": actual, "ok": ok}
            )
            numeric_ok = numeric_ok and ok

        expected_item = case.get("expected_item")
        if expected_item:
            account = expected_item["account"]
            items = result.get("items") or []
            match = next((i for i in items if i.get("account") == account), None)
            if match is None:
                numeric_ok = False
                numeric_checks.append(
                    {
                        "field": f"item[{account}]",
                        "expected": expected_item,
                        "actual": None,
                        "ok": False,
                    }
                )
            else:
                for field, expected in expected_item.items():
                    if field == "account":
                        continue
                    actual = match.get(field)
                    ok = _near(actual, expected, tol)
                    numeric_checks.append(
                        {
                            "field": f"item[{account}].{field}",
                            "expected": expected,
                            "actual": actual,
                            "ok": ok,
                        }
                    )
                    numeric_ok = numeric_ok and ok
    else:
        numeric_ok = False
        if case.get("expected_values") or case.get("expected_item"):
            numeric_checks.append(
                {
                    "field": "*",
                    "expected": "result",
                    "actual": result,
                    "ok": False,
                }
            )

    lineage = (result or {}).get("lineage") if result else None
    lineage_in_result = bool(lineage and lineage.get("workflow") and lineage.get("version"))
    lineage_in_reply = False
    if reply and lineage:
        version = str(lineage.get("version", ""))
        workflow = str(lineage.get("workflow", ""))
        reply_l = reply.lower()
        lineage_in_reply = version in reply or workflow.lower() in reply_l or "v1.0.0" in reply_l

    lineage_ok = True
    if case.get("require_lineage", True):
        # Logic-only mode has no reply; require lineage on the result.
        lineage_ok = lineage_in_result and (lineage_in_reply or reply == "")

    passed = tool_ok and numeric_ok and lineage_ok
    return {
        "id": case["id"],
        "passed": passed,
        "tool_ok": tool_ok,
        "numeric_ok": numeric_ok,
        "lineage_ok": lineage_ok,
        "expected_tool": expected_tool,
        "actual_tool": tool_name,
        "numeric_checks": numeric_checks,
        "lineage": lineage,
        "lineage_in_result": lineage_in_result,
        "lineage_in_reply": lineage_in_reply,
    }


def run_logic_only(cases: list[dict[str, Any]], tol: float) -> list[dict[str, Any]]:
    scores = []
    for case in cases:
        clear_tool_call_log()
        tool = case["expected_tool"]
        args = _default_tool_args(tool, case)
        result = execute_tool(tool, args)
        scores.append(
            score_result(case, tool_name=tool, result=result, reply="", tol=tol)
        )
    return scores


def run_with_assistant(cases: list[dict[str, Any]], tol: float) -> list[dict[str, Any]]:
    from assistant.agent import FinanceAssistant

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required unless you pass --logic-only")

    assistant = FinanceAssistant()
    scores = []
    for case in cases:
        clear_tool_call_log()
        assistant.reset()
        outcome = assistant.ask(case["question"])
        tool_calls = outcome.get("tool_calls") or []
        tool_name = tool_calls[0]["name"] if tool_calls else None
        result = tool_calls[0]["result"] if tool_calls else None
        # If multiple tools, prefer the expected one if present.
        for tc in tool_calls:
            if tc["name"] == case["expected_tool"]:
                tool_name = tc["name"]
                result = tc["result"]
                break
        score = score_result(
            case,
            tool_name=tool_name,
            result=result,
            reply=outcome.get("reply") or "",
            tol=tol,
        )
        score["reply_preview"] = (outcome.get("reply") or "")[:240]
        scores.append(score)
        status = "PASS" if score["passed"] else "FAIL"
        print(f"[{status}] {case['id']}: tool={tool_name} lineage_reply={score['lineage_in_reply']}")
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description="Run governed finance evals")
    parser.add_argument(
        "--logic-only",
        action="store_true",
        help="Evaluate deterministic workflows only (no OpenAI calls)",
    )
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "logs" / "eval_results.json",
        help="Where to write JSON results",
    )
    args = parser.parse_args()

    cases = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(cases)} golden cases from {GOLDEN_PATH}")

    if args.logic_only:
        scores = run_logic_only(cases, args.tolerance)
    else:
        scores = run_with_assistant(cases, args.tolerance)

    passed = sum(1 for s in scores if s["passed"])
    total = len(scores)
    summary = {
        "mode": "logic-only" if args.logic_only else "assistant",
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "cases": scores,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print("\n=== EVAL SUMMARY ===")
    print(f"Mode: {summary['mode']}")
    print(f"Passed: {passed}/{total} ({summary['pass_rate'] * 100:.1f}%)")
    for s in scores:
        mark = "✓" if s["passed"] else "✗"
        print(
            f"  {mark} {s['id']}: tool_ok={s['tool_ok']} "
            f"numeric_ok={s['numeric_ok']} lineage_ok={s['lineage_ok']}"
        )
    print(f"\nWrote {args.output}")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
