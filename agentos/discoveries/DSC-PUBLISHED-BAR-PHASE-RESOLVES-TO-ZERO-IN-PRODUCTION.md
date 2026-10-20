---
key: PUBLISHED-BAR-PHASE-RESOLVES-TO-ZERO-IN-PRODUCTION
claim: >
  The `session_anchor` phase contract published by #772 is correct, covered, and currently resolves
  to `barAnchor 0` on EVERY served document — so what #772 changes observably in production is the
  bar KEY CONVENTION (closing session to opening session) and the separate `closeTime` availability
  timestamp, not the phase. The reason is `index`, not `basis`: every stamped document carries
  `index: 0`, because the served feed begins at the symbol's own first listed session and the
  global session index therefore equals the array index. The consumer computes
  `barAnchor = anchor.index - at` clamped `>= 0` (terminal/lib/sessionBars.ts:110-111), which for
  `index: 0` is `-at` and clamps to 0 on every window, truncated or full — whatever the basis says.
  Measured on the serving host 2026-09-29, 81 stamped documents: 19 `basis: "ipo"` and 62
  `basis: "feed"`, `index: 0` on all 81, resolved `barAnchor 0` on all 81. Engine and browser AGREE
  under that resolution: `ingest/gen_slices_all.py:124-137` computes from the same served
  `<SYM>.json` array the browser reads, and the engine's published `bar_index` places every one of
  5,769 signals inside the bar the browser computes from the published anchor — 5,769/5,769.
falsifier: >
  On the serving host, resolve the published anchor the way the consumer does and check the phase
  it yields:
  `python3 -c "import json,glob,os;D='terminal/public/data';print([(os.path.basename(p)[:-5], json.load(open(p))['session_anchor']) for p in sorted(glob.glob(D+'/*.json')) if os.path.basename(p).count('.')==1 and json.load(open(p)).get('session_anchor')][:20])"`
  Any document with `index` greater than 0 whose anchor date sits at row 0 of its feed refutes the
  claim for that symbol — the phase IS live there, and the membership differential in
  DSC-A-REPHASED-GRID-SHARES-ZERO-BAR-KEYS must be re-measured with the resolved anchor rather
  than with 0. The AGREEMENT half is falsified by that differential dropping below 100%. Note the
  phase arithmetic is NOT unexercised: the generated golden
  terminal/lib/__tests__/fixtures/sessionBars3D.golden.json carries four `truncated` cases with
  `basis: "ipo"` and anchor indices 41/42/43/53, all reproducing the full grid's tail exactly, and
  the degenerate path is covered by name at sessionBars.test.ts:78-81 and :267.
so_what: >
  Four things a future session needs before touching this.
  First, `index` decides the phase and `basis` decides nothing at the consumer — see the section
  below. Do not read a `basis: "ipo"` document as having a live phase; check `index`.
  Second, do not "fix" this by making a producer emit a non-zero `index` from a truncated feed.
  `signal_layer/confluence.py:215-219` is explicit that the integer alone cannot distinguish
  "genuinely session 0 of a full-history feed" from "could not find out". For the 19 `ipo`
  documents `index: 0` is a VERIFIED statement that the feed starts at the symbol's first listed
  session, which is the legitimate case — not a fallback. Fabricating a non-zero index would
  silently re-phase every 3D bar and every marker on it against an engine that did not move.
  Third, do not accept a 3D grid repair on NVDA. Its served feed begins 1999-01-22, its own first
  listed session, so feed-phase and IPO-phase coincide and the symbol is structurally incapable of
  discriminating a phase error. It was the witness the original acceptance argument rested on.
  Fourth, do not read the resolution-to-zero as the repair having failed. Engine/browser agreement
  is what the product needs, it is measured rather than assumed, and the anchor's value today is
  that it makes the phase explicit and unfabricable rather than that it moves a bar.
