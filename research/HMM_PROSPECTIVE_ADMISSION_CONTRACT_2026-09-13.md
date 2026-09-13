# HMM prospective forecast admission contract

**Research date:** 2026-09-13 UTC. **Owner:** Sol. **Carrier:** existing PR #7015 (`claude/hmm-regime-research-20260909`).

**Capability state:** `SPEC_ONLY` for the corrected prospective forecast/admission contract. The existing current-state HMM display remains display-only. No model is promoted and no risk, sizing, gross, rank, or trade authority changes here.

**Current evidence pins:** protected Mastermind Skillpack `0d300934d0f7b9838f2e0a1afed3ecf73329b5a3`; Macro main inspected at `a6939ca6f8e6bfea6e4e765d2cfe8e16ec607fdb`; PR #7015 pre-addendum head `0bd578085ee2e51e27de6b8610794a88cbbc28f8`.

## Executive ruling

The next HMM wave must not merely turn on the existing grader. Four separate gaps currently prevent an honest forward-skill claim:

1. **Issuance provenance is insufficient.** Saved rows do not bind the exact bytes decoded by the estimator, read/fit timing, or decoded date bounds. A timestamp does not authenticate a vintage.
2. **The scored target is mismatched to the stored model output.** `regime_one._causal_filtered_pquad` produces a filtered *current-state* distribution `P(Z_t | X_<=t)`. The existing ledger stores that distribution, while `validate_regime_fwd.py` scores its modal state against the legacy quad 21 later observations away. That is a persistence probe, not an HMM 21-step forecast.
3. **The current realized target is correction-unsafe.** US `engine.run` rewrites `data/regime/regime_history.parquet`; the validator later rereads that mutable history. A future outcome must be bound to an as-issued target observation, not silently reconstructed from a later rewritten history.
4. **The existing promotion statistic is dependence-unsafe.** Daily/sparse +21-session forecast windows overlap heavily. A Wilson interval over raw matured rows treats correlated horizon outcomes like independent Bernoulli trials. The existing 20-row/0.25 gate is descriptive shadow evidence, not decision-grade admission authority.

A fifth implementation defect makes the live status look even less mature than the ledger: `engine.run` passes `data/regime` into `regime_one.compute`, while `_forward_read` appends another `/regime`. The committed `regime_one.json` therefore reports HMM grading `n=0` even though the canonical ledger currently contains 43 saved rows through 2026-09-11. This display/path bug does not repair any of the four research gaps above.

Do **not** schedule or promote the existing grader first. Freeze the forecast contract, emit genuinely prospective rows under it, then mature and evaluate only eligible rows.

## What the existing model output actually means

Let `alpha_t` denote the filtered probability over the supervised HMM states after seeing observations through time `t`, and let `A_t` denote the transition matrix fitted using only information available through `t`.

The current saved distribution is approximately:

`alpha_t = P(Z_t | X_1:t, theta_t)`

A homogeneous HMM forecast at an `h`-step state horizon is instead:

`p_(t+h|t) = alpha_t A_t^h`

For the current 21-observation target, the candidate model distribution is therefore `alpha_t A_t^21`, projected into the stable Q1-Q4 ordering. The current `alpha_t` remains useful as a current-state estimate but must not be renamed a 21-step forecast.

This is already consistent with the parent research document's distinction among current filtered state, hindsight reconstruction, and future-state distribution. This addendum converts that principle into the exact admission contract.

## Frozen prospective target v1

### Prediction event

For every eligible issuance date `t`:

- information set: exact bytes of `data/regime/regime_history.parquet` read for the fit, with decoded maximum index exactly `t`;
- feature basis: `growth_score`, `inflation_score`;
- supervised state/label basis: committed legacy `quad` values available in that same decoded snapshot;
- estimator: current informed Gaussian Markov-regime filter unless a later accepted research decision changes the estimator under a new model-method identity;
- current-state posterior: `alpha_t`;
- forecast horizon: 21 sequential US regime-history observations, **not** 21 generic weekdays and not 21 successful ledger writes;
- predictive state distribution: `alpha_t A_t^21` over the states present in the issuance-time fit, then projected to Q1-Q4 with zero only for unsupported states;
- point prediction: argmax of that predictive distribution;
- no future observation, future fitted parameter, later reconstruction, or target-state row may enter issuance.

### Outcome event

The outcome is the **as-issued legacy quad on the exact target session** corresponding to the +21 observation endpoint.

The mutable `regime_history.parquet` may be used to resolve that future endpoint date once the horizon has actually elapsed, but it must not by itself supply the scored target state. The target state must come from an existing append-only/as-issued owner record. The current `data/regime/freshness_ledger.jsonl` is the first candidate because it already persists `asof`, `quad`, `label_quad`, freshness, and degradation once per issued session.

If no as-issued target row exists for the exact target date, the forecast is `OUTCOME_UNAVAILABLE`; it is not silently graded from a later reconstruction. If the target issuance is degraded, preserve that fact and predeclare whether the primary score excludes it or reports it as a separate stratum; do not decide after seeing performance.

### Correction behavior

