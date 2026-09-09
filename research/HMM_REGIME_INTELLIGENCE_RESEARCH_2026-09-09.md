# Regime intelligence across Mastermind: research and implementation proposal

**Research date:** 2026-09-09. **Author:** Sol. **Status:** research completed at the scope stated below; proposed implementation is **SPEC_ONLY**, not a production release or authority promotion.

**Commission:** investigate the supplied HMM/RL allocation paper and design how Mastermind's neural web and models should understand, anticipate, and respond to regimes. This document preserves ambition across the product without authorizing a new composite regime authority, an unvalidated trading overlay, or a replacement graph/memory/evaluation system.

**Evidence pins:** protected Mastermind skillpack and Brain reader at `686af274d8ae1558f3f3ae35e0b3aae68be80a01`; Macro source inspected and tested at `c3d7f1d4149176e35abf6077c18c96513abe6600`. Main was rechecked at `d220f1127831ea02ed947f8418e05d9fbc7b386c`; the only intervening commit changed marketing data, not the analyzed regime code. Skillpack 1.0.1 / bootstrap major 1 remained compatible on recheck.

**What was actually done:** primary-source literature review; complete reading of the nine-page focal manuscript, including performance tables; pinned source and organizational-record archaeology; one read-only synthetic experiment executing two isolated functions from the actual pinned source. No trading backtest was replicated, no production service was modified, no capital policy was changed, and no implementation worker was dispatched. Existing production capability was not comprehensively re-proven in this review.

## 1. Executive recommendation

Make Mastermind **regime-aware end-to-end**, not **HMM-driven everywhere**.

The useful capability is a coherent answer to: what environment are we in; what changes are plausible at each horizon; which observations support or contradict that view; which existing theses, relationships, and exposures are sensitive to those changes; and what, if anything, has earned permission to change a decision?

The moat is not a particular clustering algorithm. It is the combination of point-in-time observations, correction-safe state estimates, explicit uncertainty, grounded transmission mechanisms, remembered successes and failures, and measured decision usefulness. A regime estimate should make the existing intelligence system more discriminating, not replace it with another market opinion.

Three priorities follow. First, repair historical-probability semantics before promoting historical model performance. Second, extend the existing consumer contract and give a real research workflow access to the resulting context. Third, test incremental predictive and portfolio value against simple, strong baselines before considering reinforcement learning.

This is a research/design proposal. The verified discovery in section 4 does not itself authorize a source takeover, rewrite historical records, reopen killed constructions, or change risk controls.

## 2. What the supplied paper establishes, and what it does not

The focal manuscript is Verma, Putri, and Lesupi, *Regime-Based Portfolio Allocation Using Hidden Markov Models and Reinforcement Learning*, arXiv:2605.27848v1. The manuscript says November 2025; arXiv records submission on 27 May 2026. Its training/test division is chronological, 70/30; the authors state that the HMM is fitted on the training sample. The baseline excludes transaction costs. Reported test-window Sharpe is 0.83 for both RL and monthly equal weighting; maximum drawdown is -23.5% for RL versus -21.8% for the simpler Top-1 rotation. These are reported results, not independently reproduced results. [S01]

### Original analytical assessment

A comparison with an all-equity benchmark does not isolate the contribution of regime inference from diversification, exposure reduction, or a different risk budget. The correct question is not simply whether an allocation chart looks smoother than SPY; it is whether this particular information and policy improve a comparable decision after realistic frictions.

One-day lagging addresses an execution-alignment problem. It does not, by itself, prove that feature transformations, state definitions, parameter fitting, and state decoding excluded future information. The manuscript's references to filtering, Viterbi paths, and smoothed probabilities make the exact trading decoder a replication question. It would be wrong to assert proven full-sample training leakage when the paper explicitly describes train-only fitting.

There is a more fundamental mathematical point. The published decision equation is:

`Q(s,a) = R(s,a) + gamma * sum_s' P(s,s') V(s')`.

Under that written formulation, market transitions depend on the regime, not the portfolio action. If the only state is the regime, and there are no holdings-dependent future costs or constraints, the continuation term is identical across actions. Therefore:

`argmax_a Q(s,a) = argmax_a R(s,a)`.

This deduction is not a claim about unpublished implementation. It means the written objective does not establish a sequential advantage over conditional one-period reward maximization. Different training populations or return alignments could produce different policies without demonstrating added dynamic intelligence.

A genuinely dynamic portfolio problem includes existing holdings, transaction costs, funding or turnover constraints, and possibly wealth/drawdown state. Actions change that portfolio state even when they do not change the market. A fair RL test must beat a simpler constrained policy solving the same problem on the same information and costs.

**Disposition:** retain the research idea; do not treat the paper as proof of a ready-to-deploy Mastermind allocation system. Exact code, data snapshot, adjustment settings, decoder, trading timestamps, reward construction, and trial history remain unverified.

## 3. HMMs, anticipation, and the limits of the infographic

An HMM separates observed measurements from an unobserved discrete state. The measurements might be market returns and volatility, or economic growth/inflation features; those choices define different questions. The model specifies state transitions and state-conditional observation distributions. A Gaussian HMM is one specification, not the definition of a market regime. Standard filtering and Markov-switching implementations are documented in the official hmmlearn and statsmodels materials. [S02, S03]

Three probability objects must remain separate:

