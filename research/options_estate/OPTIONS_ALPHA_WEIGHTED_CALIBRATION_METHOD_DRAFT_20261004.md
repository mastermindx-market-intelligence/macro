# Draft decision packet: weighted calibration methods for Options Alpha

Status: DRAFT — NOT RATIFIED — NOT EXECUTABLE POLICY.
Date: 2026-10-04.
Carrier: mastermind-terminal issue 599, operation
options-alpha-product-integration-20260917-sol-001.
Author: the assigned root engineering orchestrator, with read-only methodological assistance.
Required acceptance: the existing Opus statistics review and Fable ratification.
Neither has been supplied for this packet.

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
Use stable summation and specify the numeric comparison representation in the
implementation review before accepting executable parity.

## 2. Proposed support gate — NOT RECOMMENDED FOR RATIFICATION AS WRITTEN

A concrete candidate is >=20 effective observations per occupied bin and
>=200 effective observations for the evaluation population, even when ties reduce
B below ten. The existing >=30 bucket and >=20 era floors would also remain.

The new 20-per-bin number is NOT implied by the old 20-per-era floor. Avoiding
tiny-bin rate claims motivates a separate gate; the neighboring era number alone
does not provide a statistical justification for this particular value.

More importantly, current global concurrency makes this candidate impractical.
For collapsed native units with equal inclusive windows of length L=H+1,

    u_i = (1/L) sum over s in W_i of 1/c_s
    sum_i u_i = covered_NYSE_sessions / L.

The inner sum across units covering a session is one. Repeating prints or adding
roots on the same covered sessions cannot increase that session's total mass.
For continuous coverage, the following are approximate covered-session needs:

| Primary horizon H | Existing N=30 | Proposed N=200 | N=200 at 252 sessions/year |
| --- | ---: | ---: | ---: |
| 5 | 180 | 1,200 | 4.8 years |
| 21 | 660 | 4,400 | 17.5 years |
| 63 | 1,920 | 12,800 | 50.8 years |

These are evaluation-population requirements, not total archive length; other
disjoint populations need their own support. Boundary and coverage details must
be reported from actual native intervals. The calculation is a data-free
consequence of the registered weight formula, not a study or a measured alpha result.

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
  sessions. Circular moving blocks contain H consecutive calendar sessions.
- Resample whole sessions with every underlying and print on each selected
  session. Retain original native weights; repeated selection is bootstrap
  multiplicity, never a change to the reported original effective N.
- Use 9,999 attempts. Require at least 20 block equivalents floor(T/H)>=20,
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
in the method receipt, and specify how partial final sampled blocks are truncated.

The 63-session block proposal itself needs about 1,260 evaluation sessions, but
the proposed native-N=200 gate is far more restrictive. This check adds no model
selection path, registered verdict cell, p-value or BH-FDR family member. It is
a calibration diagnostic, not independent evidence of alpha.

## 5. Refusals and transitions

Invalid inputs, empty evaluation, one class, unresolved method law, inadequate
effective/era/time support, G<2, an infeasible whole-tie partition, or too few valid
bootstrap replicates yield CALIBRATION_INSUFFICIENT with a specific reason.
Report safe descriptive metrics and actual counts; gate decisions stay null.
Insufficiency does not kill a construction and cannot produce an artifact.

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
methodological assistance is not the mandatory Opus review. Fable can examine
this concrete draft, but neither that examination nor generic worker availability
fills the named review gate. A genuinely eligible review binding is a required
capability change. No provider refusal was retried or bypassed.

Open ratification decisions are explicit: support/dependence feasibility; approval
of the changed nominal-bin wording; approval of the new inference/time gates; and
the two implementation-level deterministic details identified above. Until all
are closed through the existing owner, frozen v1 and the current no-artifact
behavior remain authoritative.
