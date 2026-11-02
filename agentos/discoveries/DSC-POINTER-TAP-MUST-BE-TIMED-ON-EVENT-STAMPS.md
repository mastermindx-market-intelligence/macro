---
key: POINTER-TAP-MUST-BE-TIMED-ON-EVENT-STAMPS
claim: >
  A gesture classifier that reads performance.now() INSIDE a pointer handler is
  measuring dispatch latency, not gesture duration — the browser queues input
  behind whatever the main thread is already doing — so on any busy thread a
  physically instantaneous tap is misclassified as a long press; the event's own
  timeStamp carries the platform time the event was generated and is immune.
falsifier: >
  mastermind-terminal PR #633 reproducible falsifier: drive a real browser and
  rerun `terminal/e2e/marker-tooltip.spec.ts:470`; hold the main thread N ms
  from a window BUBBLE-phase
  pointerdown listener (capture:false, so every product handler has already
  recorded its start time), then tap with zero travel. If the handler-clock
  delta did NOT track N while the two events' timeStamps stayed <1ms apart, the
  two clocks are not separable and this is wrong. Measured on the Terminal chart
  at bb2e2270 (pre-fix): N=0/120/250 -> tooltip OPEN, N=400/700 -> tooltip DEAD,
  travelPx=0 and eventStampDelta=0 at every N, on tablet AND mobile, for BOTH
  the signal-marker and premium-prim tooltip layers. Note what does NOT falsify
  it: general CPU saturation. 40 busy processes on a 24-core Mac left 120/120
  taps clean, because the renderer main thread still got scheduled promptly —
  only blocking that thread reproduces it.
so_what: >
  Any future touch/pointer gesture predicate in Terminal (or a native shell
  bridging to one) takes the events' timeStamps and falls back to the handler
  clock only when an endpoint cannot date itself; treat a `0` stamp as
  undateable, since a pair of zeroes makes a five-second press look
  instantaneous. Consume stamps ONLY as a delta between two events of one
  gesture — then epoch and unit need not match performance.now(), which is what
  makes an epoch-ms timeStamp safe. And when a threshold is deliberately SHARED
  across layers (here 300ms/12px across the marker tooltip, the prim tooltip and
  ChartPanel's double-tap maximize, so one gesture cannot be a tap for one and a
  drag for another), every consumer moves together — fixing a subset creates
  exactly the divergence the sharing existed to prevent. Diagnostic tell: a
  tooltip node present in the DOM but EMPTY means a guard rejected the gesture
  before the tooltip was ever written, not that it opened and was hidden.
kind: landmine
verified_at: 2026-09-18
verified_by: "mastermind-terminal PR #633 (1f56eae265bd). Pre-fix CI failure run 35302575443 [mobile] terminal/e2e/marker-tooltip.spec.ts:470 — '.mm-sig-tip' resolved EMPTY and hidden. Repair in terminal/lib/markerTooltip.ts (gestureStamp/isTapSample) + its two callers; mutation (force the event clock off) turns all four new browser cases red. Live on app.mastermind-x.com: janked tap perfDelta=401ms, eventStampDelta=0ms, tooltip OPEN, while a genuine 650ms press stays refused, on 390x844 and 820x1180."
scope:
  - "mastermind-terminal"
  - "terminal/lib/markerTooltip.ts"
  - "terminal/lib/indicator-canvas/render.ts"
  - "terminal/components/ChartPanel.tsx"
  - "any future pointer/touch gesture predicate"
confidence: verified
---

The structural rule this sits beside is unchanged and was NOT the defect: both
overlay layers stay `pointer-events:none` and resolve tooltips from delegated
wrapper events, because lightweight-charts owns pan/crosshair/wheel/pinch on a
SIBLING canvas subtree that a hit-testable overlay node would permanently cut
off. See the module header in `terminal/lib/markerTooltip.ts`.

Second, unrelated finding from the same reproduction, recorded because it wears
the same costume: `usable()` in `terminal/e2e/indicator-prim-tooltip.spec.ts`
filtered by absolute pixel insets sized for desktop-only gestures, leaving a
70px-wide window on a 390px viewport — 9 failures in 24 mobile repeats on
pristine master, all `should paint at least two premium prims`, none a product
fault and none retry-fixable. A viewport-proportional cap left the desktop band
byte-identical and made it 24/24. A responsive harness must not carry absolute
insets tuned at one breakpoint into another.
