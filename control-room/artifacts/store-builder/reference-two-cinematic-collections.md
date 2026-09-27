# rato. — Second video reference applied to collection navigation

Date: 2026-09-27
Status: IMPLEMENTED AND TESTED IN CONVERSATION ARTIFACT; NOT VERIFIED ON THE PUBLIC DEPLOYMENT.
Source supplied by the owner: ScreenRecording_09-27-2026 19-36-06_1.mp4 (237.44 seconds). Visual review of sampled frames and detail crops; no claim of an audio transcript.

## What the reference actually shows

The opening cycles through several site concepts. Around 02:08–02:32, an editor assembles related pool/float imagery and a page preview. Around 03:04–03:28, a large orange-and-white float remains the visual protagonist against animated water while framing and short headlines change. The visible recording does not establish whether the final visual is video, frame sequences, or an interactive 3D asset. Do not identify its implementation from appearance alone.

Adopt consistent art direction and a controlled object-centred narrative. Do not copy the pool images, cartoon characters, branding, typography assets, or other protected media from the reference. Do not copy its claims about AI tooling or generated-business success.

## Applied to Project Rich

Original progressive-enhancement module: rato-cinematic.js, included in the conversation package rato_referencia_aplicada.zip. Self-contained updated demo: rato_demo_interactiva.html. The package is not yet a repository code deployment.

A three-moment cinematic entry replaces the old hero visually, preserving the old section for compatibility with its scripts:

1. Quedarse — Mascotas en casa. Headline: Menos lío. Más casa. Conceptual roller; entry to kit and roller candidates.
2. Salir — Mascotas en movimiento. Headline: Sal ahí fuera. Con ellos. Conceptual portable water container; entry to car-cover and bottle candidates.
3. Llevar — Viaje y coche. Headline: Lleva lo justo. Vive lo demás. Conceptual packing organizers; entry to cubes and sunshade candidates.

The backdrop, headline, and object change together. There is restrained light movement and slow object rotation. Desktop native scroll progresses through the moments; direct selection is always available. Mobile uses direct chapter controls instead of a long pinned scroll. A direct catalogue link remains visible. No text is automatically cycled on a timer.

The 3D geometry is original and illustrative. Labels explicitly say conceptual / not the final product. Do not infer availability, performance, materials, measurements, or purchasable colours from these models. Keep the 20–50 validated-SKU objective; six demo concepts are not six launch-approved products.

## Interaction and safeguards

- Collection CTA displays the corresponding two demo candidates.
- Drag and keyboard/button rotation, reset, pause/resume.
- Animation pauses offscreen, when hidden, and with open dialogs.
- Reduced-motion starts paused; direct controls still work.
- Original search, product details, conceptual film, and existing detail scene retained.
- No orders, payment activation, advertising, tracking or lead capture.
- No additional external runtime, stock image or video dependency for the new hero.
- One additional canvas; WebGL where available, original CPU-projected Canvas 3D fallback, static fallback if Canvas is unavailable.

## Executed verification

30/30 interaction checks passed in local Chromium with external media deliberately blocked. Covered desktop (1440px), mobile emulation (390px and 360px), reduced motion, Canvas-unavailable fallback, collection navigation, search, details, pause/resume, native scroll and absence of JavaScript errors.

The environment did not provide WebGL; the tested interactive renderer was Canvas 3D. WebGL hardware rendering, real iPhone Safari, live external media delivery and public hosting were NOT verified. Do not present these tests as deployed-device QA or Core Web Vitals measurements.

## Integration handoff

Merge the module into the latest store-preview.html only after rereading its current version and SHA. Preserve the separate Store Builder improvements to collections and product validation. Use an additive script include or bundle; do not overwrite the page using an older local copy. Run the supplied checks again against the merged document. Read back the committed code and verify the actual deployment before saying live. Keep control-room/state.json owned by the Orchestrator and do not fabricate telemetry.

Creative: prepare consistent, licensed real product footage and context photography for the eventual final SKUs. This reference improves presentation; it does not replace sourcing or customer validation.
