"""
Evaluation harness for the governed finance assistant.

Scores:
  1. Correct tool called
  2. Numerical accuracy (within tolerance) against golden expected_values
  3. Whether lineage was surfaced in the tool result and/or assistant reply

Modes:
  --logic-only   Skip the LLM; run tool_args from each golden case
  (default)      Call the OpenAI assistant for each golden question

Usage:
  python3 evals/run_evals.py --logic-only
  OPENAI_API_KEY=... python3 evals/run_evals.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Bootstrap before local imports when run as a script.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

from evals.scoring import score_result
from project_paths import ENV_FILE, LOG_DIR
from tools.openai_tools import clear_tool_call_log, execute_tool

load_dotenv(ENV_FILE)

GOLDEN_PATH = Path(__file__).with_name("golden.json")
DEFAULT_TOLERANCE = 0.01


def run_logic_only(cases: list[dict[str, Any]], tol: float) -> list[dict[str, Any]]:
    scores = []
    for case in cases:
        clear_tool_call_log()
        tool = case["expected_tool"]
        args = case.get("tool_args")
        if not args:
            raise SystemExit(
                f"Golden case {case['id']} missing tool_args (required for --logic-only)"
            )
        result = execute_tool(tool, args)
        scores.append(
            score_result(case, tool_name=tool, result=result, reply="", tol=tol)
        )
    return scores


def _select_scored_call(
    tool_calls: list[dict[str, Any]], expected_tool: str
) -> tuple[str | None, dict[str, Any] | None]:
    if not tool_calls:
        return None, None
    for tc in tool_calls:
        if tc["name"] == expected_tool:
            return tc["name"], tc["result"]
    first = tool_calls[0]
    return first["name"], first["result"]


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
        tool_name, result = _select_scored_call(
            outcome.get("tool_calls") or [], case["expected_tool"]
        )
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
        print(
            f"[{status}] {case['id']}: tool={tool_name} "
            f"lineage_reply={score['lineage_in_reply']}"
        )
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
        default=LOG_DIR / "eval_results.json",
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
