# Risk Radar historical calendar qualification

**Dated:** 2026-10-17 UTC. **Status:** documentary research and retrospective reconciliation; no calendar, source data, census results or release changed.

## Conclusion and scope

The records below explain the **seven supplied differences as exchange closures**, with a document-custody qualification for the exact 1994 date. Conditional on the parent's reported set comparison, removing those dates from the calendar's expected-session set reconciles its count: **8,493 − 7 = 8,486**. This does **not** certify the completeness of either the trading calendar or the historical price census.

The internal comparison was supplied by the parent and was not rerun for this research: the frozen 36-ETF census uses 8,486 SPY-reference sessions, 1993-01-29 through 2026-10-15 inclusive; `lib.nyse_calendar` at Macro commit `3ab3382af89242c7b7fe8c65360bd883a7dd3504` yields 8,493 expected sessions and precisely the seven dates below are absent. The parent reports that its one-off closure list currently contains Sandy 2012, Bush 2018 and Carter 2025. These internal statements are premises, not facts established by the web sources.

## Date-by-date qualification

| Date(s) absent from the supplied SPY-reference set | Count | Direct documentary support | Qualification |
|---|---:|---|---|
| 1994-04-27 | 1 | NYSE historical special-closing chronology, PDF page 18 (zero-based page 17), lists a closure for Richard M. Nixon's funeral. [S1] | Exact date is supported by a reproduced NYSE document hosted outside NYSE. SIFMA's institutional presentation lists the 1994 Nixon funeral among NYSE closures and cites NYSE's original chronology URL; the contemporary SEC digest independently establishes April 27 as the mourning date, but does not itself establish exchange closure. [S2, S3] |
| 2001-09-11, 2001-09-12, 2001-09-13, 2001-09-14 | 4 | GAO reports that U.S. stock and options exchanges closed on the day of the attacks and did not reopen until September 17. SEC's September 16 release confirms that equity markets would resume on Monday, September 17. NYSE chronology explicitly lists September 11–14 as closed. [S4, S5, S1] | First-party institutional retrospective account, contemporary regulator reopening notice and exchange chronology agree. These are four weekdays, not four independent shock episodes. |
| 2004-06-11 | 1 | SEC release 2004-77, dated June 7, confirms the securities markets' Friday, June 11 closure for Ronald W. Reagan's national day of mourning. NYSE chronology also lists the date. [S6, S1] | Contemporary first-party regulator confirmation. |
| 2007-01-02 | 1 | Nasdaq Trader General News 2007-22 explicitly states that equity markets were closed on January 2 for Gerald Ford's national day of mourning. NYSE chronology lists that exact date. [S7, S1] | First-party exchange operational notice. Nasdaq also says normal T+3 settlement remained operational; an equity trading closure must not be substituted for every settlement or funding calendar. |

## Source register and custody

- **S1 — NYSE, historical special-closing chronology, revised through November 2008.** Accessible reproduced PDF: <https://www.ltadvisors.net/Info/research/closings.pdf>. Exact locations: PDF page 18 for April 27, 1994; page 19 for September 11–14, 2001; page 20 for reopening; page 21 for June 11, 2004 and January 2, 2007. This is an externally hosted copy of the NYSE chronology, not a presently retrieved first-party NYSE file. Byte identity with the former original was not independently established.
- **S2 — SIFMA presentation appended to TMPG meeting minutes, September 23, 2014, hosted by Federal Reserve Bank of New York.** <https://www.newyorkfed.org/medialibrary/microsites/tmpg/files/september_minutes_2014.pdf>. Final PDF page (15; slide 12) lists the 1994 Nixon funeral among NYSE closures and attributes its history to `http://www1.nyse.com/pdfs/closings.pdf`. This corroborates event/year and provenance, not the exact April date. Its Reagan-year entry conflicts with S6 and is not used to qualify the 2004 date.
- **S3 — SEC News Digest, issue 94-78, April 26, 1994, page 1.** <https://www.sec.gov/news/digest/1994/dig042694.pdf>. Establishes April 27, 1994 as Nixon's mourning date and explains SEC office arrangements. Government closure alone is not exchange-closure evidence.
- **S4 — GAO-03-251, Potential Terrorist Attacks: Additional Actions Needed to Better Prepare Critical Financial Market Participants.** <https://www.gao.gov/assets/a157377.html>. See “Most Securities Exchanges and Market Support Organizations Were Not Directly Damaged”: stock and options exchanges closed on the day of the attacks and reopened September 17, 2001.
- **S5 — SEC release 2001-92, September 16, 2001.** <https://www.sec.gov/newsroom/press-releases/2001-92-sec-monitor-securities-markets-when-they-open-monday>. Confirms September 17 reopening after successful weekend systems tests.
- **S6 — SEC release 2004-77, June 7, 2004.** <https://www.sec.gov/newsroom/press-releases/2004-77-sec-confirms-closure-securities-markets-june-11-2004-observe-national-day-mourning-former-president>. Confirms June 11 closure for Reagan mourning.
- **S7 — Nasdaq Trader, General News 2007-22, August 2, 2007.** <https://www.nasdaqtrader.com/TraderNews.aspx?id=gn2007-022>. See the paragraph beginning “On January 2, 2007” under the Regulation SHO threshold-list explanation; it distinguishes the equity closure from operating settlement.

Direct retrieval of the former NYSE chronology URLs (`https://www.nyse.com/pdfs/closings.pdf` and `http://www1.nyse.com/pdfs/closings.pdf`) and a Wayback dated route was unsuccessful in this session. S1's hosting qualification therefore remains visible. No Wikipedia, news report, software calendar or vendor price series is used as the substantive closure authority.

## Implication for the frozen census

These seven absences are consistent with non-trading dates, so they should not automatically be classified as seven missing SPY price observations or filled with synthetic closes. The result resolves the **observed seven-date discrepancy**, conditional on the supplied comparison, while leaving other calendar and data questions open: historical recurring-holiday rules, early closes, halts, venue-specific availability, listing/inception dates, duplicate or erroneous prices, point-in-time membership, and each ETF's independent coverage were not certified here. Nor does this documentary reconciliation validate predictive claims or establish historical information availability at a trading decision time.

Keep the frozen census and its cutoff unchanged. Any correction to the shared calendar should be a separate owner-reviewed source change with its own comparison evidence; this memo grants no such release authority.
