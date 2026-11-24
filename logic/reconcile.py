"""
Governed reconciliation workflow.

Matches transactions from two sources on amount + date + reference,
with a configurable amount tolerance. Pure function — no LLM math.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence, Union

from .common import (
    find_column,
    make_lineage,
    parse_amount,
    parse_date,
    round_money,
)

WORKFLOW_NAME = "reconcile_transactions"
WORKFLOW_VERSION = "1.0.0"

TransactionLike = Mapping[str, Any]
SourceInput = Union[Sequence[TransactionLike], str, Path]

_AMOUNT_KEYS = ("amount", "Amount", "amt", "value")
_DATE_KEYS = ("date", "Date", "txn_date", "transaction_date")
_REF_KEYS = ("reference", "Reference", "ref", "check_number", "id")


def _normalize_transaction(raw: Mapping[str, Any], *, source: str, index: int) -> dict[str, Any]:
    amount_key = find_column(raw, _AMOUNT_KEYS)
    date_key = find_column(raw, _DATE_KEYS)
    ref_key = find_column(raw, _REF_KEYS)
    if amount_key is None or date_key is None or ref_key is None:
        raise ValueError(
            f"Transaction missing required fields (amount/date/reference): {dict(raw)}"
        )
    return {
        "source": source,
        "index": index,
        "amount": parse_amount(raw[amount_key]),
        "date": parse_date(raw[date_key]).isoformat(),
        "reference": str(raw[ref_key]).strip().upper(),
        "description": str(raw.get("description") or raw.get("Description") or ""),
        "raw": dict(raw),
    }


def _load_transactions(source: SourceInput, *, label: str) -> list[dict[str, Any]]:
    if isinstance(source, (str, Path)):
        path = Path(source)
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        return [_normalize_transaction(row, source=label, index=i) for i, row in enumerate(rows)]

    return [
        _normalize_transaction(row, source=label, index=i) for i, row in enumerate(source)
    ]


def _amounts_match(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= tolerance


def _match_key(txn: Mapping[str, Any]) -> tuple[str, str]:
    return (str(txn["date"]), str(txn["reference"]))


def reconcile_transactions(
    left: SourceInput,
    right: SourceInput,
    *,
    amount_tolerance: float = 0.01,
    left_label: str = "bank",
    right_label: str = "ledger",
) -> dict[str, Any]:
    """
    Reconcile two transaction sets.

    Matching rules (all must hold):
      - same calendar date
      - same reference (case-insensitive)
      - amounts within ``amount_tolerance``

    Returns a structured summary including lineage metadata.
    """
    left_txns = _load_transactions(left, label=left_label)
    right_txns = _load_transactions(right, label=right_label)

    # Index right-side rows by (date, reference) for O(n+m) matching while
    # preserving original first-available semantics via ascending indices.
    buckets: dict[tuple[str, str], list[int]] = defaultdict(list)
    for i, txn in enumerate(right_txns):
        buckets[_match_key(txn)].append(i)

    used = [False] * len(right_txns)
    matched: list[dict[str, Any]] = []
    unmatched_left: list[dict[str, Any]] = []

    for left_txn in left_txns:
        match_idx = None
        for i in buckets.get(_match_key(left_txn), []):
            if used[i]:
                continue
            if _amounts_match(left_txn["amount"], right_txns[i]["amount"], amount_tolerance):
                match_idx = i
                break

        if match_idx is None:
            unmatched_left.append(left_txn)
            continue

        used[match_idx] = True
        right_txn = right_txns[match_idx]
        matched.append(
            {
                "left": left_txn,
                "right": right_txn,
                "amount_variance": round_money(left_txn["amount"] - right_txn["amount"]),
            }
        )

    unmatched_right = [txn for i, txn in enumerate(right_txns) if not used[i]]

    matched_left_total = sum(m["left"]["amount"] for m in matched)
    matched_right_total = sum(m["right"]["amount"] for m in matched)
    unmatched_left_total = sum(t["amount"] for t in unmatched_left)
    unmatched_right_total = sum(t["amount"] for t in unmatched_right)
    total_variance = round_money(
        (matched_left_total + unmatched_left_total)
        - (matched_right_total + unmatched_right_total)
    )

    return {
        "matched_count": len(matched),
        "unmatched_left_count": len(unmatched_left),
        "unmatched_right_count": len(unmatched_right),
        "matched": matched,
        "unmatched_left": unmatched_left,
        "unmatched_right": unmatched_right,
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
                "left_source": (
                    str(left) if isinstance(left, (str, Path)) else f"inline[{len(left_txns)}]"
                ),
                "right_source": (
                    str(right) if isinstance(right, (str, Path)) else f"inline[{len(right_txns)}]"
                ),
            },
        ),
    }
