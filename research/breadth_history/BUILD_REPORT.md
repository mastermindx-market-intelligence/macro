# Reconstructed sector breadth history — build report

Sector Intelligence quant lead, 2026-11-12. Data only: nothing here relates breadth
to any outcome on any period (no forward returns, hit rates or backtests).
**Read before the tables:** on the dated basis only 50.6% of members carry a sector
label at the end of 1996 (46.5% before the free SIC fill), and only 221 of 488 have a
Tiingo close, so the early years are a sample of about half the index. All 11 sectors
(10 or more counted members) are first valid together on 2007-01-10, but
Communication Services drops out again on some sessions until 2009-03-26; all 11 are
valid without a break only from 2009-03-27 (2014-04-02 before the fill). The pre-2009
dated series is a thin, survivor-leaning sample.

**Rights.** The Tiingo archive's member rows stay on the SSD and never enter git.
What is committed is group-level aggregates (shares and counts per sector), the
same class as the aggregate evidence already published under
`docs/tiingo-evidence/`. The Chairman's Business Advanced / full-redistribution
attestation is on record in `docs/TIINGO_DATA_OS_INGESTION_20261009.md` (lines
10-11). The research reader's `redistribution_admitted=false` (same document,
lines 586-595) applies to licensed rows read through it, which are not committed
here. No sentence in that document forbids committing derived aggregates; its
one prohibition on redistribution (line 192) covers news and fee feeds.

## What was built

`engine/group_breadth_history.py` — pure functions; a closes matrix and a membership
map in, per group per session out. The same functions build this history and the
nightly member ledger (`engine/member_breadth_ledger.py`, written from
`collectors/breadth.py` in the `daily.yml` collect step; nothing on the render path).

Per GICS sector per session: members counted, members with 50 and 200 sessions of
history, share above each average; plain change of each share over 5/20/63/126
sessions (`lvl_chg_*`); like-for-like change on the members at t over the same
horizons (`fix_chg_*`, with `n_fixed_*`); rank of every change across the valid
sectors that session (1 = largest increase; `n_ranked_*`); a state from the sign
(improving / deteriorating / flat at exactly 0) and how many rows it has held.

Weekly file: last session of each calendar week, the fixed-set change of the share
above the 200-session average over 13 and 26 weeks (headline
`fix_chg_pct_above_200_13w`), rank and state; the plain difference of the two
weekly levels is kept separately as `lvl_diff_pct_above_200_{13,26}w`.

Fixed rules, none tuned: a member counts only with a defined average (and, for a
fixed-set change, at both dates); a sector with fewer than 10 such members is
missing, never zero. Each ticker's average is over its own last 200 closes.

## Bases and files (`data/breadth/history/`)

| File | Basis | Rows |
|---|---|---|
| `group_breadth_daily_dated_sp500.parquet` + `group_breadth_dated_sp500.meta.json` | `reconstructed_dated_membership` | 179,300 |
| `group_breadth_weekly_dated_sp500.parquet` | same | 37,180 |
| `group_breadth_daily_current.parquet` + `group_breadth_current.meta.json` | `reconstructed_current_membership` | 179,300 |
| `group_breadth_weekly_current.parquet` | same | 37,180 |

Group-level shares and counts only. Member-level prices stay off git.

Prices: Tiingo end-of-day archive on the Mastermind SSD (captures 2026-10-11..16),
total-return-adjusted closes. These are today's restated values, not the prices
printed at the time. 2,161 of 2,597 wanted tickers matched; no file disagreed with
its requested ticker. Eleven partial vendor rows (fewer than half the usual names
priced: 1970-02-23, 1972-11-07, 1972-12-28, 1973-01-25, 1976-11-02, 1977-07-14,
2026-02-16, and the partial captures 2026-10-12..15) were dropped and are listed
in each sidecar. The history ends 2026-10-09, the last complete capture.

Cross-check against the collector's yfinance closes on 497 shared names over 396
shared sessions: no name has a median daily-return difference above 0.5%.

## Spans

