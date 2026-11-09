# PR 10896 — CI repair and evidence refresh

Date: 2026-11-09
Operation: `macro-saas-polish-20261109-astra-01`
Runtime source head: `5b4317c83934c8b82387fbad2d7afa3f5c57c6bb`
Protected Mastermind procedure pin: `494d095813dad415938800fa0e4d2719497738fa`

## Why this follow-up was required

Run 42621307439 found four candidate-caused failures: missing P0B shared-asset
receipt closure, two shifted copy-deck citations, a delayed-library test reading
selection across an asynchronous repaint, and the exact dashboard binding in
the EW-P4 visual receipt. The existing merge-on-green label was removed and
read back before edits. No live writer was displaced and no failed check was
rerun without a repair.

## Changes

- The delayed-library cases now wait for the actual 27-match repaint and
  `aria-busy=false` before checking the selected ticker, focused control,
  active descendant, page boundary and Enter destination. All existing
  behavioral assertions remain.
- Two copy-deck source citations now identify the current exact lines carrying
  the existing English/Chinese text. No copy or role changed.
- The existing pinned P0B renderer/verifier genuinely recaptured Hong Kong and
  Canada. Both receipts report pass, including seven initial states and 64 owner
  projection cases per market. The 16 owner-empty screenshots remain bound.
  The original baseline and all 20 historical repair extensions are retained.
- The existing EW-P4 probe genuinely recaptured all 68 cases; all 31 render and
  fixture inputs were compared with the exact capture source and current bytes.
- The existing W9 owner genuinely recaptured 74/74 states. Its manifest pins the
  unchanged runtime source head above. This closes the render-gate obligation
  as well as the immediate PR failures.

The repair changes test synchronization, source citations and evidence. It does
not change the already verified search/dialog runtime bytes.

## Verification

- 33 focused tests passed: all 20 original interaction-browser cases and the
  copy-deck owner.
- The 120 P0B source/receipt assertions were verified: 119 passed on the first
  complete run, then the sole stale manifest-binding assertion passed after
  the genuine captures were bound into the existing manifest history.
- The EW-P4 and W9 exact-source receipt checks both passed.
- P0B receipt-closure guard returned 0 on the complete diff against
  `9a13c64bf69f782332afa29efb09fe48ee30b857`.
- P0B used its required Chromium 149.0.7827.55 / Playwright 1.61.1 on darwin/arm64,
  including the required headless-shell digest and committed-font audit.
- Representative captured Risk Radar, P0B mobile and W9 dialog images were
  visually inspected. Captures use explicit fixture data and do not prove a
  production deployment or signed-in acceptance.

## Delivery state

This record supports a new source publication and natural CI run on the original
PR. Merge, a covering production render and actual live search/dialog acceptance
remain separate required steps. The broader main-dashboard redesign is isolated
in operation `macro-experience-redesign-20261109-astra-02`.
