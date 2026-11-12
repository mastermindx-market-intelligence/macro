# Grey Deer: crash warnings, capital protection and recovery

Date: 2026-09-27 America/New_York (execution crosses 2026-09-28 UTC).
Operation: `grey-deer-warning-crash-recovery-20260927-sol-c1-001`.
Workstream: `WS:GREY-DEER-RISK-INTELLIGENCE`; Linear: MAS-258.
Parent: Macro #6989, `risk-radar-all-regions-upgrade-20260908-sol-001`.
Commissioning authority: Chairman Chris; accountable owner: Sol.
Source audit: `977dca13603204300a9d3888c0081eff100e091f`.
Implementation branch base: `f607c857239a5336b1a2196e563b038f62178e67`.

## Outcome and release boundary

A user on a country dashboard, stock page or Terminal must see serious deterioration without having to discover a modal. Early fragility, an active break, and recovery must remain distinguishable. A high risk intensity is not a probability. A warning is not permission to execute a trade. The existing Risk Envelope remains the canonical derived projection; existing Radar engines, Chronicle/Reflexes/QLedger, country profiles and data collectors remain owners. No universal fused score, second ledger, scheduler or automatic held-position exit is authorized.

The Chairman requests substantially better research, not an arbitrary conversion of today's 80/99 readings into a sell-all rule. This commission authorizes a new bounded warning-delivery candidate and research program. It does not blanket-release prior HOLDs or promote previously rejected signals. Production acceptance requires source, pipeline, publication, authenticated browser and evidence receipts, not merely a PR or unit-test pass.

## What the source actually proves

1. `scripts/build_rr_banner.py` reads only US `data/regime/latest.json.risk_radar` and requires gated `state == risk-off`. Caution and elevated deliberately yield no legacy alert. `site/rr_banner.json` at the audit pin has source session 2026-09-25 and `alert:null`.
2. `templates/wh_banner.js` fetches the two channels at boot, places White House first and alternates only when reduced motion is disabled. The two-channel reduced-motion path needs an adversarial visibility test. Dismissal hides both channels. These are source findings, not a completed production incident reproduction.
3. The settled US envelope at the implementation base is `mastermind.risk_envelope/v1`, session 2026-09-25, bundle `2c342c61cab94630`. Its measured state is MIXED/59; hazard stage FRAGILE; leadership monitor BROKEN (42 fresh of 42 tracked names); Radar caution/80, rates/inflation driver. Two issued warning sessions are not the existing five-session persistence threshold. Do not invent persistence.
4. The envelope says FRESH because its source artifacts share a session, while market-state detail says `any_input_stale=true`, `worst_input_age_days=86`. Artifact freshness and underlying-input freshness must not be collapsed. This is a quality warning, not proof that the entire market-state result is wrong.
5. Existing recovery engines and the nine-file source repair in #7029 must be reused. #7029's actual current release/check state needs fresh reconciliation; its historical proof is not a new production receipt.
6. The replay/live state mismatch recorded in `DSC-RISK-RADAR-REPLAY-LIVE-STATE-PARITY-DEFECT.md` invalidates pre-repair state-dependent backtest interpretations until rerun with canonical transitions. Do not promote from the old gate-latency table.
7. CN #7897 supports qualified external-driver hazard, not a 99% probability. CN #7884 rules `DISPLAY_CONTEXT_ONLY`, no exact x0.62 risk-budget advice. #7872's episode-aware authority and #7875's presentation wording must be reconciled on their existing carriers. All previous explicit HOLDs remain respected.

## Architecture: four questions, not one number

- Economic regime: growth/inflation conditions. Reflation can coexist with dangerous equities.
- Market condition: observed trend, breadth, leaders, credit and liquidity damage.
- Forward hazard: separately calibrated target/horizon, or explicitly unvalidated fragility. Distinguish precursor, trigger, amplifier and contemporaneous confirmation.
- Response and recovery: evidence-qualified protection policy and a separate repair process. A falling hazard score does not prove a bottom.

The visible priority is danger first, explanation next, regime context after that. Contradictions stay visible. Coverage and underlying-input quality travel beside every reading. International markets retain their own indices, calendars, monetary systems, effective membership, units and evidence cohorts. US MOVE is a global dollar/rates transmission input, not a substitute for local rate volatility or local policy.

## Delivery slice W1: warning projection and transport

Use the existing banner publisher/client, not a second global banner or poller. Preserve the legacy `alert` field and its meaning for existing operator-exposure consumers until a versioned migration is reviewed. Add a versioned display projection rather than silently redefining old alert counts.

