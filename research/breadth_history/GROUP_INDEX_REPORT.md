# Group price indexes for baskets and sectors (COO ruling 38 Part B)

House group-level equal-weight **total-return** price indexes for the 11 GICS sectors and the
49 curated US theme baskets. Data only — no outcome relation, no backtest, no signal, ranking
or score column. Group-level numbers and counts only: no member ticker, price or per-security
date is committed.

## Files (new only)

| file | basis | levels | rows | span |
|---|---|---|---|---|
| `group_index_daily_dated.parquet` | reconstructed_dated_membership | sector | 85184 | 1996-01-02 .. 2026-10-09 |
| `group_index_daily_current_sensitivity.parquet` | reconstructed_current_membership (sensitivity) | sector, basket | 978000 | 1962-01-02 .. 2026-10-09 |
| `group_index.meta.json` | counts-only sidecar | — | — | — |
| `group_index_key_map.csv` | group_key, level, engine_key, spdr_parent | — | 60 keys | — |

Columns: `date, level (sector|basket), group, index, n_priced_members, membership_basis`.
`index` is the equal-weight total-return level (1.0 at the first active session); rows below the
floor keep `n_priced_members` with a blank `index`.

## Method

- Reuses `engine.baskets._ew_level` (called, not copied): equal-weight daily total-return level,
  cumprod of (1 + the equal-weight daily return), a member counting only inside its membership
  window. Dated loaders and cleaning come from `scripts/build_group_breadth_history.py`
  (`membership_dated`, `drop_partial_rows`, `duplicate_series_pairs`, `count_duplicates_once`);
  the current-membership floor gating reuses `scripts/build_tree_breadth_and_index.py::group_index`.
- **Floor of 5 priced members.** First date per key = the earliest session with at least 5 priced
  members (in the sidecar). Below-floor sessions are blank; the chain stays flat across the gap
  and resumes from the last valid level.
- **Total return** = the dividend-adjusted close already used in the breadth history. Adjusted
  closes are today's restated values (split and dividend adjustment as of the Tiingo archive
  capture 2026-10-11..16), not the prices printed at the time. **Data end 2026-10-09** (partial
  capture rows 2026-10-12..15 dropped by the centred 21-row median rule).
- Duplicate-series scan: 0 pairs flagged in any of the three membership views (detection and
  labelling only; no store repaired).

### Sectors — dated

S&P 500 **dated** membership (`sp1500_pit_membership.parquet`, `src=sp500`) × **as-of-now** GICS
sector classification (`sp1500_pit_sectors.parquet`). The classification is as of now, **not
era-correct**. This is the same basis as #11094's `group_breadth_daily_dated_sp500.parquet`.
Prices: the Tiingo archive `repo_closes.parquet`. Real Estate first reaches the floor on
2005-08-19 (when ≥5 of its members were first priced); the other ten sectors from 1996-01-02.

### Baskets — no dated file

The basket membership on main carries `added`/`removed` fields, but `added_semantics` states
`added` is an **index-inclusion mask back-projected to seed_date (2023-05-09)** for any roster
curated later (35 of 49 baskets are back-projected), and `curated_added` is a recent curation
stamp, not an era-correct entry date. `membership_history.parquet` holds only **4 snapshots
(2026-08-13 .. 2026-10-14)**. There is no historical point-in-time basket entry/exit record
covering the price span, so a dated basket index would misrepresent hindsight-curated,
back-projected rosters as genuine dated history. Baskets are therefore **today's members only**,
in the sensitivity file. Prices: the same closes #11107 used (`basket_closes_tradj.parquet`).
Two baskets never reach the floor of 5 priced members over the span: `memory_storage`,
`pgm_miners` (blank index throughout; counts retained).

### Sensitivity

The current-membership file applies today's members to every past session (survivors only, not
point-in-time), labelled `reconstructed_current_membership`, sidecar `sensitivity: true`.

## Key map

`engine_key` is read from engine code, never name similarity. Sectors: the SPDR sector ETF ticker
via `engine/neuralweb/sector_map.py::GICS_TO_ETF` (the explicit code map), matching
`engine/sector_cycles.py::SECTORS` and `engine/subsector_rotation.py::SECTOR_ETFS`. Baskets: the
basket id, the key `engine/us_basket_turn.py` and `engine/baskets.py` read from
`data/baskets/membership.json`. `spdr_parent` is blank for house groups (it applies only to
subsectors). One row per key (60).

## Dated membership census (Step 1)

All three dated S&P sources exist in `sp1500_pit_membership.parquet`, with the desk's expected
first dates:

| source | rows | tickers | first start | open rows |
|---|---|---|---|---|
| S&P 500 | 1255 | 1202 | 1996-01-02 | 503 |
| S&P 400 | 969 | 930 | 2012-01-13 | 400 |
| S&P 600 | 1062 | 1048 | 2019-12-17 | 603 |