kind: constraint
verified_at: 2026-09-29
verified_by: >
  Consumer arithmetic at terminal/lib/sessionBars.ts:110-111, producer at
  signal_layer/confluence.py:208-225, published in PR "#772" (d284493688ba).
  Read on the serving host after the 2026-09-29 21:30Z nightly began stamping: 81 stamped
  documents, basis 19 ipo / 62 feed, `index: 0` on all 81, resolved barAnchor 0 on all 81;
  membership of the engine's published `bar_index` against the browser grid computed from those
  published anchors, 5,769/5,769. Deep store on the serving host
  `/opt/macro/data/stocks` contains 247 parquet files, which is why 19 single stocks resolve
  `basis: "ipo"` while ETFs and ADRs absent from it fall back to `"feed"`. Consumer arithmetic
  confirmed by porting `resolveBarAnchor` and validating against the repository golden, where
  `basis: "ipo"` anchors 41/42/43/53 resolve to barAnchor 41/42/43/53 and reproduce the full grid.
scope:
  - mastermind-terminal terminal/lib/sessionBars.ts
  - mastermind-terminal ingest/session_anchor.py
  - mastermind-terminal ingest/gen_slices_all.py
  - macro signal_layer/confluence.py
  - "generation 8795dfb1e39c676bc62a80f846e1207979333a22 served at app.mastermind-x.com"
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
4. Served feeds begin at the symbol's first listed session, so step 1 returns index 0 where it
   succeeds, and step 3 yields `-at` → clamped to **0**, on every window.

⚠️ **The deep store is NOT absent on the serving host.** `ipo_bar_anchor`'s docstring
(`confluence.py:235-237`) says it returns 0 "when the deep store is unavailable (e.g. the rsync
VPS…)", and that parenthetical is **stale for this host**: `/opt/macro/data/stocks` holds 247
parquet files, and 19 symbols resolve a real `ipo` basis from it. An earlier draft of this record
asserted the store was absent and that every document carried `basis: "feed"`; both were wrong.
The inertness conclusion survived the correction because it never depended on the basis — only on
`index` being 0 — but the mechanism as first stated would have sent the next reader looking for a
missing store that is present.

## `basis` never gates the arithmetic — it carries cache identity only

⚠️ Do not cite `basis` in a receipt as though it constrained consumer behaviour. `resolveBarAnchor`
reads **only** `anchor.date` and `anchor.index`; it never references `.basis`. In the whole
consumer the anchor's `basis` occurs exactly twice:

- `terminal/lib/sessionBars.ts:78` — `parseSessionAnchor` copies it onto the object.
- `terminal/components/ChartPanel.tsx:473` — it is interpolated into a cache-key string,
  `${anchor.date}@${anchor.index}:${anchor.basis ?? ""}`.

(Every other `basis` in those files is an unrelated field: live-quote basis, signal basis, the
Bollinger mid-line.) So the field is not dead — a basis change invalidates the cached resample,
which is real and desirable — but it decides no phase. A producer emitting `basis: "ipo"` with a
WRONG `index` would be indistinguishable at the consumer from a correct one. The provenance
guarantee in `confluence.py:215-219` is PRODUCER-side documentation that nothing on the consumer
enforces; if it is ever meant to be load-bearing it needs a consumer check that does not exist.

Found by the TERMINAL-05 session while attempting to refute this record's golden coverage; the
attempted refutation (`grep -c feed` over `sessionBars.test.ts` returning 0) was itself withdrawn
as a wrong instrument, since counting a string the code never reads measures nothing.

## Two writers stamp, and only one is the universe-wide pass

⚠️ `ingest/build_polygon_universe.py` — the nightly's FIRST step — writes its own anchors for the
flagship set, and `ingest/stamp_session_anchors.py` at `ops/terminal-data:126` stamps the whole
published universe about an hour later. On 2026-09-29 the flagship anchors appeared at 21:30:56Z,
roughly 55 seconds into a run whose universe-wide pass had not started. A probe that asks "does
NVDA have an anchor yet" therefore answers YES long before the stamping pass has run, because NVDA
is a flagship. To observe the universe-wide pass, probe a NON-flagship symbol; 44 documents were
stamped at 21:32Z and 81 by 21:40Z, against 30,882 served documents in total.

Related: DEC-BAR-PHASE-IS-PUBLISHED-BY-THE-PRODUCER,
DSC-A-REPHASED-GRID-SHARES-ZERO-BAR-KEYS,
DSC-CHART-3D-GRID-DISAGREED-WITH-ENGINE-ON-EVERY-BAR.
