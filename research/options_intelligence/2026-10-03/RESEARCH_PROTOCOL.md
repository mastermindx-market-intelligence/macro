# Incremental-value research protocol

**Status:** research governance and promotion contract. The exact six-pilot [Markdown specification](PILOT_STUDY_SPEC_V1.md) and [JSON companion](pilot-study-spec.v1.json) are accepted for bounded research engineering under [PRINCIPAL_DECISIONS_20261003.md](PRINCIPAL_DECISIONS_20261003.md). Their frozen design is not sealed empirical preregistration, an owner/source/power pass or predictive authority. The source/dataset/date and acceptance bindings remain required before an empirical run. “Registered” below describes that future state unless an existing study is explicitly identified. Historical hashes inside the frozen specification/reviews continue to identify their original input versions and are not rewritten by this integration.

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

Before outcome inspection, bind and commit the complete packet: operation/owner and hypothesis; source/dataset manifest and availability class; frozen population rule and missingness policy; feature definitions and exact implementation hash; primary target/horizon; train/validation/test dates and maturity boundaries; transforms; baseline and augmented models; repeated-test family; cost/latency/execution assumptions; decision rule; success/kill criteria; and report schema. For v1, ordinary algorithm and evaluation choices are already fixed by the accepted pilot specification; implementations cannot choose alternatives when filling the remaining evidence bindings.

Keep one confirmatory primary endpoint/horizon per pilot family. Secondary endpoints are diagnostics with their own accounting, not a route to relabel a failed primary result as success. Register changes as new versions with the reason, preserving prior results. Use the existing options-history and candidate evaluation owners; a new registry, generic scoring service or alternate promotion route is unnecessary.

### Pilot-specific primary questions

| Pilot | Accepted engineering primary; empirical gates remain | Diagnostic comparisons |
|---|---|---|
| P1 attention/quality | OIF01 next-30-minute exact log high/low range; B2-RI versus B1-RI squared loss. Discovery precision at fixed capacity is a separate utility study. | Activity/quality/coverage diagnostics as frozen in v1; broader control challenges remain separate |
| P2 signed delta | OIF04 next-30-minute market/sector-residual log return; B2-RI versus B1-RI squared loss under the exact as-of residual-label algorithm. | Package/unknown mass, quote timing and quality diagnostics; multi-session variants queued |
| P3 IV/physical-variance residual | OIF19 matched-20-session ACT/365F variance; the fixed positive B2-RI mapping versus positive B1-RI, evaluated with QLIKE. | OIF20 remains separately queued; fixed sampling/coverage/event diagnostics; expression utility separately |
| P4 carry-aware relative pricing | OIF22 five-session residual log return after a one-session skip from Friday formation; B2-RI versus B1-RI squared loss. Borrow/carry qualifications are required. | Raw spread on identical pairs, low-fee and borrow-missing cohorts; broader private-information claims require stronger controls |
| P5 hedge scenarios | Numerical qualification first; one fixed inventory/shock OIF13 scalar adds to B1-RI for next-10-minute variance QLIKE. | Inventory/shock alternatives are diagnostics, not selected primaries; missing ETF incumbent receipts block forecasting only |
| P6 contract quality | Actual 60-second full-fill implementation-shortfall MAE, B2-RI versus B1-RI, strictly conditional on independently observed complete fills and fees. | Quote coverage and simulated hedged markouts are diagnostics; partial/no-fill/missing records remain separate outcomes |

Exact price sampling/annualization, baseline adapters, losses, formation rules, training/cross-fitting, screening margins, deterministic resampling, power planning and numerical refusal are fixed by the pilot specification. Actual empirical dates, causal data/snapshot receipts, dataset manifests, owner acceptance and power feasibility remain unbound. P6 explicitly supersedes the catalogue's previous coverage-plus-simulated-markout primary: that original endpoint is retained in the catalogue's disposition record as diagnostic history. No empirical success or production-policy utility follows from this design adoption.

