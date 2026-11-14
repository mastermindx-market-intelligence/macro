# Slice-1b input: `vol_putcall` (CBOE put/call)

Status: present in code, **accruing, does not fire on any date**. All paths relative
to the repo root; data was opened read-only with pandas. No fetch, no ingest, no write.

## 1. What the leg computes today
- Spec `vol_putcall` in `engine/risk_radar.py:113`: `lead_d: 5`, `thr_pct: 0.85`, `accruing: True`, `lift_2020: None`.
- Tier-B "vol" scare, weight 0.3 (`vol_term 0.5 / vol_putcall 0.3 / vol_gex 0.2 / corr_floor_break 1.0`), `engine/risk_radar.py:178-183`.
- Transform `pcol(pc["equity_pc_ratio"])` (`engine/risk_radar.py:718-730`) = causal trailing percentile `pct_rank_window(..., 504)` with `min_periods = 504 // 2 = 252` (`engine/risk_radar.py:52-53,675-678`; `engine/indicators.py:65-67`). Fires when the percentile ≥ `thr_pct = 0.85`.
- Leg is added only when `len(pc) >= 252` sessions (`engine/risk_radar.py:718-730`); it is deliberately absent from `leading_signals()` until then (`engine/risk_radar.py:665-668`).
- **Fires on no date**: `flow_status()` reports `putcall_rows: 95`, `mature: False` (`engine/risk_radar.py:904-938`), and `leading_signals()` has no `vol_putcall` column.

## 2. Source
- Writer: `PutCallAdapter` (`name="cboe_putcall"`), `collectors/cboe.py:73-134`; registered at `scripts/collect.py:163-169`.
- Origin: **computed in-house** from CBOE delayed option-chain quotes — `config.yml:547-572` `chain_url: https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json`. Index P/C from `_SPX`; equity proxy from SPY+QQQ+IWM summed volumes. Not the official total-market ratio (`collectors/cboe.py:73-134`).
- Stored: `data/cboe/putcall.parquet` (`CORE_CHAIN_SERIES`, `collectors/cboe.py:279-286`); columns `index_pc_ratio, equity_pc_ratio, index_put_vol, index_call_vol, equity_put_vol, equity_call_vol`.

## 3. First date in stored data
- `data/cboe/putcall.parquet`: **min 2026-06-10, max 2026-11-10**, 95 raw rows = **82 NYSE sessions**, 0 nulls in the ratio columns.
- Quality: **25 missing NYSE sessions** inside the span (incl. the declared `KNOWN_PERMANENT_GAPS` 2026-07-27/30/31 and 2026-08-03/04/05, `collectors/cboe.py:290`); 5 rows are byte-identical repeats of the prior session's row (e.g. 2026-06-12 == 2026-06-11).

## 4. Point-in-time reconstruction before 2026-06-10?
- **No.** The delayed-quotes endpoint serves only the live snapshot; a missed session cannot be honestly backfilled (`collectors/cboe.py:290`; `scripts/ci/chain_snapshot_salvage.py:1-20`; `collectors/cboe.py:73-134` records that the official CSV endpoints moved behind the SPA in 2025/26).
- Whether CBOE sells an accessible historical daily P/C archive is **UNVERIFIED** — nothing in this repo cites one.

## 5. Publication lag / as-of rule
- The input is known after the US close; ingest runs nightly at 22:30/23:30 UTC = **18:30 ET** (`.github/workflows/daily.yml:36-37`), collect step `.github/workflows/daily.yml:403`.
- Session stamping is wrong before fix **#4807 (2026-08-07)**: earlier rows were stamped with the UTC run date = **session + 1** (`collectors/cboe.py:379-433`; `lib/nyse_calendar.py:272-282`).
- Causal as-of rule: a row stamped session `d` is usable only from `d` 18:30 ET; on pre-2026-08-07 rows shift the stamp back one session. Any tighter rule is **UNVERIFIED**.

## 6. Data rights
- `docs/COMMERCIAL_DATA_RIGHTS.md` does **not exist in this repo** (it is a Mastermind path). Nearest Macro citation: `docs/runbooks/OPTIONS_FREE_SOURCE_EVALUATION.md:23` — Cboe restricts raw redistribution; derived external release needs paid licensing; free access is internal evaluation only.

## 7. Path to the engine
- Enters as a candidate on the desk's pass line (APPROVAL_v2) and reaches the live engine only by the challenger rule (`research/risk_radar/WORLD_CLASS_MASTERPLAN_2026-11.md:392-435` §12.3).
- The 504-session percentile becomes *defined* at `min_periods = 252` sessions (`engine/risk_radar.py:52-53`). From the stored start that is **2027-06-10** (the 504th session is **2028-06-09**).
- Earliest date scoreable from stored data: **2027-06-10**, assuming no further permanent gaps.
