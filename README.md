# MeterTruth MVP v0.7 — private beta candidate

MeterTruth is an independent revenue-assurance layer for usage-based SaaS. It compares product-source usage with metered/billing usage, flags discrepancies with evidence, and produces a reviewable Revenue Leak Report. It does not issue invoices or mutate billing providers.

## v0.7 changes

- Main reconciliation upload accepts CSV, JSON arrays/objects, common `data`/`events`/`rows` wrappers, JSONL and NDJSON (UTF-8; maximum 5 MiB per file).
- Schema aliases remain inferred by RecoveryCore v0.2.
- Findings keep their v0.x `type` for compatibility and expose a stable machine-readable `code` (for example `MISSING_USAGE`, `DUPLICATE_USAGE`, and `ORPHAN_METERED_EVENT`).
- Event-level and Stripe aggregate/portfolio pricing uses decimal arithmetic; reportable euro impacts round to cents with half-up rounding.
- CSV usage quantities and form/catalog rates are kept as decimal strings through normalization, avoiding a float conversion before reconciliation.
- Event-level and read-only Stripe scans are stored in local SQLite scan history; original uploads and API keys are not stored.
- Each scan can be reopened as an evidence-rich HTML Revenue Leak Report.
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

The current report does **not yet** compare invoice totals or credit ledgers, infer pricing from versioned catalogs, implement billing-period-aware tier rating, or prove a recovery action was successfully applied. Stripe portfolio mode remains aggregate-level and read-only. These are explicitly tracked in `PROJECT_STATUS.md`.

No uploaded source file, Stripe key, invoice adjustment, refund or customer mutation is retained/performed. Hosted deployment on Render Free uses ephemeral local storage; scan history can disappear on restart. Do not use production customer data until authentication, retention and storage requirements are independently reviewed.
