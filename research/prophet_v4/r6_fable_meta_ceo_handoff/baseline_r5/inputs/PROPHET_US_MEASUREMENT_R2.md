# Prophet US — R2 decision-time measurement and policy-comparison design

**Date:** 2026-09-23. **Status:** PROPOSED FOR MASTER PLAN / NOT A REGISTERED TRIAL.  
**Operation:** `prophet-us-measurement-r2-20260923-sol-001`.  
**Parent:** existing Prophet US program, including V4 Recovery, Conditional Fusion, Entry Truth and Evaluation owners.  
**Procedure:** protected `Mastermind@c18ea2ca779f042702a63a78bf1f10f5a1e0c0f6`; Skillpack 1.0.1 / bootstrap 1.  
**Source-analysis pin:** `macro@d34993def9fa00e88c930f39a498b6ecad97455b`.  
**Prior cumulative research:** Macro #6805 comment 5787643381; R1 dossier SHA-256 `96d0ab34f5db94537fe60b493af166b0c50ca8eac2b89641703d9bb290166465`.

This document specifies how to tell whether a future Prophet genuinely improves discovery, ranking, entry, management and delivery. It does not register new experiments, replace accepted source laws, modify strategies, launch a worker, or claim a new model works. The accompanying Python file uses invented observations only. No protected W3, Door or B4 outcomes were read in this round. No production module was executed or changed.

The final flagship mission remains incomplete. The measurable advance in this round is a source-grounded experimental design, a readiness/owner map, and executable synthetic demonstrations of denominator, clock, risk, probability and inference errors that the implementation must prevent.

## 1. The user outcome and the four questions

The product must make it possible to discover a meaningful opportunity, understand the evidence and risk, identify the relevant strategy and horizon, observe a valid entry or explicit wait, retain the thesis coherently, and judge the outcome honestly. A narrower list with a prettier win rate is not necessarily a better product.

We will keep four experimental questions distinct. **Discovery:** which valid opportunities can the system identify early, including names that never enter the final board? **Ranking:** given the exact same decision-time field, which candidates deserve attention first? **Entry:** on the same original episodes, which executable timing policy produces better opportunity-level value? **Management:** given entries that were already selected, which hold/exit policy better retains upside and limits damage? Delivery is a separate constraint across all four: knowledge not delivered to the user is not a historically delivered recommendation.

These distinctions prevent familiar attribution errors. A repaired data feed must not be credited to a new ranker. A better exit must not be called evidence of better discovery. More conservative position sizing must not be described as better stock selection. A list selected after outcomes are known is not a discovery universe.

The current R1 proposal prioritizes three research sleeves: Early Leadership/Sector Rotation under its existing 2–15-session identity; Quality Earnings/Expectation Revision; and Cycle Capture. R1's 20–90-session earnings and 6–24-month cycle envelopes are research proposals, not frozen outcome horizons. This document focuses the first detailed policy comparison on the existing tactical sleeve while making the measurement structure reusable. It does not transplant tactical thresholds into long-cycle investing.

## 2. What we verified in the current source

The following are code/contract observations, not claims of complete current data or deployed behavior.

| Source inspected at the analysis pin | Relevant verified meaning | What this does not establish |
|---|---|---|
| `engine/grading.py`, lines 1–265, blob `1208a7aa597159969a0ed7ccd359972bc413941a` | The next-bar helper fills on the next available row's close; horizons are positional; adverse/favorable extrema are measured from entry using closes | That every name's row sequence has every expected exchange session; that a close-based excursion is intraday risk |
| `engine/us_prophet_grades.py`, lines 1–215, blob `da7d1f625dc3d20431806502d9f36be82973ffa2` | Fixed-horizon, policy-free H10/21/42/63 marks; existing grade identity; frozen outputs; native loader/writer ownership | A sleeve-aware execution simulator or the ability to infer historical delivery from a grade |
| `engine/us_candidate_episode.py`, lines 1–205, blob `a34f2c2bf80411ffaa9800774abb4cc7238c90d1` | Canonical B1 episodes, source events, suppressions, Data OS identity, immutable generations and correction vocabulary | That the latest nightly reconciled successfully, or that every historical source event already has an episode |
| D5 A7–A9 amendments, lines 1–265, blob `141782387738bfd955c0622d7de91c16bdf5c26b` | Source/observed/correction-time constraints; source-revision access; B1-owned cut and generation binding | Universal complete body-revision history or a researcher-minted action clock |
| Conditional Fusion masterplan §9, blob `9f02020815cd51b6e4d9baa9d79ab3a1cf415cda` | Train-only transforms, date grouping, horizon-based purge/embargo, minimum usable folds, identity controls, multiplicity and promotion restrictions | Permission to relax those rules to obtain more samples |

Two metric distinctions deserve emphasis. The current `fwd_mdd` expression is `min(0, minimum_future_close / entry_close - 1)`. It is an entry-relative adverse excursion, not running-peak maximum drawdown. The corresponding `fwd_mfe` uses future closes, not highs or executable exits. Both are legitimate descriptive metrics when named correctly. Neither should be silently reinterpreted.

