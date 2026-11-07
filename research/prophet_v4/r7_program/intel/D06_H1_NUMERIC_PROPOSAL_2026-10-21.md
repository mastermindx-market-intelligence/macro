# D06 numeric proposal for H1 — source-blind, PROPOSED only

- Unit: `Q05-H1-PEER-PARTICIPATION-ACCELERATION-V1` (R20:6, R21:7).
- Status: **PROPOSED — NOT RULED, NOT REGISTERED, NOT ADMITTED.** Definition is not
  admission. Every number below is a proposal for the Fable seat to rule on; after ruling,
  the frozen numbers route to the owner of #8091 / #8192 (INTEL_DISPOSITION_2026-10-21.md:335-339,
  decision F4).
- Compiled 2026-10-21 on branch `lane/pro-intel-d06num-20261021-r1` at BASE
  `c5ee0941b4e4b2132caabd4d43a4b419d46ec22e`. Source-blind: no outcome file was opened
  (see "Source discipline" at the end).
- Citation shorthand: **Ruling** = `research/prophet_v4/r6_program/wave0/SEAT_RULING_R6-PREREG-01_2026-09-23.md`;
  **PREREG** = `research/prophet_v4/b4_entry_policy_calibration/PREREG.json`;
  **Cell G** = `research/prophet_v4/CELL_G_FLAGSHIP_VOI_MEASUREMENT_LAW_2026-08-22.md`;
  **DR** = `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/DECISION_REGISTER.json`;
  **Audit** = `research/prophet_v4/r6_program/wave0/OPUS_SCIENCE_SEAMS_AUDIT_2026-09-23.md`;
  **D07-01** = `research/prophet_v4/r6_program/rulings/R6-D07-01_EVIDENCE_CLASS_REGISTER_ADOPTION_2026-09-27.md`;
  **DNR** = `research/DO_NOT_REBUILD.md`. **R20/R21 exist ONLY at the #8091 head
  `410965bd243d94e9f0e528e15f0c97df53fae732`** (read as `git show`, never checked out);
  they are absent at BASE, whose rulings directory instead carries `R6-B04-01a_DOSSIER_CONTRACT_AMENDMENT_DRAFT`
  and `R6-D07-01` — the #8091 head predates both. The #8192 script
  `scripts/check_prophet_h1_prospective_accrual.py` and
  `research/prophet_v4/S0_CAPTURE_INTEGRITY_R2_20261005.json` likewise exist only at the
  #8192 head `07136c56ec6f8492067b468f90c6b4372ca649b4` (script/keys read there; S0 values never read).

## Premise check (all mission premises confirmed against the artifacts)

- R20:93 `trial_may_start=false`; R20:98 gate 4 reads "Chronological partitions, test count/power
  and the numeric D06 worthwhile-gain/tail-harm fields are not frozen". Confirmed verbatim.
- R21:80-90 lists nine open gates; R21:88 gate 7 is "chronological partitions, test count/power and
  numeric D06 worthwhile-gain/tail limits". Confirmed.
- R21:92 primary, non-numeric: "paired date-level C2-minus-C1 top-five H10 SPY-excess mark utility on
  one frozen, source-qualified MOMENTUM population". Confirmed verbatim.
- PREREG:170-172 `search_family_includes: ["EL_H10_timing_study_registered_under_D06"]`. Confirmed.
- D06 is `OPEN_TECHNICAL_DECISION_FABLE_AUTHORIZED_TO_RESOLVE` (DR:149). Confirmed.
- No artifact contradicted a mission premise; no quoted-bytes exception to report.

## 0. Estimand (fixed by prior record, restated; nothing new proposed here)

Per-decision-date paired difference d_t = (C2 top-five H10 SPY-excess mark utility) − (C1 same),
on one frozen source-qualified MOMENTUM population, K = 5 (R21:92). Same-clock, market-excess,
full-opportunity per M1 (Ruling:20): refused rows are carried at cash inside each arm's utility
(PREREG:181-182, Ruling:44), so participation differences price in as sitting out. H10 = 10 sessions
(PREREG:157-158 fixes 10 as the primary horizon in this family). The confirmatory statistic is the
mean of d_t across matured decision dates, with dependence-aware uncertainty (Cell G:369 — daily
observations with an H10 overlapping outcome: HAC/Newey–West lag H−1 = 9, or a preregistered
moving-block bootstrap with block length ≥ 10). Historical rows are diagnostic only
(R20:103, R21:57).

## 1. Worthwhile gain

