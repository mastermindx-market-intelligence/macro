# Slice-1b input: `vol_gex` (dealer net GEX)

Status: present in code, **accruing, does not fire on any date**. Paths relative to the
repo root; data opened read-only with pandas. No fetch, no ingest, no write.

## 1. What the leg computes today
- Spec `vol_gex` in `engine/risk_radar.py:114`: `lead_d: 3`, `thr_pct: 0.85`, `accruing: True`, `lift_2020: None`.
- Tier-B "vol" scare, weight 0.2 (`engine/risk_radar.py:178-183`); structurally display-only until gauntlet promotion.
- Transform `pcol(-gx["net_gex_bn"])` (`engine/risk_radar.py:718-730`): sign is flipped so a *negative* net dealer gamma (dealers short gamma) ranks high; then the causal trailing percentile `pct_rank_window(..., 504)`, `min_periods = 252` (`engine/risk_radar.py:52-53,675-678`; `engine/indicators.py:65-67`). Fires when percentile ≥ `thr_pct = 0.85`.
- Leg is added only when `len(gx) >= 252` sessions (`engine/risk_radar.py:718-730`); absent from `leading_signals()`.
- **Fires on no date**: `flow_status()` reports `gex_rows: 96`, `mature: False` (`engine/risk_radar.py:904-938`); no `vol_gex` column in `leading_signals()`.

## 2. Source
- Writer: `GexAdapter` (`name="cboe_gex"`), `collectors/cboe.py:145-273`; registered at `scripts/collect.py:163-169`.
- Origin: **computed in-house** from CBOE delayed chains (same `config.yml:547-572` `chain_url`; convention `GEX = ±gamma · OI · 100 · spot² · pct_move`, +call / −put, ±25% strike window, `config.yml` `gex:` block). Only a 1-row/day summary is persisted — "a VOL-REGIME + LEVELS MAP, not alpha" (`collectors/cboe.py:145-160`).
- Stored: `data/cboe/gex.parquet` (`CORE_CHAIN_SERIES`, `collectors/cboe.py:279-286`); columns `net_gex_bn, flip_strike, spot, spot_vs_flip_pct`. Per-symbol summaries also at `data/cboe/gex_<SYMBOL>.parquet` (`DEFAULT_GEX_SYMBOLS`, `collectors/cboe.py:145-273`).

## 3. First date in stored data
- `data/cboe/gex.parquet`: **min 2026-06-10, max 2026-11-10**, 96 raw rows = **83 NYSE sessions**.
- Quality: **24 missing NYSE sessions** in span (incl. declared `KNOWN_PERMANENT_GAPS`, `collectors/cboe.py:290`); `flip_strike` and `spot_vs_flip_pct` are null on 16 rows while `net_gex_bn` and `spot` are populated.

## 4. Point-in-time reconstruction before 2026-06-10?
- **No, not this series.** Live-snapshot-only endpoint; missed sessions are unrecoverable (`collectors/cboe.py:290`; `scripts/ci/chain_snapshot_salvage.py:1-20`). The one cross-fill attempt (`scripts/backfill_cboe_gex_20260730_from_polygon.py:1-12`) is a declared one-shot and states `putcall + gex + gex_SPX` stay permanently lost.
- A **different-basis** multi-year index-gamma history is reconstructable from the ThetaData T1 EOD store (2017→) by `scripts/build_index_gex_history.py:1-12` (SPY/QQQ/IWM/DIA via `engine.gex_engine.compute_gex`, `reconstructed=True`, display-only) — it is *not* the same series and cannot stand in for `data/cboe/gex.parquet`. The Polygon estate is legacy/dark and frozen 2026-08-12 (`scripts/build_polygon_gex.py:1-12`).

## 5. Publication lag / as-of rule
- Input is known after the US close; ingest runs nightly at 22:30/23:30 UTC = **18:30 ET** (`.github/workflows/daily.yml:36-37`), collect step `.github/workflows/daily.yml:403`.
- Session stamping is wrong before fix **#4807 (2026-08-07)** — pre-fix rows carry the UTC run date = **session + 1** (`collectors/cboe.py:379-433`; `lib/nyse_calendar.py:272-282`).
- Causal as-of rule: use a row stamped `d` only from `d` 18:30 ET; shift pre-2026-08-07 stamps back one session. Tighter timing is **UNVERIFIED**.

## 6. Data rights
- `docs/COMMERCIAL_DATA_RIGHTS.md` does **not exist in this repo** (Mastermind path). Nearest Macro citation: `docs/runbooks/OPTIONS_FREE_SOURCE_EVALUATION.md:23` — Cboe limits raw redistribution; derived external release needs paid licensing; internal evaluation only. The ThetaData basis in §4 is governed separately (`DEC:AD-OPTIONS-CANONICAL-SOURCE-THETADATA`, cited at `scripts/build_polygon_gex.py:1-12`).

## 7. Path to the engine
- Enters as a candidate on the desk's pass line (APPROVAL_v2) and reaches the live engine only by the challenger rule (`research/risk_radar/WORLD_CLASS_MASTERPLAN_2026-11.md:392-435` §12.3).
- The 504-session percentile is defined from `min_periods = 252` sessions (`engine/risk_radar.py:52-53`): from the stored start that is **2027-06-10** (504th session **2028-06-09**).
- Earliest date scoreable from stored data: **2027-06-10**, absent new permanent gaps.
