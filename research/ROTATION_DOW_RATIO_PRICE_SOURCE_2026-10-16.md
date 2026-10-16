# Dow-vs-Nasdaq registered rotation input: Yahoo source coverage

**Date:** October 16, 2026. **Operation:** rotation-dow-benchmark-coverage-20261016-sol.
**Chairman mission:** Mastermind/Prophet defensive-rotation and early-leadership response.
**Base Macro SHA:** 3fb66dba9cfab778066e75652e8989b296ee2a02.
**Protected procedure:** Mastermind 2cc4942e136ad4fb544fd5c72ab1856608a5dac1,
Skillpack 1.0.1/bootstrap major 1. **Release:** source-only, not accepted.

## Original failure

The October 15 native Rotation Command pair dia_vs_qqq is preregistered
under scripts.leadership_rotation_study.PAIRS as
(broadening_proxy, DIA, QQQ), yet its first-market-session ratio was refused
with STALE_NUMERATOR/TWO_SESSION_CONTEXT_UNAVAILABLE. Exact committed
source parquet reads: data/yahoo/DIA.parquet ends Oct 14, while
data/yahoo/QQQ.parquet, XLP, XLK, XLV reach Oct 15.

The incumbent YahooAdapter.all_tickers() returned 746 maintained symbols
but **omitted DIA**. The existing config.yml Yahoo extras list included
^DJI (Dow cash index), but ^DJI is not DIA ETF and cannot replace its close.
A good source health run can thus leave a preregistered Dow-vs-Nasdaq
denominator/numerator pair unevaluable indefinitely.

## Minimal pre-existing-owner correction

Add exactly DIA after QQQ in the original config.yml yahoo.tickers.extras
list, preserving ^DJI, all other tickers, provider selection, data source,
retry/clock owner and no new identity/registry. No fresh market data or
correction to historical results was invented.

The existing CI-registered tests/test_rotation_early_context.py now
checks every ETF constituent of the original preregistered
scripts.leadership_rotation_study.PAIRS against the actual
YahooAdapter.all_tickers() fetch roster, with no second hard-coded
constituent list. It initially FAILED exactly on ['DIA']; after the
one-ticker correction it PASSED, with exactly one DIA occurrence.

## Verification

- Original RED: absent DIA from active daily fetch roster, all other
  preregistered pair legs present.
- Focused GREEN: 1 passed.
- Broader existing rotation and Yahoo suites: **208 passed, 1 skipped,
  2 expected failures**; no new ordinary test failures.
- Existing sparse checkout initially lacked tracked
  data/oracle/ratio_pairs.json. A normal local Git sparse-checkout
  expansion restored data/oracle (26 original tracked files) without
  modifying those original bytes. The complete broader suite then passed.
- The config semantic comparison against the original base confirms
  DIA as the **only** changed YAML value (Yahoo roster 746 -> 747);
  QQQ/^DJI and every other group are unchanged.
- No live Yahoo call, external provider request, credential access,
  collection-run dispatch, trade, alert, forecast or price-data write.
- CI acceptance, independent source review, publication, merge,
  installation and natural nightly/customer rendering remain separate.

## Product relevance and next acceptance

A normal Yahoo collector will now request the original DIA ETF series
alongside QQQ, eliminating one source-registration reason why the Dow
broadening comparison could not be dated correctly. The next ordinary
collection must still prove a valid **completed-session** DIA close
and original availability before the ratio can be evaluated and shown.
Do not substitute ^DJI, infer capital flows or treat a relative-price
difference as a qualified BUY/SELL or forecast.

WM is also absent from Yahoo's current fetch roster but is not added
because a named hindsight winner does not automatically establish an
eligible strategy or source membership. F3 theme discovery, Prophet B4,
alert delivery and Risk Envelope producer ordering remain open.
