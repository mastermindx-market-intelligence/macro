# Sector-label coverage of dated S&P 500 members (basis `reconstructed_dated_membership`)

COO item 2, 2026-11-12. Inputs: `data/breadth/sp1500_pit_membership.parquet` (src = sp500)
joined to `data/breadth/sp1500_pit_sectors.parquet` on ticker. All labels are as of now
(current GICS or current SEC SIC mapped to sectors); none is era-correct. A member
without a label belongs to no sector and is absent from every sector series.

| Year-end | Members | Labeled | Share labeled | of which SIC-derived |
|---|---|---|---|---|
| 1996 | 488 | 227 | 46.5% | 21 |
| 2001 | 496 | 299 | 60.3% | 44 |
| 2006 | 497 | 331 | 66.6% | 47 |
| 2011 | 497 | 392 | 78.9% | 49 |
| 2016 | 506 | 439 | 86.8% | 40 |
| 2021 | 505 | 476 | 94.3% | 19 |
| 2026-11-10 | 503 | 502 | 99.8% | 1 |

Labeled members by sector, 1996 year-end: Industrials 49, Financials 29, Consumer
Discretionary 24, Consumer Staples 23, Health Care 20, Materials 20, Information
Technology 18, Utilities 18, Energy 13, Communication Services 8, Real Estate 5.
With the 10-member floor, Communication Services and Real Estate are missing (not
zero) in the earliest years on this basis.

Reading: before about 2010 the dated basis is weighted toward survivors, because the
unlabeled names are almost all leavers. The early years of basis (a) should be read
with that in mind; basis (b), today's members, is survivors-only by construction.

Free SIC fill (Tiingo metadata, SEC SIC by CIK): not done in this pull request. The
worker commissioned for it could not run (its session was quarantined and the SSD
pool is at its storage floor). It is the next pull request. No purchase, no hand
labelling.