**PROPOSED: 50 bps per decision date**, i.e. the confirmatory read may certify gain only when the
paired C2−C1 top-five H10 SPY-excess mark-utility mean difference clears +50 bps net of the
registered cost floor charged to both arms.

Derivation, from the inputs only:

1. Cost-floor anchor. The round-trip cost floor of **50 bps** is registered as a FLOOR, not a
   measurement, pending the D08 measured range, and "a read using a lower floor is invalid"
   (Ruling:43; PREREG:179-180 `cost_floor_bps_round_trip: 50`, `cost_floor_treatment:
   "floor_not_measurement_pending_D08"`). An effect smaller than the cost floor the registration
   itself refuses to undercut cannot be economically meaningful: with D08 unmeasured, cost
   assumptions alone could erase it. → worthwhile gain ≥ 50 bps.
2. Harm-symmetry anchor. The family's declared economic immateriality magnitude is **25 bps**
   (PREREG:174-178, lower confidence bound margin −25 bps). A gain threshold below the family's own
   materiality bar would certify as "worthwhile" what the family tolerates as immaterial in the
   harm direction. → worthwhile gain ≥ 25 bps. This anchor is dominated by anchor 1.
3. No user economic budget above those two numbers exists in the record. D06's required evidence is
   a "User economic loss/coverage budget independent of held-out results" (DR:151) and the margin
   must be defined "from that job and permitted development evidence, not whichever holdout result
   later looks best" (DR:171). The only registered economic numbers available source-blind are the
   50 bps cost floor and the −25 bps bound, so 50 bps is the largest non-invented value.

Alternatives considered and rejected:

- **25 bps (harm-symmetric):** rejected — below the registered cost floor; a read could certify a
  "win" that one round of registered cost assumptions erases.
- **0 bps / any-positive-net:** rejected — that is the significance/non-inferiority question, not
  materiality; D06 forbids "unrestricted threshold search" (DR:153) and Cell G:589 forbids treating
  statistical nonzero without material value as a win.
- **75 or 100 bps:** rejected — no registered anchor; would be invented.
- **OPEN alternative:** a user-economic-budget-derived value. If the seat commissions the bounded
  design analysis D06 step 3 permits (DR:171), its budget-derived number may replace 50 bps before
  the freeze. Absent that commission, 50 bps stands as the proposal.

## 2. Tail harm

**PROPOSED (primary harm limit):** the one-sided 95% lower confidence bound on the paired
date-level mean difference (C2−C1, H10, SPY-excess, net of the 50 bps floor) must be
**≥ −25 bps**. A nonsignificant point estimate is NOT non-inferiority (PREREG:177; DR:173).

Consistency with the shared search family: this adopts the family convention verbatim
(PREREG:174-178) — same horizon (H10), same bps scale, same one-sided lower-bound form, same
−25 bps magnitude, same nonsignificance carve-out — with the single mapping that the comparison is
the paired C2−C1 difference rather than "net excess vs C0" (R21:92 fixes H1's comparison; C0 is not
an arm of H1). The interval is dependence-aware per Cell G:369 and uses the one-sided 95%
convention of Cell G:511. No difference from the family margin is proposed; if the seat prefers a
different margin for the paired timing estimand it must say so as a versioned amendment.

**PROPOSED (registered adverse-tail endpoint, guardrail only):** `tail_loss_ES10` of the per-date
paired difference distribution — expected shortfall over the worst 10% of matured per-date
differences — under Cell G §6.8 exactly: `tail_n = ceil(0.10 * n_matured)`, `UNESTIMABLE` when
`tail_n < 10` (normally `n_matured < 100`), 10th percentile descriptive-only below that floor,
and no rescue authority (supporting endpoints are descriptive-only per Ruling M2 :21 and
PREREG:121-137). Harm is thereby read on both the mean (the −25 bps bound) and the adverse tail
(the ES10 guardrail), which answers Audit M3's "wide interval hides harm" failure mode
(Audit:81-95).

## 3. Chronological partitions

