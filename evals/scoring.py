"""Scoring helpers for golden eval cases."""

from __future__ import annotations

from typing import Any


def dig(obj: dict[str, Any], dotted: str) -> Any:
    cur: Any = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def near(actual: Any, expected: Any, tol: float) -> bool:
    if expected is None:
        return actual is None
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return abs(float(actual) - float(expected)) <= tol
    return actual == expected


def lineage_mentioned_in_reply(reply: str, lineage: dict[str, Any] | None) -> bool:
    if not reply or not lineage:
        return False
    version = str(lineage.get("version", ""))
    workflow = str(lineage.get("workflow", ""))
    reply_l = reply.lower()
    return (
        (bool(version) and version in reply)
        or (bool(workflow) and workflow.lower() in reply_l)
        or (bool(version) and f"v{version}" in reply_l)
    )


def score_result(
    case: dict[str, Any],
    *,
    tool_name: str | None,
    result: dict[str, Any] | None,
    reply: str = "",
    tol: float = 0.01,
) -> dict[str, Any]:
    expected_tool = case["expected_tool"]
    tool_ok = tool_name == expected_tool

    numeric_checks: list[dict[str, Any]] = []
    numeric_ok = True
    if result and "error" not in result:
        for key, expected in case.get("expected_values", {}).items():
            actual = dig(result, key)
            ok = near(actual, expected, tol)
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
                    ok = near(actual, expected, tol)
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
    lineage_in_reply = lineage_mentioned_in_reply(reply, lineage)

    lineage_ok = True
    if case.get("require_lineage", True):
        # Logic-only mode has no reply; require lineage on the result.
        lineage_ok = lineage_in_result and (lineage_in_reply or reply == "")

    return {
        "id": case["id"],
        "passed": tool_ok and numeric_ok and lineage_ok,
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
