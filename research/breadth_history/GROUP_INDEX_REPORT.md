# Group price indexes for baskets and sectors (COO ruling 38 Part B)

House group-level equal-weight **total-return** price indexes for the 11 GICS sectors and the
49 curated US theme baskets. Data only — no outcome relation, no backtest, no signal, ranking
or score column. Group-level numbers and counts only: no member ticker, price or per-security
date is committed.

Continuation (three fixes): the branch base now includes #11158 (vendor internal-only files
kept off git; `data/breadth/history/internal_only/` is empty at the tip); a **dated basket
index** is built from the recorded membership windows on main; and **dated S&P 400 / S&P 600
sector indexes** are added, per universe, never pooled with the S&P 500.

## Files (new only)

| file | basis | levels | rows | span |
|---|---|---|---|---|
| `group_index_daily_dated.parquet` | reconstructed_dated_membership | sector | 85184 | 1996-01-02 .. 2026-10-09 |
| `group_index_daily_current_sensitivity.parquet` | reconstructed_current_membership (sensitivity) | sector, basket | 978000 | 1962-01-02 .. 2026-10-09 |
| `group_index.meta.json` | counts-only sidecar | — | — | — |
| `group_index_key_map.csv` | group_key, level, engine_key, spdr_parent | — | 60 keys | — |
| `group_index_basket_daily_dated.parquet` | reconstructed_dated_membership | basket | 42091 | 2023-05-09 .. 2026-10-09 |
| `group_index_basket_daily_dated.meta.json` | counts-only sidecar | — | — | — |
| `group_index_daily_dated_sp400_sp600.parquet` | reconstructed_dated_membership | sector (+ `index_universe`) | 59598 | 2012-01-13 .. 2026-10-09 |
| `group_index_daily_dated_sp400_sp600.meta.json` | counts-only sidecar | — | — | — |

Columns: `date, level (sector|basket), group, index, n_priced_members, membership_basis`
(the sp400/sp600 file adds `index_universe` in {sp400, sp600}).
`index` is the equal-weight total-return level (1.0 at the first active session); rows below the
floor keep `n_priced_members` with a blank `index`.

The four original `group_index*` files are **byte-frozen** (hashes under Provenance); the
continuation adds new files and new sidecars only.

## Method

- Reuses `engine.baskets._ew_level` (called, not copied): equal-weight daily total-return level,
  cumprod of (1 + the equal-weight daily return), a member counting only inside its membership
  window. Dated loaders and cleaning come from `scripts/build_group_breadth_history.py`
  (`membership_dated`, `drop_partial_rows`, `duplicate_series_pairs`, `count_duplicates_once`,
  `unpriced_in_window`); the current-membership floor gating reuses
  `scripts/build_tree_breadth_and_index.py::group_index`.
- **Floor of 5 priced members.** First date per key = the earliest session with at least 5 priced
  members (in the sidecar). Below-floor sessions are blank; the chain stays flat across the gap
  and resumes from the last valid level.
- **Total return** = the dividend-adjusted close already used in the breadth history. Adjusted
  closes are today's restated values (split and dividend adjustment as of the Tiingo archive
  capture 2026-10-11..16), not the prices printed at the time. **Data end 2026-10-09** (partial
  capture rows 2026-10-12..15 dropped by the centred 21-row median rule).
- Duplicate-series scan: 0 pairs flagged in any membership view, including the two new dated
  views (detection and labelling only; no store repaired).

### Sectors — dated (S&P 500)

S&P 500 **dated** membership (`sp1500_pit_membership.parquet`, `src=sp500`) × **as-of-now** GICS
sector classification (`sp1500_pit_sectors.parquet`). The classification is as of now, **not
era-correct**. This is the same basis as #11094's `group_breadth_daily_dated_sp500.parquet`.
Prices: the Tiingo archive `repo_closes.parquet`. Real Estate first reaches the floor on
2005-08-19 (when ≥5 of its members were first priced); the other ten sectors from 1996-01-02.

### Sectors — dated S&P 400 and S&P 600 (new)

