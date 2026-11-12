# Sector Intelligence: price-store finding (2026-11-12)

From the Sector Intelligence quant lead (COO thread 2f136a11, ruling 27). This note is for the rotation programme. Data-health issue: #11124.

## In plain words

The nightly breadth collector keeps a cache of S&P 500 closes, `data/breadth/_closes_cache.parquet`. Each night it re-downloads only the last month, with dividend back-adjustment, and keeps every older row as it was first stored. Older rows therefore never receive later dividend adjustments. They sit too high, so each name's 200-session average sits too high. A dividend payer close to its average reads as **below** it when it is not.

The cache is the defective store. An independent end-of-day archive with one adjustment throughout does not show the effect.

## Counts by cause

The comparison covers 485 members priced in both stores, at 41 week-ends from 2026-01-02 to 2026-10-09. A disagreement is a name-week where the name is above its own 200-session average in one store and not in the other.

| cause | name-weeks | direction |
|---|---|---|
| dividend vintage, step where the one-month refresh window starts | 50 | all: cache reads below |
| dividend vintage, step at the ex-dividend date | 12 | all: cache reads below |
| within 0.5% of the average in both stores | 57 | 55 of 57: cache reads below |
| one-session date timing | 2 | cache reads below |
| split handling or wrong series | 0 | |
| **total** | **121** | |

Sector concentration of the 62 dividend-vintage rows:
- Financials 15, Real Estate 15, Utilities 11, Materials 6, Consumer Staples 5;
- every other sector 3 or fewer.

## The test that could have failed

We downloaded today's members once over the full window with the same library and the same adjustment setting, so the whole window was on a single vintage. We then reran the same comparison.

| | collector cache | single-vintage download |
|---|---|---|
| name-week disagreements | 121 | 9 |
| dividend-vintage rows | 62 | 1 |
| largest sector gap, 13-week like-for-like change in share above the 200-session average (pct points) | 15.27 (Real Estate) | 4.76 (Communication Services; one name in a 21-name sector) |

## What this means for you

- The nightly sector breadth on main (`data/breadth/sector_breadth.parquet`) and the reconstructed breadth history (`data/breadth/history/`) are built from **different price sources**. Compare them; never join them into one series.
- The nightly file's share above the 200-session average is **biased down for dividend payers**: most in Real Estate, Utilities, Financials and Consumer Staples. The bias grows with time since the cache was last fully re-downloaded.
- Any forward record built on the nightly file inherits that bias until the collector's owner fixes the cache. The remedy is the owner's call (#11124).
- Two tickers on today's membership list, MMC and FI, get no prices from the source under those symbols. Fixing the list is the list owner's job.

Nothing here is related to forward returns or outcomes. This note contains no member prices and no name-level archive figures.