The pure projection consumes existing country-bound Radar snapshots and an independently supplied expected settled session. It never recomputes scores, probability surfaces, state gates, `can_force`, rankings, sizing or portfolios. Existing state-to-attention mapping is fixed for this candidate:

| Existing state | Attention | Meaning |
|---|---|---|
| calm | none | No current Radar warning; not a guarantee of safety |
| watch | watch | Monitor emerging risks |
| caution | warning | Risk building; confirmation incomplete where the engine says so |
| elevated | high | Elevated risk conditions warrant prominent attention |
| risk-off | critical | Severe risk conditions; capital protection deserves priority |
| absent/malformed/stale/future/foreign scope | unavailable | Current risk cannot be established; never substitute calm |

Raw intensity and `state_ungated` are explanatory context only. A raw 99 capped at caution cannot become a confirmed critical signal merely through this adapter. Separately observed emergency market damage can only arrive through an existing qualified canonical producer, not a hand-built numerical override in the banner.

Requirements: strict dates and finite scores; no manufactured observation time; explicit expected-session provenance; unknown is not zero; per-market scope and coverage; no averaging country scores into global odds; deterministic identities; no mutation of inputs; no forecast or capital authority by projection; underlying-input warnings separate from artifact clock; omission from a new payload cannot silently clear a previous severe warning. Historical replays use their own frozen expected sessions, never wall-clock now.

Presentation: critical uses a steady deep-red treatment, explicit words/icon, and a direct link to evidence. It must never rotate out behind a routine news channel, including reduced-motion mode. Use restrained optional onset emphasis, never a repeated strobe. Acknowledge may compact the notice, not erase the active critical indicator; escalation and a genuinely new episode resurface it. Early amber warnings may be snoozed under bounded, state-aware policy. Fresh lower risk may be shown as improving, not 'safe to re-enter'. Failed/missing refresh preserves a labelled last-known severe warning and shows verification failure. Long-open pages need refresh/visibility-resume through the existing delivery path. Keep EN/ZH, dark/light, keyboard, 390px and 1440px support.

W1 completion requires real publisher output through the existing client, all country adapters explicitly accounted for, and real production proof. A standalone projection or synthetic browser is only a component milestone.

## Research R1: mechanism-based crash atlas

Classify episodes as multi-label mechanisms, not mutually exclusive stories: credit/banking solvency; inflation/rates repricing; valuation/duration/earnings unwind; leveraged positioning or carry liquidation; market-liquidity/funding break; external policy/geopolitical shock; and slow distribution/leadership exhaustion. Label trigger date, first observable precursor, peak, drawdown breach, trough, recovery, failed rallies and source availability separately. Do not label the exact future trough as an input or assume every high-VIX day is a bottom.

Use algorithmic outcome labels for evaluation, expert causal narratives for interpretation, and mark disagreements. A predictive association is not causal proof. A surprise shock may have no observable precursor; resilience detection and rapid damage recognition remain useful outcomes.

### Wide-net candidate registry

| Family | Candidate observations | Initial role / evidence caution |
|---|---|---|
| Breadth/distribution | above 20/50/200-day; advance-decline; new lows/highs; equal-weight divergence; down-volume; failed breakouts | Early/confirming; require point-in-time constituents, delistings and universe coverage |
| Last leaders | fixed-before-event leadership cohort; fraction losing trend; support breaks; formerly strong relative strength rolling over | Existing leadership-crack owner; BROKEN is observed cohort damage, not independently validated crash timing |
| Credit | HY/IG spreads and changes; BBB/CCC dispersion; distressed share; default/recovery and financing availability | Distinguish spread velocity, spread level and lagged reported defaults |
| Banks/real estate | bank relative strength, funding/credit spreads, deposit and lending stress, property credit | Price weakness is not proof of insolvency; reported data have release lags |
| Rates | MOVE level/change/term structure where licensed; nominal/real yields; curve and term premium; rate/equity correlation | Reuse parallel MOVE commission; rates up in growth is not automatically adverse |
| Equity volatility | VIX9D/VIX/VIX3M; futures slope; VVIX; implied/realized spread; skew; implied correlation and dispersion | VIX is non-directional. Coiling is a preregistered hypothesis, not accepted truth; retain existing null results |
| Options/positioning | signed delta/vega flow, put demand, dealer gamma estimates, expiry concentration, systematic deleveraging | Respect trade-sign and dealer-position uncertainty, same-vendor lineage and history limits |
| Market liquidity | bid-ask, depth, price impact, dislocations, auction/ETF discounts, volume capacity | Direct trading liquidity is not interchangeable with a central-bank balance-sheet subtraction |
| Funding liquidity | repo dispersion, SOFR-policy spreads, CP and swap-basis stress, haircuts, collateral/intermediation capacity | Market-local conventions; announcements distinct from effective intervention |
| Leverage/crowding | margin debt scaled by market size, credit gaps, debt service, CFTC positioning, fund concentration | Slow vulnerability, not a daily sell clock; public data leave important blind spots |
| Global transmission | breadth of local indices; synchronized declines; FX/carry and dollar funding; foreign credit/rates | Preserve local calendar/FX/ETF-vs-cash distinctions; correlated markets do not create independent votes |
| Macro/earnings/shocks | earnings revision breadth, lending standards, activity surprises, inflation/oil and event intelligence | Use first-released vintages and source timestamps; narrative/news cannot mint calibrated odds |

