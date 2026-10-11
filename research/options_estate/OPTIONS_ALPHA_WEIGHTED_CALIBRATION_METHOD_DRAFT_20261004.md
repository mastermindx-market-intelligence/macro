# Draft decision packet: weighted calibration methods for Options Alpha

Status: DRAFT — NOT RATIFIED — NOT EXECUTABLE POLICY.
Date: 2026-10-04.
Carrier: mastermind-terminal issue 599, operation
options-alpha-product-integration-20260917-sol-001.
Author: the assigned root engineering orchestrator, with read-only methodological assistance.
Required acceptance: the existing Opus statistics review and Fable ratification.
Fable principal review 5403843781 returned UNRATIFIED / REVISE for head
ed5617599e73cc2d389c6de29924f5270ef762e6. The proposed 20-per-bin/200-total
gate and monotonicity/dependence rule are not ratified. This revision records
corrections and open scientific choices only; frozen v1, trainer behavior and
no-artifact status remain unchanged. The named Opus review is still missing.

This packet makes the remaining method decision concrete. It does not modify the
frozen registration, authorize a study, or make calibration available. In particular,
the proposed support gate below is operationally prohibitive under the frozen
weight law. It must not be adopted merely because it is now written down.

## Existing law and the finite gap

The owners remain [the FS-3 amendment](../OPTIONS_ALPHA_FLOW_SCORE_AMENDMENT.md)
§§4.4, 5, 7 and 11, and [the masterplan](../FLOW_SIGNAL_ML_MASTERPLAN_BY_FABLE.md)
FS-R7/FS-R8. The amendment freezes native uniqueness weights, temporal calibration,
10 equal-mass bins, ECE < 0.05, weighted Brier improvement, reliability monotonicity
within tolerance, and effective-N floors. It does not specify weighted bin edges,
ties, a numerical per-bin floor, or the monotonicity tolerance.

FS-R8 requires registration before computation, Opus statistics review before
verdicts, and Fable ratification through the Options Alpha boundary. The existing
fit-free preregistration permits repair; it supplies no admitted fit or artifact.
Source PR #8377, merged 4176875142889a3c650f041f067d1cb954fedf7e, therefore correctly
leaves calibration unavailable and forbids an FS5 artifact.

The five proposed choices below form a single review candidate. No partial choice
may be silently installed in the trainer. Existing populations, source clocks,
horizons, 15 CPCV paths, 24-point grid, trial count, era registry and BH-FDR family
remain unchanged by this draft.

## Denominators are not interchangeable

| Quantity | Permitted role in this candidate |
| --- | --- |
| Raw event rows | Descriptive coverage only; never support or independence. |
| Sum of native global-concurrency weights | The frozen bucket/era support quantity; proposed bin support also uses this absolute scale. Weighted rates, ECE and Brier divide weighted mass by this sum. |
| Kish N = (sum w)^2 / sum(w^2) | Not used for any display gate, calibration gate or inference claim. It cannot replace the frozen support quantity. |
| Calendar block equivalents floor(T/b) | Proposed temporal-support prerequisite only, not a proven number of independent observations. |

ECE, Brier and replicate rates are invariant to a common weight rescaling; the
frozen support gates are not. Therefore rescaling native weights to pass a floor
is forbidden. The proposed block inference assumes the chosen temporal
resampling model is adequate; neither the table nor the bootstrap proves
independence, stationarity, or that dependence stops after the proposed block
length b. Anchor-calendar length T, native label-window length L=H+1 and
bootstrap block length b are distinct quantities.

## 1. Evaluation population and proposed weighted bins

Fit isotonic regression only on the earlier calibration_fit population. Evaluate
the resulting probabilities once on the later untouched calibration_eval population.
Use the existing native row weights w_i > 0, calibrated probabilities p_i in [0,1],
and binary labels y_i. Effective N is sum(w_i), not raw rows or Kish N.

First group exact equal calibrated probabilities. For each score group g retain
its probability p_g, weight A_g = sum(w_i), predicted mass P_g = sum(w_i p_i),
and positive-label mass Y_g = sum(w_i y_i). Sort groups by p_g. Construction of
edges uses only probabilities and weights, never labels.

Proposed amended wording: up to ten contiguous whole-tie bins with minimum
squared mass imbalance. This explicitly changes the literal ten equal-mass rule;
it must not be described as an already-authorized interpretation.

Let G be the number of score groups and B = min(10,G). Partition the groups into
exactly B nonempty contiguous bins. Subject to each proposed support constraint,
minimize sum_j (W_j - W/B)^2, where W = sum_i w_i. Break equal objective values by
the lexicographically earliest vector of ending score-group indices. Do not
reduce B to rescue an infeasible partition. If G < 10, report the actual B and
10-G collapsed bins; never draw ten apparently independent bins from one tie.

A reference dynamic program over prefix weights is:

    DP[b,g] = min over h<g with weight(h+1..g)>=floor:
                  DP[b-1,h] + (weight(h+1..g)-W/B)^2

