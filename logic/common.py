"""Shared helpers for governed finance workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, Iterable, Mapping, Optional


@dataclass(frozen=True)
class Lineage:
    workflow: str
    version: str
    inputs_used: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_lineage(workflow: str, version: str, inputs_used: dict[str, Any]) -> dict[str, Any]:
    return Lineage(workflow=workflow, version=version, inputs_used=inputs_used).to_dict()


def parse_amount(value: Any, *, empty_as_zero: bool = False) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("$", "")
    if text == "":
        if empty_as_zero:
            return 0.0
        raise ValueError(f"Empty amount value: {value!r}")
    return float(text)


def parse_date(value: Any) -> date:
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


def find_column(row: Mapping[str, Any], candidates: Iterable[str]) -> Optional[str]:
    for key in candidates:
        if key in row:
            return key
    return None


def round_money(value: float, digits: int = 6) -> float:
    return round(value, digits)
