"""
Governed variance analysis workflow.

Compares actuals vs budget by account/category, flags items above a
threshold. Pure function — no LLM math.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Union

WORKFLOW_NAME = "analyze_variance"
WORKFLOW_VERSION = "1.0.0"

AmountMap = Mapping[str, Any]
SourceInput = Union[AmountMap, str, Path]


@dataclass(frozen=True)
class Lineage:
    workflow: str
    version: str
    inputs_used: dict[str, Any]


def _to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("$", "")
    if text == "":
        return 0.0
    return float(text)


def _load_amount_map(source: SourceInput) -> dict[str, float]:
    """
    Load account/category -> amount mapping.

    Accepts:
      - dict of {account: amount}
      - CSV path with columns account/category + amount (or actual/budget)
    """
    if isinstance(source, Mapping):
        return {str(k): _to_float(v) for k, v in source.items()}

    path = Path(source)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    if not rows:
        return {}

    account_key = next(
        (
            k
            for k in ("account", "Account", "category", "Category", "name", "Name")
            if k in rows[0]
        ),
        None,
    )
    amount_key = next(
        (
            k
            for k in ("amount", "Amount", "actual", "Actual", "budget", "Budget", "value")
            if k in rows[0]
        ),
        None,
    )
    if account_key is None or amount_key is None:
        raise ValueError(
            "CSV must include an account/category column and an amount column "
            f"(found columns: {list(rows[0].keys())})"
        )

    result: dict[str, float] = {}
    for row in rows:
        account = str(row[account_key]).strip()
        if not account:
            continue
        result[account] = result.get(account, 0.0) + _to_float(row[amount_key])
    return result


def analyze_variance(
    actuals: SourceInput,
    budget: SourceInput,
    *,
    threshold_pct: float = 5.0,
    threshold_abs: float | None = None,
) -> dict[str, Any]:
    """
    Compute absolute and percent variance by account/category.

    An item is flagged when |% variance| >= ``threshold_pct``, or when
    ``threshold_abs`` is set and |absolute variance| >= that value.
    """
    actual_map = _load_amount_map(actuals)
    budget_map = _load_amount_map(budget)
    accounts = sorted(set(actual_map) | set(budget_map))

    items: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []
    total_actual = 0.0
    total_budget = 0.0

    for account in accounts:
        actual = round(actual_map.get(account, 0.0), 6)
        budget_amt = round(budget_map.get(account, 0.0), 6)
        abs_var = round(actual - budget_amt, 6)
        if budget_amt == 0:
            pct_var = None if actual == 0 else (100.0 if actual > 0 else -100.0)
        else:
            pct_var = round((abs_var / budget_amt) * 100.0, 4)

        is_flagged = False
        if pct_var is not None and abs(pct_var) >= threshold_pct:
            is_flagged = True
        if threshold_abs is not None and abs(abs_var) >= threshold_abs:
            is_flagged = True

        row = {
            "account": account,
            "actual": actual,
            "budget": budget_amt,
            "absolute_variance": abs_var,
            "percent_variance": pct_var,
            "flagged": is_flagged,
        }
        items.append(row)
        if is_flagged:
            flagged.append(row)

        total_actual += actual
        total_budget += budget_amt

    total_abs = round(total_actual - total_budget, 6)
    total_pct = (
        None
        if total_budget == 0
        else round((total_abs / total_budget) * 100.0, 4)
    )

    lineage = Lineage(
        workflow=WORKFLOW_NAME,
        version=WORKFLOW_VERSION,
        inputs_used={
            "account_count": len(accounts),
            "threshold_pct": threshold_pct,
            "threshold_abs": threshold_abs,
            "actuals_source": (
                str(actuals) if isinstance(actuals, (str, Path)) else f"inline[{len(actual_map)}]"
            ),
            "budget_source": (
                str(budget) if isinstance(budget, (str, Path)) else f"inline[{len(budget_map)}]"
            ),
        },
    )

    return {
        "item_count": len(items),
        "flagged_count": len(flagged),
        "items": items,
        "flagged": flagged,
        "totals": {
            "actual": round(total_actual, 6),
            "budget": round(total_budget, 6),
            "absolute_variance": total_abs,
            "percent_variance": total_pct,
        },
        "lineage": asdict(lineage),
    }
