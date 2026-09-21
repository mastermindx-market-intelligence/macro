# Native independent review and cached-refresh repair

Chairman's 2026-09-21 continuation explicitly authorized native Studio subagents
and Sol model selection. The installed Macro reviewer ran read-only on the
unchanged f03d40273145356bde2f73ef8b979f5e5a9754c6 candidate. Effective model:
claude-opus-5; native session 6eec35bc-5e25-4ca5-9c8a-cfd4eff880cb.
This was a substantive independent static review, not a GitHub approval or an
executed test run. The complete returned text is preserved alongside this record.
The finite review returned PARTIAL and ended; it owns no source or deployment.
Protected procedure: Mastermind@5103486e8d8c460c94f1563fec50a1e4dfc08aa3.

## Findings adjudication

- Accepted: same-day cache merge could fill missing fresh latest prices before
  coverage was counted. Seven added cases failed before repair: failed cells,
  missing date, empty pull, partial NaN/invalid refresh and absent-column shape.
- Accepted: the old cache test could age out of the incremental path. Cache tests
  now use a recent synthetic date and assert the actual `1mo` downloader path.
- Not reproduced: the suggested empty-frame TypeError. All original 17 cases
  passed unchanged on Python 3.12.13, pandas 3.0.6, NumPy 2.5.3. Empty reindex
  yielded float64, not object. The initial missing-yfinance collection error was
  environmental; an isolated Python 3.12 environment resolved it, not a code fix.
- Clarified: the 60% configured quote/MA floor and inherited 80%-of-recent-panel
  retention floor both apply. Rejection flows to the existing source failure and
  circuit-breaker owner. The repair does not weaken either gate or add retries.
- Preserved: required uninterrupted MA eligibility matches inherited calculation;
  this is a curated large-cap sample, not all A-shares. Suspensions can reduce it.
- Added: the accepted cache omits wholly unavailable columns; configured names
  still determine coverage. Runner tests no longer read shared run-status state.

## Repair and verification

Fresh observations are qualified before merging. A fresh tail older than the
cache is rejected. The existing split-seam repair remains the price-basis owner;
its valid repaired prices survive, while missing/invalid latest fresh cells stay
missing after merge. Cache bytes cannot certify a failed current pull.

Seven new behavioral RED cases failed with 17 controls passing. After repair,
one cache assertion exposed parquet dropping the pandas frequency hint; the test
now compares exact dates/values/dtypes without requiring that unstored hint.
The final five-suite command from README passes **94 tests**, no warnings, in the
isolated Python 3.12 environment. This includes 27 China coverage cases, valid
same-day/new-day incremental controls and the real incremental runner rejection.
The genuine stored-input canary was rerun with exact original-math equality and
unchanged receipt bytes; its source still ends September 4, not today.

Historical RED/84-test receipts in README retain their original source and
procedure dates. Integration is not a reason to rewrite historical evidence.
Current commands and content hashes are in `review_repair_receipt.json`.

## Remaining release/product gates

PR7592 remains the only producer repair carrier. The revised semantics require
another independent review and exact-head CI. Current CI's unrelated P0B
nav/theme receipt failures are already owned by PR7578, whose parent requested
two manifest receipt-hash rebindings; do not absorb that writer. PR7485's owner
acknowledged review5263939650 and froze release for the two copy/live-headline
repairs. PR6989 retains the original shared radar candidate and source custody.
No forecast, risk odds, sizing, ranking, trading or new data-plane authority was
changed. Merge, production collection and full China-page acceptance remain open.
