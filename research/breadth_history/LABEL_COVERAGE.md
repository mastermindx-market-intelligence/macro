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

Overlay `data/breadth/sp1500_pit_sectors_sic_fill.parquet`, 227 tickers, every row
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
| Tiingo price series starts by the membership start, and no handover inside one index | 303 |
| Name maps to exactly one SEC CIK | 229 |
| SIC maps to one of the 11 sectors | 227 |

Coverage after the fill, beside the table above:

| Year-end | Members | Labeled before | Labeled after | Priced members | Priced and labeled before | after |
|---|---|---|---|---|---|---|
| 1996 | 488 | 46.5% | 50.6% | 221 | 85.1% | 94.1% |
| 2001 | 496 | 60.3% | 64.9% | 296 | 85.5% | 93.2% |
| 2006 | 497 | 66.6% | 71.6% | 352 | 84.4% | 91.5% |
| 2011 | 497 | 78.9% | 84.5% | 415 | 88.0% | 94.7% |
| 2016 | 506 | 86.8% | 90.1% | 457 | 91.9% | 95.6% |
| 2021 | 505 | 94.3% | 95.6% | 475 | 97.7% | 99.2% |

The priced columns are what the series uses (an unpriced member is absent with or
without a label). After the fill, the binding limit in early years is price
coverage, not labels: only 221 of 488 members at end-1996 have a Tiingo close.
On the rebuilt dated basis all 11 sectors are first valid together on 2007-01-10
(Real Estate last), but Communication Services drops below 10 members again on some
sessions until 2009-03-26; all 11 are valid without a break from 2009-03-27 (before
the fill: first 2009-06-30, without a break from 2014-04-02).

Not filled (576 rows): tickers with several companies in Tiingo metadata (ambiguous
reuse), tickers whose Tiingo series starts after the membership (a later holder), a
ticker handed over inside one index (GAS: Nicor to 2011-12-12, AGL Resources after),
no Tiingo series at all, names with zero or several SEC CIKs, and two SIC codes that
map to no sector.

**Limits (independent review, all 228 first-run fills checked by hand).** The series
start check screens out a later holder whose vendor history begins after the
membership, but it does not prove identity: a vendor can attach a predecessor's
history to today's ticker. The review found 1 plainly wrong company (GAS, now
excluded) and about 6 earlier or later filers of the same company family (PCH, GRA,
CCEP, MWV, X, MYL); none of these six changes the sector the CIK gives. Labels are the
filer's CURRENT SIC, so some early-year sectors are era-wrong: PCH reads Real Estate
for 1996-2001 when it was a paper company, NC reads Energy (coal) for 1996-2000 when
it was an industrial. The existing collector labels leavers by CIK only (seat ruling
2026-10-04); this fill reaches the CIK through the vendor's ticker -> company-name
record, which includes inactive companies. That route is disclosed here and in the
builder's docstring, and every row carries `label_join = tiingo_name_sec_cik`.

Sample of filled rows (5 per start-year bucket, seed 11, reviewer's verdicts; SEC
names, no vendor names):

| ticker | membership window | SEC company name | SIC | sector | verdict |
|---|---|---|---|---|---|
| HSH | sp500 1996-01-02..2012-06-29 | Hillshire Brands Co | 2000 | Consumer Staples | right company (Sara Lee CIK, renamed) |
| MWV | sp500 1996-01-02..2015-07-02 | MEADWESTVACO Corp | 2621 | Materials | unsure (2002 filer; 1996-2001 member a predecessor; same sector) |
| CAL | sp500 1996-01-02..1996-07-22 | CALERES INC | 3140 | Consumer Discretionary | right company (Brown Group CIK) |
| CVG | sp500 2000-06-13..2009-12-21 | CONCENTRIX CVG Corp | 7373 | Information Technology | right company (Convergys CIK, later acquired) |
| FDO | sp500 2001-08-06..2015-07-07 | FAMILY DOLLAR STORES INC | 5331 | Consumer Discretionary | right company |
| CHK | sp500 2006-03-03..2018-03-19 | EXPAND ENERGY Corp | 1311 | Energy | right company (Chesapeake, renamed) |
| MTW | sp500 2007-11-16..2009-09-01 | MANITOWOC CO INC | 3531 | Industrials | right company |
| HCBK | sp500 2007-02-15..2015-11-02 | HUDSON CITY BANCORP INC | 6036 | Financials | right company |
| TWC | sp500 2009-03-30..2016-05-18 | SPECTRUM MANAGEMENT HOLDING COMPANY, LLC | 4841 | Communication Services | right company (Time Warner Cable CIK, renamed) |
| DNR | sp500 2009-04-02..2015-03-23 | DENBURY INC | 1311 | Energy | right company |
| VVC | sp400 2012-01-13..2019-02-06 | VECTREN CORP | 4932 | Utilities | right company |
| CAA | sp400 2012-01-13..2018-02-13 | CalAtlantic Group, LLC | 1531 | Industrials | right company; homebuilder to Industrials is a SIC-map limit |
| CVEO | sp400 2014-05-30..2014-12-16 | Civeo Corp | 7000 | Consumer Discretionary | right company |
| WBMD | sp400 2016-04-04..2017-09-18 | WebMD Health Corp. | 7389 | Industrials | right company |
| CCEP | sp500 2016-01-04..2016-05-31 | COCA-COLA EUROPACIFIC PARTNERS plc | 2086 | Consumer Staples | wrong filer (successor plc; member was Coca-Cola Enterprises; same sector) |
| SITC | sp600 2019-12-17..2025-12-22 | SITE Centers Corp. | 6798 | Real Estate | right company |
| VSI | sp600 2019-12-17..2019-12-17 | Vitamin Shoppe, Inc. | 5400 | Consumer Staples | right company |
| MEI | sp600 2019-12-17..2024-06-24 | METHODE ELECTRONICS INC | 3678 | Information Technology | right company |
| COOP | sp600 2020-09-21..2025-10-06 | Maverick Merger Sub 2, LLC | 6199 | Financials | right company (Mr. Cooper CIK, now a merger subsidiary) |
| ARCH | sp600 2024-03-18..2025-01-14 | ARCH RESOURCES, INC. | 1221 | Energy | right company |

## Price coverage is the binding limit (read-only count, 2026-11-12)

The 453 dated S&P 500 membership rows with no Tiingo close inside their own window
were checked against the whole archive (47,564 tickers, all capture days) and the same
Tiingo name -> SEC CIK chain:

| Start year | (a) under another ticker | (b) ticker held only by a later company | (c) not in the archive | Total |
|---|---|---|---|---|
| 1996 | 2 | 93 | 173 | 268 |
| 1997-2001 | 1 | 33 | 60 | 94 |
| 2002-2010 | 1 | 12 | 35 | 48 |
| 2011-2026 | 2 | 4 | 37 | 43 |
| All | 6 | 142 | 305 | 453 |

231 of the 453 rows resolve to no CIK, so the six rows under another ticker are a
floor reached by this chain, not a proven total. The five unambiguous pairs are
ANTM -> ELV, ENDP -> ENDPQ, RSHCQ -> RSH, SIVB -> SIVBQ and TUP -> TUPBQ; FPC matches
two CIKs and is ambiguous. Because (a) is small, no remap was built. The early dated
years are therefore a sample of about half the index (221 of 488 members priced at
end-1996): the archive does not carry most pre-2000 leavers, and no free chain found
here recovers them. No purchase.