Per-sector equal-weight indexes on **dated S&P 400 membership** and, separately, on **dated
S&P 600 membership** (`sp1500_pit_membership.parquet`, `src=sp400` / `src=sp600`), same method
and floor of 5, same as-of-now GICS classification (not era-correct), same prices
(`repo_closes.parquet`). **The S&P 500, 400 and 600 indexes are never pooled.** Each universe
carries its own `index_universe` value and its own sidecar entries.

- S&P 400: 969 membership rows, 930 tickers, first start **2012-01-13**; all 11 sectors reach
  the floor on that first session. **204** membership rows carry no sector classification and
  are absent from every sector; **121** rows have no stored close inside their own membership
  window (counts only). Known gap: Communication Services is below the floor on **390**
  sessions (including the last date, n=3); every other sector has zero below-floor sessions.
- S&P 600: 1062 membership rows, 1048 tickers, first start **2019-12-17**; all 11 sectors reach
  the floor on that first session. **221** membership rows carry no sector classification;
  **114** rows have no stored close inside their own window. No below-floor sessions in any
  sector.

### Baskets — dated from 2023-05-09 (new)

`group_index_basket_daily_dated.parquet` is built from `data/baskets/membership.json` on main:
every member row (including removed members) as its recorded `[added, removed)` inclusion
window — the same mask `engine/baskets.py` and `engine/us_basket_turn.py` read. A member counts
only on sessions inside its own window. Same EW total-return method, same floor of 5, same
basket prices as the sensitivity file (the closes #11107 used, `basket_closes_tradj.parquet`).

**Dated basket membership starts 2023-05-09** (the membership file's `seed_date`); before that
date the basket has only the current-members sensitivity series. The file span begins at the
first session on/after the seed; 47 of 49 baskets reach the floor on that first session.
`memory_storage` and `pgm_miners` never reach the floor (blank index throughout; counts
retained), and 1,718 basket-sessions in total are below the floor.

**Provenance caveat (reconstruction, not a point-in-time record).** `added` is the
index-inclusion mask; for the 35 baskets curated after the seed it is back-projected, so
pre-curation history shows what today's recorded windows did, not what anyone held at the time.
`curated_added` is the provenance stamp; treat history before a member's `curated_added` as
context, never as a track record. 34 member rows in 3 baskets carry a recorded `added` date
(2023-01-03) earlier than the seed; they are effective from the first session on/after the seed
in this file. This supersedes the earlier no-dated-basket disposition recorded in
`group_index.meta.json` (which remains byte-frozen): the continuation brief asks for the dated
windows as recorded, labelled `reconstructed_dated_membership`, with this caveat.

### Sensitivity

The current-membership file applies today's members to every past session (survivors only, not
point-in-time), labelled `reconstructed_current_membership`, sidecar `sensitivity: true`.
It remains the only basket series before 2023-05-09.

## Key map

`engine_key` is read from engine code, never name similarity. Sectors: the SPDR sector ETF ticker
via `engine/neuralweb/sector_map.py::GICS_TO_ETF` (the explicit code map), matching
`engine/sector_cycles.py::SECTORS` and `engine/subsector_rotation.py::SECTOR_ETFS`. Baskets: the
basket id, the key `engine/us_basket_turn.py` and `engine/baskets.py` read from
`data/baskets/membership.json`. `spdr_parent` is blank for house groups (it applies only to
subsectors). The committed key map stays **house only: exactly 11 sector and 49 basket rows
(60)**; the new files reuse those keys (the sp400/sp600 distinction lives in the
`index_universe` column, not in new keys).

## Dated membership census

All three dated S&P sources exist in `sp1500_pit_membership.parquet`, with the desk's expected
first dates:

| source | rows | tickers | first start | open rows |
|---|---|---|---|---|
| S&P 500 | 1255 | 1202 | 1996-01-02 | 503 |
| S&P 400 | 969 | 930 | 2012-01-13 | 400 |
| S&P 600 | 1062 | 1048 | 2019-12-17 | 603 |

The original dated sector index uses **sp500** (the same basis as #11094); the continuation
adds **sp400 and sp600** as separate universes. **Nothing was purchased or downloaded.**

The input data/breadth/sp1500_pit_membership.parquet (writer scripts/midsmall_pit.py) carries duplicate sp600 membership rows for 14 tickers; the index counts distinct tickers, so n_priced_members is unaffected. The input is not repaired here.

Basket dated membership (the census answer for Fix 2): `data/baskets/membership.json` on main
carries **49 baskets and 1,046 dated member rows** (1,020 active + 26 removed), seed
**2023-05-09**, 713 unique member tickers of which 664 are priced in the basket store. 16
baskets have at least one removed member; 35 baskets were created after the seed
(back-projected windows); 34 rows carry an `added` date before the seed. The dated basket
index is built from these recorded windows; `membership_history.parquet` holds only 4
snapshots (2026-08-13 .. 2026-10-14) and is not a dated entry/exit record.

## Per-key first date and n at the last date

`basis`: dated = reconstructed_dated_membership; current = reconstructed_current_membership
(sensitivity). "never" = the floor of 5 priced members is never reached. The sp400/sp600 rows
are the separate universes of `group_index_daily_dated_sp400_sp600.parquet`.

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
| ai_agents | basket | dated | 2023-05-09 | 7 |
| ai_infra | basket | dated | 2023-05-09 | 22 |
| ai_neoclouds | basket | dated | 2023-05-09 | 8 |
| ai_semiconductors | basket | dated | 2023-05-09 | 12 |
| ai_software | basket | dated | 2023-05-09 | 16 |
| big_pharma | basket | dated | 2023-05-09 | 9 |
| critical_minerals | basket | dated | 2023-05-09 | 8 |
| crypto | basket | dated | 2023-05-09 | 5 |
| crypto_rails | basket | dated | 2023-05-09 | 6 |
| cybersecurity | basket | dated | 2023-05-09 | 9 |
| data_center_power | basket | dated | 2023-05-09 | 8 |
| defense | basket | dated | 2023-05-09 | 20 |
| defensives | basket | dated | 2023-05-09 | 18 |
| energy_complex | basket | dated | 2023-05-09 | 21 |
| gold_miners | basket | dated | 2023-05-09 | 11 |
| housing | basket | dated | 2023-05-09 | 18 |
| industrial_distribution | basket | dated | 2023-05-09 | 12 |
| insurance | basket | dated | 2023-05-09 | 18 |
| mag7 | basket | dated | 2023-05-09 | 7 |
| managed_care | basket | dated | 2023-05-09 | 9 |
| memory_storage | basket | dated | never | 3 |
| non_ai_software | basket | dated | 2023-05-09 | 13 |
| non_ai_tech | basket | dated | 2023-05-09 | 11 |
| nuclear_power | basket | dated | 2023-05-09 | 7 |
| obesity_glp1 | basket | dated | 2023-05-09 | 14 |
| payments_fintech | basket | dated | 2023-05-09 | 19 |
| pgm_miners | basket | dated | never | 4 |
| power_grid | basket | dated | 2023-05-09 | 22 |
| quantum_computing | basket | dated | 2023-05-09 | 11 |
| regional_banks | basket | dated | 2023-05-09 | 19 |
| reshoring | basket | dated | 2023-05-09 | 16 |
| retail | basket | dated | 2023-05-09 | 21 |
| robotics_automation | basket | dated | 2023-05-09 | 12 |
| semicap_equipment | basket | dated | 2023-05-09 | 16 |
| silver_miners | basket | dated | 2023-05-09 | 8 |
| space_economy | basket | dated | 2023-05-09 | 13 |
| travel | basket | dated | 2023-05-09 | 23 |
| uranium_miners | basket | dated | 2023-05-09 | 8 |
| us_sector_comm | basket | dated | 2023-05-09 | 20 |
| us_sector_discretionary | basket | dated | 2023-05-09 | 47 |
| us_sector_energy | basket | dated | 2023-05-09 | 20 |
| us_sector_financials | basket | dated | 2023-05-09 | 73 |
| us_sector_health | basket | dated | 2023-05-09 | 58 |
| us_sector_industrials | basket | dated | 2023-05-09 | 81 |
| us_sector_materials | basket | dated | 2023-05-09 | 24 |
| us_sector_realestate | basket | dated | 2023-05-09 | 29 |
| us_sector_staples | basket | dated | 2023-05-09 | 33 |
| us_sector_tech | basket | dated | 2023-05-09 | 68 |
| us_sector_utilities | basket | dated | 2023-05-09 | 30 |
| Communication Services | sector | dated sp400 | 2012-01-13 | 3 |
| Consumer Discretionary | sector | dated sp400 | 2012-01-13 | 57 |
| Consumer Staples | sector | dated sp400 | 2012-01-13 | 15 |
| Energy | sector | dated sp400 | 2012-01-13 | 15 |
| Financials | sector | dated sp400 | 2012-01-13 | 62 |
| Health Care | sector | dated sp400 | 2012-01-13 | 32 |
| Industrials | sector | dated sp400 | 2012-01-13 | 84 |
| Information Technology | sector | dated sp400 | 2012-01-13 | 46 |
| Materials | sector | dated sp400 | 2012-01-13 | 24 |
| Real Estate | sector | dated sp400 | 2012-01-13 | 27 |
| Utilities | sector | dated sp400 | 2012-01-13 | 14 |
| Communication Services | sector | dated sp600 | 2019-12-17 | 22 |
| Consumer Discretionary | sector | dated sp600 | 2019-12-17 | 84 |
| Consumer Staples | sector | dated sp600 | 2019-12-17 | 23 |
| Energy | sector | dated sp600 | 2019-12-17 | 26 |
| Financials | sector | dated sp600 | 2019-12-17 | 107 |
| Health Care | sector | dated sp600 | 2019-12-17 | 74 |
| Industrials | sector | dated sp600 | 2019-12-17 | 86 |
| Information Technology | sector | dated sp600 | 2019-12-17 | 66 |
| Materials | sector | dated sp600 | 2019-12-17 | 23 |
| Real Estate | sector | dated sp600 | 2019-12-17 | 41 |
| Utilities | sector | dated sp600 | 2019-12-17 | 13 |

## Provenance

The two frozen regime files are unchanged (`regime_inputs_daily_current.parquet` sha256
`c15d5c2d533ae7d66dd84a67c8c1abfa19457aa44fcd1e8504d00bc0c9348177`;
`regime_inputs_current.meta.json` sha256
`552260044b01a67b6a5aed0a30dee52db634c77dd100fb7726d5f282cf0f634d`).

The four original group_index files keep their exact bytes from
`ac0da85fadab861477c23d107eaa62033fcc06a0`:

| file | sha256 |
|---|---|
| `group_index.meta.json` | `5a22beeb1e09b0bb618913de1cafc8043a21ff5f9a9e59815733b3bd535e02da` |
| `group_index_daily_current_sensitivity.parquet` | `1116577f3fb10a7fe9f9da534c9726fa63009ccd3c6496c30229a87be0514fba` |
| `group_index_daily_dated.parquet` | `27a4420e0c990fb97486a3e2829e6e3580f5f199a3267ba2d09731f68ebea6e3` |
| `group_index_key_map.csv` | `b34de4871aac30c0e26c1735092163f88d77867bfe0944e7700866d85f1b7de2` |

The continuation merges the #11158 base head
`1c22905b3e7e7b9ac6f28ec15dcd5b157e5440a1`, so `data/breadth/history/internal_only/` is empty
at the tip (vendor internal-only files stay off git; the repository is public). The vendor
subsector builder (`scripts/build_vendor_subsector_index.py`) writes only outside the
repository tree and now refuses an in-tree `--out` at the CLI with a non-zero exit before
reading any prices; no vendor group name or per-group number appears in this report, the
builder, its fixtures or any committed file.

## In-repo producer (reproducibility, #11171)

`scripts/build_group_index_house.py` is the in-repo producer of all eight house files
above. It ports the ruling-38 builders' method verbatim (same engine loaders, same floor
of 5, same rules and sidecar text); every input is a required command-line argument
(`--closes`, `--basket-closes`, `--membership-dir`, `--basket-membership`) and `--out`
defaults to `data/breadth/history/` at the repo root. Nothing is fetched.

Reproduced 2026-11-12 from the same inputs the original builds used: all four parquets
and `group_index_key_map.csv` are byte-equal (sha256) to the committed files at
`66bb54ba0ae8c8a6489b1179cb9d312690d55e6a`; each sidecar differs only in `build_time_utc`.
The committed data bytes are unchanged.
`tests/test_build_tree_breadth_and_index.py` runs the builder's core functions on a
made-up 3-group fixture everywhere, and asserts value equality of a full rebuild against
the committed files when the price inputs are present (skips cleanly otherwise).
