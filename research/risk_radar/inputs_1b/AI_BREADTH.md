# Slice-1b input: `ai_breadth_divergence` (AI vs non-AI breadth)

Status: present in code, **resolves in the panel and fires**, but registered
`display_only` — it can never move the scare tier as things stand. Paths relative to
the repo root; data opened read-only with pandas. No fetch, no ingest, no write.

## 1. What the leg computes today
- Spec `ai_breadth_divergence` in `engine/risk_radar.py:132-139`: `lead_d: 5`, `thr_pct: 0.85`, `accruing: True`, `display_only: True`.
- "internals" scare, weight 1.0 alongside `nh_contraction` (`engine/risk_radar.py:199-204`), Tier B.
- Input `spread_50` = AI-cohort % above 50dma − non-AI % above 50dma (`engine/breadth_split.py:198-201`).
- Transform `build_ai_breadth_divergence(spread_50)` (`engine/risk_radar.py:580-601`): requires `len(s) >= _AI_BREADTH_MIN_HISTORY = 252` (`:70-75`); `abs_pct = _midrank_pctile_series(s.abs(), 252)`; fires when `abs_pct >= _AI_BREADTH_PCT_THR = 90.0`, returning a 0/1 series. The reader also adds it only when `len(ai_clean) >= _CORR_HIST_MINP = 63` and then carries it forward (`engine/risk_radar.py:784-801`).
- **It does fire**: on the stored `spread_50` (365 obs, 2025-05-28 → 2026-11-06) the leg is 1 on **20 of 365** dates — clustered at 2026-06-03, 2026-07-17, 2026-07-27…07-31, 2026-09-29…10-07, 2026-10-30…11-06 (firing at the end of the sample). In the live panel (`leading_signals`, 367 obs to 2026-11-10) it is 1 on 22 dates. It cannot change the tier: `display_only=True` excludes it from the scare's scored weight (`engine/risk_radar.py:820-856,1112-1126`).

## 2. Source
- Computed in-house by `engine/breadth_split.py:_compute()` (`:128-323`) from `data/breadth/_closes_cache.parquet` (`:143`, `as_of = closes.index.max()` at `:159`) plus the AI tags from `scripts.build_ai_adjacency_tag.ensure_ai_tags` (`:165`).
- Base closes: `collectors/breadth.py:390-417` downloads them via **yfinance**; cache `data/breadth/_closes_cache.parquet` is gitignored and restored in CI from `actions/cache` (`collectors/breadth.py:1-18`). Constituents are **current** Wikipedia members (survivorship caveat, same docstring).
- Written by `scripts/build_theme_addons.py:150-163` (JSON to `site/basketdata/breadth_split.json`); the parquet is `_persist_series()`'s "DETERMINISTIC DERIVED ARTIFACT (overwritten each run, not a ledger)" at `engine/breadth_split.py:316-343`.
- Stored: `data/breadth/breadth_split.parquet` (9 columns incl. `spread_50`); base cache `data/breadth/_closes_cache.parquet`.

## 3. First date in stored data
- `data/breadth/breadth_split.parquet`: **min 2025-03-18, max 2026-11-06**, **414 rows**. `spread_50` is NaN for the first 50 rows (50dma warm-up) — **first valid 2025-05-28**, **365 non-null** observations.
- `data/breadth/_closes_cache.parquet`: 416 rows × 519 columns, 2025-03-18 → 2026-11-10.

## 4. Point-in-time reconstruction before 2025-03-18?
- **Partially.** The series is a deterministic function of the closes cache + the AI tag, so it *can* be recomputed (`engine/breadth_split.py:316-343`) — but the cache itself begins 2025-03-18, and membership is current-Wikipedia plus a static tag, so any rebuild carries survivorship and look-ahead. This is not a PIT reconstruction.
- The Macro rights ledger rates this input **UNREGISTERED / `source_unavailable`** for backtesting (unregistered + Yahoo-derived + non-PIT membership), `research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_2026-10-11.md:137`. Its shortness is already recorded (`research/MEGACAP_SUCTION_FIELD_GUIDE.md:22,174,208`: begins 2025-03-18, "recent-accrual only… label as thin").

## 5. Publication lag / as-of rule
- Input is EOD closes; the nightly collect run is 22:30/23:30 UTC = **18:30 ET** (`.github/workflows/daily.yml:36-37`, collect step `:403`), and `build_theme_addons.py` runs in the **render** pipeline (`.github/workflows/render.yml:225`, downstream of daily). The exact render-trigger time relative to the close is **UNVERIFIED**.
- Causal as-of rule (conservative): use `spread_50` for session `d` only from `d+1`. A same-evening rule cannot be justified until the render trigger time is proven from the workflow.

## 6. Data rights
- `docs/COMMERCIAL_DATA_RIGHTS.md` does **not exist in this repo** (Mastermind path); no vendor entry applies. The governing Macro record is the grey_deer qualification above (`source_unavailable`, unregistered, Yahoo-derived, non-PIT).

## 7. Path to the engine
- Enters as a candidate on the desk's pass line (APPROVAL_v2) and reaches the live engine only by the challenger rule (`research/risk_radar/WORLD_CLASS_MASTERPLAN_2026-11.md:392-435` §12.3); it is currently excluded from the catalogue read as "no history on D" (`research/risk_radar/catalogue_read/ledger_rows.py:1-50`). In the live engine it stays `display_only` until promoted.
- The engine's 504-session percentile needs `min_periods = 252` sessions (`engine/risk_radar.py:52-53`); the leg's own gate is also 252 obs (`:70-75`). Reached on **2026-05-28** from stored data (already passed); the full 504-observation window fills on **2027-05-28**.
- Earliest date scoreable from stored data: **2026-05-28** on the 252-obs floor, **2027-05-28** once the full 504-session window exists.
