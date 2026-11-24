"""
Governed variance analysis workflow.

Compares actuals vs budget by account/category, flags items above a
threshold. Pure function — no LLM math.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Union

from .common import (
    find_column,
    make_lineage,
    parse_amount,
    read_csv_rows,
    require_non_negative,
    round_money,
)

WORKFLOW_NAME = "analyze_variance"
WORKFLOW_VERSION = "1.0.1"

AmountMap = Mapping[str, Any]
SourceInput = Union[AmountMap, str, Path]

_ACCOUNT_KEYS = ("account", "Account", "category", "Category", "name", "Name")
_AMOUNT_KEYS = ("amount", "Amount", "actual", "Actual", "budget", "Budget", "value")


def _load_amount_map(source: SourceInput) -> dict[str, float]:
    """
    Load account/category -> amount mapping.

    Accepts:
      - dict of {account: amount}
      - CSV path with columns account/category + amount (or actual/budget)
    """
    if isinstance(source, Mapping):
        return {str(k): parse_amount(v, empty_as_zero=True) for k, v in source.items()}

    rows = read_csv_rows(source)
    if not rows:
        return {}

    account_key = find_column(rows[0], _ACCOUNT_KEYS)
    amount_key = find_column(rows[0], _AMOUNT_KEYS)
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
        result[account] = result.get(account, 0.0) + parse_amount(
            row[amount_key], empty_as_zero=True
        )
    return result


def _percent_variance(actual: float, budget_amt: float) -> float | None:
    if budget_amt == 0:
        if actual == 0:
            return None
        return 100.0 if actual > 0 else -100.0
    return round((actual - budget_amt) / budget_amt * 100.0, 4)


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
    threshold_pct = require_non_negative("threshold_pct", float(threshold_pct))
    if threshold_abs is not None:
        threshold_abs = require_non_negative("threshold_abs", float(threshold_abs))

    actual_map = _load_amount_map(actuals)
    budget_map = _load_amount_map(budget)
    accounts = sorted(set(actual_map) | set(budget_map))

    items: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []
    total_actual = 0.0
    total_budget = 0.0

    for account in accounts:
        actual = round_money(actual_map.get(account, 0.0))
        budget_amt = round_money(budget_map.get(account, 0.0))
        abs_var = round_money(actual - budget_amt)
        pct_var = _percent_variance(actual, budget_amt)

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

    total_abs = round_money(total_actual - total_budget)
    total_pct = None if total_budget == 0 else round(total_abs / total_budget * 100.0, 4)

    return {
        "item_count": len(items),
        "flagged_count": len(flagged),
        "items": items,
        "flagged": flagged,
        "totals": {
            "actual": round_money(total_actual),
            "budget": round_money(total_budget),
            "absolute_variance": total_abs,
            "percent_variance": total_pct,
        },
        "lineage": make_lineage(
            WORKFLOW_NAME,
            WORKFLOW_VERSION,
            {
                "account_count": len(accounts),
                "threshold_pct": threshold_pct,
                "threshold_abs": threshold_abs,
                "actuals_source": (
                    str(actuals)
                    if isinstance(actuals, (str, Path))
                    else f"inline[{len(actual_map)}]"
                ),
                "budget_source": (
                    str(budget)
                    if isinstance(budget, (str, Path))
                    else f"inline[{len(budget_map)}]"
                ),
            },
        ),
    }
