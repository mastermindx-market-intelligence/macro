# PB-G policy-behavior baseline — frozen-return reconciliation

**Status:** completed PB-G Phase 2 integration. **Research outcome:** a compatible 40–60-episode M0/M1/rich-M2 evaluation is not supported by the returned evidence; the precise data-insufficiency branch is satisfied. No source forecast, outcome, decision-time input, cohort or probability was changed. The result has research authority only and does not complete the unperformed richer-model study or authorize production changes.

## 1. Result that the evidence supports

PB-A's **M2-min** and literal **M0** make identical predictions on all **eight common primary episodes**, scoring **4/8, 7/8 and 5/8** at one, three and six months. The empirical M2 is action persistence with one conventional-floor exception; the commissioned richer actions/constraints/revealed-preference model is untested. The all-three comparison contains only **four primary episodes**: all models score 0/4 at one month; M0 and M2-min score 3/4 versus inversion's 0/4 at three and six months. PB-B supplies no scored forecasts, and PB-E supplies financial dossiers rather than comparable prediction rows. This preserves PB-F A01–A06, A13, A18–A19, B01/B12 and X06 without resurrecting their rejected extrapolations. [A1–A4; B1; F1–F2]

The useful scientific result is narrower than a behavioral forecasting advantage: preserving instrument decisions, constraints and horizons prevents category errors, and a simple floor constraint avoids one mechanical action-persistence error. Neither result identifies private motives, validates rich M2, supports a universal inversion strategy, nor supplies rate/FX/rank/entry/size/alert authority.

## 2. Immutable inputs and independent arithmetic

