---
key: SEC-COMPANYFACTS-KEEPS-EVERY-FILING-OF-A-PERIOD
claim: >
  SEC companyfacts (data.sec.gov/api/xbrl/companyfacts/CIK##########.json) returns one row per filing
  that reported a value for a concept and period, not one row per period. Each row carries the
  accession number, form and filed date. It includes 8-K recasts as well as 10-K/10-Q figures. So a
  restated period shows up as several rows with different values. GE (CIK 40545) us-gaap Revenues
  for 2022-01-01..2022-12-31 has four rows:
  - 76,555M in the 10-K filed 2023-02-10
  - 58,100M in the 8-K filed 2023-04-25
  - 58,100M again in the 10-K filed 2024-02-02
  - 29,139M in the 10-K filed 2025-02-03
  Separately, EDGAR's daily form index (Archives/edgar/daily-index/{y}/QTR{q}/form.{ymd}.idx)
  answers HTTP 403, not 404, for a day with no index: weekends and holidays.
falsifier: >
  Either of these would disprove it:
  (1) A companyfacts GET for CIK0000040545 with a declared User-Agent whose us-gaap Revenues USD rows
  for start 2022-01-01 and end 2022-12-31 are a single row, or do not include both 76555000000
  (filed 2023-02-10) and 29139000000 (filed 2025-02-03).
  (2) form.20261017.idx (a Saturday) answering anything other than 403 while form.20261016.idx
  (a Friday) answers 200.
so_what: >
  First, companyfacts alone is enough to source "a restated period keeps its filing version" (E11
  AC-03, #922). No as-filed vendor feed is needed, and Massive no longer has one (see
  DSC:MASSIVE-VX-FINANCIALS-SUNSET-LEAVES-NO-AS-FILED-HISTORY). The Terminal producer is
  ingest/annotate_sec_lineage.py, which runs in ops/nightly_fund.sh after gen_fund_us.py
  (mastermind-terminal PR #1067).
  Second, matching must use concept, duration and period end. Revenue tags are told apart by what
  the filings they share report. A tag the latest filing dropped is the current tag's predecessor (a
  rename, whose history counts) when every shared filing reports the same figure under both. It is a
  parallel measure, never pooled, when a shared filing reports different figures. A dropped tag that
  never shared a filing counts only if it carried the same figure; a different value there could be
  a restatement or a narrower measure, so no claim is made. Nor is one made when a parallel tag
  also carried the shown figure, because the current tag may have taken over its meaning. Two values are the same figure only within
  the precision they were reported at (trailing zeros, up to millions) and 1%: a later filing can
  repeat the figure (GE 2024-02-02) or round it, and a smaller restatement is still a restatement.
  Third, any EDGAR daily-index reader must treat 403 as "no index that day". A reader that treats it
  as an error never advances past the first weekend.
kind: data
verified_at: 2026-10-19
verified_by: >
  At 2026-10-19T07:20Z the companyfacts GET for CIK0000040545 returned status ok. The cached extract
  holds the four FY2022 Revenues rows above, with accessions 0000040545-23-000023,
  0000040545-23-000137, 0000040545-24-000027 and 0000040545-25-000015.
  At 2026-10-19T07:41Z, curl with the producer's User-Agent returned:
  - 200 (646,408 B) for form.20261016.idx
  - 403 for form.20261017.idx
  - 403 for form.20261018.idx
  At 2026-10-19T09:13Z the producer at PR #1067 head 65f47fa66, run offline on production copies of
  GE and AAPL, attributed 16 columns, marked 2 restated (GE FY2022 and FY2023) and left 4 without a
  revenue anchor (including both fiscal Q4 columns). A second write run changed no file and left the
  bytes identical. tests/test_sec_lineage.py has 54 tests. The tag-rename, different-figure and
  stale-stamp tests fail against head 9ff4129e9. The shared-filing tests fail under an any-filing
  rule, a one-direction comparison, or with the parallel-tag guard removed.
scope:
  - mastermind-terminal
  - ingest/annotate_sec_lineage.py
  - ops/nightly_fund.sh
  - SEC EDGAR companyfacts / daily-index
confidence: verified
---

## Why it matters

The obvious reading of companyfacts is "one figure per period". That reading throws away exactly the history a restatement badge needs. Three things in the data are easy to mistake for restatements:

- The 8-K rows. They are recasts, filed between annual reports.
- The repeated 10-K rows. They repeat the figure, so they are not new versions.
- Different revenue tags for the same period.

Read naively, the 8-K looks like noise, the repeat looks like a second version, and the tags look like conflicting figures.
