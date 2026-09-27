"""Read-only checks between metered usage, invoice lines and credit ledger.

These amounts are reported separately from source-to-meter exposure: invoice
usage is priced from metered quantities, so each comparison covers one edge of
the revenue pipeline and does not count the same usage loss twice.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from money import ZERO, required_decimal, round_money
from recoverycore_v02 import infer, _price_amount

INVOICE_ALIASES = {
    "invoice_id": ["invoice_id", "invoice", "bill_id"],
    "customer_id": ["customer_id", "customer", "account_id", "customer_external_id"],
    "metric": ["metric", "meter", "usage_type", "sku"],
    "amount": ["amount", "line_amount", "amount_due", "total", "subtotal", "net_amount"],
    "line_type": ["line_type", "type", "kind", "category"],
}
CREDIT_ALIASES = {
    "customer_id": ["customer_id", "customer", "account_id", "customer_external_id"],
    "amount": ["credit_amount", "amount", "applied_amount", "value", "used_amount"],
}


def _infer(headers: list[str], aliases: dict[str, list[str]]) -> dict[str, str]:
    # Use RecoveryCore's header normalization while keeping ledger-specific aliases.
    from recoverycore_v02 import norm
    normalized = {norm(header): header for header in headers}
    return {key: next((normalized[norm(alias)] for alias in values if norm(alias) in normalized), "")
            for key, values in aliases.items()}


def reconcile_ledgers(metered: list[dict[str, str]], invoice: list[dict[str, str]] | None,
                      credits: list[dict[str, str]] | None, cfg: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    invoice_mapping: dict[str, str] = {}
    credit_mapping: dict[str, str] = {}
    invoice_rows = invoice or []
    credit_rows = credits or []

    if invoice_rows:
        invoice_mapping = _infer(list(invoice_rows[0]), INVOICE_ALIASES)
        mm = infer(metered[0])
        if not mm.get("customer_id") or not mm.get("quantity"):
            raise ValueError("Metered file needs customer_id and quantity for invoice reconciliation")
        if not invoice_mapping["customer_id"] or not invoice_mapping["amount"]:
            raise ValueError("Invoice file needs customer_id and amount columns")
        metric_col = mm.get("metric")
        expected_quantities: dict[tuple[str, str], Decimal] = defaultdict(lambda: ZERO)
        for row in metered:
            customer = str(row.get(mm["customer_id"], "")).strip()
            metric = str(row.get(metric_col, "default")).strip() if metric_col else "default"
            if not customer:
                raise ValueError("Metered file contains a blank customer ID")
            quantity = required_decimal(row.get(mm["quantity"]), "Metered quantity")
            expected_quantities[(customer, metric or "default")] += quantity
        metrics = {metric for _, metric in expected_quantities}

        billed: dict[tuple[str, str], Decimal] = defaultdict(lambda: ZERO)
        credits_in_invoice: dict[str, Decimal] = defaultdict(lambda: ZERO)
        evidence: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
        credit_evidence: dict[str, list[dict[str, str]]] = defaultdict(list)
        type_col = invoice_mapping["line_type"]
        metric_col = invoice_mapping["metric"]
        amount_col = invoice_mapping["amount"]
        for row in invoice_rows:
            customer = str(row.get(invoice_mapping["customer_id"], "")).strip()
            if not customer:
                raise ValueError("Invoice file contains a blank customer ID")
            amount = required_decimal(row.get(amount_col), "Invoice line amount")
            kind = str(row.get(type_col, "usage")).strip().lower() if type_col else "usage"
            if kind in {"credit", "discount", "credit_note", "credit note"}:
                credits_in_invoice[customer] += abs(amount)
                credit_evidence[customer].append(row)
            elif kind in {"tax", "taxes", "subtotal", "total", "fee", "adjustment", "refund"}:
                # Non-usage lines cannot be compared to metered consumption.
                continue
            else:
                metric = str(row.get(metric_col, "")).strip() if metric_col else ""
                if not metric:
                    if len(metrics) > 1:
                        raise ValueError("Invoice file needs a metric column when metered usage contains multiple metrics")
                    metric = next(iter(metrics), "default")
                key = (customer, metric or "default")
                billed[key] += amount
                evidence[key].append(row)

        expected = {key: _price_amount(key[1], quantity, cfg) for key, quantity in expected_quantities.items()}
        for key in sorted(set(expected) | set(billed)):
            customer, metric = key
            expected_amount = expected[key]
            billed_amount = billed[key]
            delta = expected_amount - billed_amount
            if round_money(abs(delta)) == 0:
                continue
            findings.append({
                "event_id": f"invoice:{customer}:{metric}", "customer": customer,
                "type": "INVOICE_MISMATCH", "code": "INVOICE_MISMATCH", "status": "CONFIRMED",
                "impact_eur": round_money(delta),
                "detail": f"Metered usage priced at €{expected_amount:.2f}; invoice usage lines total €{billed_amount:.2f} for {metric}.",
                "action": "Inspect invoice line mapping; prepare a reviewed invoice correction candidate",
                "evidence": {"expected_metered_eur": str(expected_amount), "invoice_usage_eur": str(billed_amount),
                             "metric": metric, "invoice_lines": evidence[key]},
            })

        if credit_rows:
            credit_mapping = _infer(list(credit_rows[0]), CREDIT_ALIASES)
            if not credit_mapping["customer_id"] or not credit_mapping["amount"]:
                raise ValueError("Credit ledger needs customer_id and credit_amount/amount columns")
            ledger_credits: dict[str, Decimal] = defaultdict(lambda: ZERO)
            ledger_evidence: dict[str, list[dict[str, str]]] = defaultdict(list)
            for row in credit_rows:
                customer = str(row.get(credit_mapping["customer_id"], "")).strip()
                if not customer:
                    raise ValueError("Credit ledger contains a blank customer ID")
                amount = required_decimal(row.get(credit_mapping["amount"]), "Credit ledger amount")
                ledger_credits[customer] += abs(amount)
                ledger_evidence[customer].append(row)
            for customer in sorted(set(ledger_credits) | set(credits_in_invoice)):
                expected_credit = ledger_credits[customer]
                applied_credit = credits_in_invoice[customer]
                delta = expected_credit - applied_credit
                if round_money(abs(delta)) == 0:
                    continue
                findings.append({
                    "event_id": f"credit:{customer}", "customer": customer,
                    "type": "CREDIT_MISMATCH", "code": "CREDIT_MISMATCH", "status": "CONFIRMED",
                    "impact_eur": round_money(delta),
                    "detail": f"Credit ledger shows €{expected_credit:.2f} expected; invoice credit lines apply €{applied_credit:.2f}.",
                    "action": "Compare credit grants and invoice applications; review a credit adjustment",
                    "evidence": {"ledger_credit_eur": str(expected_credit), "invoice_credit_eur": str(applied_credit),
                                 "credit_ledger_rows": ledger_evidence[customer], "invoice_credit_lines": credit_evidence[customer]},
                })

    positive = sum((required_decimal(f["impact_eur"], "Ledger impact") for f in findings if f["impact_eur"] > 0), ZERO)
    negative = sum((-required_decimal(f["impact_eur"], "Ledger impact") for f in findings if f["impact_eur"] < 0), ZERO)
    return {
        "input_mapping": {"invoice": invoice_mapping, "credits": credit_mapping},
        "findings": findings,
        "summary": {"findings": len(findings), "potential_underbilling_eur": round_money(positive),
                    "potential_overbilling_eur": round_money(negative),
                    "period_exposure_eur": round_money(positive + negative),
                    "additive_to_usage_exposure": False},
    }
