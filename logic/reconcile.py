"""
Governed reconciliation workflow.

Matches transactions from two sources on amount + date + reference,
with a configurable amount tolerance. Pure function — no LLM math.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence, Union

WORKFLOW_NAME = "reconcile_transactions"
WORKFLOW_VERSION = "1.0.0"

TransactionLike = Mapping[str, Any]
SourceInput = Union[Sequence[TransactionLike], str, Path]


@dataclass(frozen=True)
class Lineage:
    workflow: str
    version: str
    inputs_used: dict[str, Any]


def _parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {value!r}")


def _parse_amount(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("$", "")
    return float(text)


def _normalize_transaction(raw: Mapping[str, Any], *, source: str, index: int) -> dict[str, Any]:
    # Accept common column aliases from bank/GL exports.
    amount_key = next(
        (k for k in ("amount", "Amount", "amt", "value") if k in raw),
        None,
    )
    date_key = next(
        (k for k in ("date", "Date", "txn_date", "transaction_date") if k in raw),
        None,
    )
    ref_key = next(
        (k for k in ("reference", "Reference", "ref", "check_number", "id") if k in raw),
        None,
    )
    if amount_key is None or date_key is None or ref_key is None:
        raise ValueError(
            f"Transaction missing required fields (amount/date/reference): {dict(raw)}"
        )
    return {
        "source": source,
        "index": index,
        "amount": _parse_amount(raw[amount_key]),
        "date": _parse_date(raw[date_key]).isoformat(),
        "reference": str(raw[ref_key]).strip().upper(),
        "description": str(raw.get("description") or raw.get("Description") or ""),
        "raw": dict(raw),
    }


def _load_transactions(source: SourceInput, *, label: str) -> list[dict[str, Any]]:
    if isinstance(source, (str, Path)):
        path = Path(source)
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        return [_normalize_transaction(row, source=label, index=i) for i, row in enumerate(rows)]

    return [
        _normalize_transaction(row, source=label, index=i) for i, row in enumerate(source)
    ]


def _amounts_match(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= tolerance


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

    matched: list[dict[str, Any]] = []
    unmatched_left: list[dict[str, Any]] = []
    unmatched_right: list[dict[str, Any]] = []

    right_available = list(right_txns)

    for left_txn in left_txns:
        match_idx = None
        for i, right_txn in enumerate(right_available):
            if (
                left_txn["date"] == right_txn["date"]
                and left_txn["reference"] == right_txn["reference"]
                and _amounts_match(left_txn["amount"], right_txn["amount"], amount_tolerance)
            ):
                match_idx = i
                break

        if match_idx is None:
            unmatched_left.append(left_txn)
            continue

        right_txn = right_available.pop(match_idx)
        variance = round(left_txn["amount"] - right_txn["amount"], 6)
        matched.append(
            {
                "left": left_txn,
                "right": right_txn,
                "amount_variance": variance,
            }
        )

    unmatched_right.extend(right_available)

    matched_left_total = sum(m["left"]["amount"] for m in matched)
    matched_right_total = sum(m["right"]["amount"] for m in matched)
    unmatched_left_total = sum(t["amount"] for t in unmatched_left)
    unmatched_right_total = sum(t["amount"] for t in unmatched_right)
    total_variance = round(
        (matched_left_total + unmatched_left_total)
        - (matched_right_total + unmatched_right_total),
        6,
    )

    lineage = Lineage(
        workflow=WORKFLOW_NAME,
        version=WORKFLOW_VERSION,
        inputs_used={
            "left_label": left_label,
            "right_label": right_label,
            "left_count": len(left_txns),
            "right_count": len(right_txns),
            "amount_tolerance": amount_tolerance,
            "left_source": str(left) if isinstance(left, (str, Path)) else f"inline[{len(left_txns)}]",
            "right_source": str(right) if isinstance(right, (str, Path)) else f"inline[{len(right_txns)}]",
        },
    )

    return {
        "matched_count": len(matched),
        "unmatched_left_count": len(unmatched_left),
        "unmatched_right_count": len(unmatched_right),
        "matched": matched,
        "unmatched_left": unmatched_left,
        "unmatched_right": unmatched_right,
        "totals": {
            "matched_left": round(matched_left_total, 6),
            "matched_right": round(matched_right_total, 6),
            "unmatched_left": round(unmatched_left_total, 6),
            "unmatched_right": round(unmatched_right_total, 6),
            "total_variance": total_variance,
        },
        "lineage": asdict(lineage),
    }
