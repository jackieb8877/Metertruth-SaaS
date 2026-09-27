# MeterTruth MVP v0.9 — private beta candidate

MeterTruth is an independent revenue-assurance layer for usage-based SaaS. It compares product-source usage with metered/billing usage, flags discrepancies with evidence, and produces a reviewable Revenue Leak Report. It does not issue invoices or mutate billing providers.

## v0.9 changes

- Main reconciliation upload accepts CSV, JSON arrays/objects, common `data`/`events`/`rows` wrappers, JSONL and NDJSON (UTF-8; maximum 5 MiB per file).
- Schema aliases remain inferred by RecoveryCore v0.2.
- Findings keep their v0.x `type` for compatibility and expose a stable machine-readable `code` (for example `MISSING_USAGE`, `DUPLICATE_USAGE`, and `ORPHAN_METERED_EVENT`).
- Event-level and Stripe aggregate/portfolio pricing uses decimal arithmetic; reportable euro impacts round to cents with half-up rounding.
- CSV usage quantities and form/catalog rates are kept as decimal strings through normalization, avoiding a float conversion before reconciliation.
- Event-level and read-only Stripe scans are stored in local SQLite scan history; original uploads and API keys are not stored.
- Each scan can be reopened as an evidence-rich HTML Revenue Leak Report.
- Optional invoice lines and credit ledger uploads detect `INVOICE_MISMATCH` and `CREDIT_MISMATCH`; invoice rows can be grouped by billing period and the report displays inferred ledger columns while keeping downstream deltas separate from raw-to-meter leakage.
- Optional effective-dated flat price catalogs detect `PRICING_DRIFT` against invoice line unit prices; economic deltas are reported once, without a duplicate invoice mismatch.
- The existing guided onboarding, preflight, demo, customer mapping and read-only Stripe portfolio scan remain in place.
- Optional Basic Auth, CSP/security headers and `/health` remain part of the private beta.

## Local run

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. The app processes uploads in memory, stores only sanitized filenames, findings, evidence and summaries in SQLite, and provides the scan history at `/history`. Set `METERTRUTH_DB_PATH` to choose a local database path. The database file is created with owner-only permissions where supported.

## Test

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Included test data

- `demo_raw.csv` / `demo_metered.csv`
- `demo_raw.json` / `demo_metered.json`
- `demo_stripe_portfolio.csv` and the existing identity-map samples

## Current coverage and boundaries

RecoveryCore v0.2 covers missing, duplicate, wrong quantity, customer mismatch, metric mismatch, late/out-of-period events, orphan metered rows, idempotency collisions, flat/tiered price configuration and an economic exposure report. CSV↔JSON event-level reconciliation and stored scan reports are now supported.

Invoice and credit checks are available as optional uploads. Invoice usage lines need `customer_id` and `amount`; `metric` and `line_type` can be provided to disambiguate multiple meters and identify credit rows (`line_type=credit`). When a single metric is present, an omitted invoice metric is inferred. Add both `period_start` and `period_end` to every invoice row to reconcile separate billing periods; ranges are UTC-normalized and half-open (`start ≤ event time < end`), and overlapping periods are rejected. Metered events outside supplied invoice windows are excluded. Credit ledger rows need `customer_id` and `credit_amount` (or `amount`). For period-grouped invoices, the credit ledger must also carry matching period columns. The invoice file must include its credit lines for credit reconciliation. Invoice usage totals are compared with metered quantities priced using the configured flat or tiered catalog, aggregated per customer, metric and period (tier thresholds reset per period).

For effective price drift, upload a catalog with `metric`, `unit_price`, `effective_from`, and optional `effective_to` (empty means open-ended), plus invoice usage lines with `unit_price`, `period_start`, and `period_end`. Catalog ranges are UTC-normalized, half-open, and may not overlap. Each invoice usage-line period must fit wholly within one catalog version; split the line when it spans a price change. A mismatched unit rate becomes `PRICING_DRIFT`; if the line amount still reconciles to catalog-rated usage, it is marked suspected with €0 confirmed exposure. Taxes, refunds, tiered effective-dated catalogs and proof that a recovery action was applied are not inferred. These downstream findings are shown separately from source-to-meter leakage to avoid double counting. Stripe portfolio mode remains aggregate-level and read-only. See `PROJECT_STATUS.md` for assumptions and limits.

No original upload, Stripe key, invoice adjustment, refund or customer mutation is retained/performed. Hosted deployment on Vercel uses ephemeral local storage; scan history can disappear on restart. Do not use production customer data until authentication, retention and storage requirements are independently reviewed.