It takes O(B G^2) time and O(B G) memory plus backpointers. A later implementation
must preserve the exact optimum and deterministic tie rule when optimizing it;
a timeout is an insufficient result, never permission for a partial partition.
The proposed reference uses finite IEEE-754 binary64 inputs, math.fsum for group
and prefix masses, and math.fsum of the prior DP objective and new squared term
for each candidate. Compare resulting objective values exactly, without an
epsilon tie or rounded display values; equal values use the lexicographic rule.
A faster implementation must reproduce this reference partition on the frozen
synthetic boundary cases. Numeric invariance tests must state their rounding
tolerance separately from the strict gate comparisons.

## 2. Proposed support gate — NOT RECOMMENDED FOR RATIFICATION AS WRITTEN

A concrete candidate is >=20 effective observations per occupied bin and
>=200 effective observations for the evaluation population, even when ties reduce
B below ten. The existing >=30 bucket and >=20 era floors would also remain.

The new 20-per-bin number is NOT implied by the old 20-per-era floor. Avoiding
tiny-bin rate claims motivates a separate gate; the neighboring era number alone
does not provide a statistical justification for this particular value.

More importantly, current global concurrency makes this candidate impractical.
Let P be the exact admitted parent population used to compute and install native
concurrency weights, and let E be its calibration_eval subset. The method receipt
must identify P by manifest/hash. Evaluation retains those installed weights;
concurrency must not be recomputed inside E.

For equal inclusive label-window length L=H+1, let c_P(s) and c_E(s) count the
collapsed (fill_session, root) units in P and E whose windows cover NYSE session s.
Then, summing only over sessions covered by E,

    sum_{i in E} u_i = (1/L) sum_s c_E(s)/c_P(s)
                    <= covered_label_window_sessions(E)/L.

Equality holds only when c_E(s)=c_P(s) on every session covered by E. For H=1,
windows [0,1] and [1,2] give c_P=[1,2,1]. If E contains only the second unit,
its retained weight is (1/2)(1/2+1)=0.75, not 2/2=1. Repeating prints cannot
create mass; expanding the root population does not make this subset equality true.

Consequently N*L covered label-window sessions is a best-case necessary lower
bound, not an equality when outside-subset units contribute to global concurrency.
For a continuous evaluation anchor calendar of T sessions, coverage is at most
T+H, yielding the separate best-case necessary anchor bound T>=N*L-H.

| Primary horizon H | N=30 covered / anchors | N=200 covered / anchors | N=200 anchor years |
| --- | ---: | ---: | ---: |
| 5 | 180 / 175 | 1,200 / 1,195 | 4.7 |
| 21 | 660 / 639 | 4,400 / 4,379 | 17.4 |
| 63 | 1,920 / 1,857 | 12,800 / 12,737 | 50.5 |

Years use 252 anchor sessions/year. Any c_E/c_P<1 increases actual requirements;
calendar length alone supplies no finite sufficient upper bound. Report anchor
sessions, covered label-window sessions and realized sum_s(c_E/c_P) separately.
These are evaluation support bounds, not total archive-length requirements or
admission evidence. Other disjoint populations need their own support. The
calculation is a data-free consequence of the weight formula, not an empirical
result. The proposed 20/200 gate remains new and unratified.

Recommendation: do not ratify the 20-per-bin candidate by default. The statistics
review must either explicitly accept this delay or commission a separately
registered weight/support amendment with a defensible dependence model. This
packet neither changes that model nor picks a smaller convenient floor. Until
that decision is ratified, calibration remains unavailable.

## 3. Exact weighted metrics

For each sufficient occupied bin j:

    mean_prediction_j = sum_in_j(w_i p_i) / W_j
    empirical_rate_j  = sum_in_j(w_i y_i) / W_j
    ECE = sum_j (W_j/W) * abs(empirical_rate_j - mean_prediction_j)
    Brier = sum_i w_i (p_i-y_i)^2 / W
    base_rate = sum_i w_i y_i / W
    base_Brier = sum_i w_i (base_rate-y_i)^2 / W

Retain strict ECE < 0.05 and Brier < base_Brier. Equality is not a pass.
A one-class evaluation population is insufficient; base Brier is zero and AUC
is undefined. Report the row count and effective weight separately, including
per-bin and per-era support.

## 4. Proposed uncertainty-aware monotonicity check

A fixed adjacent-bin probability-point tolerance is not justified by the old
word "tolerance." At small bin support, sampling noise alone can make a flat
reliability curve appear to decrease. The candidate below uses a simultaneous
time-block diagnostic instead of inventing a fixed 5-point kill threshold.

Proposed design, also requiring statistics ratification:

- Keep the accepted score-bin boundaries fixed.
- Construct the complete NYSE evaluation anchor calendar, including zero-event
  sessions. Circular moving blocks contain b consecutive calendar sessions;
  b=H is the current unratified candidate, not a consequence of L=H+1.
