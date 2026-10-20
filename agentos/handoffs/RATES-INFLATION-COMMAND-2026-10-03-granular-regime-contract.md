---
workstream: WS:RATES-INFLATION-COMMAND
session: claude/granular-regime-intelligence-lead-8387ff
model: fable
ended_because: complete
mission: >
  Granular Regime Intelligence programme (issue #8317, parent PR #7088). This checkpoint covers
  one deliverable of a continuing programme: freeze the contract that the first descriptive
  state-and-paths vertical is built against, after independent adversarial review, so builders,
  reviewers and researchers work from one reviewed document instead of the issue thread.
state_before: >
  The programme packet in #8317 named the outcome (Now, What changed, Paths, History, Exposures,
  Watch) and the workcards, but no document said which owner fields a path reading may use,
  what a reading means, or what a later outcome study must do first. Four draft pull requests
  (#8257, #8301, #8304, #8306) were BUILT_NOT_PROVEN under HOLD-FOR-SOL with open review
  findings; #7871 (cycle-vintage collector) was unfinished. The parent architecture (#7088)
  is unmerged.
changed:
  - path: research/macro_regime_intelligence/STATE_PATH_AND_SCIENCE_CONTRACT_2026-10-03.md
    what: The contract, revision 3.1. Product workflow, the additive `regime_outlook` projection inside the Rates & Inflation Command artifact, nine overlapping path hypotheses, the verdict mapping `VERDICT_MAPPING_V1` pinned to producer code at main 5f20adbd6be6, rules R-A to R-I, the owner defects to repair first (slice E0), the science rules and seen-history register, the build slices E0 to E3, and three change logs (§15 to §17) answering 54 review findings one by one.
  - path: agentos/decisions/DEC-GRANULAR-REGIME-OUTLOOK-CONTRACT-V1.md
    what: The decision record for the choices that are expensive to revisit — one writer and one projection, readings as statements about wording, admission from producer code, one row convention, no cross-path arithmetic, an authored and versioned mapping, preregistration before any outcome is inspected.
verified:
  - claim: The Agent OS records validate with the new decision and this handoff present.
    command: python3 scripts/agentos.py validate
    result: 0 errors (warnings are pre-existing review-overdue notices on other records).
  - claim: Every producer rule quoted in Appendix A matches the code at the pin.
    command: git show 5f20adbd6be6b136b2efe41585bd4ef964b5bf2e:<path> | sed -n '<lines>p' for engine/rate_inflation_transmission.py (223-261, 356-388, 422-423), engine/conditions.py (535-538, 622, 738-748, 973-974), engine/regime.py (183-202), engine/market_state.py (100-105, 317-321), engine/yield_momentum.py (159-182), engine/leadership_crack.py (319-323, 342), engine/run.py (987-993)
    result: Matched by the seat and re-verified independently by the read-only reviewer in its confirmation pass (items I-1 to I-9 of its report); the one guard it could not confirm (leader-damage clock) was rebuilt in revision 3.1.
  - claim: The worked example in A.6 follows from the rules and the pin-date artifacts.
    command: Recomputed by hand from `git show 5f20adbd6be6:data/{transmission,regime,market_state,leadership_crack,bonds}/latest.json` field reads, by the seat and separately by the reviewer.
    result: Every cell matched under revision 3; revision 3.1 changes three cells (OD-6 removed, TP-6 unknown, LH-1 wording) and the family roll-ups were updated with them.
unverified:
  - claim: The mapping reads sensibly on dates other than the pin.
    what_would_verify: Slice E1r — the labelled hindsight coverage replay on the four dates fixed in rule R-I (2018-10-31, 2019-08-30, 2022-06-30, 2022-10-31). It may only move tokens to unknown or tighten guards.
  - claim: Publishing null instead of a default token or 0.00 (slice E0) breaks no page render or nightly step.
    what_would_verify: The read-only consumer census commissioned on 2026-10-03 (who reads each owner field E0 changes and what a null does there), then the E0 slices' own tests and one natural nightly run.
  - claim: Anything in this contract is visible in the served product.
    what_would_verify: Nothing is built yet. The first served surface is slice E2, which needs a committed mockup ratified by the operator before any template work.
  - claim: The four held pull requests' repaired candidates are correct.
    what_would_verify: Each has its own exact-head independent review, concluded CI and a RESULT / HOLD-FOR-SOL on its own carrier; none of that is claimed here.
unresolved:
  - "#8257, #8301, #8304 and #8306 remain DRAFT under HOLD-FOR-SOL. This seat prepares repaired candidates on `claude/gri-*` lane branches and brings each to its gate; release stays with Sol."
  - "#7871 belongs to its own owner branch. The seat's candidate (collector contract enrolled in the merge gate) is offered on that carrier, never pushed to the owner's branch."
  - "The live verification of #8257's served block is still owed. The earlier production-artifact capture was safety-denied and is not to be retried in any form."
  - "The parent decision and discovery records live only on unmerged #7088; this checkpoint cites the pull request, not record keys that do not exist on main."
next_actions:
  - "Slice E0 (owner repairs, micro-sliced from the consumer census): no token when the input is missing; per-field clocks; the Rates Command `asof` fallback and `compact_state.usd_dir`; publish the dollar rate of change; publish which leg set the credit-stress flag."
  - "Slice E1: the `regime_outlook` projection with the rule-pin test (R-E) and the mapping lint test (R-H). Slice E1r: the coverage replay. Slice E2 only after a committed mockup is ratified. Slice E3: Brain and Macro Command readers."
  - "Finish the per-PR chains for #8257, #8301, #8304, #8306 and the #7871 offer; then compose the four repaired candidates on current main with a single writer for `.github/ci/legacy-jobs.yml`."
  - "Workcards D (qualified history), F (owners for the eight evidence families that have none), G (#7441 answer evaluation; preregistered baseline-first transition study) and H (cross-product integration) per #8317."
do_not_redo:
  - "Do not re-open the reviewed choices in the decision record without new evidence: no probability, rank, score or cross-path count; no negated statements; the owner's middle token is always not_discriminating; no reading from a bare-sign verdict or a default token whose input is not published."
  - "Do not re-admit the breakeven cause badge as a reading (retired OD-6, §17 C-B1) or give equity breadth a side for a rates turn (TP-6, §17 C-S1). Both were tried and rejected on review."
  - "Do not build a second regime engine, history store, evaluator or page for this. The projection is one additive key in the Rates & Inflation Command artifact."
  - "Do not re-run the three producer-code audits or the review rounds; their findings and answers are in §15 to §17."
danger_areas:
  - "Appendix A is pinned to producer code at 5f20adbd6be6. A producer rule change after that commit silently invalidates a row until slice E1's rule-pin test exists; re-check the cited lines before building against a later main."
  - "At the pin a missing core-PCE input reads `below target`, a missing change reads `stable`, and eight `state` numbers are written as 0.00 when missing. Until slice E0 lands, the guards in rule R-B are the only thing standing between those defaults and a reading."
  - "The coverage replay (R-I) is the one permitted look at the motivating episodes. Using it to move any token into fits or does_not_fit, or to choose between paths, is fitting on seen history and is forbidden by the contract."
  - "A hold recorded on a pull request binds every merge path. Never arm, mark ready or merge #8257, #8301, #8304 or #8306 from this workstream."
decisions: ["DEC:GRANULAR-REGIME-OUTLOOK-CONTRACT-V1"]
discoveries: []
---

# WS:RATES-INFLATION-COMMAND — Granular Regime Intelligence contract checkpoint (2026-10-03)

This is a checkpoint of a continuing programme, not its end. It records one frozen deliverable
so the work survives a session change.

## What exists now

One reviewed contract and one decision record. Nothing is built against them yet, and nothing in
them is visible in the product.

The contract says what the first vertical publishes: a description of the current state family
by family, what changed since the previous completed session, and nine path hypotheses that may
overlap. Each path is a short list of positive statements. Each statement reads one owner
verdict and yields one of four readings: fits, does not fit, not discriminating, unknown. There
is no probability, no ranking and no forecast.

## How it was reviewed

Three independent read-only audits of producer code established which owner tokens exist, how
each is decided and what each does when its input is missing. Three adversarial review rounds
then attacked the drafts. They returned 16, 26 and 12 findings. Every finding was accepted, and
§15, §16 and §17 of the contract list each one beside the change that answers it.

The findings that mattered most:

- Several owner tokens are the default for a missing input. A missing core-PCE number reads
  "below target". The contract now reads a default token only when the number behind it is
  published.
- Negated statements ("is not cooling") counted the owner's middle token as agreement. Every
  statement is now positive, and the middle token never counts either way.
- The credit-stress flag can be set by a bare sign. It is read only when the published numbers
  prove which leg set it.
- Two rows gave a side to evidence that has none (priced rate rises against a premium shock;
  equity breadth for a rates turn). Both are now open rows that read unknown.

## What the pin date shows

On the 2026-10-02 artifacts every path card has at least one evidence family that cannot be
read, and every market-structure card lacks an owner for the discriminators that define it.
That is the honest output of version 1, and it sets the order of the owner work that follows.

## Where the rest of the programme stands

The four held pull requests and the collector pull request are being repaired on lane branches
by bounded workers, each under independent exact-head review. Their state is on their own
carriers and in issue #8317; this record makes no claim about them.
