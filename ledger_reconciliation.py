"""Read-only checks between metered usage, invoice lines and credit ledger.

These amounts are reported separately from source-to-meter exposure: invoice
usage is priced from metered quantities, so each comparison covers one edge of
the revenue pipeline and does not count the same usage loss twice.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any

from money import ZERO, required_decimal, round_money
from recoverycore_v02 import infer, _price_amount, parse_time

INVOICE_ALIASES = {
    "invoice_id": ["invoice_id", "invoice", "bill_id"],
    "customer_id": ["customer_id", "customer", "account_id", "customer_external_id"],
    "metric": ["metric", "meter", "usage_type", "sku"],
    "amount": ["amount", "line_amount", "amount_due", "total", "subtotal", "net_amount"],
    "unit_price": ["unit_price", "price_per_unit", "rate", "unit_amount"],
    "line_type": ["line_type", "type", "kind", "category"],
    "period_start": ["period_start", "billing_period_start", "service_period_start", "start_date"],
    "period_end": ["period_end", "billing_period_end", "service_period_end", "end_date"],
}
CATALOG_ALIASES = {
    "metric": ["metric", "meter", "usage_type", "sku"],
    "unit_price": ["unit_price", "price_per_unit", "rate", "unit_amount"],
    "effective_from": ["effective_from", "valid_from", "starts_at", "start_date"],
    "effective_to": ["effective_to", "valid_to", "ends_at", "end_date"],
}
CREDIT_ALIASES = {
    "customer_id": ["customer_id", "customer", "account_id", "customer_external_id"],
    "amount": ["credit_amount", "amount", "applied_amount", "value", "used_amount"],
    "period_start": ["period_start", "billing_period_start", "service_period_start", "start_date"],
    "period_end": ["period_end", "billing_period_end", "service_period_end", "end_date"],
}


def _infer(headers: list[str], aliases: dict[str, list[str]]) -> dict[str, str]:
    # Use RecoveryCore's header normalization while keeping ledger-specific aliases.
    from recoverycore_v02 import norm
    normalized = {norm(header): header for header in headers}
    return {key: next((normalized[norm(alias)] for alias in values if norm(alias) in normalized), "")
            for key, values in aliases.items()}


def _period_key(row: dict[str, str], mapping: dict[str, str], label: str) -> tuple[str, str] | None:
    start_col, end_col = mapping.get("period_start", ""), mapping.get("period_end", "")
    if not start_col and not end_col:
        return None
    if not start_col or not end_col:
        raise ValueError(f"{label} needs both period_start and period_end")
    start = parse_time(row.get(start_col))
    end = parse_time(row.get(end_col))
    if start is None or end is None or start >= end:
        raise ValueError(f"{label} has an invalid billing period; expected start < end")
    return start.isoformat(), end.isoformat()


def _period_for_timestamp(timestamp: Any, starts: list[datetime],
                          periods: list[tuple[datetime, datetime, str, str]]) -> tuple[str, str] | None:
    moment = parse_time(timestamp)
    if moment is None:
        raise ValueError("Metered file needs valid timestamps to match invoice billing periods")
    index = bisect_right(starts, moment) - 1
    if index < 0:
        return None
    start, end, start_text, end_text = periods[index]
    return (start_text, end_text) if start <= moment < end else None


def _load_price_catalog(rows: list[dict[str, str]]) -> tuple[
    dict[str, list[tuple[datetime, datetime | None, Decimal, dict[str, str]]]], dict[str, str]
]:
    mapping = _infer(list(rows[0]), CATALOG_ALIASES)
    if not mapping["metric"] or not mapping["unit_price"] or not mapping["effective_from"]:
        raise ValueError("Price catalog needs metric, unit_price and effective_from columns")
    schedules: dict[str, list[tuple[datetime, datetime | None, Decimal, dict[str, str]]]] = defaultdict(list)
    for row in rows:
        metric = str(row.get(mapping["metric"], "")).strip()
        start = parse_time(row.get(mapping["effective_from"]))
        end_text = str(row.get(mapping["effective_to"], "")).strip() if mapping["effective_to"] else ""
        end = parse_time(end_text) if end_text else None
        rate = required_decimal(row.get(mapping["unit_price"]), "Catalog unit price")
        if not metric or start is None or (end_text and end is None) or (end is not None and start >= end):
            raise ValueError("Price catalog has an invalid metric or effective date range")
        if rate < 0:
            raise ValueError("Catalog unit price must be non-negative")
        schedules[metric].append((start, end, rate, row))
    for metric, versions in schedules.items():
        versions.sort(key=lambda item: item[0])
        for previous, current in zip(versions, versions[1:]):
            if previous[1] is None or current[0] < previous[1]:
                raise ValueError(f"Price catalog versions overlap for metric {metric}")
    return dict(schedules), mapping


def _catalog_rate_at(versions: list[tuple[datetime, datetime | None, Decimal, dict[str, str]]],
                     timestamp: Any) -> tuple[Decimal, dict[str, str]]:
    moment = parse_time(timestamp)
    if moment is None:
        raise ValueError("Metered timestamps must be valid to use an effective-dated price catalog")
    starts = [item[0] for item in versions]
    index = bisect_right(starts, moment) - 1
    if index < 0:
        raise ValueError("Price catalog does not cover a metered event timestamp; add the missing effective price version")
    start, end, rate, evidence = versions[index]
    if end is not None and moment >= end:
        raise ValueError("Price catalog does not cover a metered event timestamp; add the missing effective price version")
    return rate, evidence


def reconcile_ledgers(metered: list[dict[str, str]], invoice: list[dict[str, str]] | None,
                      credits: list[dict[str, str]] | None, cfg: dict[str, Any],
                      price_catalog: list[dict[str, str]] | None = None) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    invoice_mapping: dict[str, str] = {}
    credit_mapping: dict[str, str] = {}
    catalog_mapping: dict[str, str] = {}
    invoice_rows = invoice or []
    credit_rows = credits or []
    catalog_rows = price_catalog or []
    schedules: dict[str, list[tuple[datetime, datetime | None, Decimal, dict[str, str]]]] = {}
    if catalog_rows:
        if not invoice_rows:
            raise ValueError("Upload invoice lines to compare observed prices with the effective-dated catalog")
        schedules, catalog_mapping = _load_price_catalog(catalog_rows)

    if invoice_rows:
        invoice_mapping = _infer(list(invoice_rows[0]), INVOICE_ALIASES)
        mm = infer(metered[0])
        if not mm.get("customer_id") or not mm.get("quantity"):
            raise ValueError("Metered file needs customer_id and quantity for invoice reconciliation")
        if not invoice_mapping["customer_id"] or not invoice_mapping["amount"]:
            raise ValueError("Invoice file needs customer_id and amount columns")
        period_columns = bool(invoice_mapping["period_start"] or invoice_mapping["period_end"])
        if schedules:
            if not (invoice_mapping["period_start"] and invoice_mapping["period_end"]):
                raise ValueError("Price drift checks need period_start and period_end on invoice usage lines")
            if not invoice_mapping["unit_price"]:
                raise ValueError("Price drift checks need unit_price on invoice usage lines")
        invoice_periods: set[tuple[str, str]] = set()
        invoice_row_periods: list[tuple[str, str] | None] = []
        for row in invoice_rows:
            period = _period_key(row, invoice_mapping, "Invoice file")
            invoice_row_periods.append(period)
            if period is not None:
                invoice_periods.add(period)
        if period_columns and any(period is None for period in invoice_row_periods):
            raise ValueError("Every invoice line needs period_start and period_end when period columns are supplied")
        ordered_periods = sorted(invoice_periods)
        for previous, current in zip(ordered_periods, ordered_periods[1:]):
            if parse_time(current[0]) < parse_time(previous[1]):
                raise ValueError("Invoice billing periods overlap; resolve them before reconciliation")
        period_intervals = [
            (parse_time(start), parse_time(end), start, end)
            for start, end in ordered_periods
        ]
        period_starts = [period[0] for period in period_intervals]
        catalog_rate_by_key: dict[tuple[str, str, str | None, str | None], Decimal] = {}
        catalog_evidence_by_key: dict[tuple[str, str, str | None, str | None], dict[str, str]] = {}
        invoice_price_by_key: dict[tuple[str, str, str | None, str | None], list[tuple[Decimal, dict[str, str]]]] = defaultdict(list)

        metric_col = mm.get("metric")
        expected_quantities: dict[tuple[str, str, str | None, str | None], Decimal] = defaultdict(lambda: ZERO)
        expected_catalog_amounts: dict[tuple[str, str, str | None, str | None], Decimal] = defaultdict(lambda: ZERO)
        for row in metered:
            customer = str(row.get(mm["customer_id"], "")).strip()
            metric = str(row.get(metric_col, "default")).strip() if metric_col else "default"
            if not customer:
                raise ValueError("Metered file contains a blank customer ID")
            period = None
            if period_columns:
                if not mm.get("timestamp"):
                    raise ValueError("Metered file needs a timestamp column to reconcile invoice periods")
                period = _period_for_timestamp(row.get(mm["timestamp"]), period_starts, period_intervals)
                # Only usage that falls inside an uploaded invoice period is in scope.
                if period is None:
                    continue
            quantity = required_decimal(row.get(mm["quantity"]), "Metered quantity")
            key = (customer, metric or "default", *(period or (None, None)))
            expected_quantities[key] += quantity
            if schedules:
                versions = schedules.get(metric or "default")
                if not versions:
                    raise ValueError(f"Price catalog has no versions for metered metric {metric or 'default'}")
                rate, catalog_row = _catalog_rate_at(versions, row.get(mm.get("timestamp", "")))
                expected_catalog_amounts[key] += quantity * rate
                catalog_evidence_by_key.setdefault(key, catalog_row)
        metrics = {metric for _, metric, _, _ in expected_quantities}

        billed: dict[tuple[str, str, str | None, str | None], Decimal] = defaultdict(lambda: ZERO)
        credits_in_invoice: dict[tuple[str, str | None, str | None], Decimal] = defaultdict(lambda: ZERO)
        evidence: dict[tuple[str, str, str | None, str | None], list[dict[str, str]]] = defaultdict(list)
        credit_evidence: dict[tuple[str, str | None, str | None], list[dict[str, str]]] = defaultdict(list)
        type_col = invoice_mapping["line_type"]
        metric_col = invoice_mapping["metric"]
        amount_col = invoice_mapping["amount"]
        for row, period in zip(invoice_rows, invoice_row_periods):
            period_start, period_end = period or (None, None)
            customer = str(row.get(invoice_mapping["customer_id"], "")).strip()
            if not customer:
                raise ValueError("Invoice file contains a blank customer ID")
            amount = required_decimal(row.get(amount_col), "Invoice line amount")
            kind = str(row.get(type_col, "usage")).strip().lower() if type_col else "usage"
            if kind in {"credit", "discount", "credit_note", "credit note"}:
                credit_key = (customer, period_start, period_end)
                credits_in_invoice[credit_key] += abs(amount)
                credit_evidence[credit_key].append(row)
            elif kind in {"tax", "taxes", "subtotal", "total", "fee", "adjustment", "refund"}:
                # Non-usage lines cannot be compared to metered consumption.
                continue
            else:
                metric = str(row.get(metric_col, "")).strip() if metric_col else ""
                if not metric:
                    if len(metrics) > 1:
                        raise ValueError("Invoice file needs a metric column when metered usage contains multiple metrics")
                    metric = next(iter(metrics), "default")
                key = (customer, metric or "default", period_start, period_end)
                billed[key] += amount
                evidence[key].append(row)
                if schedules:
                    versions = schedules.get(metric or "default")
                    if not versions:
                        raise ValueError(f"Price catalog has no versions for invoice metric {metric or 'default'}")
                    invoice_start, invoice_end = parse_time(period_start), parse_time(period_end)
                    matches = [v for v in versions if v[0] <= invoice_start and (v[1] is None or invoice_end <= v[1])]
                    if len(matches) != 1:
                        raise ValueError(f"Split invoice usage periods at effective price changes for metric {metric or 'default'}")
                    catalog_rate_by_key[key] = matches[0][2]
                    catalog_evidence_by_key.setdefault(key, matches[0][3])
                    invoice_rate = required_decimal(row.get(invoice_mapping["unit_price"]), "Invoice unit price")
                    if invoice_rate < 0:
                        raise ValueError("Invoice unit price must be non-negative for usage lines")
                    invoice_price_by_key[key].append((invoice_rate, row))

        expected = {
            key: expected_catalog_amounts[key] if schedules else _price_amount(key[1], quantity, cfg)
            for key, quantity in expected_quantities.items()
        }
        for key in sorted(set(expected) | set(billed)):
            customer, metric, period_start, period_end = key
            expected_amount = expected[key]
            billed_amount = billed[key]
            delta = expected_amount - billed_amount
            rate = catalog_rate_by_key.get(key)
            actual_rates = invoice_price_by_key.get(key, [])
            rate_mismatch = bool(schedules and rate is not None and any(actual != rate for actual, _ in actual_rates))
            rounded_delta = round_money(delta)
            if round_money(abs(delta)) == 0 and not rate_mismatch:
                continue
            period_detail = f" for [{period_start}, {period_end})" if period_start else ""
            if rate_mismatch:
                code = "PRICING_DRIFT"
                status = "CONFIRMED" if rounded_delta != 0 else "SUSPECTED"
                rate_detail = f"Effective catalog rate €{rate:.8f}; invoice rate(s) " + ", ".join(f"€{actual:.8f}" for actual, _ in actual_rates) + ". "
                action = "Review the effective price version and correct the invoice rate after approval"
            else:
                code = "INVOICE_MISMATCH"
                status = "CONFIRMED"
                rate_detail = ""
                action = "Inspect invoice line mapping; prepare a reviewed invoice correction candidate"
            findings.append({
                "event_id": f"invoice:{customer}:{metric}:{period_start or 'all'}", "customer": customer,
                "type": code, "code": code, "status": status,
                "impact_eur": rounded_delta,
                "detail": f"{rate_detail}Metered usage priced at €{expected_amount:.2f}; invoice usage lines total €{billed_amount:.2f} for {metric}{period_detail}.",
                "action": action,
                "evidence": {"expected_metered_eur": str(expected_amount), "invoice_usage_eur": str(billed_amount),
                             "metric": metric, "period_start": period_start, "period_end": period_end,
                             "effective_catalog_rate": str(rate) if rate is not None else None,
                             "applied_invoice_rates": [str(actual) for actual, _ in actual_rates],
                             "catalog_version": catalog_evidence_by_key.get(key), "invoice_lines": evidence[key]},
            })

        if credit_rows:
            credit_mapping = _infer(list(credit_rows[0]), CREDIT_ALIASES)
            if not credit_mapping["customer_id"] or not credit_mapping["amount"]:
                raise ValueError("Credit ledger needs customer_id and credit_amount/amount columns")
            if period_columns and not (credit_mapping["period_start"] and credit_mapping["period_end"]):
                raise ValueError("Credit ledger needs period_start and period_end when invoices are period-grouped")
            ledger_credits: dict[tuple[str, str | None, str | None], Decimal] = defaultdict(lambda: ZERO)
            ledger_evidence: dict[tuple[str, str | None, str | None], list[dict[str, str]]] = defaultdict(list)
            for row in credit_rows:
                customer = str(row.get(credit_mapping["customer_id"], "")).strip()
                if not customer:
                    raise ValueError("Credit ledger contains a blank customer ID")
                amount = required_decimal(row.get(credit_mapping["amount"]), "Credit ledger amount")
                period = _period_key(row, credit_mapping, "Credit ledger") if period_columns else None
                if period_columns and period not in invoice_periods:
                    raise ValueError("Credit ledger period does not match any invoice period")
                key = (customer, *(period or (None, None)))
                ledger_credits[key] += abs(amount)
                ledger_evidence[key].append(row)
            for key in sorted(set(ledger_credits) | set(credits_in_invoice)):
                customer, period_start, period_end = key
                expected_credit = ledger_credits[key]
                applied_credit = credits_in_invoice[key]
                delta = expected_credit - applied_credit
                if round_money(abs(delta)) == 0:
                    continue
                period_detail = f" for [{period_start}, {period_end})" if period_start else ""
                findings.append({
                    "event_id": f"credit:{customer}:{period_start or 'all'}", "customer": customer,
                    "type": "CREDIT_MISMATCH", "code": "CREDIT_MISMATCH", "status": "CONFIRMED",
                    "impact_eur": round_money(delta),
                    "detail": f"Credit ledger shows €{expected_credit:.2f} expected; invoice credit lines apply €{applied_credit:.2f}{period_detail}.",
                    "action": "Compare credit grants and invoice applications; review a credit adjustment",
                    "evidence": {"ledger_credit_eur": str(expected_credit), "invoice_credit_eur": str(applied_credit),
                                 "period_start": period_start, "period_end": period_end,
                                 "credit_ledger_rows": ledger_evidence[key], "invoice_credit_lines": credit_evidence[key]},
                })

    positive = sum((required_decimal(f["impact_eur"], "Ledger impact") for f in findings if f["impact_eur"] > 0), ZERO)
    negative = sum((-required_decimal(f["impact_eur"], "Ledger impact") for f in findings if f["impact_eur"] < 0), ZERO)
    return {
        "input_mapping": {"invoice": invoice_mapping, "credits": credit_mapping, "price_catalog": catalog_mapping},
        "findings": findings,
        "summary": {"findings": len(findings), "potential_underbilling_eur": round_money(positive),
                    "potential_overbilling_eur": round_money(negative),
                    "period_exposure_eur": round_money(positive + negative),
                    "confirmed_findings": sum(f["status"] == "CONFIRMED" for f in findings),
                    "suspected_findings": sum(f["status"] == "SUSPECTED" for f in findings),
                    "unverifiable_findings": sum(f["status"] == "UNVERIFIABLE" for f in findings),
                    "additive_to_usage_exposure": False},
    }
