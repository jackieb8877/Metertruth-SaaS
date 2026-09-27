"""Small shared helpers for deterministic decimal money and quantity math."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

CENT = Decimal("0.01")
ZERO = Decimal("0")


def to_decimal(value: Any) -> Decimal | None:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return number if number.is_finite() else None


def required_decimal(value: Any, label: str) -> Decimal:
    number = to_decimal(value)
    if number is None:
        raise ValueError(f"{label} must be a finite number")
    return number


def rounded_money(value: Any) -> Decimal:
    return required_decimal(value, "Money amount").quantize(CENT, rounding=ROUND_HALF_UP)


def round_money(value: Any) -> float:
    """Return JSON-compatible euros after conventional half-up cent rounding."""
    return float(rounded_money(value))
