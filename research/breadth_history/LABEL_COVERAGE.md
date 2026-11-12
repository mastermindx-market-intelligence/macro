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

## Free SIC fill (2026-11-12, `scripts/build_sp1500_sic_fill.py`)

Overlay `data/breadth/sp1500_pit_sectors_sic_fill.parquet`, 228 tickers, every row
`basis = sic_derived_fill`, as of now (the filer's CURRENT SEC SIC), `era_correct =
False`. Chain: Tiingo fundamentals metadata name for the ticker -> SEC EDGAR public
`cik-lookup-data.txt` CIK -> SEC submissions SIC -> sector by the existing collector
mapping (`collectors/sp1500_pit_sectors._map_sic`). Free sources only; no purchase,
no hand labelling. It labels only tickers the substrate leaves unlabeled and never
overrides an existing label. Tiingo names are a join key only and are not written.

A row is filled only when every link is unambiguous:

| Step | Rows left |
|---|---|
| Unlabeled in the substrate | 803 |
| Exactly one company under the ticker in Tiingo metadata | 584 |
| Tiingo price series starts by the membership start (not a later holder of a reused ticker) | 304 |
| Name maps to exactly one SEC CIK | 230 |
| SIC maps to one of the 11 sectors | 228 |

Coverage after the fill, beside the table above:

| Year-end | Members | Labeled before | Labeled after | Priced members | Priced and labeled before | after |
|---|---|---|---|---|---|---|
| 1996 | 488 | 46.5% | 50.8% | 221 | 85.1% | 94.6% |
| 2001 | 496 | 60.3% | 65.1% | 296 | 85.5% | 93.6% |
| 2006 | 497 | 66.6% | 71.8% | 352 | 84.4% | 91.8% |
| 2011 | 497 | 78.9% | 84.7% | 415 | 88.0% | 94.9% |
| 2016 | 506 | 86.8% | 90.1% | 457 | 91.9% | 95.6% |
| 2021 | 505 | 94.3% | 95.6% | 475 | 97.7% | 99.2% |

The priced columns are what the series uses (an unpriced member is absent with or
without a label). After the fill, the binding limit in early years is price
coverage, not labels: only 221 of 488 members at end-1996 have a Tiingo close.
On the rebuilt dated basis all 11 sectors are valid from 2007-01-10 (Real Estate is
last; Communication Services from 2006-04-03); before the fill, about 2010.

Not filled (575 rows): tickers with several companies in Tiingo metadata (ambiguous
reuse), tickers whose Tiingo series starts after the membership (a later holder), no
Tiingo series at all, names with zero or several SEC CIKs, and two SIC codes that map
to no sector.