The existing grade key is `(stamp_date, ticker, board_definition, horizon)`. B1's episode identity is a different grain. A new research join must preserve both and disclose unmatched/many-to-one relationships; it must not rename legacy board rows as canonical B1 episodes. The wrapper also reindexes SPY onto a name's calendar and forward-fills. That is a native convention to record, not proof that every comparison uses identical elapsed sessions.

## 3. Three evidence classes, three different claims

A point-in-time cutoff is necessary but does not, by itself, prove that the actual product possessed or delivered the information.

**Observed-as-run evidence** uses the real historical source version, actual observed/recorded times, exact computation and publication identities, and the original decision. It can support statements about what the system knew. A historical user-delivery statement additionally requires evidence from the relevant serving or notification path.

**Point-in-time replay evidence** recomputes a declared policy today from source versions that can be proven admissible at a historical cut. It supports a counterfactual mechanism/policy study under its market-tape and fill assumptions. Today's replay execution time is not the original computation time. Later software can be tested retrospectively, but that does not make it an out-of-sample historical deployment; model/policy selection and holdout chronology must be disclosed separately.

**Retrospective diagnostic evidence** may use latest corrected data or an outcome-selected case to understand a mechanism. It can expose a defect or formulate a hypothesis. It cannot silently join a confirmatory race or be presented as a recommendation delivered in the past.

All three can be valuable. The mistake is pooling them under one performance number. The analysis manifest must state which claim each row is allowed to support. An admissible historical replay is not made invalid merely because its CPU ran today; instead, it must faithfully separate historical input eligibility from present execution and model-selection provenance.

Target-trial methods provide a useful design analogy: align eligibility, policy assignment and the start of follow-up, rather than defining participation using future events. We borrow that temporal discipline, not a claim that a market-tape replay is a randomized experiment. [E1, E2]

## 4. Two cohort grains before any ranking or timing test

### 4.1 Discovery cohort: owner-native nominations and explicit suppressions

The earliest source event may not yet satisfy B1's identity/anchor requirements. Its absence from B1 is itself informative. The discovery audit therefore references existing source-native event IDs and suppression receipts, including unresolved identity, missing structural anchor, ineligible instruments and unavailable prices.

No ticker/date surrogate episode is minted. No observer creates a parallel candidate store. A source event that later maps to B1 remains an earlier source event with its true clocks, not a backdated B1 opening. A current observed B1 population cannot by itself measure all the opportunities the discovery system missed before B1.

Reference opportunity coverage must also be defined before looking for attractive stories. The broad denominator should be a PIT supported/investable universe under an explicit data-quality contract. Ex-post large-move labels can identify a reference set for recall analysis, but the detector and selection cannot use those labels. Recall must be reported alongside false positives, alert burden, liquidity and lead time; simply nominating everything is not success.

### 4.2 Policy cohort: genuine canonical episodes

The timing experiment begins only with a validated owner-issued episode at the declared origin. The origin is pinned to B1's generation and native clocks, not a later chart trough or a more convenient backdated anchor. Require the accepted strategy eligibility definition before applying the entry-policy arms.

A later correction may alter an opening field. Preserve the earlier as-run belief and a separately identified correction, rather than silently replacing the evaluation origin. An invalid source is not an economic losing trade, but removal from the main score must be visible, counted and examined for selective bias.

The primary timing cohort must not require eventual slower confirmation. That would exclude precisely the early false starts whose cost we are trying to measure. Similarly, do not require a future pullback, a successful fill, or a surviving listing at the end of the horizon to enter the cohort.

## 5. The decision-time observation: one join, existing identities

This is an analytical join specification, not a proposed new production database or wire schema.

Each analytical observation retains the canonical security/issuer identity and identity epoch; B1 episode ID and immutable generation; source event IDs and source bytes; strategy definition and policy version; relevant owner decision cut; feature versions and availability clocks; model version, training cutoff and transform versions; exact candidate population, ranking lane and rank as published; B4 state and its fact receipts; serving/notification evidence where present; and fill, exit and label-ruler versions.

The researcher should be able to explain why every field was usable. A ticker is a display/routing attribute, not the primary historical identity. A model margin is not automatically a probability. A null rank outside a scored lane is not the worst possible rank. A candidate that is not featured is not a nonexistent candidate.

D5 v1 already binds the decision cut to B1's `opened_at`, `opened_session` and `known_at`-bearing events, with the generation included. It explicitly prohibits synthesizing that cut from a board, calendar, plan or Radar row. The analytical sampling schedule may select owner-issued observations but does not redefine those clocks. Where an intended intraday landmark has no lawful source observation, the answer is unavailable. [I3, I4]

## 6. Timing and corrections: a conjunctive admissibility test

For an observed-as-run earnings observation, the D5 contract requires `source_available_at <= cut` and `observed_at <= cut`. A correction additionally needs its generation time no later than the cut. Missing required clocks cannot be replaced by a statutory filing lag, fiscal period, retrieval time, or current wall clock. [I4]

The following example is deliberately synthetic. A filing published at 10:00 but first observed at 10:07 was not in the running system's possession at 10:05. It may support a separate public-information replay with an explicit acquisition assumption, but not a 10:05 as-run knowledge claim. A correction generated at 10:10 must not replace the value seen at 10:05.

Use the permitted source-revision reader, not the current event body. Source revisions do not guarantee all body revisions are observable: D5 already specifies the case where correction lineage is not observable. That state is neither proof of no correction nor permission to use today's value.

