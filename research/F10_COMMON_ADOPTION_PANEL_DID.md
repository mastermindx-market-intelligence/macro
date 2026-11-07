# F10 — Common-Adoption Balanced Panel Two-Way Fixed-Effects / Difference-in-Differences

- **Component:** `engine/panel_did.py` (+ `tests/test_panel_did.py`)
- **Engineering item:** MO-DELTA-015/016 (new F10 econometric family, research-only estimator + JSON CLI)
- **Authority:** `research_only` / `descriptive_estimate`
- **Status:** implemented and unit-tested; **not** an empirical study, **not** a completion claim for the F10 family, and **not** validated against any real dataset.

## 1. What this is (and explicitly is not)

This module fits one descriptive difference-in-differences coefficient on a
strictly balanced `N x T` panel whose treatment mask has a single common
adoption date. It is an engineering building block for the F10 econometric
toolkit.

It does **not**:

- claim causal identification of any effect;
- test, verify, or validate parallel trends, no anticipation, or no spillover
  (all three are reported as `NOT VERIFIED` in every successful result);
- attach significance language, trading authority, or product decisions to an
  estimate;
- perform any study of real data (no data source, no network, no files);
- search specifications: exactly one pre-specified specification is estimated,
  with no automatic multiple-specification search and no registration side
  effects.

## 2. API contract

```python
estimate_common_adoption_panel(outcomes, treatment, *, unit_ids, periods,
                               cluster_ids, design_id=None) -> dict
```

| Field | Shape / type | Rules |
| --- | --- | --- |
| `outcomes` | `N x T` array-like | finite real numbers; booleans rejected; NaN/±inf rejected |
| `treatment` | `N x T` array-like | entries exactly 0 or 1 (booleans accepted for the mask only) |
| `unit_ids` | N strings | nonempty, unique |
| `periods` | T strings | canonical ISO `YYYY-MM-DD`, strictly increasing, unique |
| `cluster_ids` | N strings | nonempty; may group units; caller-supplied actual assignment/dependence unit |
| `design_id` | optional string | opaque provenance label echoed back |

Return value is a JSON-safe dict. `status == "ok"` carries the estimate;
anything else is a typed abstention with `reason_code` / `reason` (and
`details` where informative). No `NaN` or `Infinity` is ever emitted.

### Acceptance gates (rejections are typed, never silent)

A request is rejected (with the stated `reason_code`) when any of the following
holds. Nothing is dropped, padded, or imputed to make a borderline panel fit.

- `boolean_outcomes`, `non_numeric_entries`, `nonfinite_outcomes`,
  `invalid_input`, `invalid_shape` — outcome matrices must be finite reals,
  rectangular `N x T`.
- `shape_mismatch`, `length_mismatch` — outcomes/treatment must share shape;
  `unit_ids`/`cluster_ids` must have N entries; `periods` must have T entries.
- `duplicate_unit_ids`, `invalid_label`, `invalid_periods` — identifier and
  date hygiene (dates must parse, be canonical, strictly increasing, unique).
- `invalid_treatment_values` — mask entries other than exactly 0/1.
- `invalid_treatment_path` — treated units must be 0 in every pre-adoption
  period and 1 in every period from adoption onward; reversals, gaps, exits.
- `staggered_adoption` — all treated units must first adopt in the same period.
- `no_pre_period` — common adoption may not fall on the first period.
- `no_treated_units` / `no_control_units` — at least one unit in each arm.
- `insufficient_units` / `insufficient_timepoints` — N ≥ 2, T ≥ 2.
- `insufficient_observations` — residual degrees of freedom `NT − (N + T)`
  must be positive (e.g. 2×2 panels are rejected: K = NT).
- `mixed_treatment_within_cluster` — a caller-supplied dependence cluster must
  be homogeneous in treatment status (treated vs control); assignment-cluster
  identity is never inferred from the data.
- `unidentified_treatment` / `unidentified_estimate` — no within variation in
  the mask after two-way demeaning, or a non-finite coefficient.

## 3. Estimator

Balanced two-way within transformation (unit and time effects absorbed):

```
ỹ_it = y_it − ȳ_i· − ȳ_·t + ȳ
d̃_it = D_it − D̄_i· − D̄_·t + D̄
β̂   = ⟨d̃, ỹ⟩ / ⟨d̃, d̃⟩          ȇ = ỹ − β̂ d̃
```

This is algebraically identical to OLS of the outcomes on an intercept, N−1
unit dummies, T−1 time dummies and one treatment indicator (Frisch–Waugh); the
within-residuals equal the dummy-regression residuals exactly (verified in
tests against an explicit dummy-OLS oracle). Full parameter count is
`K = N + T = 1 + (N−1) + (T−1) + 1`, and residual degrees of freedom are
`NT − K`.

### Cluster-robust uncertainty (CR1)

Scores are aggregated over units *and* time within each caller-supplied
assignment cluster:

```
s_g = Σ_{i∈g} Σ_t d̃_it · ȇ_it ,        G = number of clusters
V̂  = (G/(G−1)) · ((NT−1)/(NT−K)) · Σ_g s_g² / ⟨d̃, d̃⟩²
```

The finite-sample correction is the usual CR1 factor (Stata-style; identical in
form to the statsmodels `cov_cluster` `use_correction=True` adjustment).
Inference uses a Student-t reference distribution with `G − 1` degrees of
freedom for the 95% interval and two-sided p-value.

### Inference ceilings (what is withheld, and when)

