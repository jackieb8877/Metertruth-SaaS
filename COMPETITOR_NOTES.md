# Competitor notes — 27 Sep 2026

## Stripe Billing

Stripe defines meters as aggregation rules for meter events, and offers a summary endpoint scoped to a customer and time window. The docs explicitly say meter-event processing is asynchronous, so aggregate summaries may lag newly submitted events. The connector currently reads summaries only and cannot prove event-level receipts from a provider aggregate.

## Lago

Lago supports event-based usage billing and assigns event period using the event timestamp; late events are assigned historically, but after an invoice is finalized they may not affect the closed invoice and can impact a later cycle. Its open-source billing core means it is a direct alternative to building a billing engine, not evidence against an independent audit layer.

## Orb

Orb publicly positions itself as a full billing engine spanning usage, pricing, credits, invoices and revenue reporting. Public pricing page shows Core/Advanced/Enterprise contact-sales flows (Advanced and Enterprise custom pricing in the captured page); a clean, low-cost auditor is a possible unbundled wedge, but unvalidated.

## Metronome

Metronome documents raw usage events transformed into billable metrics through filtering and aggregation, then rated with products and rate cards. Stripe's current guide describes Metronome covering usage, credit-based pricing and contracts, while Stripe handles payment collection. This reinforces that MeterTruth should inspect truth across the chain rather than compete on rating breadth.

## Product / price attack

- Product: collect independent source exports, metered summaries, invoices, credit entries and price versions; output exact diff evidence and a recovery candidate.
- Price: fixed low monthly price with scan/event limits could be easier to trial than enterprise billing migrations. €49/€99/€199 has no willingness-to-pay evidence yet.
- Unbundle: keep invoices, entitlements, pricing authoring and payment collection in the billing platform.
- Simplify: first scan should be two uploads and a report; progressively reveal mapping/pricing only when needed.
- Verticalize: AI API/token products first, with retries, late events, credits and frequent model price changes.
- Recovery: after explicit approval, create a replay/adjustment proposal and prove its result in a follow-up scan. Beta remains read-only.

## Sources

- Stripe meter events and asynchronous aggregation: https://docs.stripe.com/api/versioning
- Stripe meter event summary endpoint: https://docs.stripe.com/api/billing/meter-event-summary/list
- Lago event ingestion and late event policy: https://getlago.com/docs/guide/events/ingesting-usage
- Lago source and license: https://github.com/getlago/lago
- Orb product positioning: https://www.withorb.com/solutions/ai
- Orb pricing: https://www.withorb.com/pricing
- Metronome event/metric/rate-card model: https://docs.metronome.com/guides/get-started/how-metronome-works
- Stripe/Metronome division of responsibilities: https://docs.stripe.com/billing/how-metronome-works-with-stripe
