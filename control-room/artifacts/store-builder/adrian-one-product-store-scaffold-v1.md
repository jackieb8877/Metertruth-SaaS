# Store Builder — one product store scaffold v1

Strategy: `adrian-one-product-v1`
Timestamp: 2026-09-27T21:14:13.874Z
Working branch: `store-builder-adrian-one-product-v1-20260927`
Base branch at branch creation: `project-rich-control-room` @ `c3d6cd2331537d122700b8659cf22bc802a0a0e2`

## Decision applied

Launch priority is now a **one product store**, one sales page and one market. The previous multi-product work is retained as research/design archive and is not deleted. The provisional `rato.` identity is retained because there is no reason to rename the project before a product is selected.

Current product: **none selected**.
Market proposal: **Spain / Spanish**, coverage not configured.
Commerce: **disabled**.
Shopify + AutoDS: **reference stack only; no connection or paid plan is assumed**.

## Reusable page skeleton

Navigation follows the course rule at 03:17: it points into the product experience rather than to a catalogue.

1. **Announcement / status banner**
   - Normal Shopify theme block.
   - During validation: clearly state non-commercial status.
   - At launch: replace only with a verified proposition (for example delivery or support) if evidence exists.

2. **Hero + CTA to product**
   - Custom editorial section.
   - One primary product image.
   - One headline = problem/result, not a list of features.
   - CTA anchors directly to the product section/page.
   - No slider required for v1.

3. **Benefits**
   - Three reorderable blocks: problem, verified benefit, differentiator.
   - Copy must come from customer/creative research and exact SKU evidence.

4. **Main product / sales card**
   - Normal Shopify main-product section where possible.
   - Required inputs: title, total price, variants if real, media, availability, product form.
   - Project-specific validation copy can be a small custom block.
   - Do not implement a custom checkout.

5. **Product demonstration**
   - Custom media block only when a real authorised asset exists.
   - Real SKU video preferred.
   - controls / playsinline / no forced audio.
   - Pause when offscreen; respect `prefers-reduced-motion`.
   - No stock footage presented as proof.

6. **How it works**
   - Standard multicolumn or custom repeatable blocks.
   - 1–3 steps, only as many as the product genuinely needs.

7. **Optional useful 3D**
   - Custom block behind an enable toggle.
   - Only for exact-SKU geometry that explains fit, form or mechanism.
   - Lazy load after viewport approach.
   - Manual rotate, pause/reset, keyboard operation.
   - Reduced-motion starts paused.
   - Static image fallback.
   - No 3D requirement if it delays the first commercial test.

8. **Trust**
   - Standard blocks.
   - Only verified delivery, returns, contact, product facts and policies.
   - No fabricated reviews, counters, scarcity, orders or price history.

9. **FAQ**
   - Standard collapsible content.
   - Questions from real objections: fit, use, delivery, returns, compatibility, care.
   - Unknown answers stay unpublished, not guessed.

10. **Final CTA**
    - Link back to the product section/product form.
    - No extra catalogue path required.

## Shopify implementation map

Shopify Online Store 2.0 uses JSON templates composed of reorderable sections. Keep most of this page in standard/reorderable sections and reserve custom code for the editorial hero, proof media and optional 3D viewer.

Planned template:
- `templates/product.one-product.json`
- main product section
- benefit blocks
- proof media section
- how-to section
- optional 3D section
- trust section
- FAQ section
- final CTA

Do not create these theme files in production until a Shopify store/theme exists and the owner authorises configuration.

## AutoDS handoff

No AutoDS connection exists. When the owner authorises account/store setup:

1. Confirm exact SKU + destination coverage + landed order cost first.
2. Follow AutoDS guided Shopify connection rather than assuming the app is already installed.
3. Import/sync **one exact product** for the active test.
4. Verify title, media rights, variants, supplier, price, shipping profile and destination availability in Shopify before publishing.
5. Keep automated ordering/add-ons/subscriptions off until explicitly approved.
6. Treat Peninsular Spain, Canary Islands and other destinations separately if supplier cost/coverage differs.

Current AutoDS help warns that manually installing the app before completing its guided setup can cause synchronization problems. That means the future connection path should be chosen once and followed deliberately; nothing is installed by this scaffold.

## Existing assets preserved

- Current multi-product `control-room/store-preview.html` remains untouched on the base branch.
- Prior editorial direction, warm palette, video preference and useful-3D requirement are retained.
- The new branch contains a small one-product HTML shell plus reusable CSS/interaction work. The connector blocked the larger HTML rewrite, so it is **not claimed as a completed frontend implementation**.
- No Pexels media is used in the one-product scaffold; therefore no stock clip is being represented as product proof.

## Creative handoff — required next inputs

Creative should deliver for the selected SKU:
- exact product name/variant;
- avatar and problem;
- one primary benefit and one differentiator;
- hero headline/subhead;
- 3 benefit blocks;
- 1–3 how-to steps;
- FAQ objections/answers with source status;
- real product media list with rights status;
- two ad creative hypotheses aligned with the same product page;
- claims that are verified vs still prohibited.

## QA handoff

QA should distinguish these levels:

### Specified now
- one product architecture;
- one-market page structure;
- Shopify/AutoDS integration plan;
- motion/3D accessibility requirements.

### Code saved on working branch
- `control-room/one-product-store.html` — minimal shell only;
- `control-room/one-product-store.css` — reusable editorial styles;
- `control-room/one-product-store.js` — mobile menu + pausable/reduced-motion calibration 3D interaction.

### Not yet proven
- full HTML composition applied;
- browser interaction test of the branch scaffold;
- real video playback;
- exact-product 3D;
- Shopify theme integration;
- AutoDS synchronization;
- deployed preview;
- commercial publication.

## Acceptance gate before launch

- exact product selected;
- supplier cost and delivery verified for chosen market;
- legal/claims/media-rights checks complete;
- total price set from explicit costs;
- Shopify product page populated;
- tracking tested;
- checkout/payment configuration separately authorised;
- owner approves paid test budget.

This document is an implementation scaffold, not a declaration that the store is live.
