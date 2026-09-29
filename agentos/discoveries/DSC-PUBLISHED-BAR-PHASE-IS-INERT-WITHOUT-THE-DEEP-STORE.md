---
key: PUBLISHED-BAR-PHASE-IS-INERT-WITHOUT-THE-DEEP-STORE
claim: >
  The `session_anchor` phase contract published by #772 is CORRECT and TESTED but behaviourally
  INERT in production, and will stay inert until the deep parquet OHLC store is reachable from
  the host that stamps. `signal_layer/confluence.py:221-225` resolves `basis: "ipo"` only by
  reading `DATA/<symbol>.parquet`; that store is absent on the serving VPS, so every stamped
  document carries `basis: "feed", index: 0`. `basis` is producer-side provenance only — the
  consumer never branches on it (see the section below), so `index` and `date` alone decide
  phase. The consumer then computes
  `barAnchor = anchor.index - at` clamped to `>= 0` (terminal/lib/sessionBars.ts:110-111), which
  for `index: 0` is `-at` and therefore resolves to 0 on EVERY window, truncated or full. What #772
  actually changes in production is the bar KEY CONVENTION (closing session to opening session) and
  the separate `closeTime` availability timestamp. Engine and browser nevertheless AGREE, because
  `ingest/gen_slices_all.py:124-137` computes from the same served `<SYM>.json` array the browser
  reads and calls `confluence.ipo_bar_anchor(close, sym)`, which returns 0 on that host for the
  same deep-store reason. Both sides phase at the feed's first row. TradingView phase parity on
  truncated feeds remains broken and is pre-existing, documented at
  `signal_layer/confluence.py:235-237` ("possibly phase-shifted vs TV until full history is fed").
falsifier: >
  Read any stamped served document and the consumer's resolution:
  `python3 -c "import json;print(json.load(open('terminal/public/data/NVDA.json')).get('session_anchor'))"`
  on the serving host. A `basis` of `"ipo"` or a non-zero `index` refutes the inertness claim for
  that symbol and means the phase correction IS live there. Conversely `ls
  "$MACRO_REPO/data/stocks" | wc -l` returning a populated store on the stamping host refutes the
  cause. The AGREEMENT half is falsified by the differential in
  DSC-A-REPHASED-GRID-SHARES-ZERO-BAR-KEYS dropping below 100% for the canonical grid. Note the
  phase machinery itself is NOT unexercised: the generated golden
  terminal/lib/__tests__/fixtures/sessionBars3D.golden.json carries four `truncated` cases with
  `basis: "ipo"` and anchor indices 41/42/43/53, all of which reproduce the full grid's tail
  exactly, so a claim that the phase code is untested is also refuted.
so_what: >
  Three things a future session needs before touching this.
  First, do not "fix" the anchor by making the stamper emit a non-zero `index` from a truncated
  feed. `confluence.py:215-219` is explicit that the integer alone cannot distinguish "genuinely
  session 0 of a full-history feed" from "could not find out", and `basis` exists precisely so a
  consumer cannot fabricate an IPO phase. Fabricating it would silently re-phase every 3D bar and
  every marker on it against an engine that did not move.
  Second, do not accept a 3D grid repair on NVDA alone. Its served feed begins 1999-01-22, its own
  first listed session, so feed-phase and IPO-phase coincide and the symbol is structurally
  incapable of discriminating a phase error. Any acceptance argument resting on it is testing half
  the change.
  Third, do not read the inertness as a defect or as the repair having failed. Agreement between
  engine and browser is what the product needs and it is measured, not assumed; the anchor's value
  today is that it removes the ambiguity rather than that it moves a bar. Turning the phase live is
  gated on deep-store availability on the stamping host, which is a data-plane question, not a
  chart question.
kind: constraint
verified_at: 2026-09-29
verified_by: >
  Read on the serving host: `terminal/public/data/*.json` carrying no `session_anchor` before the
  first natural stamping pass, and `basis` values of the published contract per
  `ingest/session_anchor.py:20-36`. Local deep store
  "/Users/chriswong/Documents/Cluade/Macro Dashboard/data/stocks" contains 1 parquet file
  (SATS.parquet), so the fallback is reached on the development host too. Consumer arithmetic
  confirmed by porting `resolveBarAnchor` and validating against the repository golden, where
  `basis: "ipo"` anchors 41/42/43/53 resolve to barAnchor 41/42/43/53 and reproduce the full grid.
  Engine/browser agreement measured at 81,503/81,503 sampled signals over 500 symbols
  (`random.seed(772)`), against 14,338/81,503 for the pre-#772 grid.
