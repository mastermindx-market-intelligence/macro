# Defensive nested washout V21–V23 (October 13, 2026)

**Research-only. Not a live signal, trade recommendation, position record, sizing model or validated alpha estimate.**

The paper-only status sheet reconstructs market bars through **October 8, 2026**, which is **stale** relative to this October 13 publication. Pending following-open fills were *not* observed, and a historical backdated reconstruction is not prospective monitoring.

## Included

- [RESEARCH_V21_V23.md](./RESEARCH_V21_V23.md): full methodology, result tables, limitations and continuation decisions.
- source/tests: original executed offline V21 confirmed/developing watch reconstruction, V22 market-beta-adjusted all-crossover comparison and V23 incremental condition contrast, with 21 passing mechanical tests.
- results: 72 dated V21 watch states, 2,771 derived V22 condition outcomes and V23 matched/clustered comparisons, verified receipts.
- specs: pre-run frozen method declarations per stage; stage extensions are posthoc to earlier V11–V20 history.
- provenance/manifest: archive member hashes and original baseline citations.

## Recovering the inputs

Requires separately permissioned V11–V12 raw/vendor price input and source as documented in the merged [V11 PR #9034](https://github.com/mastermindx-market-intelligence/macro/pull/9034), independently owned [V12 PR #9064](https://github.com/mastermindx-market-intelligence/macro/pull/9064), and [V13–V20 PR #9129](https://github.com/mastermindx-market-intelligence/macro/pull/9129). Original vendor OHLC files, raw FRED data and brokerage credentials are not in this package. The provided source retains its M2 research workspace path assumptions; do not install into a service.

## Boundaries

Do not convert any positive retrospective fraction or unadjusted interval to a calibrated buy probability. The user’s actual chart-native 2W phase and RSI-MACD species remain unverified. Peer groups are heterogeneous, comparisons overlap, and all historical evaluation years have already been inspected.

**The next experiment must collect genuine time-stamped forward outcomes and source-known issuer and rates covariates before promoting a hypothesis into a trading rule.**
