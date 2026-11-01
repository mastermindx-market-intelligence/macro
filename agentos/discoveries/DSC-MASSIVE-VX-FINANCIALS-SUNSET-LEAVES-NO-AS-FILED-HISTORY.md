---
key: MASSIVE-VX-FINANCIALS-SUNSET-LEAVES-NO-AS-FILED-HISTORY
claim: >
  Massive (polygon.io) retired `vX/reference/financials`. On both api.polygon.io and
  api.massive.com it returns HTTP 410 `GONE` with `deprecation: true` and
  `sunset: 2026-10-09`. Its successors, `stocks/financials/v1/{income-statements,
  balance-sheets,cash-flow-statements}`, serve exactly one row per fiscal period: no
  amendment, restatement or as-filed version. Each row has only a `filing_date`.
  So the vendor no longer offers a source for "restated values keep their source
  version". The Terminal's deep-history producer, ingest/massive_financials.py
  (BASE = https://api.polygon.io/vX/reference/financials), now fails on every call.
  The nightly never runs it anyway: ops/nightly_fund.sh calls collect_us_fund.py and
  gen_fund_us.py directly. Only ingest/refresh_fund.sh runs
  backfill_fund_statements_massive.py, and it treats a failure as a non-fatal WARN.
falsifier: >
  Any of these would disprove it:
  (1) `vX/reference/financials?ticker=AAPL&timeframe=annual` answering 200 with results;
  (2) a v1 statements response for AAPL annual (limit=100) with two rows for one
  (fiscal_year, fiscal_quarter), or a row field naming an amendment, version or
  source filing beyond `filing_date`;
  (3) ops/nightly_fund.sh invoking refresh_fund.sh or backfill_fund_statements_massive.py.
  Check (1) and (2) with an authenticated curl that reads the key at runtime and never
  echoes it. Check (3) with `git grep -n backfill_fund_statements_massive origin/master`.
so_what: >
  First, E11 AC-03 (restatement provenance, #922) cannot pass on production data from
  this vendor. The restatement source is now SEC EDGAR companyfacts, read by
  ingest/annotate_sec_lineage.py (mastermind-terminal PR #1067; see
  DSC:SEC-COMPANYFACTS-KEEPS-EVERY-FILING-OF-A-PERIOD).
  Second, #364's deep statement history is dark in production. Re-pointing
  massive_financials.py at v1 restores depth but not versions, and the nightly must
  also call it.
  Third, before blaming a key or a plan when a Massive endpoint fails, read the `sunset`
  and `deprecation` headers. A 410 here is a vendor retirement, not an entitlement
  change.
kind: landmine
verified_at: 2026-10-19
verified_by: >
  Probes from m1 at 2026-10-19T06:27Z, with the vendor key read from the program's env file at
  runtime and never echoed:
  - api.massive.com/vX/reference/financials returned HTTP/2 410 with `deprecation: true`,
    `sunset: 2026-10-09` and body status GONE;
  - api.polygon.io/vX/reference/financials (the producer's BASE) returned the same 410
    and headers;
  - v1 income-statements and balance-sheets for AAPL annual each returned 16 rows,
    16 distinct periods, no duplicate periods, covering 2010-09-25..2025-09-27; the only
    filing field is `filing_date`.
  The first observation was on 2026-10-18 during the E20 program close-out, with the same
  result.
  Code at mastermind-terminal master fb0dacd4e: ingest/massive_financials.py:60 (BASE);
  ingest/refresh_fund.sh:197 (the only caller of the backfill); and ops/nightly_fund.sh:274-276
  (collect_us_fund.py, then gen_fund_us.py, with no backfill).
scope:
  - mastermind-terminal
  - ingest/massive_financials.py
  - ingest/backfill_fund_statements_massive.py
  - ops/nightly_fund.sh
  - Massive / polygon.io fundamentals
confidence: verified
---

## Why it hides

The backfill is non-fatal by design, so the fundamentals refresh still ships yfinance depth and nothing goes red. The nightly never called the backfill in the first place. So the sunset changed nothing anyone watches. It only shows up when a feature asks for version history and finds none.