For P3, sqrt(E[RVar_H]) is not E[RVol_H]. OIF19 has volatility units; OIF20=IV²-vhat has variance units and equals OIF19×(IV+sqrt(vhat)), so the two are related but not interchangeable regressors. A negative OIF19 is valid. The accepted mapping is `v_B2-RI=v_B1-RI*exp(beta*z19)`, with beta in [-1,1], training-only scaling, no extra intercept or second smear, and beta=0 exactly B1-RI. The specification fixes its solver and finite-value refusals. QLIKE evaluates positive variance forecasts against nonnegative matched ACT/365F realized variance, including zero; it never scores the residual itself. Positive mapping is now a design decision, while data/fit qualification and empirical registration remain gates.

## 4. Point-in-time population and temporal splits

For P1–P4, freeze the rule, not today's constituents: US common stocks in the latest causally consumer-admitted incumbent buy-pool revision at formation, then the exact v1 source/liquidity/quote/contract/history qualifications. Preserve full eligible/failed census, revision/population digests, source ages and selection lineage. Unknown revision/receipt or all-missing incumbent covariates is unavailable, not confirmed absence. P5's fixed ETF scenario population and P6's existing authorized order/plan population remain distinct and still need genuine covariate receipts for forecasting. Report broader and qualified counts; no options feature gains by silently removing difficult names from its baseline. A broader fixed-root B0 feasibility lane is separately labelled and cannot establish incumbent outperformance.

For P1 and other discovery tests, define how outcomes will be observed for candidates that the old policy never selected for review. When the target is objectively calculable from authorized market data, apply the same label rule to the full frozen eligible population. If the target depends on human review or discretionary follow-up, use a prespecified blinded/random audit sample with known selection probabilities, or restrict the claim to the labelled population. Fixed review capacity alone does not remove selective-label bias. Unreviewed is not a negative label.

For each observation record decision time, all input availability/revision references, label end and maturity times, overlapping candidate/exposure groups, and dataset mode: captured PIT versus reconstructed history. OI and late/corrected prints obey their availability; later earnings surprises and calendar revisions are not formation inputs. All joined stock/option/borrow/catalyst features require matched time semantics.

Use time-ordered evaluation. V1 permits only its frozen algorithms: training-only transforms/fits, nested as-of/held-out B0 and B1-RI forecasts, mature labels and exact overlap purging. It does not add imputation, winsorization, model search or validation-driven hyperparameter selection. Validation supports pipeline/domain audits and pretest power planning; no post-validation refit is allowed in v1. Every label used at any fitting/planning stage must mature before that stage's cutoff, including the H20 validation tail before the test seal. Broader future designs must separately freeze any tuning/calibration and embargo rather than relying on an arbitrary gap.

Cross-sectional observations share market events. Cluster or resample calendar blocks jointly across roots; use additional symbol clustering where justified. For intraday data, a print is not an independent experimental unit. Group repeats/packages/candidates and preserve day/regime blocks. For overlapping multi-session labels, use a registered HAC/block-bootstrap design and report effective independent counts. Choose block lengths from the horizon/dependence argument, with sensitivity fixed before final evaluation.

Reserve untouched later data for the final test. Existing 2017–2025 results have already been inspected and cannot be relabelled as an untouched holdout. Fresh forward capture is therefore especially valuable, subject to the active producer's source-preserving recovery. A short natural-session pilot proves data integrity; it is not automatically enough statistical power to validate alpha.

## 5. Baselines and comparisons

Compare on identical eligible rows, with upstream feature and selection lineage audited:

1. **B0: each pilot's exact options-free-input research comparator**, subject to upstream lineage audit. It is not a claim about today's Prophet and is evaluated on the same selected cohort.
2. **B1-RI: the fixed incumbent-information research adapter in specification Appendix A.** It adds a small, causal receipt-derived score/stage/missingness/age vector to the same B0 target algorithm, using only qualified historical training forecasts and mature labels. A rank never directly becomes a variance or return forecast.
3. **B2-RI: that fixed B1-RI plus one specified OIF coefficient.** Its primary estimand is added loss improvement over the accepted summary-information adapter. Improvement over B0 is a distinct diagnostic.
4. **Wider actual-production-policy incrementality remains separate and unsatisfied.** A later study must compare the actual accepted incumbent policy/model, including all relevant options/GEX lineage, with its qualified augmentation under the appropriate target and policy utility. Beating B1-RI does not establish that result or capture all incumbent raw information.

