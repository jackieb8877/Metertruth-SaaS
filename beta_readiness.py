from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Iterable

from identity_mapping import apply_identity_mapping


def _iso_z(epoch: int) -> str:
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat().replace('+00:00', 'Z')


def build_preflight(
    normalized_raw: Iterable[dict[str, Any]],
    *,
    identity_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Validate a normalized raw-usage dataset before any Stripe API call.

    The function is intentionally network-free. It reports schema/content readiness,
    mapping completeness, metric/date coverage, and actionable warnings.
    """
    raw = list(normalized_raw)
    if not raw:
        raise ValueError("Raw usage CSV needs at least one normalized row")

    metrics = Counter(str(r.get("metric") or "default") for r in raw)
    source_ids = sorted({str(r["customer_id"]) for r in raw})
    timestamps = [int(r["timestamp_epoch"]) for r in raw]

    mapped_rows, identity_meta = apply_identity_mapping(raw, identity_map, strict=False)
    mapped_stripe_ids = sorted({str(r["customer_id"]) for r in mapped_rows})

    warnings: list[str] = []
    blockers: list[str] = []

    if identity_meta["unmapped_internal_customers"]:
        warnings.append(
            f'{identity_meta["unmapped_internal_customers"]} internal customer IDs are unmapped and would be excluded from Stripe scans.'
        )
    if not mapped_stripe_ids:
        blockers.append("No Stripe customer IDs are available after identity mapping.")
    if len(metrics) > 1:
        warnings.append("Multiple metrics were detected. Stripe portfolio scans reconcile one metric/meter at a time in this MVP.")
    if len(mapped_stripe_ids) > 250:
        blockers.append(f"{len(mapped_stripe_ids)} Stripe customers exceed the MVP scan limit of 250.")

    readiness = "READY" if not blockers else "BLOCKED"
    return {
        "readiness": readiness,
        "rows": len(raw),
        "source_customers": len(source_ids),
        "stripe_customers_ready": len(mapped_stripe_ids),
        "metrics": [{"name": name, "rows": count} for name, count in sorted(metrics.items())],
        "window": {
            "first_event": _iso_z(min(timestamps)),
            "last_event": _iso_z(max(timestamps)),
        },
        "identity_mapping": identity_meta,
        "warnings": warnings,
        "blockers": blockers,
        "recommended": {
            "metric": metrics.most_common(1)[0][0],
            "start_time": _iso_z(min(timestamps)),
            "end_time": _iso_z(max(timestamps) + 1),
        },
    }


def executive_summary(report: dict[str, Any]) -> dict[str, Any]:
    """Build a concise, non-hyped billing/finance summary from a portfolio report."""
    s = report.get("summary", {})
    customers = list(report.get("customers", []))
    exposure = float(s.get("period_exposure_eur", 0.0))
    under = float(s.get("potential_underbilling_eur", 0.0))
    over = float(s.get("potential_overbilling_eur", 0.0))
    leaking = int(s.get("customers_with_findings", 0))
    scanned = int(s.get("customers_scanned", 0))
    failed = int(s.get("customers_failed", 0))

    top = [c for c in customers if float(c.get("period_exposure_eur", 0.0)) > 0][:3]
    actions: list[str] = []
    if under > 0:
        actions.append("Review under-metered customers before the next invoice or adjustment cycle.")
    if over > 0:
        actions.append("Review potential overbilling before issuing or finalizing customer charges.")
    if failed > 0:
        actions.append("Re-run failed customer checks before treating portfolio totals as complete.")
    if not actions:
        actions.append("No billing discrepancy was detected in the selected dataset/window; repeat on another billing period before drawing a broader conclusion.")

    return {
        "headline": f"€{exposure:,.2f} of potential billing exposure across {leaking} of {scanned} scanned customers.",
        "potential_underbilling_eur": round(under, 2),
        "potential_overbilling_eur": round(over, 2),
        "customers_with_findings": leaking,
        "customers_scanned": scanned,
        "customers_failed": failed,
        "top_customers": top,
        "recommended_actions": actions,
        "scope_note": "Potential exposure is calculated from the selected usage window and configured unit price; it is not a booked financial loss or refund obligation.",
    }