| Object | Question | Permitted historical interpretation |
|---|---|---|
| Current filtered state | What state is plausible using information available now? | Valid as an as-issued estimate only when its inputs and model existed by issuance |
| Historical reconstruction | How does a model fitted later interpret an earlier date? | Research/hindsight, explicitly labeled; not a historical trading signal |
| Future state distribution | What states are plausible at a named later horizon? | A forecast that must be issued before the outcome and graded against a declared target |

For a row-vector filtered distribution `p_t`, a fixed row-stochastic transition matrix `A`, and a horizon of `h` model steps:

`p_(t+h | t) = p_t A^h`.

This is not the same as taking the transition row of the single most likely state. The latter discards uncertainty. With time-varying transitions, the forecast requires a product of transition matrices; future covariates must themselves be forecast or supplied as explicit scenarios, not borrowed from realized future data.

A standard homogeneous HMM implies geometric state duration. Conditional on state `k`, its expected duration is `1/(1-A_kk)` model steps. An expected duration is not a countdown, and endpoint probability of being in another state is not the probability of ever leaving and returning during the interval. Explicit-duration semi-Markov models are a legitimate challenger when duration behavior matters. [S04]

Anticipation is possible as a conditional probability forecast. Instant, error-free recognition of a hidden turning point is not promised by the model. Useful evaluation must measure false alarms, detection delay, calibration, and opportunity cost together.

### Correcting the supplied randomness infographic

The valuable lesson is to distinguish decision quality from one realized outcome. But the central limit theorem is not a license to assume that raw returns are Gaussian, stationary, or independent. Financial return distributions and dependence properties are precisely why naive statistical assumptions can fail. [S05]

A displayed 70% must name an event, horizon, information set, and validation basis. An HMM state posterior is not automatically a 70% chance of profitable trading. State entropy, model disagreement, missing-data uncertainty, and predictive outcome uncertainty are different quantities.

Value at Risk describes a loss quantile, not a maximum loss. Expected shortfall adds information about the modeled tail but does not make unmodeled shocks disappear. Kelly sizing requires payoff information and defensible probability estimates; a regime posterior alone supplies neither. These are mathematical interpretation constraints, not new trading instructions.

## 4. New verified finding: reconstructed filtered history is not as-issued history

### Source mechanism

At the inspected Macro commit, `engine/regime_one.py::_causal_filtered_pquad` estimates state means, covariances, transition probabilities, and initial probabilities from the entire supplied frame. It then applies a forward-only recursion across that frame and publishes the final 252 historical probability rows as `history_filtered`.

The recursion is forward-only **conditional on the fitted parameters**. For historical rows, those parameters were estimated using observations that occur later than the row. The output description says each point uses information only up to that date; that is too strong for this reconstructed history. [I01]

The distinction is:

`filter(x_1:t ; theta_fitted_through_T)` is not generally equal to
`filter(x_1:t ; theta_available_at_t)` when `T > t`.

A latest-day fit can still be legitimate if all fitting data were actually available by its issuance. This finding therefore does not prove that today's endpoint estimate is invalid, that any live portfolio used leaked signals, or that every regime-related backtest is wrong.

### Actual experiment and receipt

The test executed only `_causal_filtered_pquad` and `_logsumexp`, extracted by AST from the pinned git object. It imported no other project module, wrote no project data, fitted no real market sample, and used one numerical thread. Environment: hmmlearn 0.3.3; NumPy/Pandas; seed 90210.

A 600-row synthetic prefix was evaluated, then 120 later rows were appended. Earlier input rows were unchanged. Comparing the overlapping portions of the two returned histories produced:

| Quantity | Observed result |
|---|---:|
| Shared historical dates | 132 |
| Dates whose probabilities changed at published precision | 132 |
| Largest absolute probability change | 0.7111 |
| Date of largest change | 2022-11-16 |
| Q1 probability in earlier reconstruction | 0.9013 |
| Q1 probability in later reconstruction for the same date | 0.1902 |

Source-file SHA-256: `7671e86ae2cce28f83a83054ad76c4920638f68a28a92af074dbf28c054d95eb`.

The synthetic 71.11-percentage-point difference demonstrates non-invariance; it is not an estimate of actual financial contamination or lost returns. The reproducible procedure is in Appendix A.

### Consequences for adjacent consumers

`engine/quad_vector.py` already distinguishes current-state probability from future transitions. It publishes `regime_one` probabilities rather than calculating another model. However, its probability momentum uses reconstructed historical probabilities. That quantity can be useful as a diagnostic in today's fitted coordinate system; it should not be described as the exact sequence of previously issued belief changes. Its `confidence = max(p) * axis agreement` is a heuristic, not calibrated probability of being correct. [I02]

`engine/regime_hmm.py` already identifies its smoothed history as hindsight/display-only. That distinction should be preserved rather than deleting useful research charts. [I03]

**Proposed repair:** retain separately labeled reconstruction views, preserve immutable as-issued estimates through the existing owner record, and ensure replay readers refuse to substitute later reconstructions for missing historical issuance evidence. Do not rewrite old records to fabricate a longer prospective track record.

## 5. Existing estate: what to extend rather than rebuild

The following is a source-verified ownership inventory, not a claim that every listed capability was re-proven in production during this review.

