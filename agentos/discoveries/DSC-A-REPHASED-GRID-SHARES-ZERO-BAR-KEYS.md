---
key: A-REPHASED-GRID-SHARES-ZERO-BAR-KEYS
claim: >
  CORRECTED 2026-09-29 — the original claim was true but over-general and its falsifier could not
  fail. Narrow fact: #772 changed BOTH the phase rule and which session keys the bar, and it is
  the KEY-CONVENTION change alone (previous grid keyed each bucket by its CLOSING session, the
  canonical grid by its OPENING session) that makes the two key sets disjoint over a feed with
  unique session dates. On the served 6,963-session NVDA document the canonical grid yields 2,322
  keys, the previous feed-start floor(i/3) grid 2,321, and the intersection is empty. Two grids
  differing ONLY in phase can and do share keys, so the original generalisation to "differ in
  phase or in which session keys the bar" is withdrawn. What a single crosshair read decides is
  therefore the key CONVENTION, not the phase.
falsifier: >
  The instrument must derive the previous grid from the pre-#772 code path and must FAIL on it.
  Transcribe `541330e4c905:terminal/components/ChartPanel.tsx::resampleTf` (3D branch: k =
  floor(i/mult), and `cur.time = r.time` on every fold, hence a CLOSING-session key) and test the
  engine's own published placement from `<SYM>.slice.json -> indicator.signals[]`, whose
  `bar_index` names a bar and whose `ts` is the DAILY session the signal fired on: assert `ts` is
  a member of the sessions spanned by `bar_index`. Measured over 500 symbols sampled
  `random.seed(772)` from 10,551 served slices, 81,503 signals, all `indicator.timeframe == "3D"`:
  canonical grid 81,503/81,503 = 100.0%, pre-#772 grid 14,338/81,503 = 17.6%. A canonical result
  below 100% refutes the claim; a pre-#772 result at or near 100% means the instrument is not
  discriminating and must be discarded. Cross-check that binds the two runs: the 14,338 pre-#772
  agreements must equal exactly the count of signals at offset 2 within their canonical bar, since
  old bar b spans [3b, 3b+2] and canonical bar b spans [3b-2, 3b], intersecting only at 3b.
  See terminal/lib/sessionBars.ts:120 (`sessionBarOpens`) and PR "#772".
