from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from money import ZERO, required_decimal, round_money
from stripe_bridge import reconcile_stripe_summaries
from stripe_client import StripeReadError


@dataclass
class CustomerScanError:
    customer_id: str
    error: str


def scan_stripe_customers(
    raw_rows: Iterable[dict[str, Any]],
    *,
    client: Any,
    meter_id: str,
    metric: str,
    start_time: int,
    end_time: int,
    grouping: str = "hour",
    tolerance: Any = 0.0,
    unit_price: Any = 0.0,
    max_customers: int = 250,
) -> dict[str, Any]:
    """Reconcile one Stripe meter across every matching Stripe customer in raw usage.

    This intentionally scans sequentially in the MVP to keep request behavior predictable
    and reduce the chance of bursty API traffic. Per-customer Stripe failures are isolated
    and returned as errors instead of aborting the entire scan.
    """
    if max_customers < 1:
        raise ValueError("max_customers must be positive")
    if grouping not in {"hour", "day"}:
        raise ValueError("Grouping must be hour or day")
    tolerance_amount = required_decimal(tolerance, "Usage tolerance")
    unit_price_amount = required_decimal(unit_price, "Unit price")
    if unit_price_amount < 0 or tolerance_amount < 0:
        raise ValueError("Unit price and tolerance must be non-negative")

    eligible: list[dict[str, Any]] = []
    customers: set[str] = set()
    for row in raw_rows:
        customer = str(row["customer_id"])
        row_metric = str(row.get("metric") or "default")
        ts = int(row["timestamp_epoch"])
        if row_metric != metric or not (start_time <= ts < end_time):
            continue
        if not customer.startswith("cus_"):
            continue
        eligible.append(row)
        customers.add(customer)

    customer_ids = sorted(customers)
    if not customer_ids:
        raise ValueError("No Stripe customer IDs (cus_*) match the selected metric and period")
    if len(customer_ids) > max_customers:
        raise ValueError(f"Scan contains {len(customer_ids)} customers; MVP limit is {max_customers}")

    by_customer: dict[str, list[dict[str, Any]]] = {cid: [] for cid in customer_ids}
    for row in eligible:
        by_customer[str(row["customer_id"])].append({
            "customer_id": str(row["customer_id"]),
            "source_customer_id": str(row.get("source_customer_id") or row["customer_id"]),
            "timestamp": row["timestamp"],
            "quantity": row["quantity"],
            "metric": str(row.get("metric") or "default"),
        })

    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    all_findings: list[dict[str, Any]] = []
    total_under = total_over = ZERO

    for customer_id in customer_ids:
        try:
            stripe_rows = client.list_meter_event_summaries(
                meter_id=meter_id,
                customer_id=customer_id,
                start_time=start_time,
                end_time=end_time,
                grouping=grouping,
            )
            report = reconcile_stripe_summaries(
                by_customer[customer_id],
                stripe_rows,
                meter_to_metric={meter_id: metric},
                grouping=grouping,
                tolerance=tolerance_amount,
                unit_prices={metric: unit_price_amount},
            )
        except (StripeReadError, ValueError, KeyError) as exc:
            errors.append({"customer_id": customer_id, "error": str(exc)})
            continue

        summary = report["summary"]
        total_under += required_decimal(summary["potential_underbilling_eur"], "Underbilling total")
        total_over += required_decimal(summary["potential_overbilling_eur"], "Overbilling total")
        for finding in report["findings"]:
            item = dict(finding)
            item["customer_id"] = customer_id
            all_findings.append(item)
        source_ids = sorted({str(r.get("source_customer_id") or customer_id) for r in by_customer[customer_id]})
        results.append({
            "customer_id": customer_id,
            "source_customer_id": source_ids[0] if len(source_ids) == 1 else ", ".join(source_ids),
            "findings": int(summary["findings"]),
            "potential_underbilling_eur": float(summary["potential_underbilling_eur"]),
            "potential_overbilling_eur": float(summary["potential_overbilling_eur"]),
            "period_exposure_eur": float(summary["period_exposure_eur"]),
            "buckets_compared": int(summary["buckets_compared"]),
            "status": "LEAKAGE" if summary["findings"] else "CLEAN",
        })

    results.sort(key=lambda r: (-r["period_exposure_eur"], r["customer_id"]))
    all_findings.sort(key=lambda f: (-abs(float(f["impact_eur"])), f["customer_id"], f["bucket_start"]))

    return {
        "mode": "stripe_multi_customer_scan",
        "meter_id": meter_id,
        "metric": metric,
        "grouping": grouping,
        "summary": {
            "customers_discovered": len(customer_ids),
            "customers_scanned": len(results),
            "customers_with_findings": sum(1 for r in results if r["findings"]),
            "customers_clean": sum(1 for r in results if not r["findings"]),
            "customers_failed": len(errors),
            "findings": len(all_findings),
            "potential_underbilling_eur": round_money(total_under),
            "potential_overbilling_eur": round_money(total_over),
            "period_exposure_eur": round_money(total_under + total_over),
        },
        "customers": results,
        "errors": errors,
        "findings": all_findings,
    }