| Capability | Existing home | Implication |
|---|---|---|
| Economic labels and informed HMM probabilities | `engine/regime.py`, `regime_hmm.py`, `regime_one.py` | Preserve the current owner; compare challengers behind its contract |
| Stable continuous current P(Quad) contract | `engine/quad_vector.py` | Extend this publisher where appropriate; no second probability truth |
| Canonical risk/context chain | `risk_radar -> market_state -> regime_vector` | No parallel universal regime verdict or gross-control mapping |
| Cross-domain composed context | `engine/neuralweb/world_state.py` | Compose existing owner outputs with gaps and timestamps |
| Regime-conditioned reliability estimates | `engine/neuralweb/kernel.py` | Respect shrinkage, outcome-basis legality, and promotion gates |
| Regime support/contrast admission | `engine/regime_conditioning_coverage.py` | Check the actual target ledger before conditional claims |
| Episodes, retrieval, replay, and corrections | Existing `engine/neuralweb/market_memory*` modules | Extend existing evidence identity and playback; no new memory plane |
| Theme semantics and memberships | GMI theme graph owners | Regimes annotate context; they do not invent theme facts |
| Relationship/propagation hypotheses | K3-D/current relationship owners | Do not infer causation from similarity or membership |
| Downstream transmission/opportunity composition | MarketOntology F04 | No new regime-owned transmission engine |
| Bot-side regime consumption | Mastermind `brain/regime_frame.py` | Extend the sole reader, not each bot's raw-JSON parser |
| Prospective grading and promotion | Existing regime record owner plus Eval OS | No competing clock, maturity resolver, or evaluation ledger |

The inspected `engine/run.py` wires the HMMs, RegimeOne, probability publisher, and accrual path. Wiring is evidence of implementation, not proof of present production freshness or usefulness. [I04]

The inspected `market_memory_operating_cortex.py` is explicitly a synthetic-only structural conformance kernel. It does not prove semantic understanding, learned synthesis, or a live operational forecasting consumer. Connecting regime context to that future capability still requires an authenticated real-input journey and semantic-quality evaluation. [I05]

## 6. Preserve existing negative evidence and authority boundaries

The repository already adjudicated a closely related proposal in `REGIME_RELIABILITY_FACTOR_CROWDING_ADJUDICATION.md`. The particular per-signal-family, market-regime-conditioned forward-drawdown reliability grid was not supported by its measured interaction evidence. Richer regime axes also lacked sufficient contrast in the historical audit. These are scoped findings, not a universal theorem against regime modeling. The old audit's coverage figures must not be represented as a fresh September census. [I06]

The existing coverage gate requires at least 20% axis coverage, two observed states, and twelve distinct months per state. Passing these necessary gates does not itself prove an economic effect. Thousands of signals emitted in one market episode do not create thousands of independent macro experiments. [I06]

Reopening the rejected construction requires the stated target-ledger estimability gate, a fresh preregistration, the family-by-regime interaction as the primary quantity, sufficient thin-cell support, and stable out-of-sample evidence. Another attractive external paper is not that evidence.

Current `DO_NOT_REBUILD.md` also preserves the prohibition on a new composite regime scorecard and on positioning fusion into a new regime score. There is a narrow, later amendment for research/shadow testing of earned conditional positioning authority **inside the existing Prophet US conditional-fusion arena**, subject to its frozen rules and promotion adjudication. This is not blanket permission elsewhere. This proposal supersedes none of those rulings. [I07]

## 7. Proposed end-to-end architecture

```text
Existing rights-safe, point-in-time source owners
    -> existing domain regime/model owners
       (economic, volatility, liquidity/credit, factor, regional)
    -> existing regime_vector / quad_vector contracts as applicable
    -> Neural Web world_state and existing context interfaces
    -> existing memory, reliability, relationship, and transmission owners
    -> real research dossier, scenario, briefing, or portfolio-risk workflow
    -> existing evaluation and narrowly earned decision authority
```

### Multiple coordinates, not one global label

An economic growth/inflation quadrant is not a volatility state. A domestic liquidity shock is not automatically a worldwide recession. A company identity epoch is not merely a local HMM state. Preserve scope, market, feature basis, and horizon so legitimate disagreement survives composition.

The initial design should use a small number of existing, interpretable domain coordinates. Do not multiply all coordinates into a giant joint state grid: support becomes sparse, labels become unstable, and repeated proxies are easily mistaken for independent evidence.

### A contract extension, not another platform

Use the existing publisher and envelope fields where they already express the following semantics; add or version only missing concepts after field/consumer census:

- Current-state probabilities versus named future-horizon distributions.
- Market/scope, observation cadence, horizon unit, and exchange-calendar identity.
- Source availability, model version, training cutoff, feature/transformation identity, and issuance reference.
- As-issued, historical-reconstruction, or counterfactual basis.
- State support, missingness, stale status, and reasons for abstention.
- Current descriptive/research/forecast/action permission already adjudicated by the owner.

These are semantic requirements, not a demand for duplicate timestamps, event IDs, schemas, or stores. Existing clocks and identities remain authoritative. An absent supported state is not evidence that the corresponding real-world environment is impossible. A uniform fallback remains a flagged fallback, not a calibrated market belief.

## 8. How the neural web becomes more useful

### Research and synthesis

A briefing should explain why a thesis is sensitive to an environment, what has changed, which evidence contradicts the reading, and what event would change the assessment. An LLM may synthesize the supplied structured evidence; it must not invent state probabilities, treat its prose confidence as a model metric, or grant a trade permission.

Acceptance should include answer quality on actual questions, not just JSON validity. For example: can the user distinguish a deteriorating economic backdrop from a healthy price tape without the system forcing them into a single contradictory headline?

### Graph and transmission analysis