Every registered field needs owner, provider/rights, unit, market, event/release/observation time, effective membership, expected cadence, missing/stale behavior, history depth, role, transform, rejection/validation status and incremental value. 'Candidate' does not mean currently collected. Preserve rejected families and failed experiments; do not delete inconvenient results.

## Research R2: preregistered forecast and policy evaluation

This document freezes the questions and safeguards, not numerical trading parameters. No new model or capital policy is promoted here. Existing historical results and the current user-reported episode have already been seen; reused history must be labelled retrospective, not pristine holdout.

Before each new numerical experiment, commit its data manifest, source/revision hashes, market universe, feature list, transformations, target, split dates, candidate count, tuning budget and acceptance thresholds. Reuse canonical replay transitions and existing audit harnesses; no second forward ledger. Genuine prospective results begin only with immutable same-model issued forecasts after the freeze.

Forecast targets should separately cover start-to-future adverse return and peak-to-trough drawdown; primary compatibility target remains the existing >=5%/21-session definition, with explicitly secondary 10%/42-session and 20%/126-session severe outcomes. Add short-horizon shock detection without calling it long-lead prediction. Do not pool horizons or overlapping daily windows as independent trials.

Use expanding/rolling walk-forward evaluation; embargo overlapping labels; train-only normalization/threshold fitting; episode/block uncertainty; leave-one-crisis and leave-one-country-out diagnostics; era sensitivity and null/permutation controls. Separate development, calibration, retrospective stress testing and forward evidence. Record every tried configuration and use multiple-testing/selection adjustment. A hundred correlated indicators are not a hundred confirmations. Compare each family and interaction to price/trend/volatility baselines, not only to random chance.

Measure precision-recall, calibration/Brier/log loss, lead-time distribution, coverage, false alerts per year, time under warning, missed events and severity-weighted misses. Publish independent episode counts and uncertainty. A higher recall with intolerable permanent alarm is not a successful warning system.

Capital policy is a distinct experiment: compare current behavior, buy-and-hold, fixed lower exposure, exposure-matched baseline, simple trend, volatility-targeting, bounded staged reductions and temporary cash, followed by explicitly specified re-entry rules. Account for local cash returns, total returns, execution lag, costs, turnover, liquidity constraints, missed upside, gap risk, worst drawdown and expected shortfall. Treat tax-aware implementation as user-specific rather than silently frictionless. Evaluate all-cash as a candidate, not as a preselected winning answer. A high-intensity score alone cannot issue exact weights. Promotion must survive independent episodes and stress the exit AND re-entry jointly.

## Research R3: bottom and recovery process

Reuse `engine/risk_radar_recovery.py`, its audit and #7029. Candidate phases: stress active; capitulation candidate; stabilization; early repair; confirmed recovery; failed repair. These are research/product concepts until a canonical producer is qualified. Both fast shock recoveries and prolonged credit bears belong in the atlas.

Candidate evidence: shrinking downside response to bad news; fewer new lows; improving participation on retests; credit/funding stabilization; liquidity actually improving; volatility normalization after stress rather than low VIX alone; broad thrust and leader repair. Evaluate how much a user gains by waiting for confirmation versus how much additional drawdown is avoided. Exhaustion is not sufficient while funding/credit continue worsening. Policy announcements are not assumed effective. A market-local clear volatility/liquidity veto cannot be supplied by a different country's evidence.

