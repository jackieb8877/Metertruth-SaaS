"""Stripe aggregate reconciliation bridge for MeterTruth.

Stripe exposes read-only meter event summaries by meter/customer/time window. This
module compares independently aggregated raw product usage with those official
summaries. It complements (not replaces) event-level reconciliation from mirrored
meter-event receipts/logs.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable

from money import ZERO, required_decimal, round_money, rounded_money


def _ts(v: Any) -> datetime:
    if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
        return datetime.fromtimestamp(int(v), tz=timezone.utc)
    s = str(v).replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _epoch(dt: datetime) -> int:
    return int(dt.timestamp())


def bucket_start(dt: datetime, grouping: str) -> datetime:
    dt = dt.astimezone(timezone.utc)
    if grouping == "hour":
        return dt.replace(minute=0, second=0, microsecond=0)
    if grouping == "day":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    raise ValueError("grouping must be 'hour' or 'day'")


def aggregate_raw_usage(rows: Iterable[dict[str, Any]], *, grouping: str = "hour") -> dict[tuple[str, str, int], Decimal]:
    """Aggregate normalized raw usage rows by customer, metric and UTC bucket.

    Required normalized keys: customer_id, metric, timestamp, quantity.
    """
    out: dict[tuple[str, str, int], Decimal] = defaultdict(lambda: ZERO)
    for row in rows:
        customer = str(row["customer_id"])
        metric = str(row.get("metric") or "default")
        start = bucket_start(_ts(row["timestamp"]), grouping)
        out[(customer, metric, _epoch(start))] += required_decimal(row["quantity"], "Raw quantity")
    return dict(out)


def normalize_stripe_summaries(records: Iterable[dict[str, Any]], *, meter_to_metric: dict[str, str]) -> dict[tuple[str, str, int], Decimal]:
    """Normalize Stripe meter-event-summary records.

    `records` must add `customer_id` because Stripe's summary response is scoped by
    the customer request and the returned object itself doesn't carry customer.
    Expected Stripe fields: meter, start_time, aggregated_value.
    """
    out: dict[tuple[str, str, int], Decimal] = defaultdict(lambda: ZERO)
    for row in records:
        meter = str(row["meter"])
        if meter not in meter_to_metric:
            raise ValueError(f"No metric mapping configured for Stripe meter {meter}")
        key = (str(row["customer_id"]), meter_to_metric[meter], _epoch(_ts(row["start_time"])))
        out[key] += required_decimal(row["aggregated_value"], "Stripe aggregated value")
    return dict(out)


def reconcile_stripe_summaries(raw_rows: Iterable[dict[str, Any]], stripe_records: Iterable[dict[str, Any]], *,
                               meter_to_metric: dict[str, str], grouping: str = "hour",
                               tolerance: Any = 0.0, unit_prices: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = aggregate_raw_usage(raw_rows, grouping=grouping)
    observed = normalize_stripe_summaries(stripe_records, meter_to_metric=meter_to_metric)
    prices = unit_prices or {}
    findings = []
    keys = sorted(set(raw) | set(observed))
    under = over = ZERO
    tolerance_amount = required_decimal(tolerance, "Usage tolerance")
    if tolerance_amount < 0:
        raise ValueError("Usage tolerance must be non-negative")
    for customer, metric, start in keys:
        expected = raw.get((customer, metric, start), ZERO)
        actual = observed.get((customer, metric, start), ZERO)
        delta = expected - actual
        if abs(delta) <= tolerance_amount:
            continue
        unit_price = required_decimal(prices.get(metric, 0.0), "Unit price")
        if unit_price < 0:
            raise ValueError("Unit price must be non-negative")
        impact = delta * unit_price
        rounded_impact = rounded_money(impact)
        if impact > 0:
            under += rounded_impact
        elif impact < 0:
            over += -rounded_impact
        findings.append({
            "customer_id": customer,
            "metric": metric,
            "bucket_start": start,
            "expected_usage": float(expected),
            "stripe_usage": float(actual),
            "delta_usage": float(delta),
            "impact_eur": float(rounded_impact),
            "type": "AGGREGATE_UNDER" if delta > 0 else "AGGREGATE_OVER",
            "status": "CONFIRMED",
        })
    return {
        "mode": "stripe_meter_summary",
        "grouping": grouping,
        "summary": {
            "buckets_compared": len(keys),
            "findings": len(findings),
            "potential_underbilling_eur": round_money(under),
            "potential_overbilling_eur": round_money(over),
            "period_exposure_eur": round_money(under + over),
        },
        "findings": findings,
    }
