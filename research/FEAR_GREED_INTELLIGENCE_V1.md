# Fear & Greed Intelligence v1

Chairman assignment: build the Macro Dashboard fear/greed, VIX dynamics and turning-evidence experience end to end. Source pin: Macro `9cfa8918b55a1c4735a90f4ca133506baa9d7966`; implementation operation `macro-fear-greed-dynamics-20261017`.

## Product decision

**Risk Radar -> Fear & Greed** is the primary home. It answers how risk appetite and volatility pressure are changing. Transmission remains the explanation of cross-asset causes and consequences, not a competing sentiment owner. Macro Signals retains the full method, component provenance and legacy comparison. The existing dialog/navigation controller is reused, with no extra fetch, polling, animation, collector, alert or runtime authority.

The improvement is not "more indicators must be better." It is separation of **level, direction, acceleration, independent confirmation and data quality**. A static extreme-fear value cannot distinguish a continuing liquidation from easing pressure. A static extreme-greed value cannot distinguish persistent healthy participation from deteriorating internals.

## CNN comparison and explicit proxy boundaries

CNN describes seven equally weighted dimensions [1]. Its exact production normalization, constituent coverage and all revision details are not reproduced here; the indexed official explainer notes a change to breadth. This is an original transparent construction, not CNN's index or a claim of numerical equivalence.

| Dimension | Public CNN description | This implementation |
|---|---|---|
| Momentum | S&P 500 versus 125-day average | SPY versus SMA125, an ETF proxy |
| Strength | NYSE 52-week highs and lows | New highs / (new highs + new lows) in our collected universe |
| Breadth | McClellan Volume Summation Index | Ratio-adjusted advancing/declining **stock-count oscillator**, not volume summation |
| Put/call | Five-day average options put/call | Five-session **SPY/QQQ/IWM delayed-chain volume proxy**, not the official equity ratio; short history is excluded |
| Volatility | VIX and its 50-day average | VIX deviation from SMA50, with a separate dynamics panel |
| Safe haven demand | Twenty-day stocks versus Treasury returns | SPY versus TLT relative return; long-duration bond proxy |
| Junk demand | Junk versus investment-grade yield spread | ICE BofA US HY option-adjusted spread, a different credit proxy |

The existing `collectors/cboe.py::PutCallAdapter` computes a volume ratio over available SPY, QQQ and IWM delayed chains. Its legacy column name `equity_pc_ratio` does **not** make it the official Cboe equity-market ratio. Historical constituent completeness is not recorded; partial-chain coverage is a disclosed limitation and this short-history leg does not qualify in the pinned snapshot. No fabricated backfill or unofficial replacement feed is used.

The two participation measures share ONE family vote; six families are equally weighted. Every raw measure gets a trailing midrank among 252 valid observations, no older than 504 sessions; inverse-oriented legs use 100 minus rank. All-tied values rank at 50. Component histories with gaps remain missing on those dates, not zero or forward-filled. A score needs at least four families including momentum and volatility. The latest qualifying **same-date** snapshot may be at most two sessions old and is explicitly marked delayed; otherwise the score is withheld. VIX has its own observation clock. Changes are suppressed whenever component coverage changes over the comparison window.

The original machine-consumed `fear_greed.dial` is preserved. The versioned display extension lives inside the existing `fear_greed.json` artifact. It neither changes the established risk probability nor originates or sizes trades. HY OAS is in **percent**, not basis points [4]; the historical unit caption is corrected without rescaling its values.

## Volatility mechanics

Cboe VIX is an annualized option-implied expected standard deviation over a constant 30-day horizon, not a price-direction forecast [2]. Our daily close diagnostics are:

```
r[t] = 100 * log(VIX[t] / VIX[t-1])
v[t] = EWMA(span=5, adjust=False, minimum=5 valid returns, reset at gaps)(r[t])
a[t] = v[t] - v[t-1]
```

Velocity has units log-percent per session; acceleration has units log-percent per session squared. Scaling all VIX levels by a constant leaves both unchanged. Daily/5-session/20-session point and percentage changes are also shown, as are trailing ranks. Positive velocity with positive acceleration means pressure is rising faster; positive velocity with negative acceleration means pressure is still rising, but more slowly. Negative velocity with negative acceleration means relief is accelerating; negative velocity with positive acceleration means relief is losing momentum, **not that VIX is already rising**.

VVIX is the option-implied expected volatility of the 30-day forward VIX price [3]. It is not the second difference of VIX. We display its level and five-session change separately. VIX/VIX3M and VIX9D/VIX use matching observation dates; these are implied-volatility horizon ratios, not VIX futures roll yield. A ratio at or above one denotes a near-term inversion, not an absolute VIX panic threshold. Stale VVIX or curve legs are unavailable rather than silently paired with current VIX.

Higher derivatives amplify noise. A third derivative is deliberately not promoted into the production signal. Daily close sampling and causal smoothing are explicit; this is not a live intraday turning-point claim. Absolute VIX 20/30/40 rules rejected by `DO_NOT_REBUILD.md` are not revived.

