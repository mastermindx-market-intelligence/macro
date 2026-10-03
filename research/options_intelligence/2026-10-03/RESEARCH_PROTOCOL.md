# Incremental-value research protocol

**Status:** proposed frozen-study template and promotion contract. This PR neither fits models nor activates scoring. The concrete dataset/feature/endpoint specification must be frozen and reviewed by the incumbent research owner before running each new empirical packet. “Registered” below describes that required future state unless an existing study is explicitly identified.

## 1. Preserve the completed October 2 study

Read the canonical [retrospective report](../../../reports/artifacts/options_theta_retrospective_20261002.md) and [merged PR #8286](https://github.com/mastermindx-market-intelligence/macro/pull/8286). The study evaluates 10 contrasts × 3 eras × 2 horizons: 60/60 cells, using eras 2017–2019, 2020–2022 and 2023–2025 and 5/21 NYSE-session horizons. Its 20 nominal scored roots have 18 usable price histories; SPY is a benchmark and SPX/SPXW are coverage-only. Of 435 expected inputs, 429 are present and six missing.

| Existing association | Exact reported evidence | Claim ceiling |
|---|---|---|
| Normalized GEX versus forward realized volatility, Era 1, H5 | Mean IC −0.105245; q≈0.00000389631 | Within-run historical association; does not repeat in Eras 2/3 |
| Same contrast, Era 1, H21 | Mean IC −0.114298; q≈0.0289418 | Overlapping labels and limited independent time blocks matter |
| Matched IV spread versus SPY excess return, Era 3, H21 | IC +0.063404; HAC 95% interval [0.0202773, 0.106531]; q≈0.0802663 | Borrow/carry, historical availability and untouched OOS remain unresolved |

Three cells reject at the study's BH alpha .10; none supplies a result across all three eras. Other registered vanna/charm/relief/spread-change/skew/term/OI/momentum contrasts do not reject in that family. At the 21-session horizon, the report has roughly 33–34 independent blocks per era; the raw daily row count overstates independent evidence. Earlier 36-cell episode-proxy work is a different study and must not be pooled as if it were a replication of these cells.

Frozen identities: protocol SHA256 `67011db3d3aed08827f027cafc5b5a2bf890289a1017b227cad15fc240826e68`; result `7af1b1ae1c871892384388695d17977cea1a6b6aa4fd21fc1625b5dad55073f3`; manifest `6b678a65f531eb31735cca7641b898887739475a9c1a479c2a0ebbecd8a164dc`. Root inspected the report and current merge metadata; this commission did not independently rerun the full raw data. Existing verification receipts remain attached to their owners.

The next work is an evidence-to-feature mapping and targeted unresolved tests. Do not rerun these 60 cells merely because the new master plan exists. Do not interpret a q-value as the probability that an individual forecast is correct, a global catalogue discovery guarantee, or evidence of profitable option execution.

## 2. Claims ladder

| Level | Required evidence | Permitted conclusion |
|---|---|---|
| O. Observation | Exact contract, input clocks, source/condition/correction identity, completeness and retained unknowns | Descriptive activity, prices and coverage |
| N. Numerical model | Units, clock/model inputs, independent calculations, finite differences and convergence | Correct output for stated assumptions |
| A. Association | Registered historical test, baseline/confounders, uncertainty and multiplicity | Association in the stated sample |
| P. Incremental prediction | Untouched out-of-time comparison on matched eligibility, dependence-aware uncertainty and stability | Added predictive information at the tested horizon |
| D. Decision utility | Frozen policy/loss function, calibrated forecasts, false-action/false-veto cost and operational coverage | Improvement in a specified decision workflow |
| X. Executable economics | Exact contracts, availability, latency, fills/cost assumptions, exercise and missing-outcome accounting | Bounded simulated or observed economics, labelled accordingly |

Production authority additionally requires the incumbent review/release process. Numerical correctness does not establish actual inventory; association does not establish causality; predictive improvement does not establish option P&L. Levels need not be a single score. P6 execution research can improve cost measurement without a directional prediction claim.

## 3. The frozen study packet

Before outcome inspection, commit: operation/owner and hypothesis; source/dataset manifest and availability class; frozen universe and missingness policy; feature definitions and exact code hash; primary target/horizon; train/validation/test dates and embargo; transforms and hyperparameter budget; baseline and augmented model specifications; repeated-test family; cost/latency/execution assumptions; decision rule; success/kill criteria; and the planned report schema.

Keep one confirmatory primary endpoint/horizon per pilot family. Secondary endpoints are diagnostics with their own accounting, not a route to relabel a failed primary result as success. Register changes as new versions with the reason, preserving prior results. Use the existing options-history and candidate evaluation owners; a new registry, generic scoring service or alternate promotion route is unnecessary.

### Pilot-specific primary questions

| Pilot | Initial primary test to freeze | Diagnostic comparisons |
|---|---|---|
| P1 attention/quality | Proposed OIF01 primary: next-30-minute realized range after the eligible consumer decision, versus the actual incumbent target-specific baseline. Discovery precision at fixed capacity is a separately specified utility study. | Activity alone; same-time stock volume/volatility; event-conditioned and quiet sessions; excluded/unknown prints |
| P2 signed delta | Proposed OIF04 primary: next-30-minute residual return after the eligible consumer decision, over the actual incumbent B1 model using B2-versus-B1. Freeze the return/benchmark construction in the empirical packet. | Premium-only, unsigned flow, high-quality sign subset, package exclusions, underlying lead/lag; multi-session variants queued |
| P3 IV/physical-variance residual | Proposed OIF19 primary: improve a matched-20-session realized-variance forecast. The feature is ATM IV minus sqrt(vhat_P,H), where vhat forecasts expected variance; QLIKE scores a separately specified positive augmented variance forecast. | OIF20 variance residual separately queued; trailing variance, event/calendar model, IV alone, jump components; expression utility separately |
| P4 carry-aware relative pricing | Proposed OIF22 primary: next five-session return after a one-session skip from the qualified weekly formation, after borrow/carry/event controls. Adverse-excursion studies are separately registered. | Raw IV spread, low-fee subset, borrow-missing cohort, synchronized versus stale quotes, maturity buckets |
| P5 hedge scenarios | First pass: repriced book delta satisfies numerical/unit/clock invariants. Later separate proposed primary: a fixed scenario-state feature improves next-10-minute realized-variance forecast. | Inventory-sign alternatives, opening inventory versus fresh flow, spot/IV/time rule sensitivity |
| P6 contract quality | First establish deterministic quote/cost arithmetic and explicit simulation assumptions. Independently test forecast execution costs only against observed fills with separate calibration/evaluation samples. | Midpoint versus crossing quotes, latency/size stress, underlying/option/defined-risk alternatives, missing exits; simulated costs are sensitivity scenarios, not independent validation labels |

The horizons and target families above are concrete design proposals aligned with the catalogue. Exact price sampling/annualization, baseline/loss, the positive P3 forecast mapping, universe, dates and acceptance effect sizes remain empirical packet fields to freeze before outcomes. The catalogue's detailed computations do not themselves constitute an accepted study registration.

For P3, sqrt(E[RVar_H]) is not E[RVol_H]. OIF19 has volatility units; OIF20=IV²-vhat has variance units and equals OIF19×(IV+sqrt(vhat)), so the two are related but not interchangeable regressors. A negative OIF19 is valid. QLIKE must evaluate a strictly positive predicted variance, never this residual directly. Specify the augmented mapping and training/calibration before testing, and use a common actual-horizon annualization/day-count or an explicit conversion between trading-time and calendar-time scales.

## 4. Point-in-time population and temporal splits

Construct candidate observations from the incumbent decision stream, preserving rejected/missing cases where the authorized data allow it. Freeze the eligible universe and define whether the estimand concerns all underlying candidates, options-covered candidates or a liquid-contract cohort. Report all three population counts where available. An options feature cannot claim improvement by silently excluding difficult names from its comparison baseline.

For P1 and other discovery tests, define how outcomes will be observed for candidates that the old policy never selected for review. When the target is objectively calculable from authorized market data, apply the same label rule to the full frozen eligible population. If the target depends on human review or discretionary follow-up, use a prespecified blinded/random audit sample with known selection probabilities, or restrict the claim to the labelled population. Fixed review capacity alone does not remove selective-label bias. Unreviewed is not a negative label.

For each observation record decision time, all input availability/revision references, label end and maturity times, overlapping candidate/exposure groups, and dataset mode: captured PIT versus reconstructed history. OI and late/corrected prints obey their availability; later earnings surprises and calendar revisions are not formation inputs. All joined stock/option/borrow/catalyst features require matched time semantics.

Use time-ordered evaluation. Fit transforms, imputation, winsorization, norms, feature selection and models only on admitted training information; tune/calibrate using the designated preceding validation/calibration data. Every label used for fitting, tuning, selection or calibration must have matured and become available before the model freeze and first test decision. This includes labels from the end of the validation slice: an H21 label extending into the test period cannot be used to choose that test's model. Remove training observations whose label windows overlap validation/test, and fence validation/calibration boundaries by the same information-availability rule. Add a declared embargo appropriate to information/label overlap; do not let an arbitrary small gap substitute for full overlap analysis.

Cross-sectional observations share market events. Cluster or resample calendar blocks jointly across roots; use additional symbol clustering where justified. For intraday data, a print is not an independent experimental unit. Group repeats/packages/candidates and preserve day/regime blocks. For overlapping multi-session labels, use a registered HAC/block-bootstrap design and report effective independent counts. Choose block lengths from the horizon/dependence argument, with sensitivity fixed before final evaluation.

Reserve untouched later data for the final test. Existing 2017–2025 results have already been inspected and cannot be relabelled as an untouched holdout. Fresh forward capture is therefore especially valuable, subject to the active producer's source-preserving recovery. A short natural-session pilot proves data integrity; it is not automatically enough statistical power to validate alpha.

## 5. Baselines and comparisons

Compare on identical eligible rows, with upstream feature and selection lineage audited:

1. **B0: an explicitly options-free research comparator**, using qualified price/volume/technical/regime/catalyst inputs. This is a constructed comparator, not a claim about today's Prophet.
2. **B1: the actual accepted incumbent decision/model**, including any existing options contribution such as admitted GEX in C1 fusion. Freeze its code, inputs, admission rules and model version.
3. **B2: that same B1 plus one proposed options family.** Improvement over B1 is the primary incremental-to-Mastermind estimand; improvement over B0 answers the distinct question of information beyond an options-free feature set.
4. Options family alone and a simple target-appropriate benchmark, as registered diagnostics for redundancy and stability.

If the cohort was selected by an incumbent policy that already uses options, removing options columns does not make the population options-free. Report conditional utility for that selected cohort. A broader universe-level claim needs a frozen preselection population and its own evaluation. Source wiring of GEX establishes a possible current contribution; actual runtime influence remains a separate evidence question.

Each fitted baseline and upstream score also needs its own training, revision and historical availability evidence. Applying today's score implementation retrospectively is a reconstruction, not proof that the historical strategy had that score. Use contemporaneously available incumbent snapshots where qualified; otherwise label the baseline reconstruction and limit the operational claim accordingly.

Do not give the augmented model a larger unrestricted search budget and call the difference “options information.” Match model capacity/tuning budgets or explicitly account for the difference. Include contemporaneous and lagged stock moves, stock volume, realized volatility, liquidity, beta/regime and known catalysts where appropriate. For IV spread/skew, borrow fees, dividend/carry and exercise conventions are mandatory confounder challenges. Missing borrow data are a separate observed limitation, not imputed evidence of a zero fee.

Normalize activity by root and the same time of day/session bucket using only trailing training information. An initial robust candidate is median/MAD normalization of log(1+activity), with explicit zero-MAD/insufficient-history states. This is a proposed transform to compare with simpler ratios, not a known optimal model. Preserve level, normalized value, coverage and bucket sample count. For rolling studies, update only according to the frozen refit schedule.

Feature interactions are limited and preregistered: for example signed flow × catalyst state, variance gap × term/event state, or assumed gamma state × liquidity. A failed marginal feature does not license unlimited interaction searches. Count all variants and retain a discovery-versus-confirmatory distinction.

## 6. Metrics that match the question

For return forecasts, report incremental rank/linear association, loss and directional calibration only if a probability target is used. For adverse events, report log loss/Brier score, reliability, precision/recall at a frozen intervention budget, and false-veto cost. For variance/range, use a suitable strictly defined forecast loss and unit conventions; include economically interpretable error. For ranking, use fixed-capacity utility and paired comparisons; report turnover and coverage.

For monitoring, measure lead time, recall before adverse excursion, repeated alerts per candidate, time under warning, missed events and false exits/vetoes. A high hit rate with many repeated warnings is not useful by itself. Notification cooldown controls duplicate messages, not sequential false discovery. Freeze the evaluation of repeated looks or aggregate to a defined candidate/window.

For scenario tools, report numerical error, convergence, partial coverage and sensitivity to assumptions. Predictive tests of scenario-state features are separate. For option economics, report mark convention, spread/fees/slippage, latency, assignment/exercise/expiry treatment, maximum adverse/favorable excursion, missing outcomes and liquidity/size stress. Do not replace option outcomes with underlying returns or expiry diagrams.

Estimate paired changes with intervals. Statistical significance alone is insufficient: record an ex-ante minimum useful effect or decision-loss improvement once stakeholder costs and pilot variance are known. Power calculations must use realistic dependence/effective sample size. If feasible data cannot distinguish the required effect, return “underpowered” instead of optimistic promotion.

## 7. Multiplicity, leakage and adversarial checks

Define the primary family across all pilot features/variants/endpoints before the test. Report nominal and adjusted evidence with the correction and dependence assumptions. BH at a stated level can be a discovery control within its registered family; it does not cover unreported explorations, earlier failed searches or a continually expanding catalogue. Confirmatory deployment claims need replication and untouched evaluation in addition to multiplicity accounting.

Required challenges include:

- Shift option features forward/backward relative to stock inputs to expose timing leakage and contemporaneous reaction.
- Remove future-adjacent quotes and corrected information not then available; compare reconstruction with captured PIT where possible.
- Compare all eligible prints with high-quality and ambiguous subsets, reporting the coverage change.
- Exclude or separately model known catalysts, high-borrow names, complex conditions and illiquid contracts according to the frozen plan.
- Stress reasonable latency, fees, spread and fill assumptions; bound capacity using observed quote liquidity.
- Recompute normalization/selection without test-period data and audit universe survivorship.
- Check results across predeclared eras, market states and roots, including concentration in a few days/names.
- For inventory features, vary participant-sign assumptions and separate starting inventory from new trades.

Placebo/sign/timestamp randomization is a diagnostic with dependence preserved. It is not a substitute for the primary causal design or for genuine future data. All excluded rows and test changes get reason counts and receipts.

## 8. Evidence report and decisions

The completed packet should include data/source manifests, code/environment hashes, feature/label definitions, population waterfall, missingness and coverage, split boundaries, effective sample size, primary/secondary results, intervals and correction, calibration, economics and sensitivity, concentration/regime stability, known limits, and a signed owner/reviewer decision through current procedures.

Allowed conclusions are explicit: **invalid construction**, **unobservable with current fields**, **descriptively useful**, **historical association only**, **underpowered**, **failed incremental test**, **qualified predictive candidate**, or **qualified for a specified policy evaluation**. None automatically activates production. A useful feature can be kept as a scenario/observation after failing predictive tests if its UI claim is narrowed accordingly.

The kill decision should name what would justify reopening: a new observable, a corrected identified defect, a new preregistered mechanism or an independent untouched sample. Repeated tuning of the same null on the same data does not qualify. Keep historical nulls and their source hashes discoverable in the existing program.

## 9. Work that is ready versus still owed

Ready now: evidence-to-feature mapping, exact formulas/units, fixture design, source/correction/clock census, borrow-data feasibility assessment, numerical witnesses, active-carrier reconciliation and frozen-study drafting. Existing data integrity/release owners can consume these requirements.

Still owed before a confirmatory run: actual capability/runtime/entitlement receipt; accepted natural-session source coverage; chosen pilot universe and primary endpoint/horizon; final dataset availability manifest; borrow source or explicit restricted estimand; untouched evaluation span and power assessment; execution/fill evidence appropriate to the claim. These are concrete research dependencies. They do not justify inventing data, rerunning completed studies, or changing production policy early.
