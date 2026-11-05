# Proposed amendment to the FS-3 weighted-calibration decision draft (PR #8385)

| Field | Value |
|---|---|
| Status | **PROPOSED — UNRATIFIED** |
| Proposer | Q06 research reference, Opus 5.5 (`claude-opus-5-5`) |
| Draft reviewed | PR #8385, head `0234ea19cb8fee75750f8c387b2fe4a3cf358a25`, as sampled once on 2026-10-09 |
| Ratifier | The existing FS-3 statistics owner and Fable ratification. This text changes nothing until they act. |

This amendment changes no frozen weight, sample membership, registration, outcome window or scoring switch. FS-3
stays `scoring.enabled: false` and every bucket stays `building_history`.

## Review states

Each item carries three states. No state is derived from another.

| Item | opus_recommendation | statistical_acceptance | fable_ratification |
|---|---|---|---|
| §A clause text (A1–A5) | PROPOSE_AMENDMENT | NOT_REVIEWED | UNRATIFIED |
| §B support-gate decision (A6) | PROPOSE_AMENDMENT (owner choice; options stated) | NOT_REVIEWED | UNRATIFIED |
| §C continuous recalibration rule R_alt as a replacement gate | RECOMMEND_REJECT | NOT_REVIEWED | UNRATIFIED |

## §A — Exact clause text proposed for insertion

**A1 Ties.** Rows are grouped by identical predicted probability. Bins are contiguous runs of whole tie groups in
ascending prediction order. A tie group is never split. The number of bins is B = min(10, G), where G is the number
of tie groups with positive weight.

The partition is the exact minimiser of Σ_j (W_j − W/B)², where W_j is the native weight sum of bin j and W = Σ_j W_j,
subject to the per-bin floor W_j ≥ F_bin. When two partitions have equal cost, the lexicographically smallest cut
vector wins.

If no partition meets the floor, or G = 0, the bucket's calibration state is `NOT_YET_ESTIMABLE` with reason
`bin_floor_infeasible`. No fallback partition or bin merging is attempted outside this rule.

**A2 Unequal weights.** All calibration statistics use the frozen native uniqueness weights, unchanged. This covers
binned rates, mean predictions, ECE, Brier and Brier difference. Resampling never renormalises, re-estimates or
truncates a weight.

Rows with weight exactly zero are dropped from every statistic and reported as a count (`zero_weight_rows`). They are
not a measured zero and not an empty cell. Negative or non-finite weights, predictions outside [0, 1] and labels
outside {0, 1} are refused with a reason code. They are never coerced.

**A3 Empty cells and missing states.** A bin with zero weight cannot form under A1. Support for a bucket is reported as
exactly one of four states:

| State | Meaning |
|---|---|
| `UNKNOWN` | No weights could be computed. |
| `EMPTY` | There are no rows. |
| `MEASURED_ZERO` | Rows exist and every weight is zero. |
| `MEASURED` | Total weight is positive. |

None of these states is ever reported as zero error.

A bootstrap replicate in which any bin's resampled weight is zero is invalid. It is excluded from every replicate
quantile and counted. If fewer than 95% of replicates are valid, the bucket is `NOT_YET_ESTIMABLE` with reason
`replicate_validity_below_floor`.

**A4 Monotonicity tolerance.** There are two checks:

- **Point check.** Bin event rates must be non-decreasing within an inclusive tolerance of 1e-3. That is,
  rate_{j+1} − rate_j ≥ −0.001 for all adjacent bins, matching the default of the existing reliability-monotone
  helper.
- **Inferential check.** The max-statistic block bootstrap applies over all pairs j < k. Here z_r = max(δ*_jk − δ_jk),
  c = max(0, z_(⌈0.95·R_valid⌉)), and the curve is broken when max(δ_jk − c) > 0.

With zero valid replicates the inferential result is `UNDETERMINED`, never "not broken". With fewer than two bins
there are no pairs and the check is vacuous. That fact is reported explicitly.

**A5 Support counting.** Support is counted only as:

- (i) the native weight sum Σw, and
- (ii) the number of distinct anchor-session blocks, floor(T/H) on the fill-session calendar.

Kish N = (Σw)²/Σw² may be reported only as a weight-concentration index, and it must never satisfy a support floor.
Uncertainty is computed with the anchor-session circular block bootstrap (block length H), with native weights held
fixed inside each resample.

## §B — The support-gate decision (A6), for the owner to choose

**Measured facts.**

- **Native concurrency law.** It bounds the accrual rate at ρ ≤ (1 + (L−1)/T)/L per anchor session. The draft
  example floors (Σw ≥ 200 and 20 per bin) therefore need at least about 200·L anchor sessions.
- **Simulation (S1).** The draft gate reached ≥ 50% support in no cell at all. The grid ran to T = 1,260 sessions at
  H=5 and T = 4,536 at H=21, about 5 and 18 years. It still failed where mean Σw reached 207–211, because 10 whole-tie
  bins × 20 leaves almost no slack.
- **Retained data (E1).** The eligible geometry is 1 fill session (0_7) and 2 fill sessions (8_90). Most graded rows
  lack the `outcome_end_session_H` boundary: 47,910 rows in 0_7 and 30,633 in 8_90 (see VERDICT.md §3).

**Options.**

- **B-1 (default if no other choice is made).** Keep the draft floors and A1–A5. FS-3 calibration stays
  `NOT_YET_ESTIMABLE` for years to decades at the current cohort shape. This is honest and requires no new statistics.
- **B-2.** Keep the draft floors but set F_bin to a number of bins compatible with whole ties, for example B = 5 with
  floor 20. Q06 did **not** test this. It needs its own preregistered simulation before adoption.
- **B-3.** Adopt a continuous recalibration rule at the FS-3 §7 floor of 30. **Not recommended** (§C).

## §C — Why R_alt is not recommended

Under a frozen preregistration (PREREG.md sha256 `23494b5254d5ddf6ef91d6b5835b9ecac47adbcbeed145b0c7895c88dcccc556`),
R_alt failed its false-reassurance bar on a local reversal. Its false-reassurance rate was 0.105 (21/200) against
0.10, at H=5 T=1260 and at H=21 T=1512 (T3 steady).

The failure is narrow: one replicate, and Wilson 95% [0.070, 0.155] includes the bar. The truth's mean gap of 0.036 is
also below the 0.05 ECE threshold. Under the frozen rule, however, the verdict is REJECT.

Partial pooling (R_pool) made the problem worse, PASSing 61/200 in a T3 cell where R_alt PASSed 4/200. Pooling may only
de-escalate and must never count as data support.

Any repaired continuous rule needs a fresh preregistration that is not tuned on these outcomes
(DNR:KILL-OUTCOME-AUDITION).

## Reference implementation

`engine/calibration_sparse_weighted.py` implements A1–A5 as pure functions. It is marked `RESEARCH_ONLY = True` and
imported by nothing. `tests/test_calibration_sparse_weighted.py` pins it:

- req1: A1, A2 and A4
- req2: A5
- req4 and req1: A3
