# ETF pilot amendment: native calendar discontinuity

Status: pre-outcome amendment, not a production calendar repair. The v1 specification at `8bc732d4c15c020bcafe068a9fad8a096e9d6e5e` remains immutable. Its first actual-data run at code `0afd2bdb222313ca5663d9506c6bf36e9e1cb699` stopped BEFORE event construction or return calculation because the native calendar and SPY session grid disagreed. No `etf-pilot-v1.json` was created; exact-path readback verified its absence.

## Observed failure and source

Saved source: macro `b4f95f98ef80b8cbb4636afbd723b5091658e1f1`.
Native source: `lib/nyse_calendar.py`, Git blob `0ece6439ffe4b081ee7a268fe99b69e1de1216a3`.
The sole continuity failure inside the originally specified 2006-2025 event range was:

| Previous observed SPY session | Next observed session | Native ordinals | Difference |
|---|---|---|---|
| 2006-12-29 | 2007-01-03 | 14412 -> 14414 | 2, expected 1 |

`ONE_OFF_CLOSURES` contains the 2012 Sandy, 2018 Bush and 2025 Carter closures but not 2007-01-02. The SEC's contemporaneous release 2006-222 explicitly confirms closure of the equities markets on January 2, 2007; Nasdaq's December 28, 2006 announcement independently states closure and resumption January 3.

Primary sources:
- https://www.sec.gov/newsroom/press-releases/2006-222-sec-supports-decision-securities-markets-observe-national-day-mourning-former-president-gerald-r
- https://www.globenewswire.com/news-release/2006/12/28/352957/111035/en/NASDAQ-to-Close-On-Tuesday-January-2-2007-in-Remembrance-of-President-Gerald-Ford.html

This is a calendar coverage defect, not evidence of a missing trading print. Absolute-grid slice invariance and exchange-calendar correctness are separate properties: the earlier 0/60 slice-invariance result does not certify historical holidays.

## Frozen amendment before any pilot outcomes

The primary exploratory event range becomes **2007-01-03 through 2025-12-31**. Early period: 2007-01-03 through 2014-12-31. Later period unchanged: 2015-01-01 through 2025-12-31. The boundary is the first observed session after the independently verified historical closure, selected from calendar evidence, not returns. This excludes all 2006 events and must be disclosed in every result.

Keep the original source snapshot, instruments, macro features, sign thresholds, native indicator formulas, native absolute anchor, next-session-close entry, ten-session outcome, cost assumption, quarter bootstrap and reporting rules unchanged. Keep the hard calendar-contiguity and price-support checks; any additional mismatch still stops the run. Do not add a calendar exception that merely turns the failed check green.

Full saved history remains indicator warm-up input. Consequently, this tests the **incumbent native bar policy on a contiguous event subperiod**, not an independently certified reconstruction of every pre-period calendar date. A different corrected-calendar phase is NOT silently substituted. Initial-vintage, source-release, organizational-capture, full Prophet-take and market-wide opportunity claims remain unqualified.

Why not simply add the missing date to production? `session_anchor.session_positions` counts from its reference epoch; removing an old phantom session can shift later 2D/3D bucket phase. A production repair therefore needs the existing calendar/Temporal Grain owner's historical scope, version/migration decision, cross-market blast-radius and golden-vector review. No live calendar, indicator, eligibility or ranking change is authorized by this research result.

## Required follow-through

Preserve the calendar defect as an R1 obligation. The bounded amended pilot does not close that obligation or prove all historical dates correct. Separately test the actual owner on the known closure and quantify candidate/bucket changes under a versioned correction before any production migration. Do not infer that this pre-2007 omission caused a deterioration beginning September 2026.

The current source files were materialized from exact GitHub code `0afd2bdb222313ca5663d9506c6bf36e9e1cb699`, verified against eight expected source hashes, and **77 tests passed** on the connected host. That is 48 existing intake/observation tests + 10 primitive tests + 19 pilot tests, not 77 economic validations. Hosted CI enrollment and independent review remain separate.
