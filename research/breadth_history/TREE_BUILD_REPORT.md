# Theme-tree breadth and equal-weight indexes: build report

Sector Intelligence quant lead, 2026-11-12. This is data only: nothing here relates breadth or
index levels to any outcome on any period (no forward returns, hit rates or backtests).

**Read before the tables.** Today's members are applied to the past
(`reconstructed_current_membership`). The history is not point-in-time and covers survivors only.
A name that sits in several groups counts in each.

## What is committed (`data/breadth/history/`), split by rights class

The files are split by rights class (COO ruling 32 section 1). The rows are the same as in the first build; only the files they sit in changed.

**Vendor files, internal only — kept off git, in scratch.** The repository is public, so the vendor files are not committed or pushed on any branch (COO ruling 38 §2b). The builder writes them to a scratch directory outside the repository tree (default `/tmp/si_plan/quant/vendor_out/`, `--vendor-out`). Families `subsector` (268) and `theme` (40) come from the vendor's theme tree (`finviz_themes`). The Chairman's gate 2 ruling, recorded at `config/theme_sources.yml:33`, reads: "retained internal-only. NO public/customer display or redistribution rights granted". These series are internal research data. No name and no number from them goes to any site page, site data file, Terminal surface, member page or public bucket. The sidecar carries `source_family: finviz_themes`, `rights_class: internal_only` and that sentence with its path and line.

| File (in the scratch vendor-out directory) | Content | Size |
|---|---|---|
| `vendor_internal_only_breadth_weekly_current.parquet` | weekly fixed-set breadth for `subsector` and `theme` | 1.3 MB |
| `vendor_internal_only_ew_index_weekly_current.parquet` | weekly equal-weight total-return index for `subsector` and `theme` | 3.1 MB |
| `vendor_internal_only_ew_index_daily_current.parquet` | the same index, daily | 14.7 MB |
| `vendor_internal_only_breadth_and_index_current.meta.json` | sidecar with the rights fields | 0.03 MB |

**House files.** Families `basket` (49) and `sector` (11) are house data. Later house families, such as the GMI theme-graph levels and the links between house groups, will go here too. No house family has breadth in this build (basket and sector breadth stay in their existing files), so there is no house breadth file.

| File | Content | Size |
|---|---|---|
| `house_ew_index_weekly_current.parquet` | weekly equal-weight total-return index for `basket` and `sector` | 0.6 MB |
| `house_ew_index_daily_current.parquet` | the same index, daily | 3.3 MB |
| `house_breadth_and_index_current.meta.json` | sidecar | 0.01 MB |

The committed house files total 3.9 MB, under the 25 MB limit, so the daily house index is committed. The vendor files (19.1 MB) are kept off git, in scratch, because the repository is public (COO ruling 38 §2b).

**Where the files are served.** One read was made before choosing the path. The live site serves `site.served` and the live public root (`app/deploy/Caddyfile`), not the repository's `data/`. The only bucket upload (`scripts/publish_r2.py`) sends named per-ticker site stores. No deploy or sync step copies `data/breadth/history/`. The vendor files sit outside the repository tree entirely, in scratch, named so their class is visible.

**Guard.** `tests/test_build_tree_breadth_and_index.py` fails if any `scripts/build_*.py`, publish or sync script, `templates/` or `site/` file names the vendor files, if the default vendor output path is inside the repository tree, or if the quoted sentence no longer matches line 33 of the config. The committed-sidecar rights check skips while the sidecar is off git.

- **Registries:** `data/themes_heatmap/themes_tree.json` (subsectors and their parent themes), `data/baskets/membership.json` (active members) and `data/breadth/constituents.parquet` (GICS sector).
- **Basket breadth and sector breadth** stay in their existing files, which are built on the Tiingo archive. These new series sit on a different price source and are never joined or mixed with them.
- **Adding a family** (for example a GMI theme-graph level) takes a registry file of (ticker, group) rows and one entry, with its rights class, in `FAMILIES` in `scripts/build_tree_breadth_and_index.py`. No new code is needed.

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

> **Superseded floors (2026-11-12, COO ruling 34 §2).** This section and the tables below
> describe the build as checked in #11107. The ruling 34 draft rebuilds every family:
> - breadth from 2 counted members, with `n_above_200` and `n_counted_200` beside each share;
> - index from 2 priced members;
> - a `size_class` per group per date (small under 10 counted members);
> - ranks within the same family and size class only.
>
> The new valid-group counts and file sizes are in `GMI_FAMILIES_REPORT.md`. In that draft
> the vendor daily index is no longer committed, so the committed files stay under 25 MB, a working size figure, not a repository rule.

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

The house set lands under `--out` (default `data/breadth/history/`); the vendor set lands under `--vendor-out` (default `/tmp/si_plan/quant/vendor_out/`), off git. This is off the render path and is never run nightly.
