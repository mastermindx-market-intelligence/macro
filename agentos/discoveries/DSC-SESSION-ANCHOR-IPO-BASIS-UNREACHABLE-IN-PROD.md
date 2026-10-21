---
key: SESSION-ANCHOR-IPO-BASIS-UNREACHABLE-IN-PROD
claim: >
  Every `session_anchor` published in production carries basis "feed", never
  "ipo", because signal_layer.confluence.ipo_bar_anchor_basis resolves the IPO
  calendar from the Macro deep store at <macro>/data/stocks/<SYM>.parquet, that
  store holds exactly ONE symbol (SATS.parquet) on the Mac and does not exist at
  all on the VPS, and the nightly that stamps the documents runs on the VPS.
falsifier: >
  On the VPS, run ipo_bar_anchor_basis for any symbol and get "ipo" back, or find
  any *.parquet under the path signal_layer.confluence.DATA resolves to there
  (`find /opt/terminal -name '*.parquet'` currently returns nothing). Equivalently,
  fetch any stamped https://app.mastermind-x.com/data/<SYM>.json and read
  session_anchor.basis == "ipo".
so_what: >
  Do NOT read basis "feed" in a production document as a bug, as a broken
  pipeline, or as evidence the anchor was not published — it is the designed,
  honest fallback meaning "the deep store did not resolve this symbol; index 0
  means phase at this feed's own first row". Equally, do NOT cite a production
  document as proof the "ipo" path works; only SATS exercises it, and only where
  the deep store is present. Any future work that genuinely needs a true IPO phase
  in production — a truncated CN/HK feed is the realistic case — must first put
  the deep store where the stamping runs, or move the stamping to a host that has
  it. That is a prerequisite, not a detail.
kind: runtime
verified_at: 2026-09-29
verified_by: >
  signal_layer/confluence.py:208-225 (ipo_bar_anchor_basis reads DATA/<symbol>.parquet,
  returns (0,"feed") on any exception); confluence.py:55 DATA = <macro>/data/stocks;
  `ls <macro>/data/stocks` = 1 entry, SATS.parquet; on the VPS
  `find /opt/terminal -maxdepth 3 -name '*.parquet'` returns no files; VPS crontab
  runs `30 21 * * * /usr/local/bin/terminal-data`, so stamping happens there.
  Rehearsed the stamp on 8 real production documents: all 8 returned basis "feed".
scope:
  - charting-app
  - signal_layer/confluence.py
  - ingest/session_anchor.py
  - ingest/stamp_session_anchors.py
  - DEC:CANONICAL-SESSION-BAR-IDENTITY
confidence: verified
---

**This does not weaken the repair in DEC:CANONICAL-SESSION-BAR-IDENTITY, and the reason
is worth stating precisely so nobody "fixes" a non-problem.**

Two independent things made the chart disagree with the engine: the grid's PHASE and the
bar's IDENTITY. Only the identity half is load-bearing in production today.

- **Phase** is inert on production, twice over. The deep store is absent, so the anchor is
  index 0; and production US documents are IPO-complete after the full-history backfill, so
  index 0 is *already the correct phase*. Feed-start and IPO phase coincide.
- **Identity** is fully active and is what actually repairs the defect: the old code keyed
  each bucket by its CLOSING session and bucketed with `Math.floor(i/3)`, the engine keys by
  the OPENING session and opens a partial first bucket. Measured on the live NVDA document,
  those differ on 2321 of 2321 bars and produce 2321 candles against the engine's 2322.

So the published anchor is currently a correctness GUARANTEE rather than a correction: it
makes the phase explicitly right instead of coincidentally right, and it is what will keep
the chart correct the first time a served feed is truncated or re-cut. `basis` existing at
all is what stops a consumer turning that coincidence into a false IPO claim.
