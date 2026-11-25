"""
Governed reconciliation workflow.

Matches transactions from two sources on amount + date + reference,
with a configurable amount tolerance. Pure function — no LLM math.
"""

from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Mapping, Sequence, Union

from .common import (
    amounts_within_tolerance,
    make_lineage,
    parse_amount,
    parse_date,
    read_csv_rows,
    require_non_negative,
    resolve_columns,
    round_money,
)

WORKFLOW_NAME = "reconcile_transactions"
WORKFLOW_VERSION = "1.0.2"

TransactionLike = Mapping[str, Any]
SourceInput = Union[Sequence[TransactionLike], str, Path]

_COLUMN_GROUPS = {
    "amount": ("amount", "Amount", "amt", "value"),
    "date": ("date", "Date", "txn_date", "transaction_date"),
    "reference": ("reference", "Reference", "ref", "check_number", "id"),
}


def _normalize_transaction(
    row: Mapping[str, Any],
    *,
    source: str,
    index: int,
    cols: Mapping[str, str],
) -> dict[str, Any]:
    return {
        "source": source,
        "index": index,
        "amount": parse_amount(row[cols["amount"]]),
        "date": parse_date(row[cols["date"]]).isoformat(),
        "reference": str(row[cols["reference"]]).strip().upper(),
        "description": str(row.get("description") or row.get("Description") or ""),
    }


def _load_transactions(source: SourceInput, *, label: str) -> list[dict[str, Any]]:
    if isinstance(source, (str, Path)):
        rows = read_csv_rows(source)
    else:
        rows = list(source)

    if not rows:
        return []

    cols = resolve_columns(rows[0], _COLUMN_GROUPS)
    return [
        _normalize_transaction(row, source=label, index=i, cols=cols)
        for i, row in enumerate(rows)
    ]


def _match_key(txn: Mapping[str, Any]) -> tuple[str, str]:
    return (txn["date"], txn["reference"])


def reconcile_transactions(
    left: SourceInput,
    right: SourceInput,
    *,
    amount_tolerance: float = 0.01,
    left_label: str = "bank",
    right_label: str = "ledger",
    include_details: bool = True,
) -> dict[str, Any]:
    """
    Reconcile two transaction sets.

    Matching rules (all must hold):
      - same calendar date
      - same reference (case-insensitive)
      - amounts within ``amount_tolerance``

    Set ``include_details=False`` to return counts/totals/lineage only (lower
    memory and faster JSON serialization for large datasets).
    """
    amount_tolerance = require_non_negative("amount_tolerance", float(amount_tolerance))

    left_txns = _load_transactions(left, label=left_label)
    right_txns = _load_transactions(right, label=right_label)

    # deque per key so matched right rows are O(1) to consume.
    buckets: dict[tuple[str, str], deque[int]] = defaultdict(deque)
    for i, txn in enumerate(right_txns):
        buckets[_match_key(txn)].append(i)

    matched: list[dict[str, Any]] = []
    unmatched_left: list[dict[str, Any]] = []
    matched_left_total = 0.0
    matched_right_total = 0.0
    unmatched_left_total = 0.0

    for left_txn in left_txns:
        bucket = buckets.get(_match_key(left_txn))
        match_idx = None
        if bucket:
            # Scan without removing until amount matches; rotate non-matches back.
            n = len(bucket)
            for _ in range(n):
                i = bucket.popleft()
                if amounts_within_tolerance(
                    left_txn["amount"], right_txns[i]["amount"], amount_tolerance
                ):
                    match_idx = i
                    break
                bucket.append(i)

        if match_idx is None:
            unmatched_left.append(left_txn)
            unmatched_left_total += left_txn["amount"]
            continue

        right_txn = right_txns[match_idx]
        matched_left_total += left_txn["amount"]
        matched_right_total += right_txn["amount"]
        if include_details:
            matched.append(
                {
                    "left": left_txn,
                    "right": right_txn,
                    "amount_variance": round_money(
                        left_txn["amount"] - right_txn["amount"]
                    ),
                }
            )

    unmatched_right: list[dict[str, Any]] = []
    unmatched_right_total = 0.0
    unmatched_right_count = 0
    for bucket in buckets.values():
        for i in bucket:
            txn = right_txns[i]
            unmatched_right_count += 1
            unmatched_right_total += txn["amount"]
            if include_details:
                unmatched_right.append(txn)

    # Preserve original right-side order for unmatched details.
    if include_details and unmatched_right:
        unmatched_right.sort(key=lambda t: t["index"])

    total_variance = round_money(
        (matched_left_total + unmatched_left_total)
        - (matched_right_total + unmatched_right_total)
    )

    matched_count = len(left_txns) - len(unmatched_left)

    result: dict[str, Any] = {
        "matched_count": matched_count,
        "unmatched_left_count": len(unmatched_left),
        "unmatched_right_count": unmatched_right_count,
        "totals": {
            "matched_left": round_money(matched_left_total),
            "matched_right": round_money(matched_right_total),
            "unmatched_left": round_money(unmatched_left_total),
            "unmatched_right": round_money(unmatched_right_total),
            "total_variance": total_variance,
        },
        "lineage": make_lineage(
            WORKFLOW_NAME,
            WORKFLOW_VERSION,
            {
                "left_label": left_label,
                "right_label": right_label,
                "left_count": len(left_txns),
                "right_count": len(right_txns),
                "amount_tolerance": amount_tolerance,
                "include_details": include_details,
                "left_source": (
                    str(left) if isinstance(left, (str, Path)) else f"inline[{len(left_txns)}]"
                ),
                "right_source": (
                    str(right) if isinstance(right, (str, Path)) else f"inline[{len(right_txns)}]"
                ),
            },
        ),
    }
    if include_details:
        result["matched"] = matched
        result["unmatched_left"] = unmatched_left
        result["unmatched_right"] = unmatched_right
    return result