Prospective-only, per D07 (DR:202: where historical provenance cannot establish the claim, start a
frozen prospective study; R20:103: the vertical "makes the prospective path executable … rather than
backfilling"; R21:57: the 2026-09-25 census remains historical evidence only).

- **Cohort start rule (PROPOSED):** the first nightly capture session, on or after the owner-merged
  landing of the frozen D06/D07 registration, that carries the #8091 prospective Context Vector
  fields and clears the #8192 S0 capture check (`S0_CAPTURE_PRESENT`; script :30-33, :465-488) —
  the direct analogue of PREREG:36-37 (`FIRST_PROSPECTIVE_B4_OBSERVATION_AFTER_PREREG_MERGE`,
  `historical_backfill: false`). Evidence class per D07-01: only prospective rows with a
  writer-stamped capture clock and pinned store generation may carry `OBSERVED_AS_RUN`; every
  pre-start row is `RETROSPECTIVE`/diagnostic and is never pooled with the confirmatory cohort
  (D07-01:22-25; Ruling B4 :19).
- **Unit of accrual:** one decision date = one nightly `stamp_date` with ≥ 1 source-qualified
  MOMENTUM row; its pair matures when the H10 window is fully settled (t + 10 sessions) and the
  settlement view is frozen (Cell G:545-547). Sessions with zero qualified rows stay in the
  coverage vector with cause breakdowns, never silently dropped (Cell G:289-291).
- **Fixed look (PROPOSED form):** one adjudicative read at N matured paired decision dates, where
  N is the 80%-power count from §5 at the seat-ruled dispersion assumption, subject to the Cell G
  estimability floors: ≥ 50 matured paired dates, `N_eff(decision_date) ≥ 20`,
  `N_eff(economic_issuer) ≥ 20` (Cell G:346-348; Ruling B2 :17), DOMINATED surfaced if > 50% of
  observations sit in one group (Cell G:357). Before the look, only status/maturity/coverage
  counters may be read — no outcome comparisons (Cell G:405-407). N is **OPEN** numerically until
  the seat rules the dispersion assumption (option set: the §5 grid).
- **Futility (PROPOSED):** one prescheduled monitoring check at ceil(N/2) matured paired dates,
  never earlier than the 50-date Cell G floor: if the one-sided 95% upper confidence bound of the
  paired mean difference is < 50 bps (the worthwhile gain), the study stops as REJECTED for the
  registered gain — mirroring the family's futility shape at half the fixed-look count
  (PREREG:191-194: at 150 of 300 per cell, stop REJECTED if every cell's primary lower bound
  excludes improvement; Ruling:45). The futility check can stop the study; it can never promote.
- **Historical rows:** diagnostic only, zero confirmatory credit (R20:103; R21:57; Ruling M7-style
  separation for current-only cohorts, Ruling:27).

## 4. Test count and multiplicity

- **Family:** Holm across the five non-control distinct B4 cells (C1–C5) on the primary endpoint
  MAE@H10, with the EL H10 timing study (H1) inside the same search family
  (PREREG:159-173 with :170-172; Ruling amendment item 4 at :41; M2 at :21: "#7751 and the EL H10
  timing study are ONE search family"). Family size = **6** confirmatory tests; H1 contributes
  exactly one (its single paired primary — one primary endpoint per experiment, Cell G:389-391).
- **Resulting alpha (PROPOSED):** family-wise α = 0.05, one-sided (the registration text fixes the
  method "Holm" but no numeric FWER — the numeric value is a seat ruling; option set {0.025, 0.05,
  0.10}). Under Holm, H1's local threshold is rank-dependent: α/6 ≈ **0.008333** one-sided if H1's
  p is smallest in the family, up to α = 0.05 if largest. All power arithmetic in §5 uses the
  most-conservative rank-1 value 0.008333.
- **Alias guard:** C6/C7 collapse into C2/C4 and never add sample or test credit
  (PREREG:144-148; Ruling:38; DR:173: "The #7751 aliases do not add sample/test credit; its
  300-episode floor is not alone a power proof").
- **Prior looks the seat must log in the trial ledger before any read** (M2/m2, Ruling:21, :30;
  Cell G:397 "every tested/abandoned variant counts toward the search family"):
  `KILL-PSS-SR2-PEER-DIFFUSION` (DNR:83) and `KILL-PSS-SR3-PARTICIPATION` (DNR:84) are the
  adjacent killed peer/participation species (both 2026-07-27, both closed with "any sign-reversed
  use must accrue prospectively or use untouched data"), and the prospective-only charter family
  `HOLD-PSS-RH1/CR1/CD1/AF1` (DNR:155-158) fixes the 2026-07-24 no-backfill boundary in this
  species neighborhood. H1's construction (paired cell-participation timing on a top-five
  selection utility, not a sector-breadth label) appears distinct, but species-equivalence is a
  **seat ruling, not a property of this proposal**. The known-answer smoke (R20:100, R21:90) is a
  fixture test, not an outcome look.

## 5. Power (TABLE ONLY over an ASSUMED dispersion grid)

Every dispersion value below is an **ASSUMPTION about the per-decision-date standard deviation of
the paired C2−C1 difference**. None is estimated from Prophet outcomes, grades, ledgers or market
return files — no such file was opened. The grid {50, 100, 200, 400} bps is the mission's example
grid, adopted as the option set.

Test powered: H0: mean paired difference ≤ 0 vs H1: > 0, one-sided, Holm rank-1 local
α = 0.008333, 80% power at true mean = +50 bps (the proposed worthwhile gain), exact t critical
values (normal approximation shown for reference; z_{1−α} = 2.3940, z_{0.80} = 0.8416).

| ASSUMED σ_d (bps) | N matured paired dates (exact t) | N (normal approx) | Prescheduled futility check at | Calendar dates under block-10 dependence (conservative) |
|---:|---:|---:|---:|---:|
| 50  | 14  | 11  | 7   | ~140   |
| 100 | 45  | 42  | 23  | ~450   |
| 200 | 171 | 168 | 86  | ~1,710 |
| 400 | 673 | 671 | 337 | ~6,730 |

Reading of the last column (ASSUMPTION-labelled): if σ_d is the *marginal* per-date dispersion and
adjacent H10 windows overlap, Cell G:369 requires lag-9 HAC or block length ≥ 10, and the
non-overlapping-block bound puts effective independent clusters ≈ dates/10 — the conservative
planning transform dates ≈ 10 × N. If instead the seat rules σ_d as the dispersion of
non-overlapping 10-session date clusters, that column does not apply and N is the calendar-date
requirement directly.

Implied calendar time, from R20/R21 counts only: **zero prospective rows had accrued as of R21**
(R20:101 "Prospective rows carrying the new fields have not yet accrued through the natural
nightly"; R21:84 gate 3 still open), and the only recorded counts are the historical 2026-09-25
census — 2,928 curated rows, 249 eligible, 8 owner-labelled MOMENTUM, 2 clearing all implemented
gates = 0.803213% (R20:75-85; R21:57). No nightly rate of qualified decision dates is recorded
anywhere in R20/R21, so calendar time beyond the arithmetic floor is **OPEN**. The floor, at the
impossible-best rate of one qualified decision date per trading session (252 sessions/year,
ASSUMED calendar convention) plus 10 sessions' maturation for the final date: ~0.06 yr (σ=50),
~0.18 yr (σ=100), ~0.68 yr (σ=200), ~2.7 yr (σ=400); under the block-10 reading ~0.6 / ~1.8 /
~6.8 / ~26.7 yr. Any slower accrual multiplies proportionally (calendar time = N/(r·252) years at
r qualified dates per session, r ≤ 1, r unmeasured). Practical consequence for the seat: the
fixed-look N should not be frozen until the #8192 checker's first months of S0 receipts establish
r — otherwise the look date is unknowable and D06's "300rows treated as sufficient power"
forbidden shortcut (DR:153) is nearby.

## 6. Field register (PROPOSED value | source | what the seat must rule | receiving owner)

Owner column: **#8091** = registration/rulings carrier (R20/R21 live there; trial ledger);
**#8192** = prospective accrual harness / S0 receipts (its checker always emits
`h1_admitted: false` and a claim limit — script :8-10, :341, :484-487; S0 JSON top-level keys
`h1_admitted` / `claim_limit` / `independent_review_accepted` / `production_nightly_verified`
read as keys only, values never opened).

| # | Field | PROPOSED value | Source citation | Seat must rule | Owner |
|---|---|---|---|---|---|
| F1 | Worthwhile gain | 50 bps per decision date, net of the 50 bps round-trip floor | Ruling:43; PREREG:179-180; DR:151,171 | value; whether to commission the user-budget design analysis (OPEN alternative) | #8091 |
| F2 | Primary tail-harm limit | one-sided 95% LCB of paired mean difference ≥ −25 bps | PREREG:174-178; Cell G:511,369 | confirm the C0→paired-C2C1 mapping and the margin | #8091 |
| F3 | Adverse-tail endpoint | ES10 of per-date paired difference; UNESTIMABLE below 100 matured dates; no rescue authority | Cell G:273-279; PREREG:121-137; Ruling:21 | adopt as guardrail | #8091 |
| F4 | Uncertainty method | one-sided 95% dependence-aware; EITHER HAC/NW lag 9 OR moving-block bootstrap block ≥ 10 (pick one) | Cell G:369,511; Ruling:17 | pick one method before outcomes | #8091 |
| F5 | Cohort start | first S0-verified capture session after the frozen registration lands through its owner; historical_backfill false | PREREG:36-37; R20:101; R21:84; D07-01:22-23; script :30-33 | the exact trigger event (merge vs first natural nightly) | #8192 |
| F6 | Fixed look | one adjudicative read at N matured paired dates; floors 50 dates, N_eff(date) ≥ 20, N_eff(issuer) ≥ 20; N = 80%-power N at ruled σ — **OPEN** (option set 14/45/171/673) | Cell G:346-348,357,405-410; Ruling:29; §5 table | the numeric N (requires the σ ruling) | #8091 + #8192 |
| F7 | Futility | one prescheduled check at ceil(N/2): stop REJECTED if one-sided 95% UCB < 50 bps; monitoring-only | PREREG:191-194; Ruling:45; Cell G:407 | adopt; confirm it cannot promote | #8091 |
| F8 | Family-wise alpha | Holm, family size 6 (C1–C5 MAE@H10 + H1 paired primary); FWER 0.05 one-sided PROPOSED; H1 planning α 0.008333 | PREREG:159-173; Ruling:41,21; Cell G:395 | numeric FWER and sidedness — **OPEN** (0.025/0.05/0.10) | #8091 |
| F9 | Prior-look ledger | log DNR:83-84 and the DNR:155-158 charter family; species-equivalence ruling for H1 | DNR:83-84,155-158; Ruling:21,30; Cell G:397 | equivalence of H1 vs SR2/SR3/charters | #8091 |
| F10 | Population freeze | conjunction: owner MOMENTUM label + identity RESOLVED + sole active equal-weight peer group + EXACT_NO_INSERTION calendar witness; K = 5 | R21:92; R20:47-53,59-65,78-85; script :61-89,200-271 | freeze the exact gate conjunction before capture | #8091 |
| F11 | Refused/empty-date treatment | refused rows at cash inside each arm's utility (full opportunity); empty sessions kept in the coverage vector | PREREG:181-182; Ruling:44; Cell G:289-291 | adopt | #8091 |
| F12 | Dispersion assumption for power | **OPEN** — assumption grid {50, 100, 200, 400} bps; seat picks the planning value or commissions a permitted-pilot estimate from the development partition only (never outcomes) | §5; DR:171; Cell G:369 | the planning σ (or its bounded estimation commission) | #8192 |
| F13 | PASS form | Holm-adjusted rejection of H0 μ ≤ 0 AND point estimate ≥ 50 bps AND F2 bound AND F3 not UNESTIMABLE-harmed; verdict PASS/REJECT/INCONCLUSIVE against the frozen rule | PREREG:209-215 pattern; Cell G:573-574,589; DR:174 | the form — stricter option: require LCB ≥ +50 bps instead of the point-estimate bar (OPEN) | #8091 |

Footnote to F13 (honest arithmetic, not a second proposal): at true μ exactly = 50 bps the joint
probability of clearing both significance and a point-estimate ≥ 50 bps bar is below 80% for any N;
the §5 table powers the significance component at μ = 50 bps. If the seat wants the table to
represent joint assurance it must either accept that subtlety or rule the stricter LCB form with
an explicit planning true effect — that choice is exactly what F13 reserves.

## 7. What this proposal does not do

- Does not admit H1, register anything, or start the trial; `trial_may_start` remains false until
  its owners' gates close (R20:93, R21:76). Definition is not admission.
- Reads no outcome: no grade, ledger, scoreboard, track-record, returns, H10 mark or accrual row
  value was opened; the S0 receipt was read as keys only. Nothing here is informed by an outcome.
- Changes no grader, prereg, threshold, cost floor, non-inferiority margin, cell definition or
  authority boundary; the existing −25 bps / 50 bps / Holm family registrations are consumed
  verbatim, never lowered or widened.
- Freezes nothing: every value in §1–§6 is PROPOSED and remains OPEN until the Fable seat rules
  and routes the frozen numbers to the #8091/#8192 owner.
- Claims no merge, push, PR, label or live authority; this file is the only artifact written.

## Source discipline

Files read in full or in part at BASE: Cell G law; Ruling; PREREG.json; DR; Q05 work card; Audit;
D07-01 ruling; DNR rows 83-84 and 155-158 (governance registry check mandated before research
work; their contents are historical PSS-family kill/hold facts from 2026-07-27, a different
species family — not H1/EL/B4 outcome data);
`r7_program/intel/INTEL_WORKLOG.md` and `INTEL_DISPOSITION_2026-10-21.md` (commissioning context).
PR heads, `git show` only: R20/R21 at `410965bd`; `scripts/check_prophet_h1_prospective_accrual.py`
(code only) and S0 JSON (keys only) at `07136c56`. Nothing under `data/` or `site/` was opened;
this sparse worktree excludes both by config. Outcome files avoided: none required avoidance — no
opened file turned out to hold outcomes.
