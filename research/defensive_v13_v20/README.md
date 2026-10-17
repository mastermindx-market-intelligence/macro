# Defensive compounder nested-washout research V13–V20

**Research-only reproduction package, October 13, 2026.** No broker calls, live orders, production signal code changes, proprietary raw OHLC data, raw FRED inputs, secrets or model weights. Do not use as trade-sizing advice.

## What is included

- `RESEARCH_V13_V20.md`: full research findings and limitations.
- `source/,` `tests/,` and `specifications/`: exact research code, mechanical checks and frozen stage specifications for V13–V20.
- `results/`: derived simulation summaries, V13 and V14 portfolio daily equity trajectories (not vendor OHLC), V15 same-date stock-selection events, V16 year-shuffled delay diagnostic, V17 prior-relative-strength tags, V18 entry paths, V19 20-to-63-session change, V20 trailing-beta-adjusted 20-to-63-session residuals.
- `references/v12_engine.py`: read-only copy of the V12 working loader/engine to show data and price conventions. It is not a production installation. V12 is independently reviewable in [PR #9064](https://github.com/mastermindx-market-intelligence/macro/pull/9064).
- `provenance/MANIFEST.json`: digest of every included member; ZIP SHA-256 stored separately in a publication receipt to avoid a self-referential checksum.
- `tests/RELEASE_TESTS_*.log`: **35 and 34 passed mechanical tests**, respectively.

## Reproduction boundary

V13 and V14 scripts rely on the already-accepted M2 V12 `results/account_daily.csv.gz`, which is **not republished here**, and the initial authorized 2010+ vendor historical snapshot. V15–V20 use the original V11 `primary_labeled_events.csv`, V12 stock histories and prior-stage results. Reproduce with authenticated and licensed inputs according to your own authorization. Original histories are not in this archive.

See the main [V11 publication](https://github.com/mastermindx-market-intelligence/macro/pull/9034), which contains source/specification/derived data and records the original V1 input hash. The earlier V12 source is separately owned; this publication does not rewrite that PR.

The code is provided with its original relative workspace assumptions. It is **not a turnkey plug-in for the trading service**; do not run `run_v12.py` or related code without verifying required input paths and authorized source rights.

## Interpretation

- V13 proves the cash idle-capital cost in the originally modeled sleeve.
- V14 measures a hindsight-tested SPY cash replacement using an audited close-reentry rule. **Ignore its earlier, corrected-away 16.80% result**; final core overlay was ~16.60% CAGR, and its selection-unadjusted block interval includes zero.
- V15–V16 challenge stock selection and exact crossover timing with same-date and within-year controls.
- V17–V20 assess whether observable pre-entry strength or the following 20–63-session recovery phase distinguishes outcomes. None is a validated prospective trading signal.
- All return studies use adjusted-price proxies, hindsight-survivor panels and repeatedly inspected history. Daily and two-day entry populations overlap. Baselines have no cash yield, fees are simplified, and real executable tax/market impact is not modeled.

The correct next phase is a prospective signal ledger with native chart parity and source-known issuer/rates factors, then an independent forward evaluation before any capital allocation.
