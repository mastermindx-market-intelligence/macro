---
key: BAR-PHASE-IS-PUBLISHED-BY-THE-PRODUCER
question: >
  Where does a multi-session (2D/3D) chart bar's phase come from — may the browser derive it
  from the rows it happens to hold, or must the producer that owns the session calendar
  publish it?
answer: >
  The producer publishes it. `ingest/session_anchor.py` stamps an additive anchor POINT
  (`{v, date, index, basis}`) onto each served OHLC document and `terminal/lib/sessionBars.ts`
  consumes it. The browser reproduces `signal_layer/confluence.py::_3d_groups`; it never
  re-derives the phase. `time` is the bar's OPENING session (identity); `closeTime` is the
  session on which its close became knowable (availability). The two are never collapsed.
rationale: >
  The phase is not a function of the data the browser holds. `/data/<SYM>.json` is a truncated
  feed for most names, so any client-side derivation is anchored to an arbitrary row and
  disagrees with the engine by one or two sessions. The failure was invisible for as long as it
  shipped because Oracle marker placement used nearest-bar snapping with a ~10-day tolerance,
  so every marker landed on a plausible neighbouring candle. Measured on the shipped
  1,255-session NVDA document, the old and new grids agreed on 0 of 419 bar keys while both
  produced 419 candles. A wrong phase must MISS, not snap.
alternatives:
  - option: Derive the phase in the browser from the loaded rows (`Math.floor(i / mult)`).
    why_not: >
      This was the shipped behaviour and the defect. It is anchored to row 0 of whatever
      history loaded, so the same symbol re-phases when the feed is truncated or backfilled,
      and it never agrees with the engine on a truncated feed.
  - option: Publish a bare integer anchor instead of an anchor point.
    why_not: >
      A bare integer does not survive the nightly. Prepending 200 backfilled sessions moves
      row 0's global index 4245 -> 4045; only a (date, index) pair can be re-resolved against
      the new array. Pinned by
      `test_the_anchor_survives_the_nightly_appending_and_backfilling_history`, which is red
      under the bare-integer reading.
  - option: Have the browser fetch the engine's grid directly per symbol/timeframe.
    why_not: >
      Adds a per-view network dependency and a second source of truth for a fact that is one
      small constant per document. The anchor is additive metadata on data the client already
      fetches.
evidence:
  - >
    mastermind-terminal PR #772, squash d284493688ba1d200c93e0b5b075edf1f3da041c; adopts and
    supersedes the unmerged #644. PR #775 closes the second copy of the stamping-seam pointer.
  - >
    Old vs new grid on the shipped 1,255-session NVDA document: same-index key matches 0/419,
    same-index membership differences 419/419, both producing 419 candles.
  - >
    Discriminating mutation matrix re-run at the merged tree, terminal/lib/sessionBars.ts
    byte-identical to the installed blob: baseline 31 passed; anchor-blind phase 12 failed;
    close-keyed identity 12 failed; closeTime collapsed onto time 10 failed; published anchor
    discarded 10 failed; bare-integer anchor 1 failed; close-keyed signal map 3 failed. Command:
    cd terminal && npx vitest run lib/__tests__/sessionBars.test.ts
    lib/__tests__/resampleCacheIdentity.test.ts
  - >
    Live acceptance on the served generation: five independent time-axis crosshair reads, every
    key in the canonical grid and in no grid the previous rule could produce; final bar keyed
    2026-09-25 while the document's last session is 2026-09-28, which is identity vs availability.
  - >
    Engine-to-chart signal placement: bar_index minus canonical_bar(ts) is {0: 317} and bar_index
    minus canonical_bar(known_ts) is {0: 317} across 317 signals spanning 27 years, no look-ahead.
  - >
    Full Python suite at the merged tree: 1277 passed, 8 skipped. Command:
    PR_NUMBER=775 python3 -m pytest tests/ -q
  - >
    Evidence is retained privately. No licensed dataset and no production capture is published in
    this record or in either public PR; only counts, hashes and SHAs appear here.
affects:
  - mastermind-terminal terminal/lib/sessionBars.ts
  - mastermind-terminal terminal/components/ChartPanel.tsx
  - mastermind-terminal ingest/session_anchor.py
  - mastermind-terminal ingest/stamp_session_anchors.py
  - mastermind-terminal ops/terminal-data
  - any future consumer of a multi-session bar grid, overlay, drawing anchor or Oracle marker
confidence: high
reversibility: costly
decided_by: Claude Opus principal, TERMINAL-01 commission (2026-09-29)
decided_at: 2026-09-29
review_by: 2026-12-31
---

## Reversibility, precisely

The DEPLOYMENT is trivially reversible: `541330e4c90593f0ec60918347330d3194c2c5ab` remains an
ancestor of `origin/master`, so the incumbent git-gated release admits it as a target SHA and
restores a compatible accepted bundle/source combination. The DECISION is `costly` to reverse
because reverting it reintroduces the defect. Two constraints hold on any revert: the additive
`session_anchor` field MUST be preserved, and stored signals must never be re-phased to match a
reverted visual grid.

## Decision scope

Bar membership, bar identity and bar availability for the `D`, `2D` and `3D` session-derived
timeframes, and the placement of engine signals onto those bars. `W / 2W / 1M / 3M` are calendar
units with no phase freedom and are deliberately untouched.

This record decides where the phase comes from. It grants no authority over indicator formulas,
fire thresholds or trade logic, and it does not declare the chart-engine program complete.

## What is true now

- The grid rule is `gi[i] = i + barAnchor`; `open(0)` is unconditional; `open(i)` iff
  `gi[i-1] % mult == 0`; `close(b) = open(b+1) - 1`. Each bar is keyed by its OPENING session.
- Each comparison leg carries its own anchor before the date join, so two legs with different
  history starts meet only on the real global calendar.
- The aggregation memo carries the source `bars` array identity plus the anchor, because
  `symbol::timeframe` said nothing about WHICH OHLC it was built from.
- **In production `basis` is always `feed` and `index` always 0, and that is correct.**
  `ipo_bar_anchor_basis` resolves a symbol's own calendar from
  `<macro>/data/stocks/<SYM>.parquet`; the VPS that runs the nightly has no parquet store.
  Consequently `resolveBarAnchor(dates, {index:0, date:dates[0]})` and
  `resolveBarAnchor(dates, null)` both return 0 — **the stamp is behaviourally inert on today's
  production documents.** It is a guarantee for the first truncated or re-cut feed, not a live
  correction. The grid correctness proven live does not depend on it.

## Exact next action

Not required by this decision, and not claimed as done: a deep session store on the host that
runs the stamping pass, which is what would let `basis: ipo` resolve in production. Until then a
served `basis: feed` is expected output and must not be read as a broken pipeline.

## Do not redo

- Do not re-derive bar phase in a client from loaded rows, under any tolerance.
- Do not collapse `time` and `closeTime`. One direction leaks future signal; the other misplaces
  it on the chart.
- Do not read the anchor as a bare integer, and do not treat an already-stamped document as
  immutable — both are red under the nightly-survival test.
- Do not cite a production document as proof the `ipo` path works; a fixture carrying
  `basis: feed` is likewise not proof of the IPO path.
- A backfill legitimately drops exactly one bar boundary — the forced row-0 partial. The
  invariant is `set(opens_before) - set(opens_after) == {row-0 date}`, not set equality. Do not
  "fix" this as a re-phasing bug.
- Do not overwrite the stale hand-made `NVDA.slice.json` fixture to make signal counts agree;
  that is a separate, still-open issue.