Attach regime context to the evaluation of an existing, typed relationship hypothesis. Preserve whether an edge represents accounting exposure, legal ownership, observational association, or a causal hypothesis. A change in regime may motivate re-examining an exposure, not rewriting the underlying fact.

Follow the current division: GMI owns theme semantics; relationship owners own propagation hypotheses; MarketOntology F04 owns downstream transmission/opportunity composition. The macro `mechanism_pathways` compiler is display-only and has a no-ticker scope; do not silently expand it into an issuer-level causal engine. [I08]

A graph must also prevent evidence multiplication. A price-derived volatility series, a price-derived stress score, and an HMM fed by those same prices are not three independent confirmations. Lineage should reveal the shared observation rather than manufacture confidence through repeated paths.

### Market Memory and analogues

Retrieve earlier episodes based on information that was knowable at the comparison date, with failures as well as successes. Show similarity dimensions, material differences, sample support, and unavailable data. Separate historical-reconstruction exploration from performance claims about historical decisions.

Analogues should answer a question: what happened after similar evidence configurations, how variable were outcomes, and what differentiated failures? A visually similar chart or a memorable successful episode alone is not an estimator. Outcome-based selection of attractive analogues must not enter the test population.

### Reliability Kernel and domain models

Regime context can be an input to a pre-registered interaction experiment or a diagnostic slice of calibration. Use the existing Kernel and its legal outcome basis; do not recreate a reliability grid that the estate already rejected.

Models should earn conditional complexity by improving the downstream task beyond their unconditional counterpart. Shrink thin cells toward an appropriate pooled baseline, keep uncertainty visible, and refuse ungradeable targets. A regime posterior is itself estimated, so soft conditioning can be preferable to hard buckets; that is an experiment, not automatic permission to bypass existing support gates.

### Prophet V4 and stock research

Expose relevant regime conditions in the candidate dossier while preserving the high-recall candidate field and server-owned entry availability. A candidate can remain visible and entry-open while its thesis has a risk caveat. New regime context must not silently remove candidates, change rank, or redefine an expert event.

Signal interaction research belongs in the existing conditional-fusion process and must respect its particular source/PIT/promotion restrictions. Market-regime context and company identity epochs remain distinct. A global state transition does not alone justify resetting a security's identity or learned expert evidence.

### Portfolio risk and eventual decisions

Use scenario-conditioned exposure and covariance estimates first as a shadow/research consumer. For a mixture with state weights `p_k`, conditional means `mu_k`, and covariances `Sigma_k`, the aggregate covariance includes both within-state and between-state terms:

`mu_bar = sum_k p_k mu_k`

`Sigma_mix = sum_k p_k [Sigma_k + (mu_k-mu_bar)(mu_k-mu_bar)^T]`.

Averaging only within-state covariance omits uncertainty about different state means. Stress tests must also include model-misspecification scenarios outside the fitted state support. Neither long-duration bonds nor gold should be hard-coded as universally safe across every inflation/liquidity environment.

Posterior state weights are not portfolio weights. Allocation requires an objective, constraints, existing holdings, realistic costs, and accepted risk limits. Existing deterministic risk controls remain in force until a narrowly specified replacement or overlay is validated and approved.

### Other uses of the mathematics

Changepoint methods may help diagnose data-feed shifts, model residual deterioration, or operational anomalies. Those are different target processes with different owners and evaluation. A market HMM must not become an Executive OS scheduler, admission rule, worker-liveness detector, or organizational control plane.

## 9. Model research: start simple, test specific weaknesses

| Candidate | Reason to test | Main burden of proof |
|---|---|---|
| Existing informed Gaussian HMM | Already owned and interpretable | Time provenance, calibrated predictive utility, state support |
| Robust/Student-t emissions | Sensitivity to heavy-tailed observations | Better held-out predictive distribution, not just fit |
| Markov-switching autoregression | Serial dynamics matter within states | Incremental benefit over simpler autoregressive/volatility baselines |
| Time-varying transitions | Observable drivers might forecast transitions | Covariates truly known then; no future covariate leakage |
| Finite explicit-duration HSMM | Constant geometric dwell hazard is inadequate | Stable duration improvement versus added estimation uncertainty |
| Penalized jump models | Excessive state switching is a measured problem | Net value after delayed recognition, tuning, and costs |
| Online changepoint diagnostic | Existing recurring states cannot explain new observations | Useful alert precision/delay; no automatic trading authority |

The official statsmodels material demonstrates Markov-switching models, including time-varying transitions. Explicit-duration modeling has a substantial primary literature. Online changepoint detection estimates run-length uncertainty rather than merely assigning a recurring state. These address different failure modes. [S03, S04, S06]

Nystrup and colleagues study persistent-state inference with jump penalties; Shu and Mulvey explore factor-specific sparse jump regimes for allocation. They motivate challengers, not a presumption that their performance transfers to Mastermind. Penalized clustering memberships must not be presented as calibrated Bayesian probabilities without an appropriate calibration construction. [S07, S08]

Avoid a large nonparametric hierarchy or neural switching architecture by default. First test whether a small, regularized model earns measurable utility. State count, feature choice, initialization, covariance regularization, and retraining cadence belong inside training-only selection. Stable state crosswalks must accompany model changes so a renamed component does not masquerade as an economic transition.

## 10. Data and correction behavior

Build a feature eligibility matrix from existing source owners before fitting. Each feature needs its observation period, publication/availability time, vintage policy, license, adjustment basis, geographic scope, and update cadence. Fit transforms on training data only. Do not backward-fill releases, use later constituent membership, or mix revised and original-release records without an explicit basis.