- Draw ceil(T/b) block start indices independently and uniformly from 0..T-1.
  Concatenate their circular b-session sequences, then truncate to exactly T
  session indices. Select the existing collapsed weighted units anchored on each
  chosen session, carrying all their event rows with already allocated print
  weights. Raw-print expansion cannot add mass. Repeated selection is bootstrap
  multiplicity, never a change to the reported original effective N.
- Use 9,999 attempts. Require at least 20 block equivalents floor(T/b)>=20,
  at least 20 distinct anchor sessions in every occupied bin, and 9,500 valid
  replicates. These are proposed additional gates, not inherited requirements.
- A replicate is invalid if a fixed bin has zero/nonfinite weight or any required
  statistic is nonfinite. Do not silently drop comparisons within a replicate.
- For every j<k define delta_jk = empirical_rate_j - empirical_rate_k.
  In replicate r compute delta_r_jk. Let z_r be the maximum over j<k of
  delta_r_jk - delta_jk.
- Sort the R valid z values ascending. Let c=max(0,z[ceil(0.95 R)]), with a
  one-based index. Monotonicity is broken only if max_j<k(delta_jk-c)>0.
  Otherwise report "monotonicity compatible", not "proved monotone".

Proposed deterministic seed: SHA-256 of UTF-8
"weighted-reliability-v1\0{bucket}\0{evaluation_manifest_sha256}", first eight
digest bytes interpreted unsigned big-endian, NumPy Generator(PCG64(seed)).
A ratified implementation must also freeze library versions and calendar identity
in the method receipt.

The candidate lacks predeclared operating-characteristic objectives. Before
"monotonicity compatible" may function as a shipping pass, the eligible statistics
review must specify and support: a maximum familywise false-kill probability for
flat/nondecreasing curves; minimum power for a defined material reversal magnitude
and persistence; expected decisions for ties and near-floor sparse bins; and
acceptable error distortion when dependence lasts beyond b, including the stress
horizons and adequacy rule. The required error, power, reversal, persistence and
dependence-envelope values are unset. Until Opus review and Fable ratification
resolve them, monotonicity gate decisions remain null. No data-free simulation
or operating-characteristic acceptance evidence is claimed in this packet.

The b=63-session block proposal itself needs about 1,260 evaluation anchor sessions, but
the proposed native-N=200 gate is far more restrictive. This check adds no model
selection path, registered verdict cell, p-value or BH-FDR family member. It is
a calibration diagnostic, not independent evidence of alpha.

## 5. Refusals and transitions

Invalid inputs, empty evaluation, one class, unresolved method law, inadequate
effective/era/time support, G<2, an infeasible whole-tie partition, or too few valid
bootstrap replicates yield CALIBRATION_INSUFFICIENT with a specific reason.
Report safe descriptive metrics and actual counts; gate decisions stay null.
Insufficiency does not kill a construction and cannot produce an artifact.
For example, a constant predicted probability has G=1 regardless of row count
or native weight, so its calibration decisions stay null. Three distinct score
groups with native masses 199, 0.5 and 0.5 satisfy W=200 but cannot form three
bins of weight20: the proposed partition is insufficient, and merging down to
two bins is forbidden. An empty input has no bins and no zero-filled ECE.

For a sufficient, separately admitted evaluation, any ECE, Brier or monotonicity
failure prevents an artifact. Preserve the existing kill/refit/persistence law:
monotonicity broken is an immediate construction kill; permanent ECE kill requires
the registered refit and a fresh later failed evaluation; Brier failure alone is
no-score/building-history. This draft creates no new kill authority.

## Review and implementation acceptance

Rejected shortcuts: raw-row quantiles; label-dependent merging; fractional
allocation of a tied score across apparently independent bins; raw Wilson
intervals; Kish-N substitution; or a smaller support floor chosen to obtain a pass.
None resolves the dependence and feasibility question.

After ratification, synthetic tests must prove row-order and repeated-print
splitting invariance; weight/prediction/label-mass conservation; label-blind edges;
deterministic tie collapse and partitioning; strict threshold equality behavior;
all-equal-score insufficiency; reproducible bootstrap receipts; and appropriate
flat-curve versus large reversed-curve behavior. No real study or fit is authorized
by those tests.

Current review state: a canonical M2 claude-native selector returned
"native subscription enrollment pending"; no worker was created. Native
methodological assistance is not the mandatory Opus review. Fable has examined
this concrete draft and returned UNRATIFIED / REVISE; neither that examination nor
generic worker availability fills the named review gate. A genuinely eligible review binding is a required
capability change. No provider refusal was retried or bypassed.

Open ratification decisions are explicit: support/dependence feasibility; approval
of the changed nominal-bin wording; approval of the new inference/time gates; and
the proposed deterministic numeric and bootstrap conventions. Until all
are closed through the existing owner, frozen v1 and the current no-artifact
behavior remain authoritative.
