# TOI Daily-first model/evaluation freeze candidate — 2026-10-06

Disposition: PROPOSED_OWNER_ADOPTION_REQUIRED / W3 STILL HOLD / NO OUTCOMES READ.

This packet closes numerical and inference choices that were still null in the v2 22-object manifest without opening the market-outcome lane.

## Frozen numerical contract

One content-hashed pure-NumPy implementation is used: deterministic full-batch Newton steps with Armijo backtracking, zero initialization, gradient-infinity tolerance 1e-8 and no fallback solver. Binary and multinomial models optimize the report's literal objective: mean NLL + 0.5 x 1.0 x squared non-intercept coefficient norm.

This is deliberately not a verbatim reuse of the current cycle-hazard or transition fitters: those helpers divide the L2 gradient by sample size and therefore represent a different penalty scaling. Synthetic-only proof validates that distinction, convergence, probability normalization, calibration, Holm and deterministic block resampling.

## Chronological evaluation

Three expanding-origin outer tests are frozen: calendar 2024, calendar 2025 and mature 2026 origins through 2026-09-01. Each fold has a separate 126-session calibration slice. Exactly 22 strict NYSE sessions separate training-origin cutoff from calibration, and calibration from outer test.

The 22-session fence is construction-derived: trigger is known at completed close, P0 is the next lawful reference, and every delayed policy keeps the same 21-RTH-session terminal measured from that original P0 reference. Q1 never extends the deadline.

## Primary inference

Eight primary claims remain four mechanism questions x two directions. Primary resampling is circular 22-session moving calendar blocks, 5,000 draws, seed 20261006; all rows sharing a date move together. Fixed 44/66-session blocks are sensitivities only.

Holm step-down FWER at 0.05 applies to exactly eight claim p-values. Blocked, unrun or invalid claims enter as p=1. Each Q1 direction is one intersection-union claim: lower entered-episode fakeout rate, timely-capture noninferiority within 5pp on the full original trigger cohort, and mean wait-price cost <=0.25 frozen ATR. Its claim p-value is the maximum of the three component p-values.

## Calibration and historical honesty

Primary model comparisons use calibrated outer-test log loss. Binary models use one unpenalized Platt slope/intercept; multinomial activation uses one shared positive log-odds slope plus nonreference intercept shifts. Missing class, numerical failure or nonpositive slope blocks that fold's calibrated probability claim. Raw loss remains diagnostic only.

No 2021-2026 history is called untouched. The recovered historical panel is developmental/retrospective. Prospective shadow begins only after accepted preregistration/source freeze and must emit immutable predictions before labels mature.

## Still open before outcomes

W1 acceptance; W2/source acceptance; strict-population scientific adoption; authoritative corporate actions; exact runtime source snapshot; accepted detector/feature adapter bytes; exact activation person-period row construction; Q0/Q1 lawful-reference implementation; independent preregistration review; then TrialLedger registration. Execution-grade spread/impact remains a promotion gate; Corwin-Schultz is not adopted as trading cost.