FRED's default view concerns information available today; ALFRED real-time periods can retrieve earlier knowledge. That capability is useful but does not eliminate the need for intraday release timestamps when a strategy acts within the day. [S09]

The estate's older `REGIME_V2_PIT_DIVERGENCE_AUDIT.md` already documents disagreement between vintage-based and revised macro classifications and identifies coverage/fallback limitations. It must not be summarized as all history being perfectly PIT-clean: the document itself distinguishes vintage, mixed, and revised-latest populations. [I09]

For corrected data, retain the original issuance and add the owner's correction/supersession reference. A corrected hindsight series can support research without rewriting what a past decision knew. Missing data must remain missing or explicitly modeled as such; an outage must not sharpen confidence, lift a risk cap, or manufacture a bullish flip.

For recurring inference, use the existing scheduled producer and storage mechanism. Separate low-cost inference from training and statistical evaluation; do not add model searches to the page renderer. Bound numerical threads, record runtime and resource use, and avoid competing with production writers.

## 11. Evaluation: four distinct questions

### A. Is the historical information set honest?

Test future-data perturbation, transform cutoffs, state-selection cutoffs, macro vintages, tradable timestamps, correction replay, and unsupported states. Require prefix invariance for the **as-issued record**, not for a clearly labeled later reconstruction. A replay with unavailable issuance evidence must say so rather than substituting reconstructed probabilities.

### B. Are forecasts useful and calibrated?

Define observable outcomes and horizon units before modeling. Suitable targets may include future realized volatility, drawdown events, credit deterioration, or a stable predeclared economic classification. Grading a model against its own retrospectively relabeled latent states is not independent validation.

Use proper probabilistic scores, such as Brier/log scores for events and distributional scores for continuous outcomes, alongside calibration and sharpness. Proper scoring rules reward honest probability distributions rather than merely confident modal labels. [S10]

Compare with persistence, state prevalence, the existing classifier, and simple continuous-feature forecasts. Count effective independent episodes and account for overlapping horizons. Report false-alarm frequency, lead/detection delay, churn, support, and performance by era.

The inspected `scripts/validate_regime_fwd.py` compares the current modal quad with the legacy quad at a later horizon, uses Wilson intervals, and has a 0.5 baseline and a twenty-matured-row threshold. This is a source-verified existing shadow grader, not sufficient evidence of transition-forecast skill. Persistence can be a much stronger comparator, and overlapping observations do not supply independent Bernoulli trials. The existing record/grading owner should be improved rather than replaced. [I10]

### C. Does the information improve decisions?

Use ablations separating no-regime baseline, continuous-feature model, hard-state conditioning, soft-state conditioning, and any proposed policy optimizer. Register the economic objective, risk budget, costs, turnover limits, and available information identically across alternatives.

Equal weighting, volatility-aware baselines, and a constrained optimizer without HMM inputs are important comparators. Moreira and Muir provide influential evidence on volatility-managed portfolios, while subsequent work discusses out-of-sample and transaction-cost problems and alternative multifactor constructions. The lesson is to test these baselines, not assume any one is universally superior. [S11, S12, S13]

Keep all tested model/policy variants in the trial history. Multiple searches create selection bias even when the final chart is called out-of-sample; the backtest-overfitting literature motivates explicit accounting for that search process. Use chronological outer tests and untouched final evaluation; do not replace genuine temporal validation with randomized cross-validation. [S14]

### D. Does the product help its user?

Measure whether users can identify changed assumptions, find materially exposed theses, retrieve appropriate contrary examples, and distinguish observations from forecasts. Instrument evidence retrieval time, correction handling, source coverage, unsupported-claim rate, and scenario comprehension. Revenue or retention effects require actual product experiments; they are not inferred from a better offline score.

## 12. Product experience proposal

Use existing navigation, design tokens, and owner surfaces. The research workflow should progress from a compact environment summary to horizon-specific scenarios, then to affected theses/exposures, historical comparisons, and the evidence that would change the view.

The interface must visibly distinguish **observed**, **estimated current state**, **forecast**, and **hypothetical scenario**. Show disagreement rather than forcing all cards to match one label. A stale source needs a visible caveat; an unsupported forecast needs an explicit unavailable state.

An illustrative, non-live interaction: a user investigates a company whose price trend is strong while financing conditions are deteriorating. The dossier preserves the technical observation, links its financing exposure through the existing relationship owner, shows the uncertainty of the regime assessment, retrieves both continuation and failure episodes, and identifies the next evidence that would challenge the thesis. It does not fabricate a current market probability or change entry eligibility.

For a historical date, the user can choose what was known then or a clearly marked hindsight reconstruction. Those views must not silently share the same chart legend or performance claim.

The existing PR census found an active held regime-hero design carrier, PR #6685, plus neighboring dashboard work. A future UI commission must refresh the exact collision/ownership census instead of overwriting that work. Proposed UI acceptance requires dark/light as deliberate designs, English/Chinese parity, desktop/mobile, and normal/stale/missing/conflicting states. None of that browser proof was performed here.

## 13. Bounded vertical implementation sequence

These are proposed slices, not dispatched work or new lifecycle records. Each is useful independently and preserves the existing authority owners.

