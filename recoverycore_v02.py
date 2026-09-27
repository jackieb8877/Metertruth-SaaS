#!/usr/bin/env python3
"""RecoveryCore v0.2

Independent reconciliation kernel for usage/billing and cross-system outcomes.
Input: raw/source CSV + observed/metered CSV + optional JSON config.
Output: deterministic JSON findings with evidence, confidence and non-overlapping impact.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ALIASES = {
    "event_id": ["event_id", "id", "usage_id", "request_id", "transaction_id", "event"],
    "idempotency_key": ["idempotency_key", "dedupe_key", "unique_key", "request_key"],
    "customer_id": ["customer_id", "customer", "account_id", "user_id", "workspace_id", "org_id"],
    "timestamp": ["timestamp", "created_at", "time", "occurred_at", "event_time", "date"],
    "quantity": ["quantity", "qty", "usage", "units", "amount", "count"],
    "metric": ["metric", "event_name", "type", "usage_type", "meter"],
}

DEFAULT_CONFIG = {
    "price_per_unit": 0.01,
    "late_hours": 24,
    "quantity_tolerance": 0.0,
    "currency": "EUR",
    "annualization_periods": 12,
    "pricing": {},
    "billing_period": None,
}

ACTIONS = {
    "MISSING": "Replay/rebill missing usage after human review",
    "DUPLICATE": "Reverse duplicate charge/event after human review",
    "WRONG_QUANTITY": "Correct metered quantity after human review",
    "LATE_EVENT": "Review billing-period cutoff",
    "ORPHAN_METERED": "Verify source event before charging",
    "CUSTOMER_MISMATCH": "Resolve customer/account mapping",
    "METRIC_MISMATCH": "Resolve metric/meter mapping",
    "OUT_OF_PERIOD": "Review billing-period assignment",
    "UNVERIFIABLE": "Inspect malformed or insufficient evidence",
    "IDEMPOTENCY_COLLISION": "Review possible replay/duplicate across event IDs",
}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.strip().lower()).strip("_")


def load_csv(path: str | Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def infer(headers: Iterable[str]) -> dict[str, str]:
    normalized = {norm(h): h for h in headers}
    out: dict[str, str] = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                out[canonical] = normalized[alias]
                break
    return out


def parse_time(value: Any) -> datetime | None:
    if value is None or str(value).strip() == "":
        return None
    s = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def round_money(v: float) -> float:
    return round(v + 0.0, 2)


def metric_name(row: dict[str, str], mapping: dict[str, str]) -> str:
    col = mapping.get("metric")
    return str(row.get(col, "default") if col else "default") or "default"


def price_for_quantity(metric: str, quantity: float, cfg: dict[str, Any]) -> float:
    """Return total price for a quantity, supporting flat and graduated tiers.

    pricing config examples:
      {"api_calls": {"unit_price": 0.02}}
      {"tokens": {"tiers": [{"up_to": 1000, "unit_price": 0.01},
                              {"up_to": null, "unit_price": 0.005}]}}
    """
    spec = (cfg.get("pricing") or {}).get(metric) or (cfg.get("pricing") or {}).get("default")
    if not spec:
        return quantity * float(cfg.get("price_per_unit", 0.01))
    if "unit_price" in spec:
        return quantity * float(spec["unit_price"])
    tiers = spec.get("tiers") or []
    remaining = max(quantity, 0.0)
    previous = 0.0
    total = 0.0
    for tier in tiers:
        up_to = tier.get("up_to")
        unit_price = float(tier["unit_price"])
        if up_to is None:
            units = remaining
        else:
            cap = max(float(up_to) - previous, 0.0)
            units = min(remaining, cap)
        total += units * unit_price
        remaining -= units
        if up_to is not None:
            previous = float(up_to)
        if remaining <= 0:
            break
    if remaining > 0:
        fallback = float(tiers[-1]["unit_price"]) if tiers else float(cfg.get("price_per_unit", 0.01))
        total += remaining * fallback
    return total


def delta_value(metric: str, expected_qty: float, actual_qty: float, cfg: dict[str, Any]) -> float:
    """Economic delta without double-counting: expected total minus actual total."""
    return price_for_quantity(metric, expected_qty, cfg) - price_for_quantity(metric, actual_qty, cfg)


def period_bounds(cfg: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
    period = cfg.get("billing_period")
    if not period:
        return None, None
    return parse_time(period.get("start")), parse_time(period.get("end"))


def evidence(row: dict[str, Any] | None, mapping: dict[str, str]) -> dict[str, Any]:
    if row is None:
        return {}
    keys = ["event_id", "idempotency_key", "customer_id", "timestamp", "quantity", "metric"]
    return {k: row.get(mapping[k]) for k in keys if k in mapping}


def finding(*, event_id: str, customer: str | None, kind: str, impact: float,
            status: str, detail: str, expected: dict[str, Any] | None,
            actual: list[dict[str, Any]], action: str | None = None) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "customer": customer,
        "type": kind,
        "status": status,
        "impact_eur": round_money(impact),
        "detail": detail,
        "action": action or ACTIONS[kind],
        "evidence": {"expected": expected or {}, "actual": actual},
    }


def reconcile(raw: list[dict[str, str]], metered: list[dict[str, str]], cfg: dict[str, Any]) -> dict[str, Any]:
    if not raw or not metered:
        raise ValueError("Both files need data rows")

    rm, mm = infer(raw[0].keys()), infer(metered[0].keys())
    required = {"event_id", "customer_id", "timestamp", "quantity"}
    missing_raw = required - set(rm)
    missing_meter = required - set(mm)
    if missing_raw or missing_meter:
        raise ValueError(
            f"Could not infer columns. raw missing={sorted(missing_raw)}, metered missing={sorted(missing_meter)}"
        )

    issues: list[dict[str, Any]] = []
    start, end = period_bounds(cfg)
    tolerance = float(cfg.get("quantity_tolerance", 0.0))
    late_hours = float(cfg.get("late_hours", 24))

    # Keep duplicates in raw visible rather than silently overwriting.
    raw_by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in raw:
        raw_by_id[str(row[rm["event_id"]])].append(row)
    metered_by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in metered:
        metered_by_id[str(row[mm["event_id"]])].append(row)

    # Same idempotency key attached to multiple event IDs is suspicious even when
    # each event reconciles independently. Do not assign economic impact until reviewed.
    if "idempotency_key" in mm:
        idem_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in metered:
            key = str(row.get(mm["idempotency_key"], "")).strip()
            if key:
                idem_groups[key].append(row)
        for key, rows in idem_groups.items():
            event_ids = sorted({str(x[mm["event_id"]]) for x in rows})
            if len(event_ids) > 1:
                issues.append(finding(
                    event_id=",".join(event_ids),
                    customer=str(rows[0][mm["customer_id"]]),
                    kind="IDEMPOTENCY_COLLISION",
                    impact=0,
                    status="SUSPECTED",
                    detail=f"Idempotency key {key!r} appears across event IDs {event_ids}",
                    expected={},
                    actual=[evidence(x, mm) for x in rows],
                ))

    for eid, raw_rows in raw_by_id.items():
        r = raw_rows[0]
        cust = str(r[rm["customer_id"]])
        rq = to_float(r[rm["quantity"]])
        raw_metric = metric_name(r, rm)
        rt = parse_time(r[rm["timestamp"]])
        expected_ev = evidence(r, rm)
        ms = metered_by_id.get(eid, [])

        if rq is None or rt is None:
            issues.append(finding(event_id=eid, customer=cust, kind="UNVERIFIABLE", impact=0,
                                  status="UNVERIFIABLE", detail="Source row has malformed quantity or timestamp",
                                  expected=expected_ev, actual=[]))
            continue

        # Raw duplicate IDs are ambiguous source evidence.
        if len(raw_rows) > 1:
            issues.append(finding(event_id=eid, customer=cust, kind="UNVERIFIABLE", impact=0,
                                  status="UNVERIFIABLE", detail=f"{len(raw_rows)} source rows share the same event_id",
                                  expected=expected_ev, actual=[evidence(x, rm) for x in raw_rows]))

        if start and end and not (start <= rt < end):
            issues.append(finding(event_id=eid, customer=cust, kind="OUT_OF_PERIOD", impact=0,
                                  status="CONFIRMED", detail="Source event falls outside configured billing period",
                                  expected=expected_ev, actual=[]))

        if not ms:
            impact = price_for_quantity(raw_metric, rq, cfg)
            issues.append(finding(event_id=eid, customer=cust, kind="MISSING", impact=impact,
                                  status="CONFIRMED", detail="Source event has no observed/metered counterpart",
                                  expected=expected_ev, actual=[]))
            continue

        valid_ms: list[tuple[dict[str, str], float, datetime]] = []
        malformed = False
        for m in ms:
            mq = to_float(m[mm["quantity"]])
            mt = parse_time(m[mm["timestamp"]])
            if mq is None or mt is None:
                malformed = True
                continue
            valid_ms.append((m, mq, mt))
        if malformed:
            issues.append(finding(event_id=eid, customer=cust, kind="UNVERIFIABLE", impact=0,
                                  status="UNVERIFIABLE", detail="At least one observed row has malformed quantity or timestamp",
                                  expected=expected_ev, actual=[evidence(x, mm) for x in ms]))
        if not valid_ms:
            continue

        first, first_qty, first_time = valid_ms[0]
        actual_evidence = [evidence(x[0], mm) for x in valid_ms]
        observed_customer = str(first[mm["customer_id"]])
        observed_metric = metric_name(first, mm)

        if observed_customer != cust:
            issues.append(finding(event_id=eid, customer=cust, kind="CUSTOMER_MISMATCH", impact=0,
                                  status="CONFIRMED", detail=f"Expected customer={cust}, observed={observed_customer}",
                                  expected=expected_ev, actual=actual_evidence))

        if "metric" in rm and "metric" in mm and observed_metric != raw_metric:
            issues.append(finding(event_id=eid, customer=cust, kind="METRIC_MISMATCH", impact=0,
                                  status="CONFIRMED", detail=f"Expected metric={raw_metric}, observed={observed_metric}",
                                  expected=expected_ev, actual=actual_evidence))

        total_mq = sum(x[1] for x in valid_ms)
        # One economic delta per event prevents duplicate + quantity mismatch double counting.
        economic_delta = delta_value(raw_metric, rq, total_mq, cfg)

        if len(valid_ms) > 1:
            issues.append(finding(event_id=eid, customer=cust, kind="DUPLICATE", impact=economic_delta,
                                  status="CONFIRMED", detail=f"{len(valid_ms)} observed rows found; combined quantity={total_mq:g}",
                                  expected=expected_ev, actual=actual_evidence))
        elif abs(first_qty - rq) > tolerance:
            issues.append(finding(event_id=eid, customer=cust, kind="WRONG_QUANTITY", impact=economic_delta,
                                  status="CONFIRMED", detail=f"Expected quantity={rq:g}, observed={first_qty:g}",
                                  expected=expected_ev, actual=actual_evidence))

        delay = (first_time - rt).total_seconds() / 3600
        if delay > late_hours:
            issues.append(finding(event_id=eid, customer=cust, kind="LATE_EVENT", impact=0,
                                  status="CONFIRMED", detail=f"Observed {delay:.2f}h after source event; threshold={late_hours:g}h",
                                  expected=expected_ev, actual=actual_evidence))
        if start and end and not (start <= first_time < end):
            issues.append(finding(event_id=eid, customer=cust, kind="OUT_OF_PERIOD", impact=0,
                                  status="CONFIRMED", detail="Observed event falls outside configured billing period",
                                  expected=expected_ev, actual=actual_evidence))

    for eid, ms in metered_by_id.items():
        if eid in raw_by_id:
            continue
        valid_quantities = [to_float(x[mm["quantity"]]) for x in ms]
        valid_quantities = [q for q in valid_quantities if q is not None]
        first = ms[0]
        metric = metric_name(first, mm)
        qty = sum(valid_quantities)
        cust = str(first[mm["customer_id"]])
        impact = -price_for_quantity(metric, qty, cfg)
        status = "CONFIRMED" if len(valid_quantities) == len(ms) else "UNVERIFIABLE"
        issues.append(finding(event_id=eid, customer=cust, kind="ORPHAN_METERED", impact=impact if status == "CONFIRMED" else 0,
                              status=status, detail="Observed/metered event has no source counterpart",
                              expected={}, actual=[evidence(x, mm) for x in ms]))

    confirmed = [x for x in issues if x["status"] == "CONFIRMED"]
    # Economic impact appears exactly once per event among economic finding types.
    economic_types = {"MISSING", "DUPLICATE", "WRONG_QUANTITY", "ORPHAN_METERED"}
    economic = [x for x in confirmed if x["type"] in economic_types]
    under = sum(max(x["impact_eur"], 0) for x in economic)
    over = sum(max(-x["impact_eur"], 0) for x in economic)
    periods = int(cfg.get("annualization_periods", 12))

    return {
        "version": "0.2.0",
        "input_mapping": {"raw": rm, "metered": mm},
        "config": cfg,
        "summary": {
            "raw_events": len(raw),
            "metered_rows": len(metered),
            "findings": len(issues),
            "confirmed_findings": len(confirmed),
            "suspected_findings": sum(x["status"] == "SUSPECTED" for x in issues),
            "unverifiable_findings": sum(x["status"] == "UNVERIFIABLE" for x in issues),
            "potential_underbilling_eur": round_money(under),
            "potential_overbilling_eur": round_money(over),
            "period_exposure_eur": round_money(under + over),
            "annualized_exposure_eur": round_money((under + over) * periods),
        },
        "findings": issues,
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        raise SystemExit("Usage: recoverycore_v02.py RAW.csv METERED.csv [config.json]")
    raw, metered = load_csv(argv[0]), load_csv(argv[1])
    cfg = dict(DEFAULT_CONFIG)
    if len(argv) > 2:
        with open(argv[2], encoding="utf-8") as f:
            cfg.update(json.load(f))
    try:
        result = reconcile(raw, metered, cfg)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