- Never rewrite an old forecast to make its input provenance look stronger.
- Never backfill a missing forecast from a later fit.
- Once a target outcome is first matured from the accepted as-issued outcome carrier, do not silently overwrite it because a reconstructed history later changes.
- If a genuine correction protocol exists for the target owner, retain original and corrected identities explicitly; do not collapse them into one mutable truth.

## Same-byte issuance evidence v1

Every new prospective row eligible for future admission must prove that the bytes hashed are the bytes actually decoded by the estimator. The implementation should therefore perform one read, hash that byte buffer, and decode that same buffer rather than hashing one file read and fitting from a second path read.

Minimum evidence fields, nested in the existing HMM ledger row rather than a new store:

- `input_evidence.schema = regime_hmm_input_evidence.v1`
- `input_evidence.source_path`
- `input_evidence.content_sha256`
- `input_evidence.byte_count`
- `input_evidence.read_started_at`
- `input_evidence.read_completed_at`
- `input_evidence.decoded_row_count`
- `input_evidence.decoded_first_asof`
- `input_evidence.decoded_last_asof`
- `fit.started_at`
- `fit.completed_at`
- `fit.model_fit_asof`
- `fit.model_method`
- `fit.transition_step_basis = regime_history_observation`
- `forecast.contract = quad_t_plus_21_observations.v1`
- `forecast.horizon_steps = 21`
- `forecast.current_p_quad_filtered`
- `forecast.p_quad_h21`
- `forecast.modal_quad_h21`
- `record_assembled_at`
- `issued_at`

Temporal invariants must fail closed: read complete <= fit start <= fit complete <= record assembled <= issuance; decoded last date must equal `model_fit_asof` and row `asof`; all probabilities finite/nonnegative/simplex; matrix power must use only the issuance-time transition matrix.

This evidence proves what local bytes and dates the model used. It still does **not** prove those source bytes are themselves fully point-in-time/vintage-safe. Keep that distinction explicit.

## Backward compatibility and legacy rows

The 43 current rows through 2026-09-11 are valuable historical records and must remain immutable. They are classified as:

`legacy_current_posterior_persistence_probe`

They may be inspected descriptively, but they are **not admission-eligible HMM 21-step forecasts** because they lack the frozen v1 prediction distribution and same-byte issuance evidence.

Do not reinterpret their `p_quad_filtered` as `p_quad_h21`. Do not retro-compute `A^21` from today's data and attach it to old rows. Do not rewrite old `pred_modal_quad` semantics.

New fields extend the existing `regime_fwd_hmm.jsonl` owner; no second forecast ledger is authorized.

## Evaluation contract v1

### Primary comparison

For each eligible matured forecast, evaluate the full four-state predictive distribution with strictly proper scores:

- multiclass Brier score;
- log score/log loss with an explicit numerical floor fixed before results are inspected.

Modal accuracy is secondary and remains useful for readability, not as the only metric.

### Strong baselines

The HMM forecast must beat useful baselines issued from the same information cutoff:

1. **Persistence:** hold the as-issued current legacy quad for 21 observations.
2. **State-prevalence baseline:** issuance-time rolling/unconditional quad frequencies using only history through `t`.
3. **Observed-state Markov baseline:** forecast from the as-issued current legacy quad using an issuance-time transition matrix and the same 21-step horizon.

The third baseline isolates whether the filtered state uncertainty/emission layer adds value beyond simply propagating the observed legacy-state Markov chain.

A 0.25 uniform comparator may still be reported, but it is not sufficient as the primary admission baseline.

### Dependence and sample size

Forecasts whose +21-observation windows overlap are dependent. Report at least:

- raw eligible/matured forecast count;
- calendar span;
- number of non-overlapping 21-observation blocks or equivalent effective-independent support;
- dependence-aware uncertainty for score differences, using a predeclared blocked/HAC-compatible method;
- an easily audited non-overlapping sensitivity analysis.

Do not convert `MIN_GRADE_N = 20` raw overlapping rows into a promotion decision. The existing Wilson gate can remain as a descriptive compatibility output but must not own HMM admission.

## Calibration and failure diagnostics

Before any promotion discussion, report:

- calibration of Q1-Q4 probabilities;
- Brier/log score versus every baseline;
- modal hit rate as a secondary read;
- transition/churn frequency;
- false alarms and detection delay around actual state changes;
- performance by era and by degraded/non-degraded issuance where support permits;
- state support and abstention counts;
- entropy/sharpness distribution;
- exact number of forecasts excluded and exclusion reasons.

State scarcity is evidence, not an inconvenience. Do not pool or relabel states after results are seen merely to make the sample pass.

## Capability ledger after this ruling