| Slice | Capability delivered | Producer/consumer path | Acceptance and stop boundary |
|---|---|---|---|
| W0: temporal honesty | A user and machine can distinguish as-issued probabilities from reconstructed history | Existing regime owner -> quad_vector/context -> one existing playback or evidence view | Repro becomes a permanent regression case; reconstruction cannot be consumed as as-issued evidence; no numerical risk-policy change |
| W1: useful regime context | A real dossier or briefing explains environment, uncertainty, and contradictions | Existing domain outputs -> world_state -> one real research consumer | Real source input through production; stale/null/contradiction behavior and browser/machine proof |
| W2: explicit anticipation | Named horizon forecasts are issued, preserved, and scored honestly | Existing regime forecasting record -> existing evaluation -> horizon view | Correct transition math/time units; persistence comparison; no accuracy promotion from overlap-inflated sample size |
| W3: memory and relationship usefulness | A scenario returns affected theses and balanced historical comparisons | Existing memory + relationship/F04 owners -> existing research journey | PIT retrieval, contrary episodes, lineage, no new causal or selection authority |
| W4: conditional modeling evidence | A permitted interaction experiment answers whether regime information adds value | Existing Kernel/Conditional Fusion experiment path | Coverage gate, preregistration, proper outcome basis, stable incremental effect or published null |
| W5: portfolio shadow comparison | Regime-aware decisions can be compared with equivalent simple policies | Existing risk/allocation simulation and evaluation owners | Realistic costs, risk matching, stress cases, held-out evidence; RL optional and separately justified |

Architecture acceptance, current owner/collision reconciliation, and applicable runtime admission precede implementation. A natural-time forward-evidence requirement cannot be replaced with retrospective accrual. A useful context-only slice need not wait for a claim of trading alpha, but it must not acquire alpha authority by being useful.

## 14. First operator packet: proposed, not an assignment

**Mission:** deliver W0, making the historical probability basis unambiguous through an existing real consumer.

**Why it matters:** otherwise both users and downstream evaluations can confuse today's reconstruction with yesterday's knowledge. The repair provides a concrete user capability without expanding a trading signal.

**Authority precedence:** current Chairman intent and protected procedure; existing regime/source owners and DNR constraints; Executive OS for any execution admission; Agent OS for continuity; this document as research evidence, not an admission token.

**Verified state:** exact source pins above; Appendix A reproduction; existing quad_vector publisher, RegimeOne owner, and shadow grading path. PR #6685 is a potential UI collision, not an assigned dependency or a carrier available for takeover. Source presence is not current runtime acceptance.

**Exact proposed scope:** census existing issuance/provenance fields; label the reconstruction basis; preserve as-issued snapshots in the existing owner mechanism; update one existing reader and one evidence/playback surface; add tests. Changes to numeric estimation are a separate declared semantic change and require their own review.

**Non-goals:** new HMM service, new event/forecast store, altered gross/rank/entry logic, replacement risk authority, changed ThemeState, fabricated historical issuances, autonomous retraining, or reuse of another worker's worktree.

**User journey:** select an historical date; see the available as-issued estimate with its source/model basis, or an explicit missing-evidence state; optionally view a separately labeled reconstruction. The machine reader makes the same distinction.

**Data/time/null/correction behavior:** inherited clocks and IDs remain controlling; all transforms and model cutoffs are explicit; corrections are referenced rather than rewriting issuance; unavailable evidence never silently becomes reconstructed operational history.

**Deterministic versus model method:** the representation and eligibility checks are deterministic. The HMM remains the existing statistical producer. No LLM participates in calculating probabilities or deciding historical eligibility.

**Failures:** stale input, unsupported state, unavailable model, malformed probability vector, missing issuance, model-version mismatch, failed source clock, and disagreement between sticky label and posterior. A legitimate label/posterior disagreement is not automatically an error.

**Implementation order:** refresh current head and owner/collision evidence; read existing record schema and consumer tests; freeze additive semantics; implement regression/negative cases; connect the real reader; validate the user view; run applicable checks; obtain exact-head review and production evidence.

**Acceptance:** later observations cannot mutate previously issued records; no as-issued consumer receives reconstructed probabilities as a substitute; real current estimates remain usable with honest caveats; a source-to-consumer production trace and all required browser states are demonstrated. CI alone is insufficient.

**Stop condition:** stop or return for a fresh ruling if the change requires a second owner/store, alters decision authority, conflicts with an occupied source carrier, or cannot bind the estimate to an honest information set. Return unknown rather than fabricate a pass.

**Continuation handoff:** preserve exact commit/PR/test identities; state which real consumer was proven; record any missing historic coverage; next action is W1 only after W0's actual acceptance, with a refreshed scope/collision census. No receiver, START, watcher, or execution status is implied by this packet.

## 15. Promotion and monitoring

Promotion is consumer-specific. A model can be useful for explanation but unproven for a forecast; useful for a forecast but unproven for allocation; useful for one country/horizon but unsupported elsewhere. A successful single outcome cannot advance those boundaries.

Monitor source freshness, probability validity, state occupancy/support, state-label crosswalks, transition churn, predictive log score, calibration, missingness, and model-version shifts. Flag when multiple indicators descend from the same observation. Drift should trigger diagnosis and the existing review process, not unbounded automatic optimization or an implicit permission increase.

Training/inference reproducibility should preserve feature and data versions, random seeds, selected hyperparameters, fit/convergence diagnostics, and execution-time environment in the existing artifact system. Keep challengers out of the production decision path until approved. Missing inputs must never lower the evidence standard.

## 16. Capability ledger and closeout

