# Editorial storefront prototype — implementation and QA

Date: 2026-09-27
Implementation: `control-room/store-preview.html`
Code commit: `9c24c7509cb1edc89f82139ba8c46c7904535506`
Git content SHA: `9500ab81e3645aaa2dd1030cca06de5d440d2b68`

## Scope
Non-commercial design study for the requested multi-product store, not a live shop. Provisional identity `rato.` has NOT been cleared for commercial use. Six candidate concepts from Product Scout are used to exercise navigation; they are not six approved, stocked or sellable SKUs. The target of 20–50 validated products is unchanged. Existing dashboard files were not modified.

## Implemented
Editorial typography and restrained paper/sage palette; responsive navigation; collection filters; working search; product detail dialogs; disabled purchase buttons; embedded editorial video element with pause/retry controls; reduced-motion and save-data handling; original geometric 3D roller with pointer and keyboard rotation, reset and three conceptual color finishes. WebGL is used when available, with a geometric Canvas renderer as an alternative. Animation stops when hidden/offscreen. No advertising trackers, checkout, payment collection or fictitious reviews/prices.

## Executed tests
17 local Chromium checks passed: 6 cards render; collection filter; detail dialog; purchasing disabled; search; empty-search state; 3D initialization; keyboard rotation; color selection; reset orientation; automatic rotation; no horizontal overflow at 1440px and 390px; reduced-motion skips video load; mobile menu opens; mobile menu closes; no unhandled JavaScript errors.

The tested local HTML and GitHub source were matched by Git blob hash after normalizing one blank line. The external network was deliberately blocked for resilience tests. The Canvas geometric 3D path was exercised; the WebGL path was not available in this test environment. This does NOT establish real-user Core Web Vitals or third-party video playback.

## Unresolved
- External Pexels image/video delivery could not be verified from this environment. Do not claim that the imagery has been viewed or the clip successfully played here. The page handles media errors explicitly. Verify actual asset appearance, rights and performance before production; replace placeholders with licensed assets matching final SKUs.
- Final product photography, video demonstrations, prices, stock, shipping, compatibility and traceability remain unverified. Procedural product imagery is labeled conceptual.
- New source committed; public hosting must be verified against the exact commit before declaring the preview live. Existing Render service has autoDeploy=yes; do not assume a successful deployment from a Git commit alone.

## References reviewed
- https://fablepets.com/ — pet-lifestyle and bundle/use-case structure.
- https://bellroy.com/ — collections and navigation by activity.
- https://www.aesop.com/ — editorial content structure.
- https://www.pexels.com/license/ — stock asset permissions and endorsement restrictions; individual media still needs verification.
- https://threejs.org/docs/pages/OrbitControls.html — interaction concepts; final prototype has no Three.js dependency.
- Installed Three.js/WebGL visualization skill read for renderer fallback, interaction, offscreen pausing and accessibility practices.

Mobbin was attempted through its connected tool but returned a paid-plan requirement. No results were obtained, no assets copied from Mobbin and no plan purchased.

## Handoff
Keep the owner's video + 3D preference; do not revert to an all-static template or silently remove 3D. Use visual quality and measured loading performance together. Improve the preview at its existing path rather than creating multiple versioned pages. Commercial publication remains gated by supplier/economic/compliance validation and owner authorization.