| Basis | First valid 200-session share | First weekly 13-week change | All 11 sectors valid from |
|---|---|---|---|
| Dated membership (S&P 500) | 1996-01-02 | 1996-01-05 | first 2007-01-10; without a break from 2009-03-27 (2014-04-02 before the free SIC fill) |
| Today's membership | 1973-03-20 | 1973-06-22 | 2008-02-01, without a break after (9 by end-1990, 10 by end-1996) |

Year-end members counted across sectors (labelled and priced) / with 200 sessions (dated column includes the free SIC fill):

| Year | Dated | Today's members |
|---|---|---|
| 1973 | — | 42 / 38 |
| 1985 | — | 144 / 129 |
| 1990 | — | 217 / 192 |
| 1996 | 208 / 207 | 293 / 289 |
| 2000 | 265 / 262 | 339 / 329 |
| 2005 | 308 / 307 | 374 / 368 |
| 2010 | 383 / 382 | 409 / 401 |
| 2015 | 421 / 417 | 445 / 438 |
| 2020 | 471 / 469 | 471 / 467 |
| 2026-10-09 | 482 / 481 | 485 / 482 |

## Who is missing

Dated basis: 453 membership rows have no Tiingo close inside their own membership
window and are absent; for 144 of them the ticker exists in the archive only
outside the window (a likely ticker reuse — the engine already counts a member
only inside its window, so a later company's prices never enter). By start year:
1996 268 (rows open at the membership file's start), 1997–2001 94, 2002–2010 48,
2011–2026 43. Separately, 425 membership rows carry no sector label and are absent
from every sector (484 before the free SIC fill); label coverage is 50.6% of members
at the end of 1996 (46.5% before), rising to 95.6% in 2021 (`LABEL_COVERAGE.md`).
The early dated years therefore lean toward survivors. Communication Services falls
under 10 members before 2006-04-03 and again on some sessions to 2009-03-26, and
Real Estate before 2007-01-10; both are missing, not zero, on those sessions.

Today's basis: only today's members; every name that left the index is absent
from every past session, and today's labels apply throughout. 18 of today's 503
have no Tiingo history in this capture: BNY, COR, COHR, CEG, DELL, DOW, DD, ECHO,
P, FI, DOC, MMC, MRNA, OKE, Q, SNDK, TEL, VLTO (several are renamed or recently
listed tickers the capture did not cover).

## Duplicate series (one company under two tickers)

Prompted by `research/data_quality/SUPN_PRICE_DEFECT_20261112.md`. The build now
scans the members it uses (`duplicate_series_pairs` in
`scripts/build_group_breadth_history.py`). A pair is flagged when at least 60
overlapping daily returns are identical and identical returns make up at least
95% of the span between the first and last identical session. The sidecar also
records the price-ratio variation. A flagged pair is counted once: the second
ticker is blanked over the span, in memory only. Detection and labelling only;
no price store is repaired and nothing under `data/yahoo/` is touched.

- **Members used, both bases:** no pairs. Both sidecars say so in the "missing"
  sentence and carry an empty `duplicate_series_pairs` list.
- **SUPN in the Tiingo archive is genuine** for 2022-06-01..06-07: the archive
  series changes on every session of that span, while the defective copy is
  flat at 20.75. SUPN and INDV are both in the store and do not flag.
- **The note's 16 alias pairs:** none has both tickers in the Tiingo matrix
  (only HLX, MRSH, SKYD of those 32 names appear, each without its partner).
- **Whole Tiingo matrix (2,161 tickers, not only members):** three pairs in the
  whole matrix, none a pair of members on either basis; recorded for reference,
  they change no row here.
- **The nightly ledger inherits whatever the collector's store holds.** The
  collector reads its own yfinance cache (`data/breadth/_closes_cache.parquet`),
  not `data/yahoo/` and not this Tiingo history. In the cache copy used here
  (416 sessions to 2026-10-09), PSKY and SKYD share returns on 17 of 19
  overlapping sessions (2026-09-09..10-06), a vendor alias. SKYD is the member on
  today's list and PSKY is not, so the ledger does not double-count it, and it is
  below the 60-session flag floor. MMC (member) has no closes in that cache;
  MRSH carries them, so Marsh McLennan is missing from the ledger under its old
  ticker. Neither is repaired here.

## Overlap check

Against `data/breadth/sector_breadth.parquet`, share above the 200-session average,
shared span 2025-12-31..2026-10-09 (195 sessions). See `OVERLAP_CHECK.md`. No tuning.

| Sector | Today's basis: mean / max abs diff (pct pts) | Dated basis: mean / max |
|---|---|---|
| Communication Services | 2.72 / 10.28 | 3.33 / 17.89 |
| Consumer Discretionary | 0.27 / 4.26 | 0.27 / 4.26 |
| Consumer Staples | 0.72 / 9.38 | 4.87 / 10.76 |
| Energy | 0.93 / 13.10 | 0.93 / 13.10 |
| Financials | 0.99 / 5.33 | 0.99 / 5.33 |
| Health Care | 1.14 / 6.37 | 1.01 / 5.95 |
| Industrials | 0.80 / 5.06 | 2.42 / 4.75 |
| Information Technology | 1.20 / 5.27 | 2.19 / 5.42 |
| Materials | 2.19 / 10.69 | 1.88 / 12.50 |
| Real Estate | 2.09 / 17.24 | 2.13 / 16.38 |
| Utilities | 3.30 / 17.96 | 3.30 / 17.96 |

Same functions, two stores: on the collector's own closes the engine reproduces
`sector_breadth.parquet` exactly (0.0 on all 11 sectors). The differences above
come from the price store, and, on the dated basis, from membership changes the
collector does not see. Large maxima fall on the small sectors (Utilities, Real
Estate, Energy), where one name moves the share by 3 to 5 points.

**Correction (2026-11-12, COO ruling 27 section 6).** An earlier version of this
report blamed "small adjusted-price differences" between the stores. That was
not tested and is wrong. The tested cause (#11124;
`research/sector_completion_20261021/SI_PRICE_STORE_FINDING_20261112.md`) is the
collector's own store:
- `collectors/breadth.py` re-downloads one month of dividend-adjusted closes
  each night and lays them over the cached history;
- the cache therefore mixes price vintages, and a dividend payer's 200-session
  average is pushed up, so it reads "below" too often.

The collector's `sector_breadth.parquet` is the series that is off, not this
history. A single-vintage re-download cut name-week disagreements with the
archive from 121 to 9. The other part of the gap is the 18 of today's members
absent from the Tiingo capture.

**Second-vendor agreement before 2000 (label, not cut).** A later
full-history single-vintage download from a second vendor (yfinance) was
compared with the Tiingo archive behind this history. The comparison counts
name-weeks where both stores hold 200 sessions for the same S&P 500 member
(485 names) and asks whether the above-200 flag disagrees. Group-level
figures only:

| Years | Name-weeks | Flag disagreement |
|---|---|---|
| 1960–64 | 812 | 4.56% |
| 1965–69 | 1,820 | 3.41% |
| 1970–74 | 6,693 | 3.83% |
| 1975–79 | 11,440 | 6.64% |
| 1980–84 | 17,679 | 5.85% |
| 1985–89 | 38,830 | 2.33% |
| 1990–94 | 58,218 | 0.80% |
| 1995–99 | 75,577 | 1.20% |
| 2000–04 | 89,694 | 0.31% |
| 2005–09 | 98,717 | 0.17% |
| 2010–14 | 107,164 | 0.09% |
| 2015–19 | 116,649 | 0.09% |
| 2020–24 | 123,116 | 0.04% |
| 2025–26 | 44,774 | 0.04% |

Before 2000 this sector history rests on one vendor, and a second vendor
disagrees on the stated share of name-weeks. The two apply dividend adjustment
differently in old history, and neither is shown to be right. The history is
not cut.

## Not done here

- S&P 400 and 600 dated bases: the functions take them (`--src`); not built.
- Themes and baskets: second pull request.

## How to rerun

```
python -m scripts.build_tiingo_member_closes --breadth-dir data/breadth \
    --out /path/off-git/sp1500_closes_tradj.parquet          # ~3 min, local SSD
python -m scripts.build_group_breadth_history --closes /path/off-git/sp1500_closes_tradj.parquet \
    --breadth-dir data/breadth --basis dated --out data/breadth/history --closes-label "<store>"
python -m scripts.build_group_breadth_history ... --basis current ...     # ~20 s each
```

Never from the nightly render.
