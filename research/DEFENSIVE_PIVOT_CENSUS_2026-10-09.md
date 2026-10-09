# Defensive compounder pivot census — 2026-10-09

## Scope and status

Current Chairman assignment: research stock-specific technical timeframes, pivot bottoms/tops and entry confluences for MCD, WMT, WM, COST, PG and related defensive compounders. Research only; no trade, position sizing, production signal, deployment, runtime job or new control plane. This is a research milestone, not a production-acceptance receipt or a claim of exact advance pivot knowledge.

Compatible protected procedure: Mastermind `326c8469a21d7f50fc9ecb1848196bf1c6e66685`, skillpack 1.0.1/bootstrap 1. Research source base: macro `3d90aad6d83152dfeeaf8345bc995826ac9d3139`. Direct execution used because method design, data-quality adjudication and statistical interpretation remain intertwined. No children dispatched, no pending external returns, no uncertain modifications.

## Data and frozen primary method

Public Yahoo chart snapshots were obtained for 18 stocks (MCD, WMT, WM, COST, PG, RSG, KO, PEP, CL, CHD, KMB, MDLZ, HSY, CLX, JNJ, ADP, CTAS, KR) and SPY/XLP/XLI/XLY. The snapshot inventory contains 44 successful files, 92,774 daily observations and 76,494 raw hourly observations. Daily history begins in January 2010; hourly history begins October 14, 2024. All research excludes October 9, 2026: the final included date is October 8, 2026. Raw vendor data is not republished here.

Daily OHLC is multiplied by adjusted-close/close; hourly prices use the corresponding daily factor. These are vendor-adjusted price proxies, not audited executable total-return portfolio accounting or point-in-time vendor vintages. The universe is survivor-selected. Earnings calendars, historical spreads, auction fills and overnight liquidity are not verified.

Daily development: 2011–2018. Validation: 2019–2022. Holdout: 2023–October 8, 2026. Signals use completed bars and enter at the following open. Outcomes use 5/10/20-session closing prices, less 10 basis points round-trip cost. Boundary-crossing outcomes are purged. Entries are nonoverlapping within each stock/rule/horizon/period, not across distinct policies. A same-stock, same-calendar-year, same-trend-state all-date return is a retrospective comparator, not an investable forecast. Confidence intervals resample calendar-quarter blocks.

Seven entry rules were evaluated: price break alone; RSI recovery above 30; MACD(12,26,9) histogram crossing positive with MACD below zero; 20EMA trend pullback; 50SMA trend reset; stressed price reclaim; failed 20-session-low breakdown/reclaim. Four top warnings were also measured. Nine implementation tests passed, covering Wilder smoothing, RSI boundary cases, prefix invariance, next-bar aggregation, unequal session tails, period purging, nonoverlap, barrier ordering and daylight-saving timestamps.

## Daily milestone findings

Retrospective pivots are local extrema within a 21-session window (ten sessions on each side). They are labels for descriptive analysis only and are not signal inputs. In the five named stocks, median RSI(14) at an uptrend pivot bottom is approximately 44–45, rather than 30. Median depth from the preceding 20-session high is MCD 5.23%, WMT 6.05%, WM 5.08%, COST 6.55%, PG 4.62%. These medians are not entry thresholds or guaranteed pullback sizes.

A candidate was eligible only with at least 12 development events, eight validation events and positive matched excess return in both periods. Selection uses validation excess return with an uncertainty penalty, never holdout rankings.

| Stock | Locked candidate | Holdout events | Positive 20-session outcomes | Mean net outcome | Matched excess | Approximate 95% block interval for excess |
|---|---|---:|---:|---:|---:|---|
| MCD | Failed breakdown/reclaim | 13 | 61.5% | +0.95% | +1.40 percentage points | -0.80 to +3.64 points |
| WMT | No candidate qualified | — | — | — | — | — |
| WM | Below-zero MACD crossover | 15 | 60.0% | +2.45% | +0.97 points | -0.42 to +2.93 points |
| COST | Failed breakdown/reclaim | 12 | 83.3% | +3.42% | +1.87 points | +0.61 to +3.90 points |
| PG | Below-zero MACD crossover | 18 | 72.2% | +1.76% | +1.57 points | +0.13 to +3.50 points |

COST and PG are promising candidates, not production-qualified strategies. Multiple-testing and small-sample uncertainty remain. The fixed-horizon win rate is not a stop-managed trade win rate. All 18 stocks and all rule comparisons are retained, including negative findings; no universal profitable rule was established.

Across the full stock panel, a first RSI crossing above 70 was followed by a mean +0.89% net 20-session outcome, positive in 56.7% of 171 holdout events. That contradicts treating RSI 70 as an automatic top, but does not by itself establish an optimal exit policy.

## Intraday qualification defect and held claims

Early-close hourly records contain missing bars and zero-volume aggregates with inconsistent ranges. Entire malformed/incomplete sessions are excluded. The current RTH grids have unequal tails: 1h/2h/3h grids finish with a 30-minute bar; 4h finishes with a 150-minute bar. They must never be labeled uniform 4-hour or 24-hour studies.

The initial hourly run produced 7,090 scenario rows, but stock and SPY valid-session calendars differ. Intraday relative comparisons require an additional common-calendar/window audit. No per-stock best intraday timeframe is accepted from this run. Indicators currently bridge excluded sessions; that limitation must remain explicit even after outcome-window fixes.

## Recovered existing research — do not substitute description for validation

Existing `reports/mwr_timeframe_personality.md` and `scripts/research/mwr_timeframe_personality_scan.py` at the research base contain a descriptive 1,623-name Stoch-RSI timeframe ladder. Its volatility/best-timeframe ordinal correlation is +0.035, not support for a universal slower-stock/higher-timeframe rule. MCD's weekly descriptive uplift is +2.22 percentage points over its own 63-session baseline, but the report is not a next-open, nonoverlapping held-out executable test. The new study should qualify, not blindly repeat, this evidence.

## Verified artifact identities

- snapshot manifest SHA256: `69703435b594cca35ea7f8e26673dc719c0ec9b3db3dc802df9ca531e0ce6ed3`
- primary analysis source SHA256: `cf118b1d0af16fd88b696ece100aad754281d00ec2186dea5d2baf1738f00bb1`
- daily summary SHA256: `0ac5e5ec3cacd820a6db381a899e6cc4108e63eaff8a10a9abd5ea44763d14a3`
- locked daily selection SHA256: `75ce12222a924cb2bd06179a5d38079f809254eac3464e9fe38a7bb9cd08a90c`
- preliminary, not-qualified intraday summary SHA256: `f265a87787b23a761bd78f1c970246603c2ce4b2189321fbc38c68574dc16516`

## Current frontier

Accepted and do not redo without an invalidator: data snapshot inventory, daily OHLC checks, nine unit tests, daily census, frozen daily selection and explicit negative results. Remaining: common-calendar intraday audit and same-opportunity timeframe comparison; causal held-out multiday/weekly ladder; cost/multiplicity/exit robustness; final stock-specific research playbook and reproducibility package. No raw quotes, future-looking pivot labels or legacy descriptive winners may be promoted into live signals. Continue the safe research phases in the current turn; this checkpoint is a save, not a stop.
