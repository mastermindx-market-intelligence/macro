# Theme-tree breadth and equal-weight indexes: build report

Sector Intelligence quant lead, 2026-11-12. This is data only: nothing here relates breadth or
index levels to any outcome on any period (no forward returns, hit rates or backtests).

**Read before the tables.** Today's members are applied to the past
(`reconstructed_current_membership`). The history is not point-in-time and covers survivors only.
A name that sits in several groups counts in each.

## What is committed (`data/breadth/history/`)

| File | Content | Size |
|---|---|---|
| `tree_breadth_weekly_current.parquet` | weekly fixed-set breadth for family `subsector` (268) and family `theme` (40) | 1.3 MB |
| `group_ew_index_weekly_current.parquet` | weekly equal-weight total-return index for `subsector`, `theme`, `basket` (49) and `sector` (11) | 3.7 MB |
| `group_ew_index_daily_current.parquet` | the same index, daily | 18.0 MB |
| `tree_breadth_and_index_current.meta.json` | sidecar | 0.03 MB |

The new files total 23.0 MB, under the 25 MB limit, so the daily index is committed.

- **Registries:** `data/themes_heatmap/themes_tree.json` (subsectors and their parent themes), `data/baskets/membership.json` (active members) and `data/breadth/constituents.parquet` (GICS sector).
- **Basket breadth and sector breadth** stay in their existing files, which are built on the Tiingo archive. These new series sit on a different price source and are never joined or mixed with them.
- **Adding a family** (for example a GMI theme-graph level) takes a registry file of (ticker, group) rows and one entry in `FAMILIES` in `scripts/build_tree_breadth_and_index.py`. No new code is needed.

## Price source and start date

- **Prices:** one single-vintage download (yfinance, `auto_adjust=True`, `period="max"`, vintage 2026-11-12 07:33Z), held off git. It never touches the collector cache or `data/yahoo/`.
- **Coverage:** 1,216 of 1,217 registry tickers are priced, including 923 of 924 tree tickers. YYGH is not served.
- **Start date: 2000-01-01, set by rule.** The rule picks the first January 1 from which every later calendar year has name-week above-200 flag disagreement against the Tiingo archive of 0.5% or less. It is measured on 485 S&P 500 members priced in both stores. 1999 is the last year over the limit, at 0.64%.
- **Before the start** no row is emitted, and the reason is `second_source_disagreement`.

| Years | Name-weeks | Disagreement | Worst year |
|---|---|---|---|
| 1960–64 | 812 | 4.56% | 8.89% |
| 1965–69 | 1,820 | 3.41% | 5.49% |
| 1970–74 | 6,693 | 3.83% | 6.91% |
| 1975–79 | 11,440 | 6.64% | 9.15% |
| 1980–84 | 17,679 | 5.85% | 8.65% |
| 1985–89 | 38,830 | 2.33% | 4.27% |
| 1990–94 | 58,218 | 0.80% | 1.02% |
| 1995–99 | 75,577 | 1.20% | 3.76% |
| 2000–04 | 89,694 | 0.31% | 0.49% |
| 2005–09 | 98,717 | 0.17% | 0.33% |
| 2010–14 | 107,164 | 0.09% | 0.23% |
| 2015–19 | 116,649 | 0.09% | 0.16% |
| 2020–24 | 123,116 | 0.04% | 0.07% |
| 2025–26 | 44,774 | 0.04% | 0.05% |

The sidecar also carries the table year by year.

- The two vendors apply dividend adjustment differently in old history, and neither is shown to be right.
- In a 10-name group, one name moves the share by 10 points. A 13-week change differences two such shares, so a large group-level gap between vendors can come from one name.
- No row is dropped for a group-level gap after the start date: the gap is labelled, not used as a gate.

## Floors and coverage

- **Floors:**
  - Share, change, rank and state need 10 counted members (engine `MIN_MEMBERS`). Below that a group has counts only.
  - The index needs 5 priced members. Below that the level is missing with reason `below_index_member_floor`, that session carries no return, and the chain resumes from the last valid level.
  - Ranks are taken among valid groups of the same family only.
- **Index rule:** the existing `engine.baskets._ew_level`. Each session's return is the plain mean of the daily total returns of the members priced that session, so the index rebalances to equal weight daily, and it is chained from 1.0. A difference in dividend method shifts the long-run level of a total-return index, not the timing of its turns.
- **Survivors only:** the index holds only names alive today, so its past returns are overstated, more so the further back and in themes with high failure rates. Relative turns between groups are less affected than levels, and that is not tested here.

Groups valid for breadth (13-week fixed-set change):

| Week | Subsectors (of 268) | Themes (of 40) |
|---|---|---|
| 2000-12-29 | 4 | 32 |
| 2006-12-29 | 10 | 36 |
| 2016-12-30 | 32 | 39 |
| 2026-11-06 | 97 | 40 |

Groups with an index level (5 or more priced members):

| Week | Subsectors | Themes | Baskets | Sectors |
|---|---|---|---|---|
| 2000-01-07 | 114 / 268 | 40 / 40 | 30 / 49 | 11 / 11 |
| 2016-12-30 | 215 / 268 | 40 / 40 | 38 / 49 | 11 / 11 |
| 2026-11-06 | 255 / 268 | 40 / 40 | 47 / 49 | 11 / 11 |

The first valid date for each group is in the sidecar (`first_valid_breadth`, `first_valid_index`).

## Rebuild

```
python scripts/build_tree_breadth_and_index.py --closes <scratch closes.parquet> \
  --download-meta <scratch download_meta.json> --disagreement <yearly csv> \
  --start 2000-01-01 --daily
```

This is off the render path and is never run nightly.
