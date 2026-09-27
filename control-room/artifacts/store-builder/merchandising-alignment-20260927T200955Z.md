# Store Builder — merchandising-aligned reversible candidate

Run ID: store-builder-20260927T200955Z
Timestamp: 2026-09-27T20:09:55.774Z
Source read: `control-room/store-preview.html` blob `702417bbd00055ee66ced65a9c946d334be70d7e`
Candidate: `control-room/artifacts/store-builder/store-preview-candidate-20260927T200955Z.html`

## Why this candidate exists
The current main preview cannot be overwritten in this run. A reversible candidate was saved instead so current work is not lost and the commercial preview remains untouched.

## Changes prepared
- Fixes the unclosed `#colecciones` section before HERO candidates.
- Aligns visible role labels with Creative v2: roller and bottle = CROSS-SELL; sunshade = seasonal CROSS-SELL.
- Keeps Viaje y coche in the 20–50 SKU architecture but visibly marks it as INCUBATOR and removes equal launch prominence.
- Preserves the six real candidates only; no catalogue filler was invented.
- Adds accessible filter-result status.
- Keeps search, reusable PDP validation, mobile navigation, real external editorial video, reduced-motion handling, pause behavior, interactive 3D and fallback.
- Checkout, payments, ads, tracking and data capture remain disabled.

## Static checks
- PASS — javascript_syntax
- PASS — section_balance
- PASS — three_collection_entries
- PASS — incubator_deprioritized
- PASS — creative_v2_roles
- PASS — six_candidates_only
- PASS — target_20_50
- PASS — purchase_disabled
- PASS — no_forms
- PASS — no_marketing_trackers
- PASS — video_control
- PASS — reduced_motion
- PASS — interactive_3d
- PASS — 3d_fallback
- PASS — search
- PASS — pdp_validation
- PASS — filter_status
- PASS — conceptual_labels
- PASS — pexels_video_still_external
- PASS — no_fake_reviews

Result: 20/20 passed.


## Media verification
- Pexels license was rechecked on 2026-09-27: website/e-commerce use is allowed under the Pexels license; endorsement must not be implied.
- Photo 1108099 is independently identified as two yellow Labrador retriever puppies, so its current pet-lifestyle use is visually coherent.
- Photo 1008155 is repeatedly used/indexed as travel imagery; its current use stays generic editorial, not product proof.
- The exact video URL 3831861 is independently described as ocean waves, matching the page's editorial-only label.
- Exact CDN delivery/playback could not be verified from this environment; do not claim it is playing publicly.

## Deployment
Render is connected to `project-rich-control-room` with auto-deploy enabled, but the latest visible live deploy still points to commit `a086c50beec708aa10351f0d8dd2d770e491aaf7`, which predates the storefront work. This candidate is code saved in GitHub, not a verified public publication.

## Handoff
Creative: preserve the warm editorial system; replace atmosphere media with final licensed assets only when the same exact product unit can be shown consistently.
SEO: keep candidate/TEST PDPs noindex until data depth is useful.
QA: promote this candidate only after browser validation of desktop/mobile, dialogs/search, reduced motion, media failure fallback, and Canvas/WebGL paths.
