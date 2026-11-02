---
key: A-MUTATION-THAT-DIES-UPSTREAM-NEVER-TESTS-THE-GATE-YOU-AIMED-AT
claim: >
  A probe or mutant aimed at gate G proves nothing about G if its input is rejected by
  an earlier gate G'. The run still LOOKS conclusive -- a refusal happens, a reason is
  declared, the mutant appears killed -- so the vacuous green is indistinguishable from
  a real one unless the declared reason is read. Measured twice on Consumer Cyclical V1
  (`engine/sector_intelligence/consumer_cyclical_projection.py`). (1) Wave-6 mutant W7
  relabelled ONE side's `period_kind` to test the new declared-basis binding, but
  `_select_pair` already required both sides to share `period_kind`, so the pair
  collapsed for a PRE-EXISTING reason and the mutant survived a test that appeared to
  exercise the new guard; it died only once BOTH sides were relabelled. (2) Probing
  pair-agreement on `sign_convention` with `negated_from_reported` returned a confident
  "caught and declared" -- but that value is not in `_SIGN_CONVENTION_ENUM`, so
  `_fact_admission_failure` refused the fact and the pair-agreement check was never
  reached. Re-run with the two LEGAL alternatives (`unsigned_magnitude`,
  `signed_difference`) the real check DID fire on both sides, so the module was sound --
  but the first probe's green was vacuous and was one step from shipping as a clean
  bill of health for a gate never exercised.
falsifier: >
  Any gate-coverage claim whose mutation was not shown to REACH the gate: no assertion
  that the observed refusal reason names the intended gate, or a mutated value that
  fails any check upstream of it. Concretely, re-run
  `python3 scratchpad/sign_probe.py` with an out-of-enum sign convention and observe
  `fact_sign_convention_missing_or_malformed` rather than
  `no_compatible_pair_for_comparison_basis`: same "refused", different gate.
so_what: >
  Positive-controlling the instrument (§3.4 -- does it fire at all?) is necessary but
  NOT sufficient. You must also control the PATH: does this input reach the gate under
  test? Three cheap disciplines, each measured in this session. (1) Mutate only to
  values LEGAL everywhere upstream of the gate under test -- an illegal value tests the
  vocabulary check, never the logic behind it. (2) Assert the DECLARED REASON matches
  the intended gate, not merely that a refusal occurred; the reason string is the only
  thing that distinguishes the two, and both probes above printed a refusal.
  (3) Guard every mutation with an explicit no-op assertion -- in this same session a
  `scale_power10: 3 -> 3` mutation reported a clean pass, because the fixture already
  held 3 and nothing changed. This is the dual of
  DSC:A-MINTING-DEFAULT-IS-INVISIBLE-TO-AN-EMPTINESS-GATE so_what (3) ("absence and
  malformedness are two tests, not one"): that one is about two halves of ONE check,
  this one is about a probe that never arrives at the check at all. Binds every session
  doing mutation or gate-coverage work on the GMI sector verticals, which layer
  vocabulary checks in front of pairing logic by construction.
kind: landmine
verified_at: 2026-09-27
verified_by: >
  Direct probe of #8103's head bytes: `scratchpad/disagree_probe2.py` (five pair
  disagreements, each with an explicit no-op assertion) and `scratchpad/sign_probe.py`
  (both sides x both legal alternatives), plus `python3 -c "from
  engine.sector_intelligence import consumer_cyclical_projection as M;
  print(sorted(M._SIGN_CONVENTION_ENUM))"` showing `negated_from_reported` is not a
  member. Wave-6 case (1) is the W7 mutant recorded in
  agentos/handoffs/WS-CONSUMER-CYCLICAL-V1-2026-09-27-declared-basis-binding.md.
scope: >
  Mutation testing and gate-coverage probing of layered validators, specifically the
  GMI sector-vertical projections that run a vocabulary/admission gate ahead of pairing
  and emission logic.
confidence: verified
---
