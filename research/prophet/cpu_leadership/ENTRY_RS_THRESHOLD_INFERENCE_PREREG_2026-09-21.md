# RS anti-chase threshold — inferential adjudication preregistration

Status: POST-DESCRIPTIVE / PRE-INFERENCE / ZERO PRODUCTION AUTHORITY
Parent prereg: ENTRY_RS_THRESHOLD_PREREG_2026-09-21.md
Frozen descriptive result: evidence/rs-threshold-study.json

The frozen cohort definitions, thresholds, outcomes and episode identities are not changed here.
This second-stage prereg only defines dependence-aware inference after the descriptive read showed
a material 0.75-versus-0.85 separation.

## Dependence problem

Sector episodes co-move and forward 21-session windows overlap. Raw episode N is therefore not the
inferential N. Collapse each cohort to one observation per calendar month before comparison.
Within each month use the mean of the frozen episode metric; months without both compared cohorts
are excluded from that paired contrast.
## Frozen paired contrasts

A. incremental_075_085 minus allowed_lt075.
B. blocked_both_ge085 minus incremental_075_085.

Metrics:
- forward relative 21d return;
- forward 21d maximum adverse excursion;
- indicator of drawdown worse than -8%;
- indicator of continuation failure (relative 21d <= 0).

For each metric compute the paired monthly difference series and report:
- number of overlapping months;
- mean and median monthly difference;
- Newey-West mean/t/p with 3 monthly lags;
- moving-block bootstrap 95% CI for the mean difference, block length 3 months,
  5,000 draws, deterministic seed 20260921.
## Interpretation frozen before inference

For contrast A, the 0.75 veto has evidence of protective value only if adverse-excursion or
>8% drawdown-risk differences are materially worse in the incremental cohort. If those risk
differences are non-worse while continuation is better, the evidence argues that 0.75 is an
over-restrictive anti-chase threshold and should advance as a 0.85 challenger under the existing
promotion owner.

For contrast B, worsening risk at >=0.85 supports retaining an anti-chase boundary near the
existing recommendation cutoff rather than deleting extension protection entirely.

No p-value or CI may authorize a CPU whitelist, named-stock exception, direct trade, rank change,
or production threshold mutation. A promotion decision still requires current-theme coverage,
source/clock integrity, independent review, and prospective shadow evidence.