The committed dated sector index uses **sp500** (the same basis as #11094). S&P 400 and S&P 600
dated membership is available for a future extension; **nothing was purchased or downloaded**.

## Per-key first date and n at the last date

`basis`: dated = reconstructed_dated_membership (sectors); current = reconstructed_current_membership
(sensitivity, sectors and baskets). "never" = the floor of 5 priced members is never reached.

| key | level | basis | first date | n at last date |
|---|---|---|---|---|
| ai_agents | basket | current | 2021-07-28 | 7 |
| ai_infra | basket | current | 1989-05-16 | 22 |
| ai_neoclouds | basket | current | 2020-12-07 | 8 |
| ai_semiconductors | basket | current | 2004-11-19 | 12 |
| ai_software | basket | current | 1993-03-22 | 16 |
| big_pharma | basket | current | 1991-04-02 | 9 |
| critical_minerals | basket | current | 2020-06-22 | 8 |
| crypto | basket | current | 2024-07-23 | 5 |
| crypto_rails | basket | current | 2021-04-14 | 6 |
| cybersecurity | basket | current | 2018-03-16 | 9 |
| data_center_power | basket | current | 2018-04-30 | 8 |
| defense | basket | current | 1977-01-03 | 20 |
| defensives | basket | current | 1972-06-01 | 18 |
| energy_complex | basket | current | 1981-12-31 | 21 |
| gold_miners | basket | current | 1996-09-30 | 11 |
| housing | basket | current | 1985-07-01 | 18 |
| industrial_distribution | basket | current | 1987-11-05 | 12 |
| insurance | basket | current | 1984-09-07 | 18 |
| mag7 | basket | current | 2004-08-19 | 7 |
| managed_care | basket | current | 2001-10-30 | 9 |
| memory_storage | basket | current | never | 3 |
| non_ai_software | basket | current | 2012-10-12 | 13 |
| non_ai_tech | basket | current | 1990-03-26 | 11 |
| nuclear_power | basket | current | 2021-07-08 | 7 |
| obesity_glp1 | basket | current | 1988-01-05 | 14 |
| payments_fintech | basket | current | 2001-06-20 | 19 |
| pgm_miners | basket | current | never | 4 |
| power_grid | basket | current | 1983-04-06 | 22 |
| quantum_computing | basket | current | 2004-08-19 | 11 |
| regional_banks | basket | current | 1990-03-26 | 19 |
| reshoring | basket | current | 1972-06-01 | 16 |
| retail | basket | current | 1985-07-01 | 21 |
| robotics_automation | basket | current | 1989-10-09 | 12 |
| semicap_equipment | basket | current | 1990-03-26 | 16 |
| silver_miners | basket | current | 2005-05-02 | 8 |
| space_economy | basket | current | 2019-12-20 | 13 |
| travel | basket | current | 1993-04-28 | 23 |
| uranium_miners | basket | current | 2007-04-05 | 8 |
| us_sector_comm | basket | current | 1990-03-26 | 20 |
| us_sector_discretionary | basket | current | 1983-04-06 | 47 |
| us_sector_energy | basket | current | 1981-12-31 | 20 |
| us_sector_financials | basket | current | 1984-07-19 | 73 |
| us_sector_health | basket | current | 1972-06-01 | 58 |
| us_sector_industrials | basket | current | 1970-01-02 | 81 |
| us_sector_materials | basket | current | 1983-04-06 | 24 |
| us_sector_realestate | basket | current | 1990-03-07 | 29 |
| us_sector_staples | basket | current | 1972-08-25 | 33 |
| us_sector_tech | basket | current | 1980-03-17 | 68 |
| us_sector_utilities | basket | current | 1972-06-01 | 30 |
| Communication Services | sector | current | 1990-03-26 | 21 |
| Consumer Discretionary | sector | current | 1983-04-06 | 47 |
| Consumer Staples | sector | current | 1972-08-25 | 33 |
| Energy | sector | current | 1981-12-31 | 20 |
| Financials | sector | current | 1984-07-19 | 73 |
| Health Care | sector | current | 1972-06-01 | 58 |
| Industrials | sector | current | 1970-01-02 | 81 |
| Information Technology | sector | current | 1980-03-17 | 70 |
| Materials | sector | current | 1983-04-06 | 23 |
| Real Estate | sector | current | 1990-03-07 | 29 |
| Utilities | sector | current | 1972-06-01 | 30 |
| Communication Services | sector | dated | 1996-01-02 | 19 |
| Consumer Discretionary | sector | dated | 1996-01-02 | 47 |
| Consumer Staples | sector | dated | 1996-01-02 | 36 |
| Energy | sector | dated | 1996-01-02 | 20 |
| Financials | sector | dated | 1996-01-02 | 73 |
| Health Care | sector | dated | 1996-01-02 | 57 |
| Industrials | sector | dated | 1996-01-02 | 81 |
| Information Technology | sector | dated | 1996-01-02 | 67 |
| Materials | sector | dated | 1996-01-02 | 24 |
| Real Estate | sector | dated | 2005-08-19 | 28 |
| Utilities | sector | dated | 1996-01-02 | 30 |

## Provenance

The two frozen regime files are unchanged (`regime_inputs_daily_current.parquet` sha256
`c15d5c2d533ae7d66dd84a67c8c1abfa19457aa44fcd1e8504d00bc0c9348177`;
`regime_inputs_current.meta.json` sha256
`552260044b01a67b6a5aed0a30dee52db634c77dd100fb7726d5f282cf0f634d`). No existing file under
`data/breadth/history/` was modified.

A separate vendor subsector index (COO ruling 38 §2a/§2b) is built **out-of-tree** and is not part
of this house report; no vendor group name or per-group number appears here.