| Item | Honest status in this review |
|---|---|
| External paper identified and scrutinized | Research completed; trading results not replicated |
| Existing model and consumer ownership recovered | Source-verified at immutable pins |
| Historical reconstructed probability non-invariance | Verified synthetic reproduction of actual pinned functions |
| Full production impact of that issue | Unverified; requires consumer/replay census and real-data assessment |
| Regime-aware neural-web architecture | SPEC_ONLY proposal over existing owners |
| New calibrated forecast or allocation edge | Not established |
| New production behavior | None |
| Prior killed reliability construction | Remains rejected in its stated scope; reopening gates unchanged |

**Before:** this intake could have led to duplicating an HMM, assuming paper-level alpha, and treating reconstructed filtered history as contemporaneous evidence.

**After:** a pinned research packet identifies existing owners, a reproducible temporal-semantics finding, preserved negative evidence, an end-to-end design, and a concrete first useful implementation slice. This is a research capability delta, not a shipped modeling system.

**Primary next action:** accept/refine W0's representation-only vertical scope, then complete its current owner/collision and runtime admission checks before implementation. Statistical research on challengers may proceed independently only as a separately admitted, preregistered experiment; it does not authorize the rejected reliability grid.

No worker was commissioned, no reciprocal watcher was armed, and no Executive lifecycle state was created in this research session. An unmerged research carrier is not main-canonical publication; merge and implementation acceptance remain distinct.

## Appendix A. Reproducing the verified synthetic finding

Run in an authorized Macro checkout that contains the pinned git object, with the already available Python dependencies. This reads source and executes only the named functions against generated data; it does not import the production module or write project files. Numerical versions can affect floating-point last digits; the structural non-invariance, not a performance claim, is the test target.

```python
import ast
import hashlib
import json
import logging
import subprocess

import numpy as np
import pandas as pd
import hmmlearn

PIN = 'c3d7f1d4149176e35abf6077c18c96513abe6600'
raw = subprocess.check_output(
    ['git', 'show', f'{PIN}:engine/regime_one.py'], text=False
)
assert hashlib.sha256(raw).hexdigest() == (
    '7671e86ae2cce28f83a83054ad76c4920638f68a28a92af074dbf28c054d95eb'
)
wanted = {'_causal_filtered_pquad', '_logsumexp'}
nodes = [node for node in ast.parse(raw.decode()).body
         if isinstance(node, ast.FunctionDef) and node.name in wanted]
assert len(nodes) == 2
namespace = {
    'np': np, 'pd': pd, '_QUADS': ['Q1', 'Q2', 'Q3', 'Q4'],
    'log': logging.getLogger('readonly-regime-research'),
}
exec(compile(ast.Module(body=nodes, type_ignores=[]),
             '<pinned-regime-functions>', 'exec'), namespace)

rng = np.random.default_rng(90210)
n = 720
labels = np.array(['Q1' if (i // 30) % 2 == 0 else 'Q2'
                   for i in range(n)])
x = rng.normal(0, .35, (n, 2))
x[:, 0] += np.where(labels == 'Q1', .25, -.25)
frame = pd.DataFrame(
    x, index=pd.bdate_range('2021-01-01', periods=n),
    columns=['growth_score', 'inflation_score'],
)
frame['quad'] = labels
prefix = frame.iloc[:600].copy()
run = namespace['_causal_filtered_pquad']
earlier = run(prefix)
extended = frame.copy()
extended.iloc[600:, 0] += 1.2
later = run(extended)
assert earlier is not None and later is not None
first = {r['date']: r for r in earlier['history_filtered']}
second = {r['date']: r for r in later['history_filtered']}
dates = sorted(set(first) & set(second))
changes = [(max(abs(first[d][q] - second[d][q])
                for q in ('Q1', 'Q2', 'Q3', 'Q4')), d)
           for d in dates]
maximum, date = max(changes)
print(json.dumps({
    'pin': PIN,
    'hmmlearn': hmmlearn.__version__,
    'shared_dates': len(dates),
    'changed_dates': sum(delta > 0 for delta, _ in changes),
    'maximum_absolute_probability_change': round(maximum, 4),
    'date': date,
    'earlier': first[date],
    'later': second[date],
}, indent=2))
```

Observed output essentials: `shared_dates=132`, `changed_dates=132`, `maximum_absolute_probability_change=0.7111`; earlier Q1 probability 0.9013 and later Q1 probability 0.1902 on 2022-11-16. This is evidence of the pinned implementation's historical reconstruction semantics, not a reproduction of the paper's strategy.

## Appendix B. Primary-source reading map

These references support the specific concepts cited, not a blanket endorsement of their applicability or replication of their numerical results.

**S01.** Verma, Putri, Lesupi. *Regime-Based Portfolio Allocation Using Hidden Markov Models and Reinforcement Learning*. arXiv:2605.27848v1. Full manuscript, especially sections 6–9. `https://arxiv.org/abs/2605.27848`.

**S02.** hmmlearn. Official tutorial and Gaussian HMM documentation, accessed 2026-09-09. `https://hmmlearn.readthedocs.io/en/stable/tutorial.html`.

**S03.** statsmodels. Official *Markov switching autoregression models* example, including Hamilton-style estimation and time-varying transition probabilities. `https://www.statsmodels.org/stable/examples/notebooks/generated/markov_autoregression.html`.

**S04.** Johnson and Willsky (2013). *Bayesian Nonparametric Hidden Semi-Markov Models*. JMLR 14, 673–701. Explicit-duration modeling; not evidence of a financial strategy edge. `https://www.jmlr.org/beta/papers/v14/johnson13a.html`.

