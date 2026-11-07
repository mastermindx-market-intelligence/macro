# Regime-aware Prophet: integrated research and implementation plan

Version 1 / 2026-10-02 America/Los_Angeles. Research candidate, not accepted production policy.

## 1. Outcome, scope, and the architectural decision

The product should identify an attractive opportunity, explain why its group and security deserve attention, distinguish an available entry from a late or unavailable one, describe conditions that would invalidate the thesis, and learn from attainable outcomes. It must be able to abstain. "All weather" means appropriate behavior and honest uncertainty across environments, not profitable trades in every state or complete knowledge of markets.

We will not build a giant indicator-count score, a ticker-to-best-timeframe lookup, or a replacement macro engine. We will connect the existing Regime/Rates, GMI Theme Graph, Stock Identity, Technical Opportunity Intelligence (TOI), Temporal Grain, Live Entry Radar, Prophet V4, Conditional Fusion and Evaluation owners. More features must demonstrate incremental information rather than merely add bullish votes.

The research unit is an interaction between **market environment, group state, security state, setup mechanism, information/indicator clock and feasible management horizon**. Regime is neither a single risk-on label nor an omnipotent veto. Market-wide fragility can coexist with persistent trends inside a narrow leader cluster. A falling-rate panic rebound can also damage a momentum construction. These alternatives must compete with the motivating fast-rotation hypothesis.

Completion is incremental but end-to-end: each admitted capability has reproducible source/data identity, usable product behavior, explicit evidence limits, independent review, existing promotion acceptance, and production/browser proof. An architecture document, passing tests, PR or backtest does not complete the parent mission.

## 2. What the takeover census actually established

Source pins: macro `85932a1b7ce0e597ad73e713f7528101e4ef58d9`; Terminal `c35b9a1d50ca4960c361645f0300fa9f95158a4e`; protected procedure Mastermind `bf1fa1db3147105e9ac3d4f7f4d20ef8efd59cba`.

The exact-source snapshot audit and its full hashed receipt are described in `EVIDENCE.md`. The intake is not a new comprehensive indicator backtest.

1. The production-cascade source already uses an absolute session anchor. Its separate cross-repo oracle intentionally uses a frozen input-window convention. Sixty leading-slice comparisons changed zero absolute grids but 42 oracle grids. Therefore the earlier report's blanket instruction to repair the live 3D clock is not current-source justified. Endpoint completeness, warm-up, upstream feed identity and Terminal parity remain separate questions.
2. The raw plan ledger has 270 rows. Canonical correction/quarantine projection leaves 259; 39 are NO_ENTRY. There are 220 entered closed plans, of which 15 are explicitly reconstructed. The 205 not marked reconstructed have 91 positive outcomes, mean +0.515779% and median -2.0121%. This is neither a portfolio return nor a verified delivered-pick record. Recent cohorts are right-censored; strategy eras, benchmark, costs and publication are not resolved by these aggregates.
3. September's candidate artifact has 70,476 rows over 20 dates and 4,622 tickers. All carry the same v3/selection-era labels, but regime basis includes 64,430 pit_live and 6,046 recomputed_history rows. Labels require source-window verification; these are not 70,476 independent market experiments.
4. The signal archive has 60,538 rows. Four rich market axes are stamped on 583 rows; rate pressure on 555. They span only three months and fail the incumbent estimability requirements. Its deep `regime_at_entry` field is per-security price trend, not historical macro state. PR #8301 already addresses that reporting distinction.
5. The inspected `regime_v2_pit` history ends July 2, 2026. It contains 1,618 pit_vintage, 6,072 mixed and 6,789 revised_latest rows. A filename containing PIT does not make every row or full lookback information-time clean.
6. Technical Lab currently publishes 195 signal definitions over 248 explicitly survivor-heavy stocks. Terminal has 27 actual built-ins plus a Lab placeholder and 31 premium modules across five suites. These counts overlap economically; they are not independent predictors. Macro's catalog already records dependency families, roles, lags and blocked/challenger status.

