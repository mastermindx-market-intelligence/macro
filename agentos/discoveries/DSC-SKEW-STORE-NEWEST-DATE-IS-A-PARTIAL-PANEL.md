---
key: SKEW-STORE-NEWEST-DATE-IS-A-PARTIAL-PANEL
claim: >
  The ThetaData skew store's newest date is a 12-root priority set written
  by an early-morning producer; the FULL panel the live emit should read
  is on `session_n_back(D, 1)`, written hours later by the T1 daily
  maintainer. A naive `max(date)` walk collapses the live surface from
  372 → 12 on any day the maintainer has not yet finished.
falsifier: >
  Inspect `<store>/greeks/<ROOT>/<YEAR>.parquet` histograms and
  `<store>/_manifest.json` (the store manifest, NOT the ledger manifest
  at `data/options_skew/_manifest.json` — the resolver reads the store
  manifest at `td / "_manifest.json"`). If the newest date in the store
  carries >= `_COMPLETE_SESSION_MIN_FRACTION × widest_roots` distinct
  roots AND `daily_refresh.greeks_S_roots` matches that count, the
  partial-priority-set hypothesis is refuted and the lane is safe to use
  `max(date)` as the accrual asof. The 12-vs-372 measurement that named
  this gap was the seat's 14:40Z `max(date)` walk on the store host,
  2026-09-23 — not a live call to `complete_store_session` (the function
  did not exist at that timestamp; it lands in this PR).
so_what: >
  Any consumer that resolves a "latest store date" by `max(date)` over a
  producer-written store must compare the per-date distinct-root counts
  (or the manifest's `greeks_S_roots`) to the widest panel, and fall back
  to the newest date that meets the threshold. A `max(date)` resolver
  cannot tell a complete panel from a priority subset; the live emit
  collapses silently, and the only signal in the receipt is the 12-row
  width — well below the lane's historical 372-378 baseline. The seat
  rule (2026-09-23, A-F03-W2-6) is the complete-session resolver: walk
  the per-date root counts newest-first, pick the newest date whose count
  is at least 0.5× the widest, and surface the skipped partial date in a
  `::notice title=options-skew-session::` line. Note: the notice fires on
  `load_chain()`'s default-asof path (gate/snapshot callers), NOT on
  `--accrue`'s lane path — `scripts.build_options_skew.accrue()` calls
  `backfill_from_store` which uses the explicit-asof path; the lane's
  evidence of the skip is its own `accrual sessions=[...]` log line.
kind: architecture
verified_at: 2026-09-23
verified_by: >
  `tests/test_options_skew.py::test_complete_store_session_skips_a_partial_newest_date`
  on a synthetic store (6 roots × 2026-06-18/19, 1 root × 2026-06-22)
  returning `{"session": "2026-06-19", "method": "breadth",
  "partial_skipped": ["2026-06-22"], "roots_on_session": 6,
  "widest_roots": 6, "newest_raw": "2026-06-22"}`. The live-store
  12-vs-372 numbers cited above were the seat's 14:40Z `max(date)`
  measurement on the store host, 2026-09-23, NOT a call to
  `complete_store_session` (the function lands in this PR).
scope:
  - "macro"
  - "engine/options_skew.py"
  - "engine/thetadata_store.py"
  - "data/thetadata_eod/**"
confidence: verified
---

## Why a `max(date)` resolver sees the wrong session

The T1 daily maintainer (`scripts/topup_thetadata_day.py --daily`,
launchd `com.macro.thetadata-daily` at 13:20/14:30/16:00/18:00 local)
writes the FULL `eod/oi/greeks` panel for
`S = nyse_calendar.session_n_back(D, 1)` — the session BEFORE the last
completed one. An earlier producer lands the newest `D` for a 12-root
priority set around 04:30 local. The two writers never agree on a single
`D`: the early set IS the newest date in the store, but the wide panel
sits one session older.

A resolver that walks `<store>/greeks/<ROOT>/<YEAR>.parquet` and returns
`max(date)` returns the priority set's date, not the maintainer's. Every
downstream consumer — `engine.options_skew.load_chain`,
`engine.options_skew.snapshot`, `scripts.build_options_skew --accrue`,
and every render host's `scripts.build_options_skew --emit` after a
`fetch_r2 --dirs options_skew` hydrate — reads a 12-row chain instead of
the 372-row panel the previous day carried.

## The manifest carries the answer the walk alone cannot give

`<store>/_manifest.json`'s `daily_refresh.S` is the maintainer's choice
of session and `daily_refresh.greeks_S_roots` is its counted width. When
the manifest's S is wider than the newest date the walk sees, it
outranks the walk. When the manifest's `greeks_S_roots` is below the
threshold (a maintainer that wrote fewer roots than the panel expects),
it is dropped and the breadth walk wins. A missing or unparseable
manifest is ignored — the walk is the authoritative fallback.

## The lane rule, in three lines

1. **Resolver** — newest date whose per-date distinct greeks root count
   is at least `_COMPLETE_SESSION_MIN_FRACTION` (0.5) of the widest panel;
   manifest S wins on tie.
2. **Catch-up** — `scripts.build_options_skew --accrue` walks NYSE
   sessions backward from the complete session to the ledger's newest
   complete thetadata session (capped at `_CATCH_UP_MAX_SESSIONS` = 5
   dates) and `backfill_from_store`s the range. A caught-up ledger is a
   no-op.
3. **Emit guard** — `engine/options_skew.emit_from_ledger` drops any
   ledger date whose row count is below `_THIN_SESSION_MIN_FRACTION` (0.5)
   of the widest count among the up-to-10 dates immediately older than
   it, and reports the skip in
   `source_detail["partial_sessions_skipped"]` /
   `source_detail["partial_rows_skipped"]` (always present).

A 6+ session outage or a holiday stretch beyond the catch-up cap is the
seat-owned repair: `python -m scripts.build_options_skew --backfill FROM TO`
per `research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md` §3.7.