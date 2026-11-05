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

## Producer-to-consumer evidence and implemented slice

The pinned `site/marketdata/rotation_events.json` is older than the pinned price-store tip: event and early-context dates October 20, generated October 21 at 08:00 UTC, overall state MIXED_ROTATION. Its XLP/SMH comparison reports two-session absolute returns +0.148365% / +1.217141% and relative wealth -1.055924%, against twenty-session relative wealth +17.929620%. It explicitly records 2S_VS_20S_SIGN_CONFLICT. This contradicts a simplistic 'defensives keep accelerating' presentation and is now visible in the repaired rail. The artifact is not an October 22 live signal.

Implementation extends `templates/rotation_events.js` and the identical published asset `site/rotation_events.js`. It mounts the existing early_context before recorded events, distinguishes absolute gains from relative shelter, checks percent units/ratio arithmetic/eligible windows/exact dates/duplicate aliases, shows stale and unavailable states, keeps horizon disagreements prominent, and provides keyboard-accessible source details. It removes unsupported money-flow language and the empty-event 'Nothing to do' all-clear. No detector, state transition, score, sizing, alert send, store or scheduler was added.

Fabric builder `defensive-rotation-ui-builder-20261022` returned terminal rc0 with response SHA256 `15c7138fad2c0b88e29a073be7240e073c4044d5c93ee8586bbd79bc7c74905d`. Its artifact was used as a starting point, not accepted unchanged. Parent repairs reject normalized impossible dates, require explicit eligibility/schema/display-only authority, use unambiguous alias tuples and full evidence signatures, distinguish missing pairs from valid empty arrays, and improve responsive presentation. The internally contradictory 'pure function but consult another current clock' requirement is resolved by using only the caller-supplied clock: source dates after that clock are rejected; a valid injected clock may intentionally replay history. The function never calls Date.now internally. The actual existing consumer passes Date.now once.

Verification: `node tests/rotation_early_context_ui.test.cjs` -> 32/32 passed. `python3 -m pytest -q tests/test_rotation_early_context.py tests/test_rotation_events.py tests/test_rotation_events_v2.py` -> 139 passed, including the executable Node suite in the already-registered Python CI pack. The initial two baseline failures were missing sparse-checkout registry bytes; materializing only the exact HEAD blob `data/oracle/ratio_pairs.json` resolved them without source changes. Existing 138 backend tests were green before the patch.

Browser probe: `python3 tests/probe_rotation_early_context_browser.py --output /tmp/defensive-rotation-ui-proof-20261022`. Four intercepted-network cases (320 light English, 390 dark English, 1280 light English, 390 dark Chinese) showed four comparisons, three horizon conflicts, zero page errors, no horizontal overflow and working keyboard disclosure. Receipt and selected screenshots are retained in `research/evidence/defensive_rotation_ui_20261022/`. This is a real candidate-script test with a pinned producer snapshot in an isolated shell, NOT authenticated production or deployment proof. No external browser requests, credentials or notifications were used.

## Stronger historical evidence: a retained October 8 observation

A bounded source-history query for `site/marketdata/rotation_events.json` before October 13 found commit `48cf3140e2ff153769044fe0b621f4719d3bace8` (committer timestamp October 9, 14:20:55 UTC). Its actual tracked build artifact, blob `6de0971e238d29a6ec3875c00880b2d67a2ec8c2`, has source date October 8 and generated timestamp October 9, 14:18 UTC. This is stronger evidence than recomputing all observations from the October 21 price history: the earlier artifact already contains `early_context` with state MIXED_ROTATION. It is still NOT proof of production deployment, a user seeing it, or an alert delivered then.

Its two-session observations (October 6 to October 8) were:

| Pair | Defensive absolute | Risk-leg absolute | Relative wealth | Honest interpretation |
|---|---:|---:|---:|---|
| XLP / SMH | +1.980434% | -3.988930% | +6.217370% | Staples rising while semiconductors fall |
| XLP / XLK | +1.980434% | -2.089110% | +4.156375% | Staples rising while technology falls |
| XLU / XLK | -0.218659% | -2.089110% | +1.910360% | Relative shelter only; utilities also fell |
| XLV / XLK | +0.640378% | -2.089110% | +2.787726% | Healthcare rising while technology falls |

The same artifact has zero active confirmed rotation events and zero newly created events. All four defensive comparisons explicitly record a two-session versus twenty-session sign disagreement. Therefore a confirmed-event-only consumer can be empty while material early sector evidence exists. This narrows a real delivery/interpretation failure; it does not retrospectively authorize buying all defensive sectors with leverage.

The previous tracked artifact found in the bounded query, `856c5939858fe6adcf41bfc2e10787a21de649a3` (October 7 commit, October 6 source date), has no early_context. This does not establish the exact first-ever production observation or delivery; it bounds only the inspected repository history. The October 9 artifact also cannot be called an alert available at the October 8 close: its recorded generation time is the following morning, 10:18 New York time.

The new production-function candidate was executed against the actual older artifact with an explicit replay clock of October 9, 14:30 UTC. Six assertions passed: the XLP and SMH absolute values, +6.22% relative display, positive absolute divergence wording, both-down relative shelter wording and horizon-disagreement visibility. The unchanged function SHA256 is `b6235b6eef93ea4cd82fdd2172bba816358135e28c1f59229a822c08df73d608`. Machine receipt: `research/evidence/defensive_rotation_ui_20261022/historical_observation_receipt.json`. This is a counterfactual consumer reconstruction using retained earlier data, not a claim that the newly built interface existed on October 9.

Interpretation rule for the product plan: short-horizon relative strength against a still-negative longer trend is a possible early reversal, whereas a negative short horizon inside a positive longer trend can signal weakening. Both are disagreements, but they are not economically identical. Preserve the signed observations and timing; do not automatically suppress an early watch merely because slow confirmation has not arrived, or promote either case to a calibrated forecast without prospective validation.

## Hosted CI styling repair and requalification

Hosted run 39910968758 on evidence head eb672786de7967a396248cc9272bd72ca9eba12f completed with one failing pack, ci-pack-9 / job120274882272. The design-system ratchet identified two new literal corner radii in the rotation rail; the other relevant test packs passed. This is a real release failure, not an inactive-context warning.

The repair uses the existing theme's canonical fallback conventions: outer card `var(--r-card,12px)`, comparison card `var(--r-ctl,8px)`. Theme.css currently documents these scales as not yet rooted, so bare token names would have lost the intended geometry. No detector, measurement, source/state or copy semantics changed. The exact pure renderer marker span remains SHA256 `16b3c49ad318e888cf17120bb515a0e3ebe7d753297a900c8e3dff5e7a48882d`; the new complete asset SHA256 is `514eba60d3d429ff90e0177d2bc51a2b5ba8d7c6f161b3113c68331a0568d061`.

Re-executed: 32 Node cases, 139 focused Python tests, and all four actual-script browser fixtures. The browser now additionally verifies the fallback radii and live overrides of both canonical tokens, then restores fallback values before capture. Receipt and four screenshots were refreshed in the existing evidence directory. Local design-system enforce-added and the incumbent visual-evidence gate both pass. These are local repair proofs, not hosted-CI or production acceptance. The previous independent review remains evidence for its unchanged semantic scope; the style/proof delta and new exact head still require release review and CI.
