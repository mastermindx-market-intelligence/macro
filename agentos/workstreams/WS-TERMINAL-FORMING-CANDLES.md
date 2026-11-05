---
key: TERMINAL-FORMING-CANDLES
title: Terminal forming candles — first implementation slice
objective: Complete the Hub forming-candle data, repair the live reducer, and share calendar/countdown boundaries so measured price changes update coherent OHLCV through the existing polling path; done requires required CI, an exact protected merge, deployment, and live verification with honest coverage.
status: active
program: terminal-charting
repos: [terminal]
owner: ceo-sol
class: build
blast_radius: user_facing
ambiguity: scoped
owns_paths:
  - hub/lib/formingCandles.js
  - hub/lib/polygon.js
  - hub/lib/quotes.js
  - terminal/lib/formingCandles.ts
  - terminal/lib/liveCandle.ts
  - terminal/lib/candleCalendar.ts
  - terminal/components/ChartPanel.tsx
  - terminal/components/TerminalShell.tsx
  - terminal/app/api/quote/route.ts
waves:
  - id: FIRST-SLICE
    title: Hub coverage, correction-aware live reducer, and shared countdown calendar
    status: done
    pr: 1102
    next_action: Retain the verified release ab5beab6b0c2362414a1da17745587d490e923e8; its production price observations exposed the bounded after-hours consumer defect tracked in SNAPSHOT-ETH.
  - id: SNAPSHOT-ETH
    title: Admit qualified pre/post snapshot prices as explicitly partial minute/hour candles
    status: in_progress
    pr: 1108
    next_action: During an eligible pre/post session, verify the serving generation contains 061e7625536d781239cbf687bea64a2e1076202a and observe genuine partial-candle movement and minute rollover. Deployment, source/public identity, compiled-asset delivery, quote contracts, and a closed-session browser inspection passed.
discoveries:
  - DSC:TERMINAL-FORMING-CANDLES-NEED-OWNERSHIP-AND-HISTORY-FENCES
decisions:
  - DEC:TERMINAL-ONE-LIVE-BAR-DERIVATION-BOUNDARY
do_not_redo:
  - The completed audit and accepted source reviews are settled unless contradicted by new evidence; continue from PR 1102.
  - Keep the existing chart derivation boundary and calendar/resamplers; do not create a second indicator, table, or session owner.
landmines:
  - Complete snapshots may retract extrema and volume; partial snapshots cannot claim unseen coverage or double-count an opaque history baseline.
  - Accepted initial, daily, and 24H background history must fence retained snapshots, even when the refreshed arrays compare equal.
  - Editing ChartPanel requires genuine recapture of its three locked screenshot evidence packets.
  - Hub currently uses delayed AM plus a real-time REST snapshot leg with an 8000 ms TTL; complete native forming activation requires a separately admitted shared OHLCV publication, not an environment-only change.
  - Preserve the existing authentication and seconds-band capability gates before quote cache access.
  - The production release owner requires a full protected target SHA; a constant BUILD_ID is not proof of served source.
next_action: Observe genuine pre/post-market partial-candle movement and rollover during an eligible session on the verified serving generation. Preserve accepted open/volume and confirm the shared countdown. Reconcile native producer/publication custody separately before any complete-feed activation.
---

# Scope and identity

This records the Chairman's 2026-10-21 request to continue the completed real-time
candle audit with its first implementation slice. The existing terminal-charting
program owns the chart behavior and consumes terminal-market-data. This is a
knowledge record of that assigned work, not a new runtime claim or execution grant.

The slice preserves the existing roughly one-second polling transport, native
U.S. provider entitlement, and the separate overnight provider path. New push
transport, new subscriptions, and new exchange calendars are outside this slice.

The native renderer replacement is a separate workstream, WS:NATIVE-CHART-ENGINE.
Its held performance protocol, default-engine flip, and retirement gates are
unchanged by this work.

The snapshot follow-up merged in Terminal PR 1108 as
`061e7625536d781239cbf687bea64a2e1076202a` at 2026-10-22T02:43:12Z.
All 17 jobs in the final CI run 39708563796 passed. The merged tree exactly
matches tested head `1912800565687e420e5a24e35b526525cb28276a`, and all
seven follow-up files match the reviewed candidate. Local checks passed 119
focused tests, TypeScript, and six fixture-driven browser cases across desktop,
tablet, and mobile. The git-gated production owner exited 0 at 03:02:08Z. Independent readback
at 03:03:37Z matched all seven installed source hashes, canonical HEAD, deployment
marker, and both public identity sets. Compiled-asset hashes matched their hosted
bytes, and the fresh browser loaded the matching reducer asset. The 92-second API
probe returned 38 HTTP 200 samples, preserved ordinary/mixed-seconds contracts,
and exposed no raw Hub payload. Its overnight response was a delayed snapshot
with no eligible pre/post print. The 1m ETH chart rendered without console errors
at 03:09:22Z. Positive post-fix pre/post-market movement and rollover remain
unverified; this deployment does not establish native complete or tick-complete
coverage.