so_what: >
  Live acceptance of a bar-grid repair needs no bulk export, licensed capture or privileged
  endpoint — but a crosshair read accepts LESS than it appears to. It establishes the key
  convention and identity-vs-availability; it cannot establish phase, and on a symbol whose feed
  begins at its own first listed session (NVDA does) feed-phase and IPO-phase coincide, so that
  symbol cannot discriminate phase at all. The instrument that does scale is the engine's own
  published `ts` / `known_ts` / `bar_index` triple in `<SYM>.slice.json`: it tests membership and
  availability against the browser's grid over tens of thousands of real signals, it needs no
  entitlement, and it HAS a negative case.
  The governing lesson is about evidence, not about grids. The original falsifier hardcoded both
  conventions, so its two index sets were {0,1} mod 3 and {2} mod 3 — disjoint by construction.
  It would have printed the same reassuring `0` had the shipped phase been wrong, and its only
  empirical content was "the bars array has no duplicate dates". Correct algebra transcribed by
  hand is not an instrument. Before recording a measurement, run the negative case; if no input
  can make the check fail, it is not evidence.
  Corollary that still stands: because the grids share no keys, EVERY marker sat on the wrong
  candle, yet nearest-bar snapping with a ~10-day tolerance put each on a plausible neighbour.
  Total disagreement and plausible output are not in tension.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  mastermind-terminal PR "#772" (d284493688ba). Differential over served
  terminal/public/data/*.{json,slice.json}: canonical 81,503/81,503 vs pre-#772 14,338/81,503;
  availability `known_ts` in span and `known_ts >= ts` 81,503/81,503. Grid transcription validated
  against the repository's generated golden
  terminal/lib/__tests__/fixtures/sessionBars3D.golden.json — full-history 2D 61 bars and 3D 41
  bars exact on time/closeTime/sessions/OHLCV, and all four `truncated` cases (dropLeading
  41/42/43/53, basis "ipo", resolved barAnchor 41/42/43/53) reproducing the full grid's tail with
  zero mismatches. Original over-general claim and tautological falsifier found on independent
  read by the TERMINAL-05 session and reproduced before retraction.
scope:
  - mastermind-terminal terminal/lib/sessionBars.ts
  - mastermind-terminal terminal/components/ChartPanel.tsx
  - mastermind-terminal 2D/3D session-derived timeframes
  - "generation d284493688ba1d200c93e0b5b075edf1f3da041c served at app.mastermind-x.com"
confidence: verified
---

## What was wrong with the first version of this record

The published falsifier was:

```
new={b[i] for i in range(len(b)) if i==0 or (i-1)%3==0}
old={b[min(i+2,len(b)-1)] for i in range(0,len(b),3)}
len(new & old)
```

Both conventions are **hardcoded into the formula**, which therefore reads the shipped phase from
nowhere. The index families are `{0,1} mod 3` and `{2} mod 3`, disjoint by construction, so with
unique session dates `0` is forced. Controls that all still returned `0`: arbitrary unique keys
with no grid semantics; the whole array shifted by one session (a phase error); and any change to
the deployed phase whatsoever. Only injecting a duplicate date made it non-zero.

The algebra was not arbitrary — `floor(i/3)` is verbatim pre-#772 and `min(i+2,n-1)` correctly
derives the old CLOSING-session key, because the old fold branch assigns `cur!.time = r.time` on
every row. That is why the underlying claim survived. It is also why the test was dangerous: it
looked principled and could not fail.

## How the live read is taken (unchanged, and still correct within its limits)

⚠️ Read the key from the **canvas time-axis crosshair label**. Do **not** read it from the legend:
`.status-ohlc` always shows the LAST bar, never the hovered one, so a hover sweep returns an
identical string at every x position and looks like a dead crosshair. A session that mistakes this
for a broken crosshair will conclude the chart is unreadable and reach for a data export it does
not need.

Five reads on the served generation, each belonging to the canonical grid and to no grid the
previous rule could produce: `22 Jan '99` (the forced row-0 partial), `23 Mar '26`, `14 Sep '26`,
`22 Sep '26`, `25 Sep '26` (final bar).

- **Identity vs availability.** The final bar's key is `2026-09-25` while the document's last
  session is `2026-09-28`. The bar is named by the session it OPENED on, not the one that closed
  it — visible without instrumentation, and matching the prediction recorded before the read.
- **The aggregation is the canonical bucket.** The legend's `O`/`H`/`L` for the final bar match the
  canonical final bucket and mismatch the previous rule's bucket on both `O` and `L`. `C` tracks
  the live quote rather than the stored close — watch it tick while `O`/`H`/`L` hold constant, and
  do not treat that as a mismatch.

These five reads are retained because they are true and cheap. They are no longer offered as the
acceptance argument; the 500-symbol differential is.

## Signals are daily-resolution events, not bar-keyed events

⚠️ The first attempt at the placement measurement asked whether a signal's `ts` was itself a bar
key and got 198/317 (~63%) on NVDA, which reads as a partial failure and is a wrong question.
Signals are daily-resolution events ASSIGNED to a 3D bar via `bar_index` (the engine's own
`honest_read` says "confluence on daily—3D"). Measured offsets of `ts` within its owning bar
across the 500-symbol sample are `{0: 52903, 1: 14262, 2: 14338}` — all three positions occur, so
membership is the contract and identity is not. Splitting the original 63% by era gave a uniform
56–67%, which ruled out a phase offset (a real phase error would have given ~0%) and is what
exposed the question as wrong rather than the code.

Availability holds exactly: `known_ts` is a session inside the same bar and never earlier than
`ts`, on 81,503 of 81,503 sampled signals — no future look-ahead and no pre-knowledge.

Related: DEC-BAR-PHASE-IS-PUBLISHED-BY-THE-PRODUCER,
DSC-PUBLISHED-BAR-PHASE-IS-INERT-WITHOUT-THE-DEEP-STORE,
DSC-ACCEPTANCE-PROBE-CAN-FIRE-ON-THE-NEGATIVE-CASE.
