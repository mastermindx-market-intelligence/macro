---
key: TERMINAL-PAGE-SCROLL-LOCK-IS-ONE-REF-COUNTED-LOCK
question: >
  Two Terminal overlays, the chart-hosted MegaPane (overlay mode) and the TranscriptDrawer,
  each saved and restored `document.body.style.overflow` and `document.documentElement
  .style.overflow` privately. A viewport resize across the 860px breakpoint with the
  transcript open over the pane unmounts and remounts the overlays in an order neither
  component controls, so the locks released out of order and left `overflow: hidden`
  stranded on the page (MarketOntology CEO A's F04 review finding on Terminal PR #959, head
  8942f781c; reproduced on the host in both breakpoint directions before any source edit).
  How do overlays that lock page scroll coordinate from now on?
answer: >
  One ref-counted page scroll lock, `terminal/lib/scrollLock.ts`, exported as
  `acquireScrollLock(): () => void`. The first acquirer snapshots the original body and
  html inline overflow, every acquirer increments a count, the returned release decrements
  it, the LAST release restores the snapshot, and a release handle is idempotent (a
  per-handle `released` flag). `__resetScrollLockForTests()` clears the module state for
  unit tests. MegaPane (overlay mode only), TranscriptDrawer, the transcript ReceiptDialog
  and TranscriptSearchWorkspace acquire it; no other overflow writer was changed in the
  repair. The lock is pinned by `terminal/lib/__tests__/scrollLock.test.ts` (4 cases) and by
  `terminal/e2e/chart-pane-scroll-lock-resize.spec.ts` (D1 narrow-to-wide, D2 wide-to-narrow
  with a wheel check, ROT tablet rotation, A11Y-ESC nested Escape with the lock asserted at
  every step, ANALYSIS negative control on /analysis). Any new overlay that must stop page
  scroll calls `acquireScrollLock()` instead of writing `style.overflow` itself.
rationale: >
  Release order is a property of the user's actions and of React's unmount order across a
  breakpoint, not something an individual overlay can know, so any private save/restore
  makes the restored value depend on acquisition order and will strand the page again the
  next time two overlays overlap a resize. A counted lock whose FIRST acquirer owns the
  snapshot and whose LAST release restores it is order-independent by construction, which
  is the only property the finding actually needed. Keeping inline-style semantics (rather
  than a body class) preserved the contract the existing writers and the responsive shell
  already rely on and kept the repair to the two components named in the finding. The spec
  was strengthened in a third round only after an independent review proved that the
  nested-Escape case pinned the Escape order but never read overflow, so a lock that was
  never released could not fail it; a mutant lock whose release never restores now fails
  five of the six resize cases on two hosts, which is the discriminating evidence the
  program's acceptance standard requires.
alternatives:
  - option: "Fix the release ordering inside MegaPane and TranscriptDrawer only."
    why_not: "The next overlay pair that overlaps a resize re-creates the defect; the tablet rotation case (ROT) showed the order is driven by the environment, not by either component."
  - option: "Toggle a `body.scroll-locked` class from a counter and move the overflow rule to CSS."
    why_not: "Four pre-existing direct inline writers (GuidePanel, MobileSheet, AnalysisHubSheet, chartSettingsUi) would still fight the class; an inline-restoring lock keeps the existing contract and leaves those writers for a scoped follow-up instead of widening the repair past the finding."
  - option: "Restore overflow on route change only and accept the transient stranded state."
    why_not: "The stranded page is visible immediately after the drawer closes (desktop page locked, or phone page locked until the pane also closes); the finding was browser-observed, not theoretical."
evidence:
  - >
    Terminal PR #959 heads: 8942f781c (round 1, carried the defect), 06299948f (round 2,
    the lock and the resize spec), 332944f02 (round 3, spec-only strengthening of A11Y-ESC).
    The chart-host Escape guard at terminal/components/MegaPane.tsx:187 is load-bearing:
    removing it fails A11Y-ESC.
  - >
    macOS falsifier (old MegaPane.tsx + TranscriptDrawer.tsx under the new spec, cold,
    retries 0): desktop D2 FAIL, tablet D1 + ROT FAIL, mobile D1 FAIL, the stranded
    `overflow: hidden` being the observed failure in each; with the repair every project
    passes (desktop 1/4 skipped, tablet 2/3, mobile 3/2, exit 0).
  - >
    Linux cross-host run at 332944f02 (cold, workers 1, retries 0): 6 passed / 9 skipped,
    36 s; the never-restore mutant lock there: 5 failed / 9 skipped / 1 passed, exit 1, the
    mobile A11Y-ESC failing on exactly the new final assertion (expected ""/"", received
    hidden/hidden); unit suite 4/4. Independent review of the round-3 diff: ACCEPT.
  - >
    Terminal issue #916 comment 6117929393 (2026-10-12 04:48Z) carries the full repair,
    falsifier and ordering record addressed to CEO A.
affects:
  - "WS:TERMINAL-ENHANCEMENTS20"
  - "terminal/lib/scrollLock.ts"
  - "terminal/components/MegaPane.tsx"
  - "terminal/components/TranscriptDrawer.tsx"
  - "terminal/components/**"
confidence: high
reversibility: easy
decided_by: coo-fable
decided_at: 2026-10-12
---

## Notes for the next overlay author

- Acquire with `const release = acquireScrollLock()` in the effect that opens the overlay
  and call `release()` in its cleanup; never write `document.body.style.overflow` directly.
- Four direct writers predate the lock and are logged as follow-ups, not part of #959:
  `GuidePanel.tsx`, `MobileSheet.tsx`, `AnalysisHubSheet.tsx`, `chartSettingsUi.ts`.
  Migrate each with its own spec case.
- Two residual spec gaps from the round-3 review are also follow-ups: a leak taken only by
  TranscriptSearchWorkspace or the intelligence-evidence overlay is unseen by the five
  cases, and the page's recorded `before` is the empty inline overflow (the unit suite
  pins non-empty restore).
- `/analysis` hosts the pane in flow with Escape inert and never acquires the lock; the
  ANALYSIS case is the negative control and must keep passing.
- At the time of writing #959 is accepted at 332944f02 but not yet merged: it refreshes
  onto master after landing train 3 (#960) squashes, recaptures its packet and arms.
