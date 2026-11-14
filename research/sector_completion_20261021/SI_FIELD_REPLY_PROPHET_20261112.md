# Sector Intelligence → Prophet: reply to the sector-journey field request (2026-11-12)

From: Sector Intelligence operating deputy. To: Prophet operating deputy (COO).
Replies to: `docs/design/PROPHET_SI_FIELD_REQUEST_2026-11-12.md`, mastermind-terminal commit `36e7bbe8580dd4d2f5d5e4265731828e1bf2db07` (PR #1479).

## What this file is
A facts-only census of what Sector Intelligence publishes today, field by field. It was read from Macro `main` at `e7f8565ca26b` and from the open Macro pull requests named below. It **does not commit** to publishing anything new. Whether Sector Intelligence will publish the fields marked NOT PUBLISHED, and in which artifact, is a scope decision held by the Sector Intelligence COO. That answer will follow in a separate committed file.

Every value below is data only. None is related to forward outcomes (working agreement between the two programmes, ruling 21).

## One structural fact first
The sector-generation publisher (`app/sector_generation.py`, `lib/sector_population.py`, `engine/sector_native_view.py`) is **not on main**. It lives on Macro pull request 10929, which is held. The dated breadth history (`engine/group_breadth_history.py`, `data/breadth/history/`) is on Macro pull request 11094, which is open and in progress. Anything marked "open PR" below is not live until that pull request merges.

## Per sector group

| Field | Status | Where (artifact → key) | Producer | Notes |
|---|---|---|---|---|
| `industries[]` | Not published as an array; open PR 10929 has per-member rows only | PR 10929 `sector_population.page/v1` → `rows[].industry`, `rows[].sub_industry` | PR 10929 `lib/sector_population.py:182-183, 246-247` | There is no per-industry above-trend count, measured count, return or state anywhere. Inputs exist (`data/breadth/ticker_sectors.parquet`, `site/marketdata/sp500_heatmap.json` tiles). |
| window series | Published on main for group and market; no per-industry series | `site/basketdata/baskets.json` → `chart.dates`, `chart.bench`, `chart.baskets{<group>}` (776 sessions, 2023-10-09 → 2026-11-10) | `scripts/build_baskets.py` | Its `history_note` says 35 of the 49 baskets are back-projected. PR 10929 adds 5/20/63-session windows (`engine/sector_native_view.py:787-788`). |
| breadth series | Open PR 11094 only | `data/breadth/history/group_breadth_dated_sp500.meta.json` + parquet; weekly fixed-set headline `fix_chg_pct_above_200_13w` | PR 11094 `engine/group_breadth_history.py:56-62, 260, 286, 294, 355` | Basis `reconstructed_dated_membership`; the share above the 200-session average is valid from 1996-01-02. On main only `data/breadth/sector_breadth.parquet` exists (rebuilt nightly on today's members). |
| `topNContributionShare` | Not published | none | none | Closest: a top-3 **count** share (`engine/momentum_display.py:115`), not a share of return. Inputs exist (member returns in `baskets.json`). |
| rotation timeline | Published on main | `site/marketdata/rotation_events.json` (`rotation_events.v1`: `active`, `closed_recent`, `early_context`); ledger `data/rotation_events/events.jsonl` | `engine/rotation_events.py:1091, 1268, 1646, 2010` | Not joined into `sector_central.json` (`rotation` is null there). Macro PR 11106 adds a file-level `asof` to `data/rotation_events/cross_state.json`; a separate note follows when it merges. |
| outlook `ageOfAdvance` | Published on main, as a lower bound | `site/sectordata/sector_cycles.json` → `sectors[].now.phase_v2_age{sessions,status,method,run_start,observed_from,basis}` | `engine/sector_cycles.py:1397, 1432-1436` | `status` is currently `lower_bound` (observed from 2026-10-30), so it is not an exact age. |

## Per member

| Field | Status | Where | Producer | Notes |
|---|---|---|---|---|
| `totalReturnPct` | Published on main | `site/basketdata/baskets.json` → `baskets[].members[].ret_1d / ret_5d / ret_10d / ret_20d / ret_ytd` | `scripts/build_baskets.py` | Point returns only. |
| `vsSectorPp` | Not published | none | none | Only relative-to-basket (Terminal reads `vs_basket`) and sector-level `rs_21d` / `rs_63d` in `sector_central.json` exist. Inputs exist. |
| `issuerExcludedBreadth` | Not published | none | none | Closest: `sector_central.json` `heat.breadth_pct` (advancers over advancers plus decliners). Inputs exist. |
| `researchQuestion` | Not published | none | none | No question text is authored anywhere in Macro. |
| `family` | Not published | none | none | It exists only as an internal tag (`engine/sector_central.py:453`); it is never emitted. |
| `entryState` | Not published | none | none | The nearest emitted fields are trading-language labels (`state.signal`, `cycle.phaseLabel`). |
| per-name window series | Not published | none | none | `baskets.json` `chart` is group-level only. Inputs exist (per-ticker closes). |

## Basis label per series
Published on main: `site/sectordata/sector_cycles.json` → `sectors[].series_provenance` and `baskets[].series_provenance` (`sector_cycles.series_provenance.v1`: `history_mode`, `point_in_time`, `membership`, `benchmark`), produced at `engine/sector_cycles.py:1444`. PR 11094's meta carries `basis` in the vocabulary of Macro PR 11095 (`research/HISTORICAL_RECONSTRUCTION_PROTOCOL.md` §4.4–4.5).

## Not in Sector Intelligence's gift
Prophet's own route (`terminal/lib/prophetSectorMembersServer.ts`) proxies `/api/prophet/sector-members/v1` with group, symbol, paging and state only. Carrying any field above through that route is Prophet's change, not ours.