For publication, preserve four distinctions: artifact generation, accepted publication, reachable user payload, and actual user exposure. A successful build is not served-byte proof. A server response does not prove a person read the card. A push sent to a notification service is not automatically a delivered or noticed alert. The experiment should make only the strongest claim that its existing receipts justify.

## 7. Sampling without manufacturing independent evidence

A stream of five-minute records is useful operational data, but its rows are not independent trades. The same episode can appear on many dates and under several strategies. More observations can improve trajectory modeling without providing the same increase in independent evidence.

For the initial timing race, use one opportunity per canonical episode and strategy version. Store every required observation through the existing owners, but compute the primary opportunity-level result once. Re-entry remains out of the first comparison unless the original owner contract specifically requires it; otherwise it adds another decision and makes attribution harder.

For trajectory models, predeclare sampling landmarks. A reasonable proposed starting form is the first owner-admissible observation plus one fixed owner-issued daily observation while the episode remains active, with transition-triggered samples reported separately. Do not choose a landmark retrospectively because it preceded the best move. Observation-heavy episodes need declared weighting so a long unresolved setup does not dominate training by emitting more rows.

All samples from an episode must respect fold boundaries. A later sample can be valid for a later rolling prediction, but its outcomes must not leak backward into training for the same earlier test episode. Corrections, duplicate policy labels and repeated horizons never earn additional independent-episode credit.

## 8. First policy experiment: early versus confirmation versus pullback

The proposed experiment is a timing comparison within the existing Early Leadership/Sector Rotation strategy. It is not a comparison of different detectors on unrelated stocks, not a fresh general-population veto waiver, and not a replacement for #7751's distinct B4 calibration.

| Arm | Proposed behavior | Mandatory boundary |
|---|---|---|
| Early-lawful | Act at the first accepted early expert opportunity for which required owner conditions are satisfied | No entry merely because an early indicator exists; preserve the B4/quote/basis/risk contract applicable to the study |
| Confirmation-lawful | Wait for a specified existing slower confirmation, then require the same relevant current-entry safety facts | Never-confirmers remain in the original cohort as no entry or another disclosed terminal state |
| Pullback-lawful | Wait for the specified owner-native pullback/zone opportunity | Never-touch and touched-but-unfilled cases remain visible; no fill at the day's eventual low |
| Cash reference | Keep the declared comparison capital in its cash convention | Cash is an actual comparator, not an excuse to zero-fill unavailable trade prices |

The arm names do not finish registration. Before execution the incumbent owners must supply exact expert/version references, allowable entry window, entry order/fill convention, shared geometry and exit-policy identity, data availability, cost model, formal primary comparison, and amendment/kill equivalence checks. These are genuinely unresolved contract values, not thresholds to guess.

For the new timing study only, propose H10 from the common episode origin as the primary diagnostic horizon, with H5/H15 supporting. This requires owner adoption. It does not change #7751's already registered H5/H10 co-primary outcomes or any legacy grade horizon. Long-cycle and earnings studies need their own frozen horizon choices before outcomes are examined.

Initially keep the management policy identical in definition across the entry arms. A stop/target policy expressed relative to each fill changes its numerical levels as an intended consequence; report that, and include a common-clock terminal-value comparison to separate timing from path termination. The first experiment must not independently optimize each arm's stop or exit. A later factorial entry-by-management experiment can test whether the optimal hold logic differs, without retroactively redefining the first result.

## 9. What the primary result means

The primary estimand is the difference in full-opportunity policy value on the same original cohort, under an explicit price-taking/execution model. It includes waiting and cash after exits, not just selected fills. Date-weight the cohort contrasts so a date with many overlapping names does not silently dominate the headline; also publish the episode-weighted result so that the weighting choice is visible.

A simple opportunity accounting form is:

`policy value = entry probability × conditional filled outcome + no-entry probability × declared cash/wait outcome`.

This identity is useful only when all components are defined on the same origin and endpoint. A no-entry case and an unpriced case are not interchangeable. Without defensible outcomes for missing paths, the complete mean can be unidentified; report coverage and sensitivity bounds rather than claim an exact value.

For each arm report both episode-origin outcomes and entry-clock trade outcomes. The former answers whether the whole strategy of waiting/entering helped; the latter describes the experiences of the trades it actually filled. Report participation, cash duration, capital-days, turnover and time to payoff alongside returns.

Equal opportunity allocations are a research convention, not a feasible portfolio backtest. A separate downstream Portfolio/Risk comparison must account for simultaneous opportunities, limited capital, issuer overlap, concentration, sizing, financing and capacity before any portfolio return is claimed. Do not sum independent hypothetical trade returns as though each used the same available dollar.

A fixed market path supports a simulated policy comparison under no-material-market-impact and fill-model assumptions. It does not identify what would happen at arbitrary size, or how discretionary users would respond. No causal claim about actual users is obtained without a separate identifiable design.

## 10. Benchmarks and the value of group selection

Use four named controls where lawful: cash, the broad market, the PIT sector/industry comparator, and the incumbent policy on the identical decision field. All must use the same intended entry and exit clock for the comparison being reported, with the same return basis.

