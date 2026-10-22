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
    next_action: Complete protected CI and merge for the tested follow-up, deploy the contained merged source, and verify release identity and current-session health. Positive pre/post-market movement and minute rollover still require an eligible live session.
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
next_action: Carry Terminal PR 1108 through protected CI, merge, deployment, and independent identity/current-session checks; then observe genuine pre/post-market partial-candle movement and rollover. Keep native complete-feed activation separate.
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

The snapshot follow-up is implemented and reviewed in Terminal PR 1108. The final
local checks passed 119 focused tests and TypeScript, plus six fixture-driven
browser cases across desktop, tablet, and mobile. Its seven changed files remain
byte-identical after updating the branch onto the deployed news release. These
checks establish the tested behavior; post-fix live pre/post-market movement and
rollover remain unverified at this release checkpoint.
