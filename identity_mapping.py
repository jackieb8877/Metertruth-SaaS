from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any, Iterable

INTERNAL_ALIASES = {"internal_customer_id", "internal_id", "account_id", "workspace_id", "customer_id", "source_customer_id"}
STRIPE_ALIASES = {"stripe_customer_id", "stripe_id", "stripe_customer", "cus_id"}


def _norm(value: str) -> str:
    return "_".join(str(value).strip().lower().replace("-", "_").split())


def _pick(headers: Iterable[str], aliases: set[str]) -> str | None:
    normalized = {_norm(h): h for h in headers}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    return None


def parse_identity_mapping_rows(rows: list[dict[str, Any]]) -> dict[str, str]:
    if not rows:
        raise ValueError("Identity mapping CSV needs at least one data row")
    headers = list(rows[0].keys())
    internal_col = _pick(headers, INTERNAL_ALIASES)
    stripe_col = _pick(headers, STRIPE_ALIASES)
    if not internal_col or not stripe_col:
        raise ValueError("Identity mapping CSV needs internal_customer_id and stripe_customer_id columns (common aliases accepted)")

    mapping: dict[str, str] = {}
    reverse: dict[str, str] = {}
    for idx, row in enumerate(rows, start=2):
        internal = str(row.get(internal_col, "")).strip()
        stripe = str(row.get(stripe_col, "")).strip()
        if not internal and not stripe:
            continue
        if not internal or not stripe:
            raise ValueError(f"Identity mapping row {idx} is incomplete")
        if not stripe.startswith("cus_"):
            raise ValueError(f"Identity mapping row {idx} has invalid Stripe customer ID: {stripe}")
        previous = mapping.get(internal)
        if previous and previous != stripe:
            raise ValueError(f"Conflicting mapping for internal customer {internal}")
        previous_internal = reverse.get(stripe)
        if previous_internal and previous_internal != internal:
            raise ValueError(f"Stripe customer {stripe} is mapped to multiple internal customers")
        mapping[internal] = stripe
        reverse[stripe] = internal
    if not mapping:
        raise ValueError("Identity mapping CSV contains no usable mappings")
    return mapping


def apply_identity_mapping(
    raw_rows: Iterable[dict[str, Any]],
    mapping: dict[str, str] | None,
    *,
    strict: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Map internal customer IDs to Stripe IDs while preserving source identity.

    Rows already using cus_* pass through. With strict=False, unmapped internal IDs are
    excluded and reported. With strict=True, any unmapped internal ID raises an error.
    """
    mapping = mapping or {}
    output: list[dict[str, Any]] = []
    unmapped: set[str] = set()
    mapped_ids: set[str] = set()
    passthrough_ids: set[str] = set()

    for row in raw_rows:
        source_id = str(row["customer_id"])
        if source_id.startswith("cus_"):
            stripe_id = source_id
            passthrough_ids.add(source_id)
        else:
            stripe_id = mapping.get(source_id)
            if not stripe_id:
                unmapped.add(source_id)
                continue
            mapped_ids.add(source_id)
        item = dict(row)
        item["source_customer_id"] = source_id
        item["customer_id"] = stripe_id
        output.append(item)

    if strict and unmapped:
        preview = ", ".join(sorted(unmapped)[:5])
        suffix = "…" if len(unmapped) > 5 else ""
        raise ValueError(f"Unmapped internal customer IDs: {preview}{suffix}")

    return output, {
        "mapping_entries": len(mapping),
        "mapped_internal_customers": len(mapped_ids),
        "passthrough_stripe_customers": len(passthrough_ids),
        "unmapped_internal_customers": len(unmapped),
        "unmapped_ids": sorted(unmapped),
    }