## Turning evidence, not a bottom detector

The existing volatility owner supplies direction and acceleration. A close counts toward persistence only when the raw VIX close move and smoothed velocity agree. Two such consecutive closes plus agreement from **stocks, participation and credit** are required for "relief is broadening" or "stress is spreading." Curve and VVIX readings do not count as extra independent votes. They can contradict the interpretation and remain visible.

A sharp-repricing watch requires positive velocity and acceleration and both trailing ranks at least 90. Decelerating upward volatility is a pressure-exhaustion watch, not a bottom. Falling volatility without independent confirmation remains a relief watch. If supporting data is missing, confirmation is unknown. The output carries `forecast_validated=false` and `probability=null`. No regime score, risk probability, sizing, trade gate or automatic alert is changed.

Two-close confirmation introduces deliberate lag. It may avoid reacting to a single reversal candle, but this is a hypothesis about usefulness, not evidence of better returns. Waiting for all three independent series can miss the first rebound. Requiring no future confirmation avoids retrospective peak picking.

## Frozen descriptive replay protocol

Written before the new replay outcomes are inspected. This is **not a prospective preregistration** and the historical market episodes are familiar. The stores contain revised dated observations, not complete availability-time vintages; historical breadth may include changing-universe effects. Consequently every result is a retrospective association, never an executable backtest or a proof of predictive superiority.

The replay uses the exact production feature and classification functions. Freeze horizons at 5, 10 and 21 sessions, suppress overlapping starts for 21 sessions within each rule, require the complete forward close path, and report censored events. Compare:

1. High VIX level alone: trailing level rank >=90.
2. VIX relief alone: at least two confirming downward closes.
3. Full relief broadening: the production two-close plus stocks/breadth/credit agreement.
4. Full stress broadening: the symmetric production rule.
5. Sharp volatility repricing: the production signed velocity/acceleration and rank rule.

For every rule report the event count, mean subsequent SPY close return, positive-return rate, mean worst subsequent close drawdown, and frequency of a 5% close drawdown. Also report next-session-close entry sensitivity. These are price-path diagnostics, not P&L: no bid/ask, financing, tax, execution or shorting-cost model. Use a fixed seed 20261017, 2,000 resamples of chronological three-event blocks for 95% bootstrap intervals when at least 12 mature episodes exist. Different rules need not share the same dates; no causal superiority can be inferred from raw mean differences. Show a common-data-span comparison and chronological 2007-2019 / 2020-2026 slices without fitting or retuning. Compare 2007-2009, 2020 and 2022 separately only where enough episodes exist; thin cells remain thin, not win-rate advertising.

A result must not be promoted because its average is positive: an equity benchmark has a positive unconditional drift. The companion eligible-date baseline, adverse tails, episode counts and uncertainty are part of the result. No thresholds will be adjusted to improve this first report. Failed or inconclusive comparisons remain in the report.

Prospective evidence begins only with first-observed snapshots naturally appended by the **existing keep-first** sentiment ledger publisher. New feature columns retain the scored date, VIX date, components, classification and `logged_at`; no existing row is backfilled and no second ledger or watcher is created. Publication-time availability, fixed episode definitions, costs and out-of-sample comparisons are required before any predictive or trade-authority promotion.

## Primary sources inspected

1. CNN, Fear and Greed Index explainer, official indexed page: https://www-stage-fastly.stellar.cnn.com/markets/fear-and-greed (index retrieved 2026-10-17; direct fetch later returned 502; component descriptions are evidence, not exact current normalization).
2. Cboe, "What the VIX and VIX1D Indices Attempt to Measure and How They Differ," 2023-04-24: https://www.cboe.com/insights/posts/what-the-vix-and-vix-1-d-indices-attempt-to-measure-and-how-they-differ ; current FAQ: https://www.cboe.com/tradable_products/vix/faqs .
3. Cboe VVIX dashboard and methodology FAQ: https://www.cboe.com/us/indices/dashboard/vvix/ .
4. Federal Reserve Bank of St. Louis, ICE BofA US High Yield Index Option-Adjusted Spread (BAMLH0A0HYM2), units Percent: https://fred.stlouisfed.org/series/BAMLH0A0HYM2 . Public accessibility does not create a new redistribution licence; this implementation uses the existing admitted caches and adds no collection entitlement.
5. McClellan Financial Publications, "A Subtle Message in the Volume Summation Index," 2022-07-21: https://www.mcoscillator.com/learning_center/weekly_chart/a_subtle_message_in_the_volume_summation_index/ . This supports the distinction between count-based breadth and the volume-summation construction, not equivalence.

## Proof and delivery

Deterministic tests cover orientation, finite/null handling, fixed history gates, ties, gaps, stale clocks, composition changes, future-data poisoning, exact signed quadrants, scale invariance and unchanged legacy machine output. UI proof must include the actual Macro dialog/navigation path, both languages/themes, desktop/mobile, disclosure operation and no page overflow. Computational and UI tests do not establish forecast skill. Research results and exact delivery receipts are appended below only after observed execution.
