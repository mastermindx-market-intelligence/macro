# EVAL-1 preregistration rationale — 2026-10-07

This note explains `eval1_preregistration.v1.json` (K3E-EVAL-1-V1). Each value in that file is traced here to an owner-authored line. Where the sources left a choice open, the note says which way the registration went and why.

The registration contains no results. It was written before any EVAL-1 outcome existed, because its boundary is set after the commit that introduces it. No held outcome was read while writing it.

All citations are `path:line` at `origin/main` `bb7847a33c5fcaa3d2963e3c6be18d3628493966`. Short names used below:

| Short name | Path |
|---|---|
| PREREG | `research/alpha_intelligence/expectation_market_dynamics/EVALUATION_PREREG.md` |
| E0 | `research/alpha_intelligence/expectation_market_dynamics/eval0_preregistration.v1.json` (K3E-EVAL-0-V1; canonical digest `986ec117…ef87fd`) |
| E0R | `research/alpha_intelligence/expectation_market_dynamics/eval0_activation_receipt.v1.json` |
| R4 | `research/alpha_intelligence/expectation_market_dynamics/R4_DRYRUN_RECEIPT_2026-10-06.md` |
| PROG | `research/alpha_intelligence/expectation_market_dynamics/INFORMATION_TO_PRICE_PROGRAM_2026-10-03.md` |
| EMS | `research/alpha_intelligence/expectation_market_dynamics/EXPECTATION_MODEL_SPEC.md` |
| ADM | `engine/k3e_eval_admission.py` (the admission code that enforces this file's shape) |

## 1. Why there is an EVAL-1

EVAL-0's fixed eras run from 2012-01-03 to 2026-08-21, with the locked holdout ending 2026-08-21 (PREREG:77, E0:309-342). The accepted source starts in August 2026, so it cannot fill those eras. The program says the answer is reduced coverage or `UNESTIMABLE_AS_PROGRAM`, "not silently moving dates" (PROG:180, PREREG:80-83).

EVAL-0 permits only one kind of change: a new version with a new digest, an explicit reason and diff, explicit supersession, and a new forward boundary. Outcomes already seen stay attached to the old registration (PREREG:234-237, E0:10-16).

EVAL-1 is that new version. Its `amendment` block carries the reason, the diff, the supersession and the boundary. EVAL-0's bytes are untouched. The `predecessor` block binds EVAL-0's exact canonical digest and `prior_trial_budget_reset: false`, which ADM:279-285 enforces.

## 2. Which experiment — T1 at 21 sessions, and why not coupling (T7) yet

`admitted_experiments` holds one experiment, `K3E-EVAL1-T1_NEXT_REVISION_DIRECTION-H21`.

T1 qualifies on four counts:

- **It can lead to promotion.** It is "eligible after SRC-A1" (PREREG:102), and E0 gives it `promotion_eligible: true` (E0:457).
- **Its dependencies exist.** It needs SRC-A1 raw observations, a source contract and canonical identity (E0:458-462).
- **21 sessions is the only horizon every registered target shares.** That keeps a later coupling version comparable (PREREG:102-109).
- **EVAL-1's decision fields need a target that can promote.** `effect_size_threshold` and the decision law presuppose a comparison that can advance.

T7, the expectation/market lead-lag target, matches the R4 phase name ("R4 — coupling experiment", PROG:200), but it cannot be the admitted experiment today, for three reasons:

- **It cannot promote.** E0 registers T7 as reserved and non-promotion (PREREG:108, PREREG:117-118, E0:561).
- **It has no comparator.** Its comparison baselines B7 and B8 are fitted on development data only (E0:130, E0:141), and its label comes from a later deterministic coupling contract (E0:560).
- **Its upstream refused every ticker.** In the R4 dry-run, MKT-1 refused every ticker: `OWNER_STATE_INVALID` on 200 of 200 rows (R4:45) and on 399 of 399 (R4:48). The finding is MKT1-OWNER-FRAME-ABSENT (R4:100).

The conservative choice is to register the one experiment whose comparison can be decided, and to leave coupling for a later version with its own boundary. That version needs MKT-1 to produce owner frames first. This is a deferral, not a kill.

## 3. Value-by-value sources

The labels in the "Choice" column mean:

- **INHERITED:** the value is copied verbatim.
- **CONSERVATIVE:** the sources left the choice open and the stricter option was taken.
- **READING:** an interpretation, flagged for review.

| Field | Value | Source | Choice |
|---|---|---|---|
| `primary_endpoint` | T1 UP/DOWN/FLAT, horizon 21 sessions, E0 grain and cutoff | E0:455-456, E0:447, E0:449-454, E0:588, E0:592, PREREG:111-112 | INHERITED (horizon picked from the registered set) |
| cohort and identity | US primary-listed common equity; canonical identity at cutoff; no ticker guess; ADR and non-US rows descriptive | E0:418, E0:431-434, PREREG:63-69 | INHERITED |
| `primary_loss` | multiclass log loss, then Brier | E0:346, PREREG:165 | INHERITED |
| calibration, abstention | reliability/ECE/intercept/slope; risk-coverage by reason | E0:344-345, PREREG:166-170 | INHERITED |
| zero-probability handling | no clipping; a degenerate baseline is UNESTIMABLE, never infinitely bad | E0:383 (missing is not zero), E0:384 (no winner shopping) | CONSERVATIVE: a baseline can never lose by a numerical artifact |
| `strongest_baseline_rule` | B0 and B6 fit on F_DEV only; lowest loss in the same partition | E0:33-45, E0:107-122, PREREG:134-136 | CONSERVATIVE: the challenger must beat the in-partition minimum of the eligible baselines, which is the hardest comparator available |
| B1–B4 excluded as comparator | fitted_on `none`; deterministic values, not probabilities | E0:53, E0:66, E0:79, E0:90 | READING (see §5, item 1) |
| B5 excluded | REV-1 contract absent | E0:94-106, R4:91 | INHERITED |
| B6 single coverage band | no band set is declared on canonical main | E0:118 ("declared coverage band") | READING (see §5, item 2) |
| `effective_n_rule` | distinct issuer episodes; identity, gap, fiscal roll, overlap, no raw rows | E0:300-307, PREREG:87-96 | INHERITED |
| 100-episode floor in each of F_DEV, F_VAL and F_HOLD | the only owner-authored episode count | E0:304, E0:262 | CONSERVATIVE: a smaller F_DEV floor would be an invented number |
| subgroup floor | no promotion-bearing subgroup claimed | E0:305, E0:369 | CONSERVATIVE |
| identity known at cutoff | rows without canonical `issuer_ref` at cutoff are ineligible; no later backfill | E0:431, E0:590, PROG:197 ("no hindsight backfill") | INHERITED, applied strictly |
| `coverage_rule` | 0.60 scored, 0.60 named cases; abstentions kept in the denominator | E0:225-226, PREREG:179-182, E0:288 | INHERITED |
| challenger abstention | UNESTIMABLE when the challenger abstains on more than 0.40 of eligible rows | E0:291 | INHERITED |
| named cases in a forward window | only post-boundary rows answer; NVDA 2023 passes when it returns UNAVAILABLE or UNESTIMABLE; MRNA counts as unanswered unless post-boundary rows exist | E0:227-252, E0:243-244, PREREG:186-189 | CONSERVATIVE: a pre-boundary case is never answered from pre-boundary outcomes |
| `dependence_rule` | issuer-episode cluster bootstrap 95%; keys issuer_ref, episode_id, event_cluster_id | E0:295-299, E0:362, E0:260, PREREG:171-172 | INHERITED |
| date-block length | 63 sessions | E0:589, E0:596 (the registered embargo and purge) | CONSERVATIVE: the longest owner-authored session span gives the widest sensitivity band |
| bootstrap replicates and seed | fixed in evaluator code on canonical main before the first outcome read | — (computational, not scientific) | Time ordering freezes it; no number is invented here |
| `censoring_rule` | UP/DOWN inside (cutoff, +21]; FLAT needs an unchanged snapshot in [+21, +63]; otherwise censored | E0:446, PREREG:111-112, E0:593, E0:587, E0:382 | READING (see §5, item 3) |
| `forward_partitions` | F_DEV → 63-session purge → F_VAL → 63-session purge → F_HOLD → shadow | E0:309-342 (era roles), E0:589, E0:596, PREREG:71-78 | CONSERVATIVE (see §4) |
| `primary_horizon_sessions` | 21 | E0:449-454, PREREG:102 | Picked from the registered set |
| `total_search_budget` | 1 trial, drawn from the unreset 64-trial family | E0:176, E0:147, E0:175, E0:177, PREREG:140-155 | CONSERVATIVE: the smallest positive budget |
| prior family consumption | 0 | `data/trial_ledger.jsonl` at bb7847a33c5 (0 K3E rows); E0R:15 (no EVAL-0 challenger trial registered) | Observed |
| challenger family | REGULARIZED_LINEAR_OR_HAZARD | E0:150-152, PREREG:144 | CONSERVATIVE: the lowest-capacity registered family |
| challenger features | EXP-1 surface components with printed denominators only; identity committed before any F_DEV label is read | EMS:47-63, EMS:85-88, E0:177 | CONSERVATIVE (see §5, item 4) |
| `effect_size_threshold` | 0.05 relative primary-loss improvement in both F_VAL and F_HOLD | E0:259, PREREG:202 | INHERITED |
| multiple testing | BY at q = 0.10 over the cumulative family `k3e_expectation_market_dynamics_v1` | E0:174, E0:366-370, PREREG:157-161 | INHERITED, cumulative across EVAL-0 and EVAL-1 |
| terminal states, kill and unestimable law | as E0, with the locked holdout read as F_HOLD | E0:269-292, E0:372-381, PREREG:216-225 | INHERITED |
| authority | all false; research only | E0:18-29, PREREG:211-214, E0:277 | INHERITED |
| `freeze_boundary_rule` | identical string | E0:5, PREREG:42-47, ADM (first NYSE open strictly after the introduction commit) | INHERITED |

## 4. Forward partitions — the design and why it is the conservative one

EVAL-0's era roles are development, then validation, then a locked single final evaluation, then an append-only shadow with no retuning (PREREG:71-78, E0:309-342). The decision law requires the strongest baseline to be beaten, by at least 5%, in *both* validation and the locked holdout (E0:258-259, PREREG:201-202). EVAL-1 mirrors that structure forward in time:

1. **F_DEV** starts at the first eligible session after the boundary. It closes at the first session where its rows hold at least 100 distinct issuer episodes. This is the only partition where anything is fit: B0, B6 and the one challenger trial.
2. **PURGE_1** is 63 NYSE sessions, the registered purge and embargo (E0:589, E0:596). Labels are 21 sessions long and resolve within the 63-session censoring window, so no F_DEV label overlaps an F_VAL cutoff.
3. **F_VAL** closes at 100 distinct issuer episodes. The frozen challenger is compared with the strongest eligible baseline, with no refit.
4. **PURGE_2** is another 63 sessions.
5. **F_HOLD** closes at 100 distinct issuer episodes. It is locked and gets one final evaluation.
6. **PROSPECTIVE_SHADOW** follows. It is append-only and never promotion-bearing (E0:336-341).

Four rules hold across all partitions:

- **Closing on counts.** Partitions close on episode counts only, never on label direction, loss, a comparison, or a date picked after outcome access (PREREG:80-83). A partition that never fills stays open and reports `INSUFFICIENT_EPISODE_N` (PREREG:222-225).
- **Committing fitted artifacts.** Everything fitted is committed to canonical main before any label of a later partition is read. That covers the trial identity, its parameters, and the B0 and B6 probabilities. As a result, canonical-main time ordering, not anyone's word, shows that no later outcome shaped the fit.
- **Post-boundary rows only.** PREREG:45-46 allows pre-boundary rows to support retrospective work. EVAL-1 still admits only rows whose cutoff falls after the boundary. That is the stricter option, and it is what makes blinding hold by construction.
- **A two-stage forward test.** The single-trial budget makes a selection stage unnecessary. F_VAL is kept anyway, so the decision law's two-era requirement stays a real second test rather than collapsing into one.

## 5. Readings the reviewer should check

1. **B1–B4 cannot be the probabilistic comparator.** Their definitions emit consensus values or revision summaries (E0:52, E0:65, E0:78, E0:89), and they are `fitted_on: none`. Mapping one to a three-class probability would need a fitted calibration that EVAL-0 never registered. They are therefore reported descriptively (accuracy and confusion counts) and never become the strongest baseline. If the reviewer reads them as zero-fit class forecasts instead, the log loss is infinite whenever they miss, so they could not be the strongest baseline either way.
2. **B6 uses one coverage band.** E0:118 stratifies B6 by "declared coverage band", and no band edges are declared anywhere on canonical main. Inventing edges would put a scientific value into this file that no owner wrote. Declaring bands needs a new version.
3. **The censoring window.** The T1 censoring text (E0:446) writes the window as 63 sessions, which is the registered maximum horizon. At the 21-session primary horizon, this registration reads 21 sessions as the label window and 63 as the outer window for observation evidence:
   - A change observed inside 21 sessions gives UP or DOWN.
   - An unchanged successful snapshot observed between session 21 and session 63 gives FLAT.
   - Anything else is censored at the last observable session, never FLAT (PREREG:111-112).

   This avoids calling a row FLAT when the source simply was not observed at the horizon. It is a stricter reading than "unchanged so far means FLAT".
4. **The challenger's features are bound, not chosen.** No owner-authored spec names a T1 feature set. EMS:78-83 lists advanced challenger types as "later", and EMS:47-63 lists the derived surface components. Writing a feature list here would make this registration originate a hypothesis. Instead, the registration binds four things:
   - **Family:** the lowest-capacity registered family.
   - **Feature universe:** EXP-1 components with printed denominators.
   - **Timing:** the identity is committed before any F_DEV label is read, and every element must cite an owner line.
   - **Accounting:** committing the identity spends the trial.

   If no identity is committed in time, the challenger arm is UNESTIMABLE.

## 6. What this registration will report today

On current inputs, every partition will report `INSUFFICIENT_EPISODE_N`:

- **No identity yet.** The R4 dry-run found `issuer_ref` null on 11,200 of 11,200 and 22,344 of 22,344 rows (R4:123), and an episode count of zero (R4:68). Under the identity rule (E0:431), those rows are ineligible until the R1 identity owner delivers a mapping known at each cutoff. Identity backfilled later never makes earlier rows eligible.
- **No comparison yet.** No comparison can start before then. That is a correct first-class result (PREREG:222-225), not a defect of this registration.

## 7. Custody and blinding

Acceptance and activation are recorded in `agentos/decisions/DEC-K3E-EVAL1-CUSTODY-UNDER-CHAIRMAN-DIRECTIVE-2026-10-07.md`.

Blinding does not depend on who authors or accepts. ADM admits outcomes only after the boundary, and the boundary is fixed by canonical-main time ordering of this digest's first introduction commit. No outcome after the boundary existed when these bytes were written.

## 8. Bytes and schema

The canonical digest (ADM `_canonical_json_digest`: sorted keys, compact separators, UTF-8, SHA-256) of `eval1_preregistration.v1.json` as authored is `1ca158a213fca3f90c5c4fdc1359d40bf9146f2400cb10d8caa202b18f293bd4`. Any edit to the JSON changes it.

The owner acceptance and the activation receipt must bind the digest of the bytes that actually land on canonical main. They must also bind the first-parent commit on main that introduces that digest (ADM:144, ADM:391-420).

The schema of record is the one ADM enforces in `_registration_reason` (ADM:271-325). `contracts/research/k3e_expectation_market_dynamics_evaluation_prereg.v1.schema.json` is the EVAL-0 contract: its `registration_id` is fixed to `K3E-EVAL-0-V1`, so it does not apply to EVAL-1. A separate EVAL-1 JSON-schema contract was not added, so that the contract does not exist in a second place.