| Reference | Immutable artifact |
|---|---|
| A1 | [PB-A method and findings, a60c620](https://github.com/mastermindx-market-intelligence/macro/blob/a60c620b2761db74070929068c969aac8c2cee57/research/policy_behavior/pro_returns/PB-A/PB_A_METHOD_AND_FINDINGS.md) |
| A2 | [PB-A frozen forecasts, a60c620](https://github.com/mastermindx-market-intelligence/macro/blob/a60c620b2761db74070929068c969aac8c2cee57/research/policy_behavior/pro_returns/PB-A/PB_A_FORECAST_FREEZE.json) |
| A3 | [PB-A outcomes, a60c620](https://github.com/mastermindx-market-intelligence/macro/blob/a60c620b2761db74070929068c969aac8c2cee57/research/policy_behavior/pro_returns/PB-A/PB_A_OUTCOMES.json) |
| A4 | [PB-A casebook, a60c620](https://github.com/mastermindx-market-intelligence/macro/blob/a60c620b2761db74070929068c969aac8c2cee57/research/policy_behavior/pro_returns/PB-A/PB_A_CASEBOOK.json) |
| A5 | [PB-A supplied pilot, a60c620](https://github.com/mastermindx-market-intelligence/macro/blob/a60c620b2761db74070929068c969aac8c2cee57/research/policy_behavior/pro_returns/PB-A/PB_A_BASELINE_PILOT.json) |
| B1 | [PB-B casebook, 1604552](https://github.com/mastermindx-market-intelligence/macro/blob/1604552006b7a91ed5d0fa89c785a983478866ea/research/policy_behavior/pro_returns/PB-B/PB_B_CASEBOOK.json) |
| E1 | [PB-E typed network edges and dossiers, 4720504](https://github.com/mastermindx-market-intelligence/macro/blob/4720504205a7307630efe249a79c4bb02e5560da/research/policy_behavior/pro_returns/PB-E/PB_E_NETWORK_EDGES.json) |
| F1 | [PB-F claim matrix, 7458a5d](https://github.com/mastermindx-market-intelligence/macro/blob/7458a5d9b8e507de435136560a5cf86cebb839b9/research/policy_behavior/pro_returns/PB-F/PB_F_CLAIM_MATRIX.json) |
| F2 | [PB-F integrator instructions, 7458a5d](https://github.com/mastermindx-market-intelligence/macro/blob/7458a5d9b8e507de435136560a5cf86cebb839b9/research/policy_behavior/pro_returns/PB-F/PB_F_INTEGRATOR_INSTRUCTIONS.md) |

`PB_G_BASELINE_SOURCE_RECEIPTS.json` records 18 exact source mirrors, each verified against its original Git blob SHA. `scripts/reproduce_baseline.py` independently joins A2 to A3 by episode ID, scores unchanged probability vectors and outcomes, and only then compares results with A5. All **60 own-score groups** reproduce: two cohorts × two targets × three horizons × five models. It also reconstructs pairwise intersections, source-family/regime slices, B's abstentions/meeting clusters and E's case taxonomy. Full derived evidence is `PB_G_BASELINE_RECOMPUTED.json`.

This is arithmetic replication of the frozen outcome artifact, not a new collection or independent re-derivation of FRED/official historical outcome series. The source-family slice is a new descriptive reaggregation; it is not a preregistered confirmatory test. No aggregate statistical significance or effective independent sample size is claimed.

### Portable reproduction

Fetch each exact immutable source listed in `PB_G_BASELINE_SOURCE_RECEIPTS.json` using authorized GitHub access. Save the unchanged bytes under the receipt's `file` basename in a disposable source directory. The receipt supplies the commit, immutable URL, expected Git blob SHA and SHA256. For a large file whose contents response is empty, fetch its specified Git blob or complete raw content; an empty response is not a source artifact. Do not normalize whitespace or add a newline. These mirrors are temporary reproduction inputs, not a new evidence store, and are not duplicated in this packet.

From the PB-G packet directory, run:

```bash
python scripts/reproduce_baseline.py \
  --source-dir /path/to/disposable/pb-g-source-mirrors \
  --receipts PB_G_BASELINE_SOURCE_RECEIPTS.json \
  --output /path/to/disposable/PB_G_BASELINE_RECOMPUTED.json
```

`--source-dir` is required. The optional `--receipts` and `--output` arguments default to this packet's receipt manifest and `PB_G_BASELINE_RECOMPUTED.json`, respectively, independent of the working directory. The script makes no network requests and verifies every source Git blob SHA before scoring. Reproduction must report **18 verified sources**, **60 exactly reproduced own-score groups**, an eight-episode M0/M2-min primary intersection and a four-episode all-three intersection. The unchanged recomputed JSON has SHA256 `5c9b534ae8e1fe1c78ad5bc432f1ba094fea4a8867b2e069116755960bd7e0e7`.


## 3. Denominator and compatibility adjudication

| Returned unit | Raw count | Comparable M0/M1/M2-min forecasts | Contribution to rich-M2 validation |
|---|---:|---|---:|
| PB-A primary policy episodes | 24 | M0 9; M1 5; M2-min 11; M0∩M2-min 8; all-three intersection 4 | 0 |
| PB-A deliberately separate pause challenge | 1 | All three forecast; retain outside every primary denominator | 0 |
| PB-B decision-time snapshots | 15 | 45 model slots, **45 abstentions**, 0 comparison-eligible predictions | 0 |
| PB-E structural financing/support dossiers | 15 | No frozen common policy forecast target, horizon, probability or comparison cohort | 0 |

The arithmetic **24 + 15 = 39** counts A primary episodes plus B snapshots. Adding the challenge to manufacture 40 violates its explicit segregation. The arithmetic **24 + 15 + 15 = 54** counts heterogeneous records, not 54 compatible policy episodes. Including the challenge yields 55 heterogeneous records, which has the same incompatibility. E's 112 typed edges are relationships/observations within those dossiers, not 112 extra episodes. [A4; B1; E1; F1 X06]

B's 15 snapshots map to **10 BOJ target decisions**. September 2025 has three snapshots; September 2026 has four; the other eight targets have one each. These are distinct information cuts sharing outcome/process clusters. Ten target decisions are not ten independent natural experiments; no independence claim follows even after collapsing duplicate target IDs. A's shared policy cycles and overlapping horizons also remain dependent. [B1]

### Target compatibility

| Family / target | Returned definition | PB-G treatment |
|---|---|---|
| A, effective Fed target midpoint net direction | Effective endpoint target midpoint versus the most recently decided and publicly known target at the cut; calendar horizons of 1/3/6 months | Score each horizon separately with original cuts/anchors and abstentions |
| A, first subsequent target **change** | First nonzero target change decided strictly after cut and effective by horizon; HOLD if none | Separate secondary target; **not** first subsequent FOMC meeting |
| B, BOJ direction/level | Next scheduled BOJ announcement strictly after cut | Keep separate; all original model outputs remain null/abstaining |
| E, obligation and execution evidence | Equity, debt, warrants/guarantees, grants, capacity, revenue, receivables, cash and amendments with distinct units/states | Context and future source examples; no conversion into policy-direction forecasts |
| Market/transmission targets | A has descriptive daily 2y/10y/real-yield/breakeven drifts; no admitted M0/M1/M2 market predictions. B windows are descriptive; key synchronized controls are incomplete | No market model league table, price-surprise estimate, causal event return or rate-to-FX mapping |

A's two policy targets happen to have identical directions on all **72 primary episode/horizon observations**, plus all three challenge observations. That equality is a property of this return, not a license to collapse their definitions or double the evidence. B's next-meeting endpoint cannot be substituted for either A definition. A frozen rate decision already announced at the cut is absorbed into the anchor even if effective tomorrow; treating it as a subsequent surprise would leak known information into the target. [A1–A3; B1]

E has genuine value as a **typed qualitative casebook**. Its 15 cases range from Microsoft–OpenAI and supplier/customer financing relationships to project finance, nuclear-power arrangements, government equity/support and an ASML historical control. Benign controls are C08, C10 and C15; non-AI strategic controls are C11–C15. The taxonomy separates commitments, actual funding, contingent support, realized receipts, capacity and utilization. None is automatically a decision-time repeated-choice predictor; retrospective support observations cannot supply missing pricing, feasible alternatives or a locked rich-M2 output. [E1]

## 4. Recomputed comparison

### Own coverage: informative about participation, not a league table

| Frozen model | Coverage of 24 primary episodes | Correct 1m | Correct 3m | Correct 6m |
|---|---:|---:|---:|---:|
| M0 literal rhetoric | 9/24 | 5/9 | 8/9 | 6/9 |
| M1 automatic inversion | 5/24 | 0/5 | 0/5 | 0/5 |
| M2-min actions plus floor | 11/24 | 6/11 | 10/11 | 7/11 |
| C0 always HOLD | 24/24 | 20/24 | 15/24 | 10/24 |
| C1 action only | 11/24 | 5/11 | 9/11 | 6/11 |

M2-min's 10/11 versus M0's 8/9 at three months compares different episodes. Its three extra episodes are July 2019, March 3 2020 and December 2021; M0's one extra episode is Jackson Hole 2022. The union of their covered primary episodes is 12, their intersection eight. [A2–A5]

### Comparisons on identical episodes

| Comparison | Common episodes | Correct 1m, left vs right | Correct 3m | Correct 6m |
|---|---:|---:|---:|---:|
| M0 vs M2-min | 8 | 4/8 vs 4/8 | 7/8 vs 7/8 | 5/8 vs 5/8 |
| M2-min vs M1 | 4 | 0/4 vs 0/4 | 3/4 vs 0/4 | 3/4 vs 0/4 |
| M0 vs M1 | 5 | 1/5 vs 0/5 | 4/5 vs 0/5 | 4/5 vs 0/5 |
| M2-min vs C0 | 11 | 6/11 vs 10/11 | 10/11 vs 6/11 | 7/11 vs 3/11 |
| M2-min vs C1 | 11 | 6/11 vs 5/11 | 10/11 vs 9/11 | 7/11 vs 6/11 |

The M0/M2-min intersection is December 2018 FOMC, January 2019 FOMC, March 15 2020 easing, November 2021 taper, March 2022 liftoff, June 2022 hike, March 2023 bank-stress hike and May 2024 QT taper. The all-three intersection contains only the four UP-coded hike cases: December 2018, March 2022, June 2022 and March 2023. M1 has no clean DOWN-guidance cases to invert into UP; its sample therefore does not cover general inversion behavior. All three are wrong when the one-month outcome is HOLD. [A2–A5]

The only C1/M2-min disagreement is March 15 2020: C1 mechanically persists a cut; M2-min respects a conventional 0–0.25% floor and forecasts HOLD. This contributes exactly one correct observation per horizon, **1/11 = 9.09 percentage points**, not three independent successes. Removing the pandemic regime removes the entire gain. Literal HOLD guidance already captures that episode. [A1–A3]

### Source-defined family slices

These are the original casebook labels, including the broad `US_FED_TREASURY` label; PB-G does not silently recode them as homogeneous economic instruments. Entries show **correct / scored**, in 1m;3m;6m order. “—” means no scored forecast, never a zero-percent success rate.

| Original A family | Primary rows | M0 own coverage | M1 own coverage | M2-min own coverage | M0/M2-min matched result |
|---|---:|---|---|---|---|
| `US_FED_POLICY` | 8 | 2/3; 2/3; 2/3 | 0/1; 0/1; 0/1 | 3/5; 4/5; 4/5 | Both 2/3 at every horizon |
| `US_FED_TREASURY` | 8 | 3/6; 6/6; 4/6 | 0/4; 0/4; 0/4 | 3/6; 6/6; 3/6 | Both 2/5; 5/5; 3/5 |
| `FED_TREASURY_EMERGENCY_CREDIT` | 1 | — | — | — | — |
| `FED_TREASURY_EMERGENCY_CREDIT_WITHDRAWAL` | 1 | — | — | — | — |
| `TREASURY_FINANCING_AND_MARKET_FUNCTION` | 5 | — | — | — | — |
| `TREASURY_BUYBACK_EXECUTED_ALLOCATION` | 1 | — | — | — | — |

The same table applies numerically to both A policy targets because their observed labels coincide. It does not supply independent corroboration. No M0/M1/M2 family score is available for Treasury financing/credit/allocation, the ten B source-family categories or E dossiers. C0's rate HOLD comparator on a Treasury event is a Fed-rate base-rate benchmark; it is not a forecast of Treasury issuance, buyback execution or financing cost. [A2–A4; B1; E1]

### Probability and uncertainty limits

Every forecast puts 0.6 on its coded class and 0.2 on each alternative. For accuracy `a`, multiclass Brier is `1.04 − 0.8a`, while negative log loss is `log(5) − a·log(3)`. They are algebraically linked summaries. Equal directions on equal rows imply equal scores; probability rescaling cannot manufacture an M2 gain. These numbers are not calibrated behavioral confidence, and a calibration slope is unavailable. [A1–A2]

The original four-regime resampling summaries remain descriptive, not population confidence intervals. The 2023–24 chronological slice was also reconstructed after outcomes existed; its two M2-min three-month successes do not form an unseen holdout. A's post-score ±7-day endpoint diagnostic preserves the M0/M2 tie but removes the small one-month M0/M1 difference under the −7-day shift. Keep it labeled exploratory; it does not justify changing primary endpoints. [A1]

## 5. Direct answers to all seven PB-G Phase 2 questions

1. **Does M2 beat M0?** No demonstrated advantage for the tested M2-min: identical forecasts and exact ties on eight common episodes at all three horizons. Rich M2 is **untested**, so its incremental value is neither established nor falsified. Different own-sample accuracies cannot answer this question. [A1–A5; F1 A01–A02]

2. **Does M2 beat M1?** M2-min beats inversion **descriptively at 3m and 6m** on their four common primary cases, 3/4 versus 0/4; they tie at 1m, 0/4. M0 attains the same 3/4 result on that intersection. This result supplies no preference-inference advantage and no broad claim across statements, regimes or countries. [A2–A5]

3. **Where does M0 beat M2?** In the deliberately separate **June 14 2023 pause challenge**, literal UP guidance is correct at 3m/6m while action-persistence HOLD is wrong; at 1m the relationship reverses. This is one selected counterexample to universal action dominance, not a pooled primary effect. Jackson Hole is additional M0 coverage while M2-min abstains, not a matched victory. No primary common-case M0/M2 disagreement exists. [A1–A4; F1 A06]

4. **Where does inversion work?** No successful primary inversion episode is demonstrated: 0/5 at each horizon, plus 0/1 in the separate challenge. All five primary literal directions are UP. December 2018 shows why failed literal guidance is not automatically successful inversion: the realized direction is HOLD. The evidence cannot determine where inversion works on dovish communication or estimate its population efficacy. [A1–A5; F1 A03]

5. **Which actors, institutions or statement types are most predictable?** No defensible actor/institution ranking is available. The scored outcomes are Fed-rate targets; B has no scored BOJ predictions and Treasury/financial-support rows lack corresponding policy forecasts. Descriptively, the four literal HOLD cases score 4/4 at 1m/3m and 2/4 at 6m; the five literal UP cases score 1/5, 4/5 and 4/5. The horizon and base rate materially change the appearance of predictability. Exact institutional actions and operational implementation can be verified more directly than motives, but that documentary advantage is not demonstrated forecast superiority. [A1–A4; B1]

6. **Is the gain from richer information rather than revealed-preference reasoning?** The only measured constraint gain is the conventional-floor adjustment over C1 in one pandemic episode; M0 already encodes its HOLD outcome. There is no independent estimate of a rich-information gain or of preference reasoning holding information constant. A2 excludes contemporaneous pricing, repeated adverse-cost choices, feasible alternatives and distributional prose from the pure predictor. Future inference requires both incremental-information ablations and an equal-information institutional comparator. [A1–A2; F1 A02/A13]

7. **Does performance survive excluding famous or hand-seeded episodes?** This has not been shown. All 24 primary A episodes are purposively selected; excluding every hand-selected episode leaves **zero** primary episodes. No prespecified famous-event partition or complete candidate universe supplies an unseeded alternative. B and E are also purposive. Regime deletion and the retrospective chronological slice do not repair this selection. Do not create a favorable fame exclusion after seeing results. [A1/A4; B1; E1; F1 A07–A09/X06]

## 6. Forward-only methodology amendment

**Amendment status:** PB-G research design; not activated, no prospective enrollment and no implementation authority. This amendment changes interpretation and the next study contract, not historical facts or scores.

1. **Keep two named quantitative models.** Preserve the original JSON key `M2` with a synthesis alias `M2-min`. Reserve `M2-rich` for the unimplemented commissioned model. Never replace A's values or claim B's null objects became predictions because A was scored retrospectively. Preserve A's challenge and E's control labels.

2. **Admit comparisons by an explicit compatibility key.** Require common policy instrument/target transformation, actor/decision event, decision cut, horizon, probability semantics, cohort definition, outcome availability, information permissions and coverage rule. Family labels alone are insufficient. B's next-meeting target stays separate from A's calendar endpoints. Any future harmonized target is a new prospective specification; an exploratory historical re-score must retain the originals and cannot be called a historical forecast.

3. **Freeze the candidate denominator before outcomes.** Enumerate scheduled and qualifying unscheduled decisions under existing source/event owners, with a prespecified missing-source/unknown state, negative/control periods and inclusion cut. Predefine fame/hand-selection flags from an external rule before scoring. Show the complete excluded and unclassified denominator. The intended 40–60 cases must be genuinely eligible cases, not a target achieved by combining slots, dossier edges, repeated snapshots, horizons or the challenge. A nominal 40–60 floor does not establish power.

4. **Lock targets and horizons independently of outcome success.** Register primary horizon, policy direction/level, change-versus-meeting distinction, non-rate implementation targets and market surprises separately. Archive pre-cut pricing for pricing-based comparators. Show what was already decided, what was operationally effective and what could change afterward. Freeze date/minute precision and source version; an updated page cannot retroactively certify earlier information.

5. **Separate information quantity from interpretive method.** Retain literal M0, inversion M1, no-change C0, action-only C1 and legacy M2-min. For M2-rich, predefine admissible prices/market expectations, macro/institutional information, observed costs, repeated actions, feasible alternatives and selective relief. Compare cumulative feature ablations and an equally informed institutional/reaction-function baseline using comparable model capacity and forecasting budget. Only the same-information comparison can test an additional predictive contribution associated with preference reasoning; predictive improvement still would not identify private motive causally.

6. **Treat abstention and probabilities honestly.** Report common-coverage comparisons and own-coverage participation separately, with fixed missingness and any prespecified selective-risk tradeoff. Never score an abstention as HOLD, zero, a correct prediction or a calibrated uncertainty estimate. Use directional metrics as the clear primary description while probabilities remain fixed research conventions. If estimated probabilities are introduced, freeze fitting/calibration data and evaluate only on separate held-out/prospective outcomes; no post-score probability repair of A or B.

7. **Specify dependence and inference before accrual.** Preserve underlying event, target meeting, policy process, source root, issuer/program and horizon clusters. Repeated B cuts can be a time-updating research series but share their endpoint. Agree in advance on common-support units, primary estimand, minimally useful effect, dependence-aware interval method, multiple-comparison allocation and precision/stopping criteria. Run feasibility/coverage checks before claiming nominal sample counts support inference.

8. **Preserve correction lineage and the original as-known record.** Record amended facts, cause and effective availability as new versions linked to the prior record under existing owners; an amendment never silently rewrites earlier predictions or their eligible inputs. Keep original and amended cohort outputs separate. Do not activate a score, rank, entry, size or alert consumer from this synthesis.

This is the smallest honest repair: complete the current integration with **precise data insufficiency**, carry the verified descriptive findings forward, and propose a separately authorized matched-data evaluation. Reconstructing null historical forecasts after observing their outcomes would not cure the missing confirmatory evidence.

## 7. Completion boundary and remaining obligation

**Completed for PB-G Phase 2:** immutable denominator census; exact A forecast/outcome arithmetic; target and source-family distinctions; B abstention and shared-target proof; E taxonomy incompatibility; all seven required answers; explicit methodology amendment preserving historical inputs; research-authority boundary.

**Not completed by these returns:** a compatible 40–60-episode rich-M2 study, representative actor/statement ranking, equal-information preference-reasoning test, unseen/future validation, calibrated probabilities, market-price surprise comparison, causal intent identification or production promotion. Those are enumerated scientific/data gaps, not reasons to fabricate a larger historical score table or leave this bounded synthesis unfinished.