The older regime-reliability null and Phase-21 forensic findings both remain relevant. Neither licenses the statement that all regime conditioning is useless or that a fast-2D regime router is validated. Phase-21's 209 episodes are already outcome-inspected; do not mine another threshold from them.

## 3. Preserve ownership and integrate current work

| Capability | Existing owner / artifact | Required integration, not replacement |
|---|---|---|
| Historical macro information | Rates/Inflation Command and existing source-vintage/replay work (#7088, #7015, #7165) | Qualify complete release-time windows and source coverage; extend missing growth families through that collector. |
| Regime research readiness | `engine/regime_conditioning_coverage.py`, current #8301 | Consume unchanged coverage/contrast rules; distinguish stock trend from market context. |
| Theme/subtheme state | GMI Theme Graph, current #8299 and original product carriers #7749/#7976/#7455 | Point-in-time membership, group identity, effective dates and paired evaluation; no new theme tree or ranker. |
| Technical research | TOI W1/W2-0; Temporal Grain G/A/K/D | Census roles and qualify actual clocks/data before outcome tournaments. Exact-chart parity cannot substitute for broad-panel admission. |
| Canonical technical identity | `engine/tech_catalog.py`, Setup Species and Terminal registries | Map formula/version/role dependencies. Do not clone indicators into a second scientific registry. |
| Tactical entry | Live Entry Radar and existing C2/C4/W5 | Retain event identity and same-cut context; preserve Phase-22 and secure-spool gates. |
| Security structural context | Stock Identity | Read accepted interfaces; do not add hindsight-derived per-name timing personalities. |
| Candidate and thesis workflow | Prophet V4, Entry Timing, B3/B4 and existing plan lifecycle | Keep discovery, entry permission, delivery and plan outcomes distinct. |
| Learned ranking | Conditional Fusion | Keep C1 baseline and v2 shadow; later conditional models use the original arena and promotion law. |
| Experiment and outcome truth | TrialLedger / Evaluation OS | Register looks, frozen populations, hypotheses, labels, costs, purging and promotions in existing owners. |

Current active sibling carriers must be reconciled at their own source heads before integration. The new folder owns only this integrated research candidate and offline intake diagnostic. No incumbent writer, runtime, held operation or denied action is displaced. No live ranking/gating/sizing authority is granted.

## 4. Historical reconstruction: two different products

### A. Ex-post mechanism atlas

Reconstruct what happened: growth/inflation shocks, real-rate and term-premium pressure where observable, credit/funding stress, liquidity, volatility, breadth, concentration, sector participation and leadership changes. Date every economic observation and publication. Historical narratives and revised data can help explain mechanisms but are labeled retrospective and cannot silently become tradable features.

### B. Decision-time replay panel

Reconstruct what could have been known before each specific decision. Keep observation period, source publication, capture/first-known time, vintage, corrections, lookback availability, timezone, market session, identity and intended-use rights. A valid latest value is insufficient when the rolling window contains unqualified revisions. A date-only series does not establish an intraday release timestamp. Do not backdate modern taxonomy, today's constituents, current earnings revisions or revised macro history.

Historical archival availability and actual organizational capture are different questions. Where an archival public vintage supports a historical research simulation, label it as reconstructed public availability, not a recommendation the organization delivered then. Actual prospective evaluation uses durable first-known records. Gaps remain explicit and can define shorter valid experiments; they are not filled by narration or current values.

Long history should be used in tiers: deep daily prices and coarse observed price states; narrower qualified macro vintages; still narrower point-in-time themes, earnings/estimates and intraday microstructure. Test scope follows the intersection of real coverage, not the oldest date in any one file. U.S. calibration does not automatically transfer to Hong Kong, China or other exchange/session systems.

### Regime dimensions to measure

Keep continuous features alongside interpretable states. Candidate dimensions are growth and inflation level/change/surprise, real and nominal rates level/change/shock, credit and funding conditions, currency/liquidity context, equity trend, realized/implied volatility, correlation/dispersion, broad and local participation, concentration, and uncertainty/transition intensity. These are research feature groups, not new heuristic weights.

Breadth needs several measures. Cap-weight versus equal-weight divergence is useful context but also contains size/sector exposures; it is not a pure measure of liquidity or breadth. Compare actual eligible-universe participation, sector-neutral breadth, high/low participation and group breadth. Missing prices and delistings must not improve breadth by shrinking its denominator.

A macro change, a breadth change and a rotation change are not automatically a causal chain. Use lagged observable states, event-time surprises where qualified, controlled comparisons, and competing explanations. Prediction can be evaluated without claiming identified causation.

## 5. Measure rotation persistence directly

The central hypothesis needs a measurable object, not an attractive label such as "chop".

Reuse GMI historical group snapshots to compute trailing leadership rank stability, top-group overlap, leadership residence time, breadth of participation within each group, cross-sectional dispersion and the speed of rank changes. Effective member weights must remain frozen at the decision cut. Do not renormalize outcomes over only the members that still have data.

Distinguish three conditions: persistent narrow leadership, rapid leadership rotation, and broad participation. Narrow breadth alone does not identify which of the first two is present. A semiconductor leader can sustain a long trend while the rest of the market fails; conversely an index rally can conceal rapid churn even among leaders.

Estimate the survival of a fresh impulse conditional on observable market/group/security state. Define termination using a registered price/relative-strength/invalidation event rather than whichever oscillator gives the nicest result. Preserve censoring and separate the candidate's age, the group's leadership age, and a newly refreshed impulse inside an old structural trend.

## 6. Technical family research instead of unconstrained combinations

Use the existing catalog as sensors grouped by mechanism and role. Initial family studies should include:

| Family / mechanism | What it measures | Key competing environments and failure mode |
|---|---|---|
| Trend / adaptive trend | Direction, smoothness, trend persistence | Persistent markets versus reversals and range churn; lag and repeated confirmation. |
| Momentum / acceleration | Rate of change and reacceleration | Fresh impulse versus an already-consumed move; MACD is one construction, not the family definition. |
| Mean reversion / oscillator | Stretch and reset relative to a local baseline | Range recovery versus strong trends or continuing breakdown; no universal overbought veto. |
| Compression / expansion | Volatility contraction followed by release | Sustained expansion versus failed breakout; distinguish observed compression from trigger. |
| Structure / reclaim | Breaks, pullbacks, reclaims and swing sequence | Genuine reversal versus relief bounce; pivots are unavailable until their confirmation time. |
| Volume / participation | Activity, relative volume and directional participation proxies | Broad sponsorship versus thin prints; daily volume cannot recreate order flow. |
| Relative strength / group leadership | Cross-sectional persistence | Stock effect versus sector/theme effect; frozen membership and benchmark controls. |
| Anchored price / auction location | Price relative to a valid VWAP/volume/structure anchor | Arbitrary hindsight-selected anchors versus predefined event anchors. |
| Risk / path geometry | Extension, volatility, adverse excursion and stop/target geometry | Useful asymmetry versus trades with little remaining room; daily bars may not identify stop/target ordering. |

The combination grammar is structural context + setup + trigger, optionally participation and risk, with dependency-family controls. RSI, StochRSI and an RSI-derived composite are not three independent confirmations. Monthly/weekly can be context; daily/multiday can define setup; intraday can localize entry. This division is a hypothesis to test, not a permanent assignment of each clock.

For each admitted definition record formula and seed, data requirements, role, direction, warm-up, actual decision availability, repaint/confirmation lag, dependency lineage and Terminal equivalent. Visual modules without executable causal definitions do not enter an outcome tournament. Proprietary methods are not copied; use owned or lawful original implementations.

## 7. Separate grain, anchor, filter memory and data

A 26-period EMA on 3D bars has a different memory from a 26-period EMA on daily bars. A daily-versus-3D test using identical period counts changes two variables at once. Run distinct experiments:

- Grain change at matched declared physical/session decay, holding feed/session/adjustment/species fixed.
- Kernel-memory change on a fixed bar grid.
- Session/anchor change with compatible remaining identities.
- An explicitly labeled policy-bundle comparison when several dimensions change together.

For an EMA, matching the decay of old information over n equal intervals uses `alpha_n = 1 - (1 - alpha_1)^n`. This matches decay, not the complete output: aggregation removes intervening path information, signals sample at different times, and a multi-stage MACD has more than one kernel. Compare native-parameter strategies separately from matched-memory diagnostics.

Use exchange sessions for 1D/2D/3D and registered weekly anchors, explicit regular/extended/overnight sources for sub-daily bars, and exact session calendars for holidays, half-days and DST. Twelve hours of clock time is not half an equity regular session. Final-bar completion, provisional snapshots, source corrections, missing sessions, adjustment conventions and warm-up are first-class inputs.

The current 0/60 slice result qualifies only its stated mechanical contrast. It does not certify every indicator or data feed. The frozen oracle must not be re-anchored without its contract/golden-vector migration.

## 8. Registered experimental ladder

The following are proposed experiments for the existing TrialLedger owner, not newly registered trials or permission to inspect held outcomes.

**E0 - Measurement and coverage.** Reproduce owner outputs, resolve plan eras/delivery versus reconstruction, audit complete windows and source-clock parity. This turn implements the first offline diagnostic. Exit: source-qualified populations and explicit excluded/unknown cases, not just green unit tests.

**E1 - Mechanism atlas and coarse conditional baselines.** On each qualified historical tier, compare simple static benchmarks and existing setup species across prespecified continuous/state dimensions. Include regime transition risk, not only entry state. Separate descriptive associations from decision-time prediction. Do not optimize a complex router before establishing a stable simple interaction.

**E2 - Rotation and impulse survival.** Test whether low participation predicts shorter impulse survival after controlling for group strength, volatility and market trend, and whether persistent narrow leaders are an exception. Test the alternative that group selection, not bar speed, explains most of the effect.

**E3 - Indicator-family tournament.** Compare a small representative set per admitted mechanism using existing defaults before limited parameter robustness. Test additional families for incremental contribution beyond cheap price trend, volatility and relative-strength baselines. Eliminate duplicates before looking at outcome winners.

**E4 - Clock decomposition.** Perform G/A/K/D factorial contrasts and compare native timeframes at common economic horizons. Test 1D, 2D, 3D, weekly and qualified intraday/12H separately. Do not manufacture 12H from daily data. Compare all methods at the same feasible decision/entry opportunities, including their absent signals and opportunity cost.

**E5 - Hypothesized confluence mechanisms.** Contrast a new slow confirmation with fresh faster reacceleration inside an established constructive trend; add lag/price-progress/group-persistence diagnostics. The existing Phase-22 future C2 x C4 test remains unchanged and supplies its own evidence. No threshold is fitted on the 209 old episodes.

**E6 - Orthogonal ablations.** Hold security population fixed when testing timing; hold entries fixed when testing exits; hold clock fixed when testing group filtering. Then compare the combined policy. Required arms: incumbent; plus qualified group information; plus remaining-opportunity features; plus regime interactions; plus management routing. Report both additions and leave-one-family-out removals.

**E7 - Conditional model and policy.** Begin with regularized, interpretable interactions or hierarchical pooling. Compare against a static model with the same feature budget. More complex state models must improve independent predictive utility, calibration and stability, not merely produce persuasive state names. Route through Conditional Fusion's existing arena; fit only on lawful folds. No new arbitrary product of five heuristic scores.

**E8 - Prospective shadow and product acceptance.** Stamp both decisions on the same candidate population with exact policy versions, preserve all false starts and exclusions, measure delivered and executable opportunities, and graduate only through existing promotion/rollback law. Browser proof must cover positive, wait, rejection, missing-data and changing-regime cases.

## 9. Evaluation contract and the anti-overfitting boundary

Freeze the eligible security universe, point-in-time membership, decision cut, next executable price rule, signal version, benchmark, transaction-cost model, target definition and common horizons before outcomes are exposed. Proposed comparison horizons are 5/10/21/63 completed exchange sessions where each setup's mandate supports them; pick the primary horizon in the actual registration. "+5 bars" is not an equal-horizon comparison between 1D and 3D.

Account for spreads, slippage, gaps, turnover, capacity, missing and delisted securities, splits/dividends and shorting constraints where relevant. Same-bar stop/target ambiguity is unresolved or conservatively bounded, not resolved in the strategy's favor. Separate stock return, benchmark excess, sector excess and an actually implementable constrained portfolio.

Use nested chronological walk-forward selection, purged overlapping label windows and an embargo appropriate to the actual target. Fit scalers, regime cutoffs, groups/clusters and thresholds inside training only. Hold out securities/groups and contrasting market episodes where coverage permits. A calendar split does not create independence when labels overlap across the boundary.

Inference must reflect shared dates, securities/groups and overlapping horizons. Report number of decision dates, episodes and independent-ish blocks alongside raw rows. Block length and sensitivity are registered; twelve calendar months is a coverage floor, not a proof of twelve independent observations. Pool sparse cells hierarchically or abstain. Do not manufacture thousands of independent regimes by crossing indicator parameters with the same twenty market dates.

The existing TrialLedger records every family, variant, interim look and abandoned construction. Use family-level multiplicity control and the existing selection-bias diagnostics; statistical correction cannot repair look-ahead leakage. Never optimize a per-ticker clock from historical winners. Preserve negative and inconclusive results and the exact construction they falsify.

Primary evaluation should pair net benchmark-relative utility with downside constraints. Report expectancy, median and tail returns, achievable MFE/MAE, time to peak, false starts, signal survival, drawdown, turnover, concentration, coverage/abstention, and retention of major winners. Reducing losers by suppressing almost every opportunity is not automatically an improvement. Compare at matched coverage or report the full precision/coverage and risk/opportunity trade-off.

Do not claim causality from the post-entry regime association. A decision rule may react only to information known by that decision; future rate or breadth changes belong to the outcome/mechanism analysis. "Remaining opportunity" is a conditional distribution with uncertainty, not hindsight remaining return or a promise that a projected target will be reached.

## 10. Product integration and management

A candidate should expose separate observations for structural state, group sponsorship, setup maturity, trigger freshness, price progress, attainable entry geometry, evidence quality and current regime compatibility. Keep missing distinct from negative. Display why the candidate remains discoverable even when entry is unavailable.

The visible decision journey should answer: why this group; why this security instead of a peer; what actually happened and when; why this clock is relevant; what must occur before entry; what would invalidate the opportunity; and what comparable qualified evidence supports the expected horizon. The explanation is generated from versioned facts and accepted policy outputs, not an LLM-originated rank or numeric confidence.

Management uses both entry context and updated hold context, but no universal five-day liquidation or slower-indicator exit is assumed. Test management independently with the same entries, accounting for reaction cost and false alarms. A broadening regime can support patience; a transition can require a different assessment, but neither is an automatic trade until the policy earns authority. Portfolio concentration limits remain with the existing portfolio/risk owner; multiple correlated AI subthemes are not independent diversification.

Deployment must preserve canonical episode, event, plan and outcome IDs. Use shared feature computation/cache and versioned snapshots, not repeated per-widget calculations or a second data/notification plane. Terminal reuses its metadata/compute separation and displays qualified regime/clock context without downloading the entire research feature matrix to mobile clients.

## 11. Ordered implementation slices and acceptance

| Slice | Concrete deliverable | Dependency / exit evidence |
|---|---|---|
| R0, current | Pinned census, corrected-ledger diagnostic, G/A/K/D manifest checks, information-cut audit, full hashed snapshot | Unit and real-source mechanical proofs; no predictive or production claim. |
| R1 | Existing-owner source/indicator/Terminal parity matrix, endpoint and warm-up tests, release-time full-window coverage report | TOI W1/W2-0 and Temporal Grain scopes reconciled; exact artifacts accepted. |
| R2 | Qualified historical regime and membership replay inputs | Existing vintage collectors and GMI evaluator; rights, missingness and lookbacks accepted. |
| R3 | Registered baseline/family/rotation experiments and dependence-aware labels | Evaluation owner registration and immutable input/partition pins before reads. |
| R4 | Clean E1-E6 result package with negative findings and ablations | Sample adequacy, purging, costs and independent replication; no per-name audition. |
| R5 | Conditional Fusion challenger plus explicit abstention/explanation contract | Beats appropriately matched baseline out of sample under original promotion law. |
| R6 | Same-cut prospective shadow and consumer vertical | Durable source/decision/outcome stamps; no re-keying or retrospective delivery claims. |
| R7 | Bounded rollout, production/browser proof and rollback | Separate product, predictive, publication and live acceptance; continue monitoring through existing owners. |

R1 data/clock work and R2 macro/group qualification can advance independently when their existing gates allow it. E1 cannot borrow unqualified future information to bypass R2. Phase-22 transport and W3 guarded validation remain on their original carriers. Current #8299/#8301 work is consumed, not rewritten here. New research does not clear an existing denied operation or human credential ceremony.

## 12. Current completion boundary and next decision

This turn has built and run an offline source-bound diagnostic and corrected material premises of the intake. It has not completed a new multi-year indicator tournament, established a profitable regime router, merged a live strategy, proved the Terminal journey, or completed the parent mission.

Next: independent review of this intake/plan and integration into the existing evaluation/TOI owners, then the exact R1 full-window and right-edge/Terminal qualification work. The highest-value scientific next step is a clean matched-population test, not adding fifty indicator combinations to the current survivor sample. Preserve the current sibling holds and denied scopes; no worker or autonomous wake is implied by this document.

## External research context (not Prophet validation)

- Daniel and Moskowitz, *Momentum Crashes*, NBER Working Paper 20439 / Journal of Financial Economics 2016. The study's panic/rebound behavior motivates transition-aware alternatives; it does not validate Prophet's 1D/3D entries. https://www.nber.org/papers/w20439
- Moskowitz and Grinblatt, *Do Industries Explain Momentum?*, Journal of Finance 1999. Industry momentum at intermediate horizons motivates group controls, not a claim that any current AI subtheme or three-day signal is superior. https://www.aqr.com/Insights/Research/Journal-Article/Do-Industries-Explain-Momentum
- Federal Reserve Bank of St. Louis, *ALFRED at 15* (2021). Archived vintages and historical revision examples motivate availability-aware reconstruction; earliest series observations do not guarantee equally deep vintage history. https://fredblog.stlouisfed.org/2021/04/alfred-at-15-archiving-fred-data-since-2006/

Internal source anchors: `engine/canon.py`, `engine/confluence_tiers.py`, `engine/session_anchor.py`, `engine/prophet_integrity.py`, `engine/regime_conditioning_coverage.py`, `engine/tech_catalog.py`; the pinned WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE, WS:TEMPORAL-GRAIN-INTELLIGENCE, WS:PROPHET-CONDITIONAL-FUSION records; Phase-22 discovery/preregistration; and the September 18 rotation-participation mandate. Current source state and exact PR heads override stale progress prose.
