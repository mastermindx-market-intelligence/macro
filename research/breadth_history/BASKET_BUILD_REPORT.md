# Reconstructed US theme/basket breadth history — build report

Sector Intelligence quant lead, 2026-11-12. Data only: nothing here relates breadth
to any outcome on any period (no forward returns, hit rates or backtests).
**Read before the tables:** this is today's basket roster applied backward
(`reconstructed_current_membership`), so every early value is a survivor-only
sample: names that left a basket or stopped trading are absent throughout. 16 of
49 baskets never reach 10 counted members and are missing on every date; of the
33 that do, the median first valid date is 1994 and six themes only begin after
2010. The companion sector history carries its own line: on its dated basis only
46.5% of members carry a sector label at the end of 1996. After the SIC label
fill, the first sector is valid on 2007-01-10 and all 11 are continuously valid
from 2009-03-27.

**Rights.** The Tiingo archive's member rows stay on the SSD and never enter git.
What is committed is basket-level aggregates (shares and counts per basket), the
same class as the aggregate evidence already published under
`docs/tiingo-evidence/`. The Chairman's Business Advanced / full-redistribution
attestation is on record in `docs/TIINGO_DATA_OS_INGESTION_20261009.md` (lines
10-11). The research reader's `redistribution_admitted=false` (same document,
lines 586-595) applies to licensed rows read through it, which are not committed
here. No sentence in that document forbids committing derived aggregates; its one
redistribution prohibition (line 192) covers news and fee feeds.

## What was built

`scripts/build_basket_breadth_history.py` runs the same pure functions as the
sector history (`engine/group_breadth_history.py`) over the US basket roster
(`data/baskets/membership.json`, suite `baskets`, active members only). It writes
to `data/breadth/history/`:

| file | rows | content |
|---|---|---|
| `basket_breadth_daily_current.parquet` | 798,700 | (date, basket): levels above 50/200-session averages, changes over 5/20/63/126 sessions, fixed-set change, cross-basket rank, sign state and run length |
| `basket_breadth_weekly_current.parquet` | 165,620 | weekly fixed-set change at k = 13 and 26 weeks (headline `fix_chg_pct_above_200_13w`), plain level difference beside it |
| `basket_breadth_current.meta.json` | | protocol §4.4 sidecar |

Same rules as the sectors: a member counts only with 200 sessions of its own
history at both dates; a basket is valid only with 10 or more such members, else
missing, not zero; no tuned threshold.

**Overlap.** 243 of the 664 priced names sit in more than one basket and count in each (one
engine column per name-and-basket pair). The `us_sector_*` baskets overlap the
themes heavily. Ranks across baskets are therefore not across independent groups.

**Why only one basis.** The dated US basket history
(`membership_history.parquet`) begins 2026-08-13 (four snapshots to 2026-10-14);
there is no dated roster to rebuild the past from.

## Source and span

Closes: Tiingo end-of-day archive, `close_tradj`, assembled off git by
`scripts/build_tiingo_member_closes.py` (664 of 702 names matched, no vendor
mismatch). Four partial vendor rows (2026-10-12..15) are dropped by the same
cleaning step as the sector build, so the series end 2026-10-09. Adjusted closes
are today's restated values.

First valid date by basket (10 or more counted members):

| from | baskets |
|---|---|
| 1973-1989 | us_sector_industrials, us_sector_utilities, us_sector_staples, us_sector_health, us_sector_financials, us_sector_tech, defensives, us_sector_discretionary, us_sector_energy, reshoring, defense, us_sector_materials, housing |
| 1990-1999 | energy_complex, regional_banks, insurance, retail, us_sector_realestate, ai_infra, power_grid, industrial_distribution |
| 2000-2009 | semicap_equipment, robotics_automation, travel, obesity_glp1, us_sector_comm, gold_miners |
| 2010 on | non_ai_tech (2011), ai_software (2013), payments_fintech (2016), non_ai_software (2020), ai_semiconductors (2024), space_economy (2025-11-28) |
| never | ai_agents, ai_neoclouds, big_pharma, critical_minerals, crypto, crypto_rails, cybersecurity, data_center_power, mag7, managed_care, memory_storage, nuclear_power, pgm_miners, quantum_computing, silver_miners, uranium_miners |

The "never" baskets are small (under 10 priced names) or mostly young listings.

## Who is missing or doubled

- 38 of 702 names have no close in this capture and are absent: B, BNY, BTDR, CEG,
  COHR, COR, CRCL, CZR, DD, DELL, DOC, DOW, DRS, ECHO, EU, FI, FLY, GLXY, HUT, IBIT,
  LAC, MMC, MRNA, OKE, P, PATH, PL, PPTA, PSKY, Q, S, SGML, SNDK, SNOW, TEL, TLN,
  UROY, VLTO. The cause (renamed ticker, recent listing or capture gap) is not checked here.
- Duplicate-series scan (the same check as the sector build): no two basket
  tickers carry the same price series.
- The roster includes non-company instruments where a basket lists them (IBIT
  among the unpriced); they are counted like any member when priced.

## Not done here

- No nightly basket ledger: the sector member ledger already records daily
  per-name flags for S&P 500 members; basket members outside it are not stamped.
- The free SIC label fill for the dated sector basis is the next pull request.
- No relation to outcomes, no signal, no change to any existing reader
  (`engine/basket_breadth_divergence.py` is a different, live 50-session measure).

## How to rerun

```
python -m scripts.build_basket_breadth_history \
  --closes <off-git basket closes.parquet> \
  --membership data/baskets/membership.json --out data/breadth/history \
  --closes-label "Tiingo EOD archive ... via scripts/build_tiingo_member_closes.py; member-level, off git"
```
