# MeterTruth private beta — tester guide

## Goal

Run a read-only reconciliation between your product-source usage and Stripe Billing meter summaries, then review customers with potential underbilling or overbilling.

## Recommended first scan

1. Open `/start`.
2. Upload a raw usage CSV.
3. If the usage file uses internal account/workspace IDs, upload an identity mapping CSV.
4. Run **Preflight**. Do not continue if it reports `BLOCKED`.
5. Open the Stripe connector.
6. Use a restricted Stripe key where possible. MeterTruth only issues GET requests in this beta.
7. Choose one meter/metric and a UTC time window.
8. Run the portfolio scan.
9. Review customers ranked by exposure and export the JSON report.

## Raw usage CSV

Minimum logical fields (common aliases are autodetected):

- customer/account/workspace ID
- timestamp
- quantity/usage units
- metric (recommended when the file contains multiple usage types)

Event/request ID is required for event-level CSV-to-CSV reconciliation, but not for aggregate Stripe portfolio scans.

## Identity mapping CSV

Two columns:

```csv
internal_customer_id,stripe_customer_id
workspace_alpha,cus_123
workspace_beta,cus_456
```

The private beta uses one-to-one mapping. Unmapped internal IDs are excluded from Stripe calls and economic totals and are reported by preflight.

## Interpreting the report

- **Underbilling**: source usage is higher than the corresponding Stripe aggregate.
- **Overbilling**: Stripe aggregate is higher than source usage.
- **Exposure**: absolute underbilling + overbilling for the selected period using the configured unit price.
- **Clean**: no discrepancy found in the selected scope and tolerance.

Potential exposure is not automatically a booked loss, refund obligation, or accounting conclusion. Review source data, pricing, credits, adjustments, and billing-period rules before taking action.

## Safety boundaries

- No automatic refunds, invoice changes, meter changes, or customer mutations.
- Stripe connector uses GET requests only.
- Original uploaded files and API keys are not persisted. Derived reports, which can contain customer IDs, event IDs, quantities, and finding evidence, are stored in local SQLite scan history.
- In the Render Free deployment, local history is ephemeral and can disappear after an instance restart or replacement.
- Use test-mode or a least-privilege restricted key where possible.
- Maximum 250 Stripe customers per portfolio scan.

## What feedback is most useful

Record:

- whether preflight understood your file without manual cleanup;
- whether identity mapping was easy to prepare;
- time to first useful finding;
- any false positive/false negative you can independently verify;
- whether the exposure ranking matches how Billing/Finance would triage work;
- missing evidence needed before taking a billing action.