scope:
  - mastermind-terminal terminal/lib/sessionBars.ts
  - mastermind-terminal ingest/session_anchor.py
  - mastermind-terminal ingest/gen_slices_all.py
  - macro signal_layer/confluence.py
  - "generation d284493688ba1d200c93e0b5b075edf1f3da041c served at app.mastermind-x.com"
confidence: verified
---

## The resolution chain, end to end

1. `signal_layer/confluence.py:208-225` — `ipo_bar_anchor_basis` tries
   `pd.read_parquet(DATA / f"{symbol}.parquet")`. Success gives `(global_index, "ipo")`; any
   exception gives `(0, "feed")`.
2. `ingest/session_anchor.py:87-93` — publishes `{v, date, index, basis}`, the anchor POINT at the
   feed's FIRST session, so a later backward extension stays correct.
3. `terminal/lib/sessionBars.ts:95-111` — `resolveBarAnchor` binary-searches the anchor date,
   computes `anchor.index - at`, and clamps negatives to 0.
4. With `index: 0`, step 3 yields `-at` → clamped to **0**, for every window.

`ipo_bar_anchor`'s own docstring names the condition: it returns 0 "when the deep store is
unavailable (e.g. the rsync VPS, or a non-US symbol not in the store) — the 3D bars are then
anchored at the feed's first row: still session-grouped (fixing the resample('3B') bug) but
possibly phase-shifted vs TV until full history is fed."

## Why this is coherent rather than broken

The docstring at `ingest/session_anchor.py:11` states that `/data/<SYM>.json` "IS a truncated feed
for most symbols". A truncated feed phased at its own row 0 does not match TradingView. But the
comparison the product must satisfy is browser against ENGINE, and both reach the same fallback
from the same array — so the markers land on the candles the engine named. The 500-symbol
differential in DSC-A-REPHASED-GRID-SHARES-ZERO-BAR-KEYS measures exactly that.

The consequence worth stating plainly: publishing the anchor is a correctness guarantee against a
FUTURE consumer inventing a phase, not a visible change today. Both halves are true at once and a
record that asserted only the first would mislead.

## `basis` never gates the arithmetic — it carries cache identity only

⚠️ Do not cite `basis` in a receipt as though it constrained consumer behaviour. `resolveBarAnchor`
(`terminal/lib/sessionBars.ts:95-111`) reads **only** `anchor.date` and `anchor.index`; it never
references `.basis`. In the whole consumer the anchor's `basis` occurs exactly twice:

- `terminal/lib/sessionBars.ts:78` — `parseSessionAnchor` copies it onto the object.
- `terminal/components/ChartPanel.tsx:473` — it is interpolated into a cache-key string,
  `${anchor.date}@${anchor.index}:${anchor.basis ?? ""}`.

(Every other `basis` in those files is an unrelated field: live-quote basis, signal basis, the
Bollinger mid-line.) So the field is not dead — a basis change invalidates the cached resample,
which is a real and desirable property — but it decides no phase. The consequence: a producer that
emitted `basis: "ipo"` with a WRONG `index` would be indistinguishable at the consumer from a
correct one, and no basis check anywhere would catch it. The provenance guarantee described in
`signal_layer/confluence.py:215-219` is a PRODUCER-side contract documented for humans; nothing on
the consumer enforces it. If that guarantee is ever meant to be load-bearing, it needs a consumer
check that does not exist today.

Found by the TERMINAL-05 session while attempting to refute this record's golden coverage; the
attempted refutation (`grep -c feed` over `sessionBars.test.ts` returning 0) was itself withdrawn
as a wrong instrument, since counting a string the code never reads measures nothing. The feed
path IS covered directly — `resolveBarAnchor(times, null) -> 0` and an out-of-range anchor date
-> 0 (`sessionBars.test.ts:78-81`), and `resampleTf(toBars(leg.bars), tf, null)` carrying the
comment `// no anchor = feed-phased` (`:267`) tests the production configuration by name.

Related: DEC-BAR-PHASE-IS-PUBLISHED-BY-THE-PRODUCER,
DSC-A-REPHASED-GRID-SHARES-ZERO-BAR-KEYS,
DSC-CHART-3D-GRID-DISAGREED-WITH-ENGINE-ON-EVERY-BAR.