| Capability | State | Evidence / meaning |
|---|---|---|
| Current filtered P(Quad) | `BUILT_NOT_PROVEN` | Implemented/displayed; no forward-skill authority |
| Saved-prediction historical honesty | `BUILT_NOT_PROVEN` | PR #7015 reader/refusal semantics exist; production acceptance still owed |
| Same-byte prospective issuance receipt | `NOT_BUILT` | Prior controlled candidate is not native integration proof |
| True +21 HMM predictive distribution | `NOT_BUILT` | Current saved value is `alpha_t`, not `alpha_t A^21` |
| Correction-safe +21 target | `PARTIAL` | Append-only freshness ledger exists; validator still reads mutable history for state |
| Maturity consumer liveness | `DARK_OR_DISCONNECTED` | 43 saved forecast rows currently have null realized fields; no repository invocation of `python -m scripts.validate_regime_fwd` found |
| RegimeOne grading status projection | `BROKEN` | live artifact says n=0 while canonical ledger has 43 rows because the run-time path is doubled |
| Existing Wilson/uniform HMM gate | `REJECTED_BY_DESIGN` for admission | May remain descriptive; ignores strong baselines and overlapping-window dependence |
| HMM predictive admission | `NOT_BUILT` | Requires prospective certified rows and dependence-aware OOS evidence |

## Exact bounded implementation wave

Use **existing PR #7015 only**. Do not create a replacement HMM branch, store, evaluator, or queue.

Expected owned paths:

- `engine/regime_one.py`
- `scripts/validate_regime_fwd.py`
- `tests/test_regime_one.py`
- `tests/test_validate_regime_fwd.py`
- one already-owned run-path line if needed to repair the doubled `data/regime/regime` status read

Implementation order:

1. Repair the RegimeOne data-root call so status reads the existing ledger; test the exact `data/` versus `data/regime/` contract.
2. Change the accrual implementation to read/hash/decode the same source bytes once and emit the v1 issuance evidence.
3. Expose the issuance-time transition matrix/state ordering internally and compute `alpha_t A_t^21`; preserve `alpha_t` as current-state context.
4. Extend new rows with the v1 forecast object; never rewrite legacy rows.
5. Change HMM maturity to resolve the +21 endpoint date and require the exact as-issued target state from the accepted append-only owner; emit typed missing/degraded outcome states rather than reconstructing silently.
6. Add proper scores and baselines. Keep the old Wilson/uniform output only as descriptive compatibility data, clearly non-authoritative.
7. Add dependence-aware evaluation and a non-overlapping sensitivity path before any `go` field can exist for HMM admission.
8. Only after the corrected contract passes exact-head tests should the existing production schedule invoke maturity/evaluation naturally. Do not manually mutate production ledgers to manufacture proof.

## Required adversarial tests

At minimum, the wave must reject:

- bytes hashed from one read while estimator decodes a second changed read;
- decoded max date later than row `asof`;
- fit completing before input read completes;
- future observations entering transition/emission estimates;
- using `alpha_t` directly as `p_quad_h21`;
- using `A` instead of `A^21`;
- state-order permutation mistakes when projecting to Q1-Q4;
- a forecast simplex with NaN/Inf/negative mass or non-unit sum;
- grading a legacy row as v1-eligible;
- grading from mutable `regime_history.quad` when the as-issued target is absent;
- silently overwriting a matured outcome after reconstruction changes;
- treating 20 overlapping forecasts as 20 independent admission trials;
- changing baseline definitions after outcomes are visible;
- the doubled `data/regime/regime` status path.

Positive controls must prove that a deterministic toy Markov chain produces the analytically expected `alpha A^21`, a state permutation leaves the four-quad forecast invariant after projection, and an exact as-issued target row matures once and remains byte-stable thereafter.

## Promotion boundary

This addendum grants **zero trading authority**.

HMM predictive admission becomes reviewable only after:

1. the corrected v1 source is accepted on #7015;
2. natural production accrues prospectively certified rows;
3. enough outcomes mature to satisfy the predeclared dependence-aware support threshold;
4. the HMM beats persistence and the stronger issuance-time baselines on proper probabilistic scores with uncertainty;
5. calibration, transition behavior, degraded states, exclusions, and era sensitivity are disclosed;
6. Sol performs adversarial review against the original product thesis and no-overreach laws.

If those conditions fail, the correct result is a published null: retain current-state regime context where useful and reject forward-predictive authority.

## References and inheritance

This addendum narrows and operationalizes, but does not supersede, `research/HMM_REGIME_INTELLIGENCE_RESEARCH_2026-09-09.md`, especially its separation of current filtered state, historical reconstruction, and future distribution; its `p_(t+h|t)=p_t A^h` rule; its proper-score/baseline requirements; and its warning that overlapping horizons do not create independent trials.

External methodological anchors remain Rabiner (1989), *Proceedings of the IEEE*, DOI `10.1109/5.18626`, for standard HMM filtering/transition structure; Gneiting & Raftery (2007), JASA, DOI `10.1198/016214506000001437`, for strictly proper probabilistic scoring; and the long-horizon/overlapping-observation literature for dependence-aware inference. These references constrain interpretation; they do not validate Mastermind's empirical HMM.

## Exact next action

On the existing #7015 carrier, implement steps 1-4 as one bounded source wave and prove them with the listed mutation/positive controls. Do **not** enable HMM promotion, rewrite legacy rows, or schedule maturity until that exact-head forecast/issuance contract passes review.