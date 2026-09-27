# Kit Muda Cero — Storefront Spec v1

Status: PRE-GO / build specification only
Owner: Store Builder
Date: 2026-09-27

## Product story
Sell a complete 3-step system, not three unrelated tools:
1. Capture loose hair from the pet with the grooming glove.
2. Remove deeper loose coat with the self-cleaning slicker.
3. Finish the home/car/clothes with the reusable roller.

Primary promise: "Menos pelo en tu mascota. Menos pelo en casa."
Do not use numerical efficacy claims unless independently substantiated.

## Benchmark patterns adopted

### Fable
Source: https://fablepets.com/products/puffin-bites-bundle
Adopt:
- premium lifestyle photography and calm visual hierarchy;
- product-first story rather than aggressive discount-first presentation;
- social proof placed as evidence, not decoration.

### Uproot Clean
Source: https://uprootclean.com/products/uproot-cleaner-mini-pro-xtra-bundle
Adopt:
- bundle framed around complete use-case coverage;
- immediate explanation of what each tool is for;
- guarantee, delivery and returns close to the purchase module;
- dense proof section after the core sales story.
Avoid:
- unverified "99.99%" or equivalent performance claims;
- fake urgency, mystery gifts or scarcity unless operationally true.

### SoothePaws
Source: https://soothepaws.store/products/calm-groom-bundle-dog
Adopt:
- position the bundle as a routine/system rather than a pile of products;
- "what you get" and first-purchase value explained near CTA;
- reassurance bullets immediately around the CTA.

### Pawzn
Source: https://www.pawzn.shop/products/home-grooming-kit
Adopt:
- concrete "What's included" block;
- simple suggested routine;
- safety/care guidance without overclaiming.

## Mobile-first page architecture

### 1. Announcement bar
Only verifiable information:
- shipping threshold / SLA when Supplier confirms it;
- returns/guarantee only when policy is final.

### 2. Hero / buy box
Above fold:
- product bundle image or 6–8 second silent demo loop;
- H1: "Menos pelo en tu mascota. Menos pelo en casa."
- subhead: "Un sistema de 3 pasos para retirar pelo suelto del pelaje y rematar sofá, ropa y coche."
- star rating only after genuine review data exists;
- price selector remains dynamic until Finance locks the test price;
- primary CTA: "Quiero el Kit Muda Cero";
- three proof chips: reusable / 3 pasos / envío desde UE only if each is verified.

### 3. Visual problem-solution strip
Three panels:
Pet -> Coat -> Home
Glove -> Slicker -> Roller
Keep copy under 14 words per panel.

### 4. Demonstration block
Use authentic close-ups:
- glove collecting loose hair;
- slicker self-clean release;
- roller lifting hair from dark upholstery.
Prefer real video/UGC over 3D.

### 5. What's included
Three cards with:
- tool;
- best use;
- material/care;
- compatibility restrictions.

### 6. The 3-step routine
Short, numbered sequence.
No wall of text.

### 7. Fit / compatibility
Explicit coat guidance for slicker.
Include "not for irritated skin" / sensitive-area guidance if supplier documentation supports it.

### 8. Comparison
Compare the complete routine against buying disconnected tools, not against named competitors unless evidence is maintained.
Rows:
- pet grooming;
- deeper coat pass;
- sofa/clothes/car;
- reusable;
- one routine.

### 9. Trust
Only real signals:
- verified delivery window;
- returns window;
- secure payment methods;
- EU traceability/manufacturer-responsible-person data where required;
- genuine customer reviews later.

### 10. FAQ
Minimum:
- Does it work for cats and dogs?
- Which coat types suit the slicker?
- Can I use the roller on all fabrics?
- How do I clean each tool?
- Delivery time?
- Returns?
- What is included?

### 11. Sticky mobile CTA
Persistent bottom bar after user scrolls past hero:
price + "Añadir al carrito".
Must never cover cookie controls, legal links or critical content.

## Offer UX
Do not hard-code discount until Finance verifies the anchor price and lowest-price rules.
Prepare three price variants:
- 29.90
- 34.90
- 39.90
with identical layout so pricing can be swapped without rebuild.
Default bundle is 3-piece; 2-piece can exist only if Finance shows a useful entry-price role.

## Motion and 3D
Use motion only to demonstrate function:
- 150–250 ms UI transitions;
- subtle card reveals;
- one lightweight product demo loop;
- respect prefers-reduced-motion.
Decision: NO WebGL/3D for v1. It does not improve product comprehension enough to justify mobile performance cost.

## Performance budget
Targets on mobile p75:
- LCP <= 2.5 s
- INP <= 200 ms
- CLS <= 0.10

Budgets:
- initial JS <= 180 KB gzip;
- hero image <= 250 KB modern format where practical;
- above-fold transferred assets <= 700 KB before optional video;
- lazy-load below-fold imagery;
- video poster first; defer video bytes unless in viewport;
- avoid third-party widgets until needed;
- self-host or system fonts, max 2 families / 3 weights.

## Analytics hooks
Prepare dataLayer/custom events:
- view_product
- select_price_variant
- view_demo
- open_whats_included
- open_faq
- add_to_cart
- begin_checkout
- purchase
- sticky_cta_click
- bundle_component_interest

Required event properties:
product, variant, price, placement, device, session_id.
Do not activate marketing trackers before valid consent where required.

## Build gate
Production build remains blocked until:
- 3-piece landed cost and shipping SLA verified;
- final price test range approved by Finance;
- supplier/manufacturer traceability captured;
- returns and shipping policies are defined;
- real product assets are available.

## Handoff
Creative:
- produce hero still + 3 short demo scenes matching the 3-step routine;
- avoid unverified performance percentages.

SEO:
- build keyword/FAQ plan around pet hair removal, deshedding and reusable home hair removal without medical or unsupported claims.

QA:
- validate mobile sticky CTA, consent, pricing, delivery copy, returns copy, traceability, image weight and Core Web Vitals before GO.