**S05.** Cont (2001). *Empirical properties of asset returns: stylized facts and statistical issues*. Quantitative Finance 1, 223–236. `https://doi.org/10.1080/713665670`.

**S06.** Adams and MacKay (2007). *Bayesian Online Changepoint Detection*. `https://arxiv.org/abs/0710.3742`.

**S07.** Nystrup, Lindstrom, and Madsen (2020). *Learning hidden Markov models with persistent states by penalizing jumps*. Expert Systems with Applications. `https://www.sciencedirect.com/science/article/pii/S0957417420301329`.

**S08.** Shu and Mulvey (2024). *Dynamic Factor Allocation Leveraging Regime-Switching Signals*. `https://arxiv.org/abs/2410.14841`.

**S09.** Federal Reserve Bank of St. Louis. FRED API real-time-period documentation; ALFRED historical-information semantics. `https://fred.stlouisfed.org/docs/api/fred/realtime_period.html`.

**S10.** Gneiting and Raftery. *Strictly Proper Scoring Rules, Prediction, and Estimation*. University of Washington working paper/revised version and JASA publication. `https://stat.uw.edu/research/tech-reports/strictly-proper-scoring-rules-prediction-and-estimation-revised`; `https://doi.org/10.1198/016214506000001437`.

**S11.** Moreira and Muir (2017; NBER working paper 2016). *Volatility-Managed Portfolios*. Journal of Finance. `https://www.nber.org/papers/w22208`; `https://doi.org/10.1111/jofi.12513`.

**S12.** DeMiguel, Garlappi, and Uppal (2009). *Optimal Versus Naive Diversification: How Inefficient is the 1/N Portfolio Strategy?* Review of Financial Studies. `https://doi.org/10.1093/rfs/hhm075`.

**S13.** DeMiguel, Martin-Utrera, and Uppal (2024). *A Multifactor Perspective on Volatility-Managed Portfolios*. Journal of Finance. Countervailing implementation/out-of-sample issues and a conditional multifactor construction. `https://doi.org/10.1111/jofi.13395`.

**S14.** Bailey, Borwein, Lopez de Prado, and Zhu. *The probability of backtest overfitting*. Author/institutional copy and publication DOI. `https://escholarship.org/uc/item/4w1110bb`; `https://doi.org/10.21314/jcf.2016.322`.

## Appendix C. Internal evidence index

Unless stated otherwise, all paths below were inspected at Macro `c3d7f1d4149176e35abf6077c18c96513abe6600`; the main recheck did not change them.

**I01.** `engine/regime_one.py`, `_causal_filtered_pquad`, lines 261–339; all-frame parameter fitting before forward recursion. Appendix A records the executed synthetic test.

**I02.** `engine/quad_vector.py`, module contract, `_momentum`, `build`; current posterior versus future transitions, reconstructed-history momentum, confidence definition, and degradation.

**I03.** `engine/regime_hmm.py`, informed Gaussian fit and smoothed/display history.

**I04.** `engine/run.py`, lines 369–458; actual producer wiring, RegimeOne artifact, accrual, and quad_vector publication. `engine/regime_vector.py` and `engine/regime_coherence.py` establish adjacent consumption/coherence responsibilities.

**I05.** `engine/neuralweb/world_state.py`; `engine/neuralweb/kernel.py`; `engine/neuralweb/market_memory_operating_cortex.py`. The latter declares `synthetic_fixture_only` and false forecast/Prophet eligibility claims. Mastermind `brain/regime_frame.py` at `686af274d8ae1558f3f3ae35e0b3aae68be80a01` is the sole bot-side reader.

**I06.** `research/REGIME_RELIABILITY_FACTOR_CROWDING_ADJUDICATION.md`, especially sections 3–7; historical scoped null, estimability gate, and reopening requirements.

**I07.** `research/DO_NOT_REBUILD.md`, `KILL-POSITIONING-FUSION`, `KILL-REGIME-SCORECARD`, `KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR`, `KILL-PER-SIGNAL-FAMILY-RELIABILITY`. Preserve the later conditional-fusion-arena-only amendment.

**I08.** `agentos/workstreams/WS-GMI-THEME-GRAPH.md`, TRANSMISSION-FOLD and landmines; `engine/neuralweb/mechanism_pathways.py` scope/semantics. These bind ownership and prevent a new parallel transmission engine.

**I09.** `research/REGIME_V2_PIT_DIVERGENCE_AUDIT.md`; its vintaged/mixed/revised populations and documented coverage limitations, not a blanket fully-PIT claim.

**I10.** `scripts/validate_regime_fwd.py`, maturity, `grade_hmm`, and `_verdict`; twenty-row threshold, Wilson bounds, and 0.5 baseline. `agentos/workstreams/WS-EVAL-OS-MEASUREMENT-LAW.md` supplies existing horizon/outcome-basis boundaries; do not generalize one ledger's horizon law to every other ledger.

**I11.** `agentos/workstreams/WS-PROPHET-US-V4-RECOVERY.md`; `agentos/workstreams/WS-MARKET-MEMORY-W2C.md`; older next-action dates are not fresh runtime proof. Existing ownership and recorded limitations were used; stale operational statuses were not promoted into present claims.

**I12.** GitHub live read on 2026-09-09: open-PR search surfaced held PR #6685 and related dashboard work. This is a collision warning, not a completed implementation placement census. GitHub compare between the two Macro pins found only marketing-data changes.
