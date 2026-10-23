# October defensive rotation: bounded historical reconstruction

Parent: WS:LEADERSHIP-ROTATION-INTELLIGENCE. Source revision: `mastermindx-market-intelligence/macro@eb5f608851a8d3ea8181953a28f271ec846240dd`. Research originated in the October 22, 2026 mission; the independent parent verification was performed October 23 UTC. This is a reconstruction from stored prices, not a contemporaneous alert receipt, forecast qualification, portfolio backtest or options P&L.

## Source and method

Six exact Git blobs: `data/yahoo/{SPY,QQQ,SOXX,SMH,XLP,XLU}.parquet` at the source revision above. The independent Fabric replay returned the calculations; the parent independently read those blobs with `git show`, decoded with pandas/pyarrow, and recomputed each 5/10/20-session endpoint return and the divergence dates. Source was never mutated or forward-filled. All six latest observations are October 21. October 22 is absent, so no result below is described as today's close.

Use stored `close`, the registry's vendor-adjusted basis; Yahoo adjustments can revise historical prices and the original availability vintage is not established. Even where price and total-return columns happen to agree over this window, do not infer a universal total-return guarantee. The examined recent history is development/reconstruction evidence, not a fresh blind holdout. No live collector or builder was run.

Return over n sessions: `100 * (close[t]/close[t-n]-1)`. Relative wealth in percent: `100 * ((1+R_def/100)/(1+R_risk/100)-1)`. A relative-wealth number is NOT the return on an equal-dollar long/short account; that requires leg sizing, gross/equity denominator, rebalancing, borrow, financing, execution and costs.

## Latest common close: October 21

| Instrument | 5 sessions | 10 sessions | 20 sessions |
|---|---:|---:|---:|
| SPY | +0.453489% | -0.531374% | +0.687674% |
| QQQ | -0.514439% | -4.293082% | -2.159983% |
| SOXX | -1.744253% | -12.432659% | -9.785758% |
| SMH | -1.423660% | -10.932277% | -7.434190% |
| XLP | +1.220083% | +6.621792% | +5.677545% |
| XLU | +0.671138% | +2.065610% | +5.660377% |

Ten-session anchors are October 7 and October 21. Recomputed relative wealth: XLP/SOXX +21.759768%; XLU/SOXX +16.556707%; XLP/QQQ +11.404477%; XLU/QQQ +6.643921%. These are ratios of wealth paths, not achievable portfolio returns or forecasts.

## When a simple observable divergence appeared

A descriptive test fixed in the replay commission: defensive 10-session return > 0, risk-leg 10-session return < 0, and relative wealth > 0. This is not an optimized trading signal. Requiring three consecutive observations illustrates confirmation delay, not a promoted rule.

| Pair | Start of the sustained qualifying episode | Third consecutive observation |
|---|---|---|
| XLP / SOXX | October 8 | October 12 |
| XLU / SOXX | October 8 | October 12 |
| XLP / QQQ | October 14 | October 16 |
| XLU / QQQ | October 14 | October 16 |

These are four trading-session increments earlier for the semiconductor comparisons, not nine. October 8 to October 14 includes the five observation dates October 8, 9, 12, 13, 14. A separate one-day XLU/SOXX qualifying observation on September 4 did not form the three-observation run; it must not be suppressed to make the rule look perfect. Dates are reconstructed first qualifying closes within the September 1-October 21 evaluation interval. No receipt proves the product had generated, published or delivered them on those dates.

The useful product lesson is not 'we knew a crash was certain'. It is that a broad SPY reading can conceal a material semiconductor-versus-defensive divergence. A user needed the sector/member-relative view and the absolute returns, with an early watch separate from slower confirmation. Waiting for QQQ or the entire market to weaken discarded earlier sector-specific information in this reconstruction.

## Worker adjudication

Replay child `defensive-rotation-replay-20261022`, root `defensive-rotation-20261022`, response SHA256 `c53ee2d5b4b39d624736a3b811c2cae746bf8e0ffea4155c4b0e35d259aaa0e7`, returned terminal rc0. Its core endpoint returns and sustained dates were independently reproduced. Its prose '~9 sessions earlier' is rejected and corrected above. Its scratch script is not a durable artifact and is not relied upon as sole proof. Entire uncorrected response is NOT_ACCEPTED; independently verified findings are recorded here.

Audit child `defensive-rotation-gap-audit-20261022`, response SHA256 `c9e4f92d7e9203854af701605c5bfcfef46e0317569e8824aab5c6116da13236`, returned terminal rc0. Entire response is NOT_ACCEPTED. The following broad claims are rejected:

- One failed utilities-bottom/tech-top crash predictor does not falsify all defensive rotation, all future predictive hypotheses, or the separate V11 nested-stock setup. No positive edge is thereby granted either.
- Absolute directional data already exists in `rotation_events.early_rotation_context` and `leadership_rotation_context.pair_interpretation`. Absence from one cohort enum is not systemwide absence.
- SMH exists in `config/rotation_universe.json`; absence from the 11-sector cohort is not absence of semiconductors across the system. SOXX/QQQ still need exact source/consumer checks, not alias substitution.
- Advisory `owns_paths` in a workstream is not a live conflicting writer. The actual open #9917 rendering path collision is respected; no fictional incumbent approval gate is created.
- The recommended new watch module/artifact/state is unnecessary for the immediate gap. Existing `rotation_early_context/v1` already provides a suitable producer; extend the existing consumer instead.
- The audit's claim that VIX-stratification was the deciding gate for six variants is inconsistent with its own report of multiple other failed checks. A possible sample-mask mismatch and fallback bug are unaccepted follow-up findings until independently verified; they do not authorize editing frozen research or promoting its signal.

## First implementation seam

At the pinned base `engine/rotation_events.py` publishes `early_context`, but `templates/rotation_events.js` never reads it. Repair that existing rail with an explicit absolute-versus-relative defensive summary, source date, independently validated windows and unavailable/stale states. Preserve canonical state, alert and data owners. Rendering this existing evidence is not a new detector, predictive promotion, alert delivery proof or the whole programme outcome.

Additional consumer census: `templates/sector_central.html.j2:4141` already renders a compact `M.early_context` state/coverage summary within the measured-group read. Therefore this is NOT a systemwide absence of early-context display. The bounded repair adds the missing explicit pair-level absolute/relative facts and honest empty/stale handling to the existing rotation-event rail. It does not introduce a second detector or replace the compact summary. The broader requirement for Macro entry-path prominence and real alerts remains open.
