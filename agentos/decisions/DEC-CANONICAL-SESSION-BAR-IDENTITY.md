---
key: CANONICAL-SESSION-BAR-IDENTITY
question: >
  How should the Terminal chart decide which daily sessions share a 2D/3D bar,
  and what timestamp identifies that bar to every other consumer?
answer: >
  The producer publishes the grid's phase; the browser reproduces it and never
  re-derives it. Each OHLC document carries an additive top-level
  `session_anchor` = {v, date, index, basis} — an anchor POINT, not a bare
  integer. Each bar is keyed by its OPENING session (`time`, the identity) and
  separately carries the session on which it completes (`closeTime`, the
  availability). signal_layer/confluence.py::_3d_groups stays the sole authority.
rationale: >
  The phase of a 2D/3D grid is the symbol's global session index counted from its
  first listed session. That is NOT a property of the rows the browser holds:
  /data/<SYM>.json is a truncated feed for many symbols, so a browser that buckets
  from its own row 0 invents a phase. The engine indexes signals by the bar's OPEN
  while the chart stamped each bucket with its CLOSE, so the two disagreed about
  which candle a signal belonged to. Publishing an anchor POINT rather than an
  integer is what survives the nightly: append leaves it untouched, and a backwards
  history extension moves row 0's global index (measured: 4245 -> 4045 after
  prepending 200 sessions) while the {date,index} pair still resolves correctly.
  `basis` is load-bearing and cannot be folded into the integer: "ipo" means the
  deep store resolved the symbol's calendar, "feed" means it did not and index 0 is
  the engine's own fallback rather than a claim about the IPO — and 0 is also the
  legitimate anchor of a full-history feed, so a consumer conflating them would
  fabricate an IPO phase out of truncated data.
alternatives:
  - option: Derive the phase in the browser from the loaded feed (the prior behaviour)
    why_not: >
      The feed is truncated for many symbols, so row 0 is not session 0. This is the
      defect being repaired; it disagreed with the engine on every bar.
  - option: Publish a bare integer bar_anchor
    why_not: >
      Does not survive backwards history extension — the integer silently becomes
      wrong when the nightly deepens history, with no way for a consumer to detect it.
  - option: Key bars by their CLOSING session
    why_not: >
      Disagrees with both the signal engine and TradingView, whose 3D crosshair key is
      the opening session. It also destroys the distinction between identity and
      availability, which is what made signal placement unfixable.
  - option: Keep nearest-bar snapping as the reconciliation layer
    why_not: >
      Snapping has a ~10-day tolerance and a phase error is one or two sessions, so it
      CONCEALED a total disagreement rather than reconciling it. A wrong phase must
      miss, not snap.
evidence:
  - "charting-app PR #772 (adopts and supersedes the stale #644 carrier)"
  - "signal_layer/confluence.py::ipo_bar_anchor_basis — returns (index, basis)"
  - "ingest/session_anchor.py (contract) -> ingest/stamp_session_anchors.py (publisher) -> terminal/lib/sessionBars.ts (consumer)"
  - "Wired at ops/terminal-data:125, after the last OHLC writer, before gen_slices_all.py"
  - "Measured on the live https://app.mastermind-x.com/data/NVDA.json (6,963 sessions, 1999-01-22..2026-09-28): pre-repair chart vs engine = 0/2321 same-index key matches, 2321/2321 membership differences, 2321 candles vs the engine's 2322"
  - "Cross-language parity on that same production document: terminal/lib/sessionBars.ts and signal_layer/confluence.py produce identical keys AND identical closeTimes for all 2322 3D bars"
  - "Truncated starts at drops 41/42/43/53/1000/1001/1002/5000 (all three 3D residues) are exact suffixes of the canonical full-history grid"
affects:
  - charting-app
  - terminal/components/ChartPanel.tsx
  - terminal/lib/sessionBars.ts
  - signal_layer/confluence.py
  - ingest/session_anchor.py
  - ingest/stamp_session_anchors.py
  - ops/terminal-data
confidence: high
reversibility: costly
decided_by: "session 45d83bc6-2754-4dea-a803-606d6cab93d1 (TERMINAL-01, native Opus principal)"
decided_at: 2026-09-29
---

`session_anchor` is additive and versioned (`v: 1`). A consumer that does not know the
field keeps working on the feed-start phase it already used, so publication was safe to
land before every consumer had adopted it.

W/2W/1M/3M are calendar units with no phase freedom and are deliberately untouched:
their key remains the bucket's LAST session, which every existing consumer
(`lib/barSnap`, `lib/pine-engine/runtime`, `TechnicalsPage`) is written against.

Out of scope by decision: the stale hand-made `NVDA.slice.json` fixture was NOT
rewritten to make signal counts agree, and no indicator formula, fire threshold or
trade logic was changed. See DSC:CHART-3D-GRID-DISAGREED-WITH-ENGINE-ON-EVERY-BAR.