Report probability/uncertainty of renewed lows and durable recovery only where calibrated. Show early repair visibly even while protection remains active. Re-entry can be staged and may be slower than protective escalation; falsifiers and failed-rally handling must be explicit. Never promise to identify the exact trough in advance.

## Implementation and acceptance sequence

W1a: pure warning projection, strict input/clock/coverage semantics, same-state severity mapping, safety tests. W1b: integrate existing publisher/client with backward compatibility, priority, persistent critical indicator and stale-refresh handling. W1c: connect every existing country artifact with local clocks and preserve entitlement boundaries; real authenticated page matrix and source-origin parity.

R1: registry and mechanism atlas with source-quality inventory. R2: canonical replay reconciliation, frozen ablations and forecast evaluation. R3: joint protection/re-entry policy evaluation and recovery validation. R4: same-model prospective shadow evidence, independent review, bounded promotion, observability and rollback. These are dependencies and deliverables, not a claim that workers have been dispatched.

Tests before implementation: caution/80 remains an early warning, not silence or critical; gated risk-off becomes critical without 99% odds; lower gated state plus extreme raw score is not promoted; no fresh timestamp laundering; stale/future/malformed/missing states are unavailable; source-market mismatch refused; zero is valid and bool/NaN/infinity are not; global summary never averages scores; absent market cannot disappear into safe coverage; inputs immutable; a fresh calm reading is not a bottom call; previous severe warning survives unverifiable refresh as last-known; critical wins over routine news in reduced-motion mode. Preserve old legacy alert semantics in its registered suite.

Release gates: exact source tests and owning CI selection; current-main collision/review checks; producer-to-consumer fixture; true country coverage; browser dark/light x EN/ZH x desktop/mobile and keyboard/reduced-motion/offline cases; actual artifact/hash and canonical-origin parity; no probability/authority regression; a simulated severe event visibly reaches an authorized user through the real pipeline. Do not display a synthetic event as current market data.

## Primary research basis

These sources motivate hypotheses and controls, not a claim that a new model has been backtested:

- Federal Reserve, May 2026 Financial Stability Report, Purpose/Framework and Overview (data as of April 23): https://www.federalreserve.gov/publications/2026-may-financial-stability-report-purpose-and-framework.htm and https://www.federalreserve.gov/publications/2026-may-financial-stability-report-overview.htm — vulnerability/trigger distinction; valuations, borrowing, leverage and funding.
- BIS, Drehmann and Juselius, Evaluating early warning indicators of banking crises, Working Paper 421 (2013): https://www.bis.org/publ/work421.htm — policy horizon, lead/noise trade-off; banking indicators are not equity crash clocks.
- Jorda, Schularick and Taylor, Leveraged Bubbles (2015): https://www.nber.org/papers/w21486 — credit-financed bubbles differ from unleveraged repricing.
- NY Fed, Treasury Market Liquidity during the COVID-19 Crisis (2020): https://libertystreeteconomics.newyorkfed.org/2020/04/treasury-market-liquidity-during-the-covid-19-crisis/ — spreads, depth, price impact and liquidity/volatility feedback.
- NY Fed, Recent Developments in Treasury Market Liquidity and Funding Conditions (2025): https://www.newyorkfed.org/newsevents/speeches/2025/per250509 — compare illiquidity with volatility, not merely raw levels.
- Cboe, VIX FAQ and VIX/VIX1D measurement explanation: https://www.cboe.com/tradable_products/vix/faqs and https://www.cboe.com/insights/posts/what-the-vix-and-vix-1-d-indices-attempt-to-measure-and-how-they-differ — non-directional horizon-specific option-implied volatility.
- Cboe, SPX Skew Signals Longer-Term Caution Despite Rally (2025): https://www.cboe.com/insights/posts/spx-skew-signals-longer-term-caution-despite-rally — index volatility, correlation, dispersion and tenor-specific demand can diverge; this is not validation of a universal coiling rule.
- Bailey et al., Probability of Backtest Overfitting (2017): https://scholarworks.wmich.edu/math_pubs/42/ — strategy-selection bias and the need to account for trials, beyond attractive historical fits.

## Execution receipt at commission

Read-only source audit completed; implementation branch created. Remote shell inspection attempts were platform-blocked; they were not replayed via another host/account. The Executive app reported readonly mode. No worker dispatch, automatic watcher, source merge, deployment, new backtest result or live capital instruction is represented by this document. Subsequent evidence must append exact achieved milestones rather than rewriting this initial state as if it were already delivered.
