---
key: CANVAS-FONT-WAIT-FONTS-READY-MISSES-CANVAS-ONLY-FACES
claim: >
  Neither `document.fonts.ready` nor `FontFaceSet.load()` is a safe wait before painting
  web-font text on a canvas. `fonts.ready` covers only the faces the page's OWN text has
  asked for: reading the getter forces a style/layout pass, which starts those loads and
  re-pends the promise, so wherever page text shares the family it loads the face for you
  and hides the gap. A face that only canvas text paints with is never requested by layout,
  so `ready` can resolve while that face is still `loading`. Blink's `fonts.load("600 16px
  Inter")` is no better: it rejects as soon as ANY matching face is in status `error`, and
  next/font declares a size-adjusted `local()` fallback face ("Inter Fallback",
  `src: local(Arial)`, unicode-range U+0-10FFFF) beside the seven Inter subset faces, which
  errors on every host without that local font (Linux CI runners, most Android). The
  Terminal's chart-capture `fontsReady()` raced exactly those two waits against a 2 s cap
  (mastermind-terminal PR #952, commit b8bf49fa0), so the provenance strip could paint in
  the fallback font before Latin Inter had loaded. Verified 2026-10-11 by a Playwright
  falsifier that moves page text off Inter, adds a fresh Latin Inter face whose .woff2 is
  held back 600 ms, and clicks capture in the same task: against the old body the capture
  was requested with `inter:loading`; against the fix (await `face.load()` on every
  non-errored Latin-range face of the family) every usable face is `loaded`.
falsifier: >
  In a mastermind-terminal checkout at or after the fix (PR #958, head ce3bf2dc2), revert
  `fontsReady()` in terminal/components/chartCapture/ChartCaptureDialog.tsx to the old body
  `Promise.all([document.fonts.ready, ...document.fonts.load(`${weight} 16px ${family}`)])`
  and run, from terminal/:
  `CI=1 npx playwright test e2e/chart-capture-review.spec.ts --project=desktop -g "waits for a Latin face only the strip needs"`.
  The claim predicts the assertion at terminal/e2e/chart-capture-review.spec.ts:382-383
  ("the capture was requested while a face it paints with was still loading") fails with
  `Received "inter:loading"` and the test exits 1; a pass with the old body falsifies it. Independently: a Chromium whose
  `FontFaceSet.load()` resolves with the loaded faces while an errored face matches the
  request would falsify the second half (check `third_party/blink/renderer/core/css/
  font_face_set.cc`, `LoadFontPromiseResolver::NotifyError`).
so_what: >
  Any Terminal surface that paints web-font text to a canvas or OffscreenCanvas (chart
  capture, snapshot/share exports, future image cards) must wait on the FACES, not the
  set: select the family's faces whose unicode-range covers Latin (U+0041), drop faces in
  status `error`, and await `face.load().catch(() => null)` on each under a cap. The shared
  helper is terminal/lib/fontFaces.ts (`paintingFaces`); do not reintroduce `fonts.ready`
  or `fonts.load()` as the wait. The e2e proof has its own trap: a test that leaves page
  text on the same family passes against a BROKEN wait, because reading `fonts.ready`
  forces the layout that loads the face. Move page text to a system family first
  (inject `* { font-family: ui-sans-serif, system-ui, sans-serif !important }`), add the
  canvas-only face fresh, and request the paint in the same task - the pattern in
  terminal/e2e/chart-capture-review.spec.ts ("waits for a Latin face only the strip
  needs"). Run the negative case before trusting the green.
kind: landmine
verified_at: 2026-10-11
verified_by: >
  mastermind-terminal PR #958 (branch claude/e19-capture-fonts-latin-faces, head
  ce3bf2dc2) against PR #952's branch. Old body: `CI=1 npx playwright test
  e2e/chart-capture-review.spec.ts --project=desktop` failed at spec line 383 with
  `Expected "inter:loaded"`, `Received "inter:loading"`, exit 1. Fixed body: cold `CI=1`
  run 12/12 passed across desktop/tablet/mobile; vitest terminal/lib/__tests__/fontFaces.test.ts
  11 cases; `npx tsc --noEmit -p .` exit 0. Blink behaviour read from
  font_face_set.cc (LoadFontPromiseResolver rejects on first errored face;
  FontFaceSetDocument::ready forces UpdateStyleAndLayout). The next/font fallback face
  was read from the served CSS of the Terminal dev server (`src: local(Arial)`, unquoted).
scope:
  - mastermind-terminal
  - terminal/components/chartCapture/ChartCaptureDialog.tsx
  - terminal/lib/fontFaces.ts
  - terminal/e2e/chart-capture-review.spec.ts
  - any canvas text painted with --font-ui or --font-num
confidence: verified
---

## Grounds

The review of commit b8bf49fa0 on mastermind-terminal PR #952 flagged the race in prose;
the measurement is what makes it a record. The first version of the falsifier passed
against the OLD body and looked like a refutation. It was not: the Terminal's page text
uses Latin Inter, so the moment `fontsReady()` read `document.fonts.ready` Chromium ran a
layout, that layout requested the Latin face, and the face was loaded by the time the
canvas painted. The gap only exists for a face that nothing in the DOM asks for, which is
exactly the state a provenance strip drawn on a canvas is in. Once the test moved page
text to a system family and added the Latin face fresh, the old body failed deterministically
and the fix passed on all three contract viewports in a cold `CI=1` run.

Two operational notes for whoever next touches this lane. First, the local() fallback
face is unquoted in the served CSS (`local(Arial)`), so a regex that expects quotes misses
it. Second, under a loaded dev server a `route.continue()` delay of 800 ms plus compile
latency exceeded the 2 s cap on the tablet project; the falsifier therefore prefetches
the .woff2 bytes with `page.request.get` and fulfils the delayed request from memory.
