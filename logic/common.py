"""Shared helpers for governed finance workflows."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Union

MONEY_QUANTUM = Decimal("0.000001")


@dataclass(frozen=True)
class Lineage:
    workflow: str
    version: str
    inputs_used: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_lineage(workflow: str, version: str, inputs_used: dict[str, Any]) -> dict[str, Any]:
    return Lineage(workflow=workflow, version=version, inputs_used=inputs_used).to_dict()


def _clean_amount_text(value: Any) -> tuple[str, bool]:
    """Return (normalized numeric text, is_negative)."""
    text = str(value).strip().replace(",", "").replace("$", "").replace(" ", "")
    if text == "":
        return "", False

    negative = False
    if text.startswith("(") and text.endswith(")"):
        # Accounting notation: (1,250.00) => -1250.00
        negative = True
        text = text[1:-1].strip()
    if text.startswith("+"):
        text = text[1:]
    elif text.startswith("-"):
        negative = not negative
        text = text[1:]
    return text, negative


def parse_amount(value: Any, *, empty_as_zero: bool = False) -> float:
    """
    Parse a currency-like value to float.

    Accepts ints/floats, `$1,250.00`, `(1250.00)` accounting negatives, and blanks
    when ``empty_as_zero`` is true.
    """
    if isinstance(value, bool):
        raise ValueError(f"Invalid amount value: {value!r}")
    if isinstance(value, (int, float, Decimal)):
        return float(as_decimal(value))

    text, negative = _clean_amount_text(value)
    if text == "":
        if empty_as_zero:
            return 0.0
        raise ValueError(f"Empty amount value: {value!r}")
    try:
        amount = as_decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Could not parse amount: {value!r}") from exc
    if negative:
        amount = -amount
    return float(amount)


def as_decimal(value: Any) -> Decimal:
    """Quantize to money precision to avoid binary-float comparison traps."""
    if isinstance(value, Decimal):
        raw = value
    elif isinstance(value, bool):
        raise ValueError(f"Invalid numeric value: {value!r}")
    elif isinstance(value, int):
        raw = Decimal(value)
    elif isinstance(value, float):
        raw = Decimal(str(value))
    else:
        raw = Decimal(str(value).strip())
    return raw.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def amounts_within_tolerance(a: float, b: float, tolerance: float) -> bool:
    return abs(as_decimal(a) - as_decimal(b)) <= as_decimal(tolerance)


def parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {value!r}")


def normalize_header(key: Any) -> Any:
    if not isinstance(key, str):
        return key
    return key.lstrip("\ufeff").strip()


def normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {normalize_header(k): v for k, v in row.items()}


def find_column(row: Mapping[str, Any], candidates: Iterable[str]) -> Optional[str]:
    """Return the actual key in ``row`` matching one of ``candidates`` (BOM-/case-tolerant)."""
    normalized = normalize_row(row)
    # Map normalized header -> original key (best-effort).
    original_by_norm = {normalize_header(k): k for k in row.keys()}
    for key in candidates:
        if key in normalized:
            return original_by_norm.get(key, key)
    lower_map = {str(k).lower(): k for k in normalized}
    for key in candidates:
        found = lower_map.get(key.lower())
        if found is not None:
            return original_by_norm.get(found, found)
    return None


def read_csv_rows(path: Union[str, Path]) -> list[dict[str, Any]]:
    """Read a CSV with UTF-8 BOM tolerance and normalized headers."""
    file_path = Path(path)
    with file_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return [normalize_row(row) for row in reader]


def round_money(value: float, digits: int = 6) -> float:
    quantum = Decimal("1").scaleb(-digits)
    return float(as_decimal(value).quantize(quantum, rounding=ROUND_HALF_UP))


def require_non_negative(name: str, value: float) -> float:
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return value


def coerce_float(value: Any, *, default: float, name: str) -> float:
    """Coerce tool/LLM optional numerics; treat null/blank as default."""
    if value is None:
        return default
    if isinstance(value, str) and value.strip() == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {name}: {value!r}") from exc