A stock can lose absolutely while outperforming a falling market. It can rise strongly but underperform its sector. Those observations answer different questions. Neither absolute nor sector-relative performance should be hidden. In particular, sector adjustment should diagnose within-group stock selection without declaring successful group allocation economically worthless.

For early-versus-late comparisons, the common-origin control tracks cash during waiting and the market over the full opportunity window. A trade-clock comparison enters its benchmark on the same fill clock as that trade. Both may be shown; their labels and denominators must not be mixed.

Do not forward-fill the security's prices to manufacture liquidity. Where a native legacy comparator forward-fills an index, disclose that convention and verify endpoint alignment before calling it exchange-session matched. Changes to a historical benchmark or fill convention create a new measurement version, not an unnoticed improvement to old results.

## 11. Price, bar and session contracts

Session dates are exchange calendar labels, not arbitrary midnight timestamps. US regular trading hours, holidays, early closes, premarket and after-hours need explicit treatment using the existing calendar/session owner. A four-hour bar over a 6.5-hour core session also requires an anchoring convention and treatment of the final partial bar; vendor defaults are not a universal definition. NYSE's official trading information distinguishes core hours and other sessions. [E3]

A technical signal that uses a completed close cannot assume a fill at that already known close unless a separately specified pre-close executable process justifies it. The existing US policy-free grader uses next available row close. Preserve that historical ruler. For a new intraday study, use a separately registered next-actionable-quote/order convention and the measured latency, rather than changing the legacy record.

The fact that a series has H later rows does not prove H expected sessions elapsed. Missing bars can move a positional endpoint. Before a new result is called H10-session performance, validate the expected endpoint and required price coverage using the existing exchange calendar. Missing sessions remain a data condition; a late fill is a different result from an on-time one.

Record whether each price is raw, split adjusted, dividend adjusted, or another owner-supported basis. Do not compare a raw live quote with an adjusted historical stop by approximate numeric agreement alone. Total-return series can be valid for economic return measurement, while price geometry and actual share/cash handling require their own consistent contract. Cash dividends, splits, special distributions and reorganizations are not interchangeable adjustments.

## 12. Execution costs and fills

The first study should not invent a sophisticated transaction-cost model that cannot be supplied with data. It should use the incumbent admissible tape and a declared hierarchy: measured quote-side execution where supported; conservative owner-approved estimates when not; and explicit unmeasurable cases when a defensible estimate is absent.

A long buy at the ask and sell at the bid already pays the spread. Do not add another half-spread on top of those prices. If execution is modeled from midpoint, add the appropriate side of spread once, plus separately identified fees, latency and any approved impact assumption. Preserve the benchmark's matching assumptions. Missing NBBO is not evidence of zero spread.

A limit touched by a daily low is not proof of a fill. Order type, arrival time, quote/trade sequence, queue/depth information and volume can matter. With only OHLC data, disclose the ambiguity and test conservative alternatives. No strategy is allowed to buy the hindsight low or sell the hindsight high simply because those values exist in a file.

Empirical trading-cost research shows variation across trade characteristics, stock characteristics, time and markets. This motivates sensitivity analysis, not importing one institution's historical cost estimate as Prophet's retail-user fill model. [E4]

The B4 NBBO/session-open substrate and basis-provenance carriers remain distinct prerequisites. #7751 explicitly makes no capacity claim; the R2 design does not remove that limit. A 50-bps initial control is a policy parameter, not a measured all-in round-trip cost.

## 13. Label families and the drawdown distinction

Use separate label families rather than a single win/loss column.

**Policy-free fixed-horizon labels:** raw/total return basis, market and sector excess, entry-relative close MFE/MAE and the ruler's native endpoint. These preserve the existing learning record.

**Policy labels:** fill state/time/price, exit state/time/price, net payoff including costs and cash, target/invalidation order when known, holding duration, capital-days and participation. These measure a declared strategy, not the unmodified signal.

**Path labels:** running-peak drawdown, close versus high/low excursion, time to favorable excursion, time to invalidation, recovery/retention and tail-event incidence. A path statistic needs its observation frequency and valuation basis beside it.

For the synthetic close path `100 → 120 → 102 → 110`, entry-relative adverse excursion is **0%**, close MFE is **20%**, terminal return is **10%**, and running-peak drawdown is **−15%**. A reader seeing only the entry-relative quantity could incorrectly conclude that the holder experienced no meaningful giveback.

The Python demonstration asserts this distinction. It does not execute or repair `engine/grading.py`; it demonstrates its inspected algebra versus a separate definition. Any additional production field must be implemented by the existing outcome owner with an explicit version, while frozen historical output remains unchanged. [I1, I2]

## 14. Target-before-invalidation and uncertainty about order

A multi-head predictor should not independently report incompatible first-event probabilities. A basic discrete-time competing-risk model can estimate conditional probabilities of target first, invalidation first and no event in the next interval. Cumulative incidence follows by multiplying each interval's hazard by the probability of surviving event-free to its start. The cumulative first-event probabilities plus remaining event-free probability must sum to one.

This is a baseline modeling proposal, not a required new neural architecture. A nonlinear alternative must beat it under the same time, sampling and calibration rules.