If the cohort was selected by an incumbent policy that already uses options, removing options columns does not make the population options-free. Report conditional utility for that selected cohort. A broader universe-level claim needs a frozen preselection population and its own evaluation. Source wiring of GEX establishes a possible current contribution; actual runtime influence remains a separate evidence question.

Each fitted baseline and upstream score also needs its own training, revision and historical availability evidence. Applying today's score implementation retrospectively is a reconstruction, not proof that the historical strategy had that score. Use contemporaneously available incumbent snapshots where qualified; otherwise label the baseline reconstruction and limit the operational claim accordingly.

Do not give the augmented model an unrestricted search budget and call the difference “options information.” V1 fixes one additional OIF coefficient and its fit domain; it does not claim complete confounder adjustment merely because required quality controls are retained as eligibility rules/diagnostics. Stronger conditional-information claims need a separately accepted common-nuisance design. For IV spread/skew, borrow fees, dividend/carry and exercise conventions remain mandatory challenges. Missing borrow data are a limitation, not imputed evidence of zero fee.

Use each v1 feature's exact normalization and training scope from the specification; no generic log-activity transform replaces OIF01's declared raw ratio or P6's raw relative spread. Preserve raw units, normalized values, coverage, sample counts and zero-MAD/insufficient-history states. Queued alternatives require a new registered version rather than substitution during implementation.

Feature interactions are limited and preregistered: for example signed flow × catalyst state, variance gap × term/event state, or assumed gamma state × liquidity. A failed marginal feature does not license unlimited interaction searches. Count all variants and retain a discovery-versus-confirmatory distinction.

## 6. Metrics that match the question

For return forecasts, report incremental rank/linear association, loss and directional calibration only if a probability target is used. For adverse events, report log loss/Brier score, reliability, precision/recall at a frozen intervention budget, and false-veto cost. For variance/range, use a suitable strictly defined forecast loss and unit conventions; include economically interpretable error. For ranking, use fixed-capacity utility and paired comparisons; report turnover and coverage.

For monitoring, measure lead time, recall before adverse excursion, repeated alerts per candidate, time under warning, missed events and false exits/vetoes. A high hit rate with many repeated warnings is not useful by itself. Notification cooldown controls duplicate messages, not sequential false discovery. Freeze the evaluation of repeated looks or aggregate to a defined candidate/window.

For scenario tools, report numerical error, convergence, partial coverage and sensitivity to assumptions. Predictive tests of scenario-state features are separate. For option economics, report mark convention, spread/fees/slippage, latency, assignment/exercise/expiry treatment, maximum adverse/favorable excursion, missing outcomes and liquidity/size stress. Do not replace option outcomes with underlying returns or expiry diagrams.

Estimate paired changes with intervals. V1's screening margins, date/root/slot weights, deterministic calendar-block procedure and power-planning algorithm are fixed in the accepted specification; those margins are not validated economic utility. The principal's minimum 20 primary calendar blocks sets validation to 400 formation sessions for P3/P4 and 100 for the others. This is a data-gated design constraint, not power proof. Unstable/no-support planning returns POWER_UNRESOLVED; infeasible required test length is not quietly capped and declared sufficient.

## 7. Multiplicity, leakage and adversarial checks

V1 fixes six primary hypotheses and Holm familywise .05, with blocked/unrun/invalid pilots retaining p=1. Its exact centered-bootstrap tail, interval and seed conventions are in the frozen specification. Report nominal and adjusted evidence and the dependence assumptions; bootstrap intervals are not an exact finite-sample guarantee. Existing BH results belong to their original family and do not cover this catalogue. Deployment claims still need untouched evaluation and policy-specific evidence beyond multiplicity accounting.

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

Ready now: accepted finite research engineering design, evidence-to-feature mapping, exact formulas/units, fixture requirements, source/correction/clock census, borrow-data feasibility assessment and active-carrier reconciliation. Existing owners can implement the bounded specification; design acceptance does not certify an implementation or empirical fit.

Still owed before a confirmatory run: actual capability/runtime/entitlement and source-coverage receipts; causal historical board/covariate and nested forecast records; final dataset and split-date manifests under the now-fixed population/endpoint rules; required borrow source; untouched evaluation span and power assessment; actual fill/fee records for P6; incumbent owner acceptance and sealed empirical registration. These dependencies do not justify inventing data, rerunning completed studies or changing production policy early.
