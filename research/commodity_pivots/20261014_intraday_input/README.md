# Commodity intraday request integrity — source-only correction

Consumer dependency: Macro issue #9235. Original eight symbols and three sessions are unchanged.

## Reproduced source defect
At source main `54195c10bbeb54d2218da99ea367ee1132e84127`, the offline planner explicitly requests volume for IEX and BOATS historical bars but not `equity-intraday-bars`. Tiingo's current consolidated-equity documentation states that historical volume is exposed only when explicitly requested in `columns`.

The change adds that one source to the existing OHLCV source set. It does not modify the collector, credentials, HTTP client, rate limits, archive permissions, admission flags, source identifiers, existing request objects or already-running captures. EOD, forex and crypto request semantics remain unchanged. Generic session/force-fill settings remain caller-owned rather than silently changing all consumers.

## Verification
- Unmodified planner/archive baseline: 55 tests passed.
- Five new parameterized regression cases: three reproduced the missing equity columns before the fix; IEX/BOATS negative controls passed.
- Exact modified planner/archive tests: 60 passed.
- Existing pure planner constructs 24 distinct original symbol/session requests.
- Both live collector and credential hooks are forbidden by the new request-plan test.

The review packet adds the ORIGINAL issue #9235 restrictions `afterHours=false` and `forceFill=false` to these new request descriptions. It is explicitly NOT_DISPATCHED and execution_authorized=false. A review packet is not a capture scope, runtime grant, source-rights receipt or source-quality approval.

## Critical distinctions
A valid request does not prove endpoint coverage, trade-derived OHLC, consolidated volume semantics, point-in-time capture or execution quality. Tiingo describes this consolidated endpoint as beta and derived reference-price data. It cannot become a trade-print tape merely by adding volume. Quote/reference-derived price bars may support separately qualified indicator research but cannot automatically establish obtainable entry/stop prices.

No repeated collection, substitution for previously refused source effects, new provider, new queue or live trading rule was introduced. The incumbent Data OS owner must resolve actual writer/quota/source-rights and per-window admission before dispatch. No active collector is displaced.

## Source references
- Tiingo consolidated equity historical data: https://www.tiingo.com/documentation/equity-realtime-stock-data
- Tiingo IEX historical volume semantics: https://www.tiingo.com/documentation/iex
- Original consumer scope: https://github.com/mastermindx-market-intelligence/macro/issues/9235

This is a source fix awaiting independent review and hosted checks, not proof of production installation or successful market-data acquisition.