An OHLC bar `open=100, high=110, low=94, close=108` touches a 105 target and a 95 stop. Without finer sequencing, the first event is unresolved. Reporting a favorable first-hit outcome is invented precision; reporting adverse-first as a conservative sensitivity is permissible only if it is labeled as an assumption, not an observed fact.

At a fixed horizon, a known competing invalidation is a negative case for the question “target first by H,” not a case to exclude from evaluation. An episode still event-free at H is distinguishable from one censored before H. Research on competing-risk predictive accuracy emphasizes these definition and censoring issues; its methods do not remove finance-panel dependence or guarantee valid imputation of missing paths. [E5]

## 15. A closed accounting of unresolved observations

Analytical categories in this document are descriptive mappings, not additions to any owner's closed enums. Production adapters must preserve native values and map them only through accepted contracts.

- **No entry by policy:** opportunity was observable; the policy chose or was required to wait. Its cash result can be known.
- **Awaiting fill:** the allowed opportunity window has not ended; no terminal no-entry assertion yet.
- **Entered, horizon not elapsed:** right-censored at the analysis date; not a losing trade or an immaturity bug.
- **Missing/stale/unpriced path:** economic outcome may be unknown; not zero, no entry, or ordinary censoring without further assumptions.
- **Confirmed halt/suspension:** owner-supported market status, not merely few future bars.
- **Delisting/reorganization:** follow the accepted corporate-action/terminal-value owner and distinguish known cash proceeds, exchanged shares, estimates and unavailable valuation. A last traded close is not necessarily an executable liquidation price.
- **Source/identity invalidated:** data-quality or lineage defect, not automatically an economic stop loss.
- **Same-bar event order unresolved:** preserve interval/bounds or a named conservative assumption.

A row-accounting identity should reconcile every original observation to a terminal or pending status at the read. Report exclusions and their reasons by arm and source coverage. A method cannot win because the difficult rows quietly vanish.

Inverse-probability-of-censoring methods require appropriate assumptions and estimability; they are not a universal repair for missing market data, delisted losers or unknown execution. Sensitivity bounds and a no-verdict outcome are sometimes the honest result.

## 16. Time splits: dates first, rows second

The canonical Fusion validation protocol already requires fold-scoped transforms, walk-forward purging and embargo at least the longest horizon, and minimum usable folds of 60 distinct training dates and 10 test dates. Higher-capacity models also face its name-disjoint/capacity/permutation controls. These remain intact; this report is not an amendment. [I5]

An implementation trap is worth calling out. The official `TimeSeriesSplit` documentation defines `gap` in **samples**, not trading sessions. Applying `gap=63` to a table with hundreds of candidate rows per day does not create a 63-session embargo. It can leave neighboring rows from the same date on opposite sides of a boundary. Split the unique owner session groups, then map the complete groups back to rows, with episode and information-interval checks. [E6]

A training label must have become available before the fit cutoff. A row with an early decision timestamp but a later unresolved H63 outcome is not usable supervised training data for that cutoff. Purging must consider outcome intervals and grouped repeated observations, not just the feature timestamp.

Every fitted transform belongs inside the training fold: normalization, percentile reference distributions, imputation parameters where allowed, feature selection, embeddings learned from the panel, calibration, hyperparameters and thresholds. Same-cut within-date ranks may be computed from the available decision field when that is the registered feature definition; they must not use future members or a larger retrospectively known field.

Separate future-date tests from identity-generalization tests. A name-disjoint test asks whether the method transfers across securities; a later-date test asks whether it survives new conditions. A random name split across the full future timeline is not sufficient to establish prospective performance. No per-ticker outcome-maximizing expert assignment is permitted.

## 17. Dependence, power and trial accounting

Report raw rows, unique episodes, unique issuers, origin dates, market blocks, filled trades, event counts, valid outcome endpoints and coverage. These are different counts. A single convenient “effective N” cannot replace the dependence analysis.

Finance panels can have both firm and time dependence; ordinary independent-row uncertainty can be misleading. Date/issuer or episode dependence must be incorporated into the chosen inference design, with block-length sensitivity for overlapping horizons and explicit limitations when few independent blocks exist. A date-cluster bootstrap alone does not automatically remove long overlapping windows; an issuer cluster alone does not remove market shocks. [E7]

For orientation only, suppose independent paired date-block differences have standard deviation 2 percentage points. A normal-approximation two-sided 5% test with 80% power requires approximately **32**, **126** or **503** independent blocks to detect differences of **1.0**, **0.5** or **0.25** percentage points. These are synthetic calculations, not a measured Prophet sample requirement. Dependence, tails, multiple comparisons and estimation uncertainty can change the requirement substantially.

Similarly, 300 observations in clusters of 30 with assumed within-cluster correlation 0.15 have the elementary one-level design effect 5.35, giving about 56 independent-observation equivalents in that toy model. This is not an estimate for Prophet. It illustrates why a 300-row minimum cannot be treated as automatic power.

Prediction-model sample-size research also distinguishes the number of parameters, events, censoring, anticipated performance and required precision. A simple floor is a safety condition, not proof of an estimable model. [E8]

Keep the existing #7751 floor and no-peeking law. Before a verdict, its owner must resolve independent episode counting, duplicate labels, endpoint hierarchy and a formal read rule. More policies, horizons, endpoints, seeds and feature combinations create more opportunities for selection. Record them in the existing trial owner, apply its multiplicity rules, and preserve failed/null results. [E9]

