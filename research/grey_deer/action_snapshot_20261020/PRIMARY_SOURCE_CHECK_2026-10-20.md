# Risk Radar — bounded primary source verification

**Recorded 20 October 2026.** This check qualifies instrument identity and one dated closing price for the [observed action map](DATED_ACTION_MAP_2026-10-16.md). It is separate from source-purpose admission for model estimation, historical point-in-time availability and current execution.

## Accepted bounded findings

| Question | Primary evidence | Result and limit |
|---|---|---|
| Is the retained SPY 16 October price the closing price? | [State Street SPY issuer page](https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-sp-500-etf-trust-spy), dated 16 October 2026 fund market-price section | Issuer closing price $763.25; retained `close_price` $763.25; exact difference $0.00. The issuer separately reports NAV $763.37, bid/ask midpoint $763.30 and intraday low $760.66. None substitutes for the official close. |
| Does QQQ represent the Nasdaq Composite? | [Invesco QQQ description](https://www.invesco.com/qqq-etf/en/about.html) and [Nasdaq NDX description](https://indexes.nasdaq.com/Index/Overview/NDX) | QQQ is Nasdaq-100 exposure. Its benchmark covers large Nasdaq nonfinancial companies, not the complete Nasdaq Composite. This proxy cannot close the literal Composite reconstruction gap. |
| Can the current Nasdaq page establish a dated 16 October NDX observation? | Nasdaq NDX page above, inspected in the 20 October session | The retrieved body displayed 19 October data while the search extract displayed 16 October. The dated 16 October value was not admitted from that mismatch. Its instrument description remains usable. |
| Does the Nasdaq QQQ historical page provide an independently usable daily table? | [Nasdaq QQQ historical page](https://www.nasdaq.com/market-activity/etf/qqq/historical) | The retrieved page did not expose a usable dated daily-price table. No QQQ daily value was promoted from it. |

## Exact retained comparison

A bounded native read used Macro commit `247677efade31ea32d6b6ef5b701de61c47392cd`, file `data/yahoo/SPY.parquet`, SHA256 `4628a0de7c489988d30e7b52843d6f25d520b553f140d17ef5a42ccf39c70ff4`. The process completed exit 0, PID 28137, runtime 1.41 seconds. It read four existing rows, performed the exact 16 October close comparison and made no provider acquisition, fit or mutation. The 16 October `close` and `close_price` both equal 763.25.

The [machine-readable check](PRIMARY_SOURCE_CHECK_2026-10-20.json) retains the compared rows, source identities and limits. Original source `available_at`, first-user publication, first executable price after publication, full daily-series authentication and all remaining ETF primary-price comparisons remain unknown. This corroborates one archive value. It does not confer predictive, fund-flow, allocation or execution authority.