- **Few clusters per arm.** Point-uncertainty is computed only when there are
  ≥ 2 treated *and* ≥ 2 control assignment clusters. Otherwise the coefficient
  is returned with `inference_status = "insufficient_clusters"` and
  `se/ci95/p_value = null`; a single cluster per arm is never given a
  fabricated standard error.
- **Degenerate uncertainty.** If the computed variance is zero, non-finite, or
  within a safety factor (64×) of the coefficient's own floating-point
  roundoff `eps·Σ|d̃·ỹ|/⟨d̃,d̃⟩`, the fit is (near-)exact and the result is
  `inference_status = "degenerate_variance"` with `se/ci95/p_value = null`.
  The routine never reports `p = 0` or unbounded confidence.
- **Small clusters.** When `G < 30` the result carries an explicit
  `small_cluster_warning`. The warning is a flag, **not** a validated coverage
  guarantee; t(G−1) inference with few clusters is known to under-cover under
  serial correlation (Bertrand–Duflo–Mullainathan, 2002).
- Cluster identity is exactly what the caller passes; the module never infers
  or reassigns dependence structure.

### Reported metadata (successful runs)

`N`, `T`, `NT`, `K` (with its decomposition), residual df, cluster counts and
per-arm counts, treated/control unit counts, adoption period index and date,
pre/post period counts, input date range, per-cluster membership and arm,
estimator description, within transformation, variance formula, cluster
variable, specification-search statement, assumption ceilings, warnings, and
standing limitations.

## 4. Invariances and numerical validation

Covered by `tests/test_panel_did.py` (22 focused tests):

- **Planted-effect recovery** with unit effects, time effects and seeded noise;
  coefficient recovered near the planted value with finite p and CI.
- **Explicit dummy-OLS oracle**: an independently built
  `[1 | unit dummies | time dummies | D]` design reproduces the coefficient to
  ~1e-15 relative and its residuals to ~1e-14 absolute; the **independently
  coded bread/meat CR1 sandwich** on that design reproduces the reported
  standard error to ~1e-16 relative (agreement measured, not assumed — the
  oracle shares no code with the implementation).
- **2-period DiD equivalence**: with T = 2 the TWFE coefficient equals the
  treated-minus-control change-in-means difference to ~1e-12.
- **Shift invariance**: unit shifts, time shifts, and level shifts leave the
  coefficient and standard error unchanged.
- **Row-order invariance**: permuting units (with labels and cluster ids
  aligned) leaves coefficient and SE unchanged to ~1e-8. Column *order* is
  semantic (periods must be strictly increasing); the matching invariance is
  date relabelling under preserved order, which is also tested.
- **Grouped assignment clusters**: grouping units into 4 clusters of 3 changes
  the reported SE (scores aggregate within clusters) while leaving the
  coefficient identical; cluster membership and arms are reported.
- **Insufficient clusters** (1 treated + 1 control cluster): point estimate
  retained, inference typed unavailable, no fabricated SE.
- **Exact fit**: a design with zero residual variation but ≥ 2 clusters per arm
  returns `degenerate_variance` with the coefficient intact and no SE/CI/p —
  no fake certainty from roundoff.
- **Input hygiene**: NaN/inf/boolean outcomes, ragged/shape-mismatched input,
  fractional mask entries, staggered adoption, reversals, no pre-period,
  missing arms, mixed-treatment clusters, duplicate/short identifier lists,
  and five classes of invalid period lists all produce typed rejections.
- **CLI contract**: valid request → exit 0 with finite JSON; malformed JSON /
  non-object / missing / unknown fields → nonzero exit with typed `error`
  payloads; a rejected study → exit 1 with a typed abstention, so a rejected
  study never looks like success.

Known limits of the validation: the seeded simulations demonstrate correctness
of the algebra and gating, **not** null calibration or finite-sample coverage
of the t(G−1) approximation; no such claim is made from one simulation.

## 5. Explicitly unsupported designs

Rejected (not approximated): staggered adoption, unbalanced or ragged panels,
treatment reversals/exits, already-treated-at-start panels, time-varying or
continuous treatment, heterogeneous adoption timing, covariate-adjusted
specifications, non-callable cluster structures. Modern staggered-adoption
estimators (e.g. Callaway–Sant'Anna, Sun–Abraham, interaction-weighted event
studies) are a separate, unimplemented F10 family.

## 6. Requirements before any product empirical use

1. An **independently identified native panel** (real data with verified unit
   identity, period alignment, and genuine common adoption timing) — this
   module ships with no data and performs no study.
2. Independent statistical review of assumption plausibility (parallel trends,
   no anticipation, no spillovers) and of cluster construction.
3. Acceptance by the parent owner; this artifact asserts nothing about
   integration or acceptance.

## 7. References

- Bertrand, M., Duflo, E., Mullainathan, S. (2002). *How Much Should We Trust
  Differences-in-Differences Estimates?* NBER Working Paper 8841.
  https://www.nber.org/papers/w8841 — serial correlation in DiD standard
  errors; motivates cluster aggregation and cautions on few-cluster inference.
- statsmodels `cov_cluster` (sandwich covariance with small-sample
  correction): https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_cluster.html
  — form of the CR1 finite-sample factor used here.

These are sources for the estimator's statistical background, not instructions
and not provenance for any empirical claim.

Parent edge-case qualification: heterogeneous boolean outcomes are rejected before
NumPy numeric coercion. A numerically underflowed Student-t tail is reported as
`p_value: null`, `p_value_status: numerical_underflow`, never as an exact zero.
Valid standard-error and interval outputs remain separately available. Caller
pre-specification and selection history are not verified or priced by this pure API.