## 18. Promotion requires evidence of acceptable harm, not absence of significance

The first study must name its primary benefit and acceptable harm before examining outcomes. A defensible form for a return comparison is a lower confidence bound on the challenger-minus-control difference above a predeclared economic loss margin, combined with the registered benefit and coverage conditions. The numerical margin must be selected for the intended user, horizon, costs and downstream risk budget, not borrowed from this synthetic report.

For example, a difference interval of **[−3, +1] percentage points** overlaps zero. That does not demonstrate safety within a **0.5-point** margin; the lower bound is far too negative. “No significant harm found” and “acceptably small harm established” are different results. Equivalence/non-inferiority methods formalize that distinction. [E10]

Coverage also needs a declared requirement or tradeoff frontier. A policy cannot be promoted only because a few selected fills look good. Primary benefit, tail-risk condition, minimum participation, missingness tolerance and reproducibility must all be declared. Where the study cannot identify those quantities, its result is insufficient evidence, not an automatic failure of the underlying market hypothesis and not a pass.

Do not turn a calibration/engineering approval into recommendation authority. The sequence remains source correctness, temporal eligibility, specified experiment, prospective or admissible OOS evidence, independent adjudication, controlled release and real production acceptance. No automatic weight updates or model-originated trading authority are introduced.

## 19. Probability calibration after ranking and selection

Evaluate probabilities where they will be consumed: by strategy/horizon/Availability lane, top-K and evidence-coverage cohort, with adequate independent observations and predeclared diagnostic resolution. A model calibrated across thousands of low-priority candidates can still mislead users among its selected top ten.

Use proper predictive scores alongside calibration curves, discrimination and decision value. Brier score assesses more than calibration alone; a low Brier score does not by itself prove useful ranking or positive economic value. Competing-risk probabilities require an appropriate target definition and censoring treatment. Do not discard competing failures to improve a calibration plot. [E5]

Separate forecast intervals for individual outcomes, intervals for conditional means, uncertainty about ranking, and operational availability. A data-health confidence badge is not an empirical probability of profit. An evidence-rich story does not deserve more precise probability text until the relevant calibration has been demonstrated.

For early deployed research views, honest states such as “forecast accruing,” “sparse evidence” or “entry unavailable” are preferable to manufactured decimals. Product readability and calibration are complementary: a well-explained uncalibrated heuristic remains uncalibrated.

## 20. Synthetic demonstration and executed verification

`synthetic_measurement_checks.py` contains invented payoff arrays and elementary examples. It imports no Prophet code, uses no market data, trains nothing, makes no provider requests, and cannot change a strategy. It checks logical consequences of the measurement design, not software integration or economic edge.

### 20.1 Same twelve original opportunities

The early arm fills all twelve. Its invented net payoffs are `12, 8, 5, 4, 3, 2, -10, -12, -9, -5, -4, -3` percent. The first six eventually confirm. The confirmation arm fills those six with payoffs `5, 3, 1, 0, -1, 0`; the other six remain cash. The pullback arm fills three with `4, 3, 2`; the other nine remain cash. Cash is assumed 0% for this example. The payoffs are stipulated, not generated by a path/fill simulator.

| Policy | Original opportunities | Filled trades | Filled-only mean | Full-opportunity mean |
|---|---:|---:|---:|---:|
| Early | 12 | 12 | −0.75% | −0.75% |
| Confirmation | 12 | 6 | +1.33% | +0.67% |
| Pullback | 12 | 3 | +3.00% | +0.75% |

Now deliberately make the bad comparison: look only at eventual confirmers. The early arm appears to earn **+5.67%**, against **+1.33%** after confirmation. Including the six never-confirming early failures reverses that conclusion in this invented example. This proves only the arithmetic of selection bias, not which timing method wins in real markets.

### 20.2 What passed

Eighteen checks passed: full-denominator means; reversal under confirmation-conditioned selection; unavailable versus cash; rejection of a no-entry row pretending to be a filled trade; late observed/correction and unknown clocks; entry-relative excursion versus running-peak drawdown; same-bar order ambiguity; coherent competing-event probabilities and invalid-hazard refusal; independent-block power arithmetic; sample-gap versus session-gap; label availability at fit time; non-inferiority versus nonsignificance; and no duplicate spread charge.

The result JSON is deterministic. The test log is an actual executed receipt, not a future acceptance claim. Production modules executed: **none**. Real observations: **zero**. Test success does not qualify the future production implementation.

## 21. Source-readiness map: what can actually support the next experiment

| Required evidence | Existing owner/path | State established this round | Required before a real result |
|---|---|---|---|
| Security identity and source nominations | Data OS, B1 source/events/suppressions | Source contract inspected | Exact supported historical dates, identity coverage, suppression counts; no surrogate episode IDs |
| Canonical episode and decision cut | B1 generation and D5 A8/A9 | Contract verified, not latest-runtime acceptance | Immutable generation selected for each observation and actual availability at its origin |
| Completed-session prices | Existing price/calendar owners; #7180 source-binding carrier | #7180 open Draft, native head advanced beyond its older qualification prose | Exact admitted vintage, missing-session and basis census, accepted publication and runtime proof |
| Original rank and scored field | Frozen board/candidate owners | R1 identified historical popup rank hazard; not re-proved here | Admission-time joins, population/lane identity and explicit unmatched rows |
| Early/slow/pullback events | Existing technical/Radar/TOI/Setup Species owners | Ownership inherited from R1; no new event tape read | Exact version/clock/rights/kill-equivalence approval and no hindsight event repaint |
| Current-entry decision | B4 through #7581 | Open Draft at `39ef2cd48e091d90f12771aab142c2197022aa79` | Accepted owner facts, runtime projection and natural real-path proof |
| Quote/basis alignment | #7584 | Open Draft at `87f85e88f75bf037e4f917ee30313444f766bb62` | Accepted provenance; numeric similarity alone insufficient |
| NBBO and session open | #7734 | Open Draft at `55e8671317af3219785e7a14e490028a9933daa4` | Accepted substrate, historical/prospective coverage and latency/rights evidence |
| Earnings revisions | D5 A7 and Earnings source-revision owner | Correct access/clock contract inspected | Usable source/body revision range, actual observed clocks and correction coverage |
| Theme/relationship evidence | Existing GMI and D5 owners | No full historical-coverage claim made in R2 | PIT memberships/edges, availability, rights and completeness before replay |
| Outcome marks | `engine/us_prophet_grades.py`, `engine/grading.py` | Native ruler inspected | Correct mapping and coverage; separate owner extension for policy/path labels |
| User-visible opportunity time | Existing publisher/auth/alert receipts | Not proven by this research round | Exact accepted-to-served/notification linkage; no fictional exposure clock |
| B4 calibration | Accepted #7751 / incumbent Evaluation path | Prior duplicate-cell finding remains on its owner PR; no later disposition in bounded comment read | Owner interpretation/amendment before inferential credit, plus prospective capture and formal read gates |

This map is intentionally not all green. Knowing an interface exists is not knowing its historical corpus can support a scientific experiment. Source readiness is a claim about fields, dates, rights, missingness, corrections and consumers together.

The native #7180 head read is `a991d4d22a933ca8953a08260352cc4b30e2ee8d`, while its body still describes older head `370b09bd...` qualification. R2 credits neither current-head CI nor release from that text. No branch is moved, reviewed, merged or duplicated here. [I6–I9]

## 22. Implementation acceptance contracts for the eventual build

The next implementation should extend the existing owners with small, user-relevant verticals rather than create a new evaluation platform. The following are proposed acceptance contracts, not newly dispatched jobs.

**Temporal join vertical.** Consume one exact source nomination, one actual B1 generation, the allowed evidence revision and the corresponding served/grade references. Its output explains what was known, what was missing and what was delivered. Positive and late-observed/corrected controls must traverse real owner readers. No invented episode, source clock or historical rank. The user-facing outcome is an inspectable opportunity timeline and an accurate “why not available” explanation.

**Policy-accounting vertical.** On a tiny declared dataset, produce all original opportunities across all registered arms, including no-entry and missing paths. Reconcile row accounting, identical policy aliases, deterministic reruns and immutable versions. Use existing outcome loaders; preserve old marks. The user-facing outcome is a trustworthy strategy comparison rather than a flattering filled-trade table.

**Path-label vertical.** Add owner-versioned path/first-event interpretations only where the input frequency supports them. Expose close-versus-intraday and unresolved-order states. The user-facing outcome is a realistic account of upside retained, giveback and invalidation risk.

**Model-evaluation vertical.** Validate whole-date/episode folds, horizon and outcome-availability boundaries, training-only transforms, identity controls and registered trial accounting before a first model is fit. Deliberately leaky fixtures must fail. The outcome is a challenger result whose claimed improvement can survive an independent audit.

**Entitled-user proof vertical.** Trace accepted input through candidate, strategy, availability, explanation and actual entitled browser/alert surface. Include stale/empty/partial/corrected/blocked states. A merged evaluator or green CI does not complete this vertical.

For each vertical, implementation should include machine consumer, product projection, tests, independent review and the required real-path proof. Fable should own difficult integration/judgment when needed; routine adapters/tests should go to the least-scarce admitted capable workers. No worker or reviewer has been assigned by this research document.

## 23. What is settled and what still must be decided

**Settled for this research proposal:** separate discovery/ranking/entry/management estimands; origin cohort before future confirmation; generation-pinned as-run knowledge; separate replay claims; all-opportunity and fill-only denominators; explicit unknown/censoring/terminal cases; price/bar/session fidelity; separate excursion/drawdown; matched controls; whole-date/episode evaluation; cost and dependence accounting; no inferential credit for duplicated policies or repeated rows.

**Still open before a registered experiment:** exact admitted expert IDs and policy versions; initial executable source range; exact entry opportunity window, order type, latency and management identity; precise cost hierarchy and fallback; first-cycle proving universe; confirmatory endpoint/horizon hierarchy; economic non-inferiority and coverage margins; test dates/block design and sufficient precision; source and model-vintage eligibility; existing-owner registration and approval.

These choices cannot be answered by manufacturing constants in a report. They are the bounded next design decisions. They should be resolved before fitting or inspecting outcomes, using the existing owner contracts and source readiness—not retrospective tuning.

The next R3 packet should specify the **first Early Leadership vertical end to end**: exact allowed evidence/events, source/feature clocks, strategy policy, baseline/model heads, user explanation and proof, then a shared template for Earnings/Revision and Cycle Capture. This converts the broad master-plan ambition into one scientifically testable, consumer-visible slice without reducing the eventual multi-sleeve scope.

## 24. Checkpoint and limits

R2 is a proposed measurement specification and synthetic verification packet. It is not a registered experiment, statistical finding of alpha, product implementation, source repair, or production acceptance.

The existing parent #6805 working checkpoint is comment **5789402164**. Its final update/readback records the packet hashes, retained R1 decisions, source observations, unresolved contracts and next action. No source custody, review obligation or running worker is transferred by this note. No background job is claimed.

Continue research in Pro for R3's exact first-sleeve contract and build decomposition. GitHub comment writing has an actual success receipt; source-edit/merge/deployment remain their own later capability and authority questions. The overall flagship mission remains incomplete.

## References and evidence scope

Internal sources are primary implementation/contracts at the pinned Macro revision unless otherwise stated. Lines refer to source-file locations, not a claim of executing the entire module.

- **I1:** `engine/grading.py`, lines 1–265; blob `1208a7aa597159969a0ed7ccd359972bc413941a`.
- **I2:** `engine/us_prophet_grades.py`, lines 1–215; blob `da7d1f625dc3d20431806502d9f36be82973ffa2`.
- **I3:** `engine/us_candidate_episode.py`, lines 1–205; blob `a34f2c2bf80411ffaa9800774abb4cc7238c90d1`.
- **I4:** `research/prophet_v4/flagship_cells/CELL_F_D5_CONTRACT_AMENDMENTS_2026-08-26.md`, A7–A9; blob `141782387738bfd955c0622d7de91c16bdf5c26b`.
- **I5:** `research/PROPHET_CONDITIONAL_FUSION_MASTERPLAN_BY_FABLE.md`, §9, lines 893–961; blob `9f02020815cd51b6e4d9baa9d79ab3a1cf415cda`.
- **I6:** Macro #7180 native metadata: open Draft, head `a991d4d22a933ca8953a08260352cc4b30e2ee8d` at this read.
- **I7:** Macro #7581 native metadata: open Draft, head `39ef2cd48e091d90f12771aab142c2197022aa79`.
- **I8:** Macro #7584 native metadata: open Draft, head `87f85e88f75bf037e4f917ee30313444f766bb62`.
- **I9:** Macro #7734 native metadata: open Draft, head `55e8671317af3219785e7a14e490028a9933daa4`.
- **I10:** #7751 comment 5787579945 and bounded later-comment read, plus previous cumulative #6805/5787643381. No outcome data were accessed.

External methods are primary papers or official documentation. They inform experimental design, not Prophet performance. Most publisher papers were read at abstract/method-summary level; the competing-risk HTML method and TimeSeriesSplit documentation received more detailed inspection. No inaccessible paper is claimed fully read.

- **E1:** Hernán et al. (2016), *Specifying a target trial prevents immortal time bias and other self-inflicted injuries in observational analyses*. Journal of Clinical Epidemiology 79:70–75. DOI `10.1016/j.jclinepi.2016.04.014`.
- **E2:** Hernán and Robins (2016), *Using Big Data to Emulate a Target Trial When a Randomized Trial Is Not Available*. American Journal of Epidemiology 183:758–764. DOI `10.1093/aje/kwv254`; https://pubmed.ncbi.nlm.nih.gov/26994063/ .
- **E3:** NYSE official trading information: https://www.nyse.com/trade/trading-information .
- **E4:** Frazzini, Israel and Moskowitz (2018), *Trading Costs*. AQR research: https://www.aqr.com/insights/research/working-paper/trading-costs .
- **E5:** Wu and Li (2017), *Quantifying and Estimating the Predictive Accuracy for Censored Time-to-Event Data with Competing Risks*. https://arxiv.org/html/1707.03971 . Method precedent; its independent-subject assumptions must not be copied into a correlated finance panel without qualification.
- **E6:** scikit-learn official *TimeSeriesSplit* reference: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html . Gap is in samples; source documentation is not a replacement for the repository's validation contract.
- **E7:** Petersen (2009), *Estimating Standard Errors in Finance Panel Data Sets: Comparing Approaches*. Review of Financial Studies 22:435–480. DOI `10.1093/rfs/hhn053`.
- **E8:** Riley et al. (2019), *Minimum sample size for developing a multivariable prediction model: PART II — binary and time-to-event outcomes*. Statistics in Medicine 38:1276–1296. DOI `10.1002/sim.7992`; published correction DOI `10.1002/sim.8409`. General precision/design lesson only; no formula from the paper implemented here.
- **E9:** Harvey, Liu and Zhu (2016), *…and the Cross-Section of Expected Returns*. Review of Financial Studies; working paper https://www.nber.org/papers/w20592 . Used for multiple-testing discipline, not a universal numerical cutoff or a claim every proposed factor is false.
- **E10:** Lakens (2017), *Equivalence Tests: A Practical Primer for t Tests, Correlations, and Meta-Analyses*. Social Psychological and Personality Science 8:355–362. DOI `10.1177/1948550617697177`.
