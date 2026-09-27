---
key: CONSUMER-CYCLICAL-V1
title: "Consumer Cyclical V1 — PLNT economic-change vertical (Fable integration program)"
objective: >
  Take the accepted R15 Consumer economics design to a real source-bound,
  entitled, browser-visible PLNT economic-change experience. Done means an
  entitled user opens PLNT and sees a source-bound explanation of the selected
  reported revenue/advertising change with correct signs, scale and limitations,
  with anonymous users receiving no paid closure. V1-CORE (the deterministic
  composition) is the merged first wave; the entitled/browser legs stay frozen
  behind external owners.
status: blocked
program: earnings-intelligence
repos: [macro]
owner: fable-integration-principal
class: build
blast_radius: reversible
ambiguity: specified
owns_paths:
  - contracts/sector_intelligence/consumer_cyclical_intelligence_read_model.v1.schema.json
  - data/sector_intelligence/fixtures/consumer_cyclical_intelligence_read_model.v1.valid.json
  - engine/sector_intelligence/consumer_cyclical_projection.py
  - tests/test_consumer_cyclical_intelligence_read_model_contract.py
  - tests/test_consumer_cyclical_projection.py
  - research/consumer_cyclical/v1/**
decisions:
  - "DEC:CONSUMER-CYCLICAL-V1-CORE-EXTENDS-INCUMBENT-NOT-TRANSPORT"
  - "DEC:CONSUMER-CYCLICAL-REFUSES-FACTS-IT-CANNOT-PUBLISH"
discoveries:
  - "DSC:A-UNIVERSAL-FALLBACK-BRANCH-IS-INVISIBLE-TO-A-VALUE-ONLY-SUITE"
  - "DSC:THE-CASE-A-SUITE-USES-MOST-IS-THE-ONE-IT-NEVER-VALIDATES"
waves:
  - id: CC-V1-CORE
    title: "V1-CORE deterministic composition"
    status: done
    next_action: >
      Merged as PR #7942 (squash 6e3e8987c5c6, 2026-09-24T13:07:49Z) and verified
      live from main: all six R6 7.1 golden values exact from native_admitted
      false facts, 0 schema errors, 61 tests green on the merged tree. That live
      verification then found the economic lead unreachable on every input (see
      landmines); repaired plus a same-class hardening pass on PR #7945, 65 tests.
  - id: CC-V1-ENVELOPE-INTEGRITY
    title: "Fact admission gate + document self-check"
    status: done
    next_action: >
      A coverage audit of the merged module (110/723 executable lines never
      executed under the full owned suite) escalated into the finding that the
      projection publishes documents violating the contract it authors, on
      ordinary inputs - most damningly a thousands separator in a financial
      figure. Repaired by refusing rather than repairing: unpublishable facts
      are withheld and declared through the existing degraded_dependencies
      vocabulary, and an end-of-projection self-check raises CaseShapeError
      rather than returning a contract-violating document. See
      DEC:CONSUMER-CYCLICAL-REFUSES-FACTS-IT-CANNOT-PUBLISH. Suite 65 -> 72.
      The 102 residual violations it left open are CLOSED by
      CC-V1-CASE-RECONCILIATION below.
  - id: CC-V1-CASE-RECONCILIATION
    title: "Synthetic case reconciled with its own contract"
    status: done
    next_action: >
      _plnt_case() 102 violations -> 0, golden oracle exact on both the
      synthetic and fixture cases. Six one-key source_record stubs became the
      single real Exhibit 99.1 record the committed fixture asserts (a results
      press release carries the prior-year comparatives in the same table, so
      six facts genuinely share one document); perimeter stopped holding the
      contract id; kind stopped defaulting to "financial", a value its own enum
      does not contain; display_quantum became a quantum instead of a unit
      label; subject lost three keys a closed object rejects and gained
      subject_type; and the two facts of a pair stopped sharing one bare
      FACT_KEY_* spelling, which had been publishing non-unique input_refs.
      One engine change: a refusal now supersedes the
      no_compatible_pair_for_comparison_basis it caused, because
      _compose_changes keys that reason on the METRIC - exactly what a refusal
      is keyed on - so the effect landed first and deduplicated the cause away.
      Suite 72 -> 76.
  - id: CC-V1-ENTITLED
    title: "V1 entitled + browser legs"
    status: todo
    next_action: >
      Consume the #7870 T09 rights correction and the #7780 mount ruling when
      they land, then take the shared private transport and company page. Frozen
      behind external owners whose heads have not moved since the R15 freeze.
blocked_by:
  - "#7870 T09 EDGAR-family/fail-closed rights correction plus T08b/T10e/T10f/T11a"
  - "#7780 cross-vertical profile/dispatch/mount ruling (owns the R15 H2 grammar)"
  - "#7669 template/page custody for the company-page consumer"
  - "incumbent source owner must natively admit the PLNT Q2 2026 exhibit"
landmines:
  - >
    app/earnings.py LOOKS like an opening (merged, entitled, private/no-store)
    and is not: R15 H1 superseded direct Earnings delivery for this dossier and
    pre-labels it "not a second publisher"; engine/earnings_narrative/** belongs
    to CDV-1 (#7792).
  - >
    native_admitted is a PROVENANCE LABEL, never a suppression gate. Gating on
    it makes the projection structurally incapable of its own golden case,
    because PLNT's exhibit is retained nowhere.
  - >
    Fact keys and result keys are DISJOINT vocabularies that read alike. The
    lead was unreachable on every input because _build_explanation tested
    FACT_KEY_* constants for membership in the set of RESULT keys, and 61 tests
    stayed green because every asserted NUMBER was still exact - only the
    sentence explaining them was missing. Never spell a result key by
    concatenating onto a FACT_KEY_*; the spellings coincide today, so drift
    would be silent. Pinned by test_result_keys_and_fact_keys_are_never_
    interchangeable.
  - >
    A new contracts/sector_intelligence/*.schema.json must expose
    properties.contract_id.const or the shared registry enumeration reds; a new
    exclusive CI job name must be added to CURATED_EXCLUSIVE in
    tests/test_ci_pack.py, which asserts exact set equality.
  - >
    The suite's own fixture builders are the least-validated inputs in the
    project. _plnt_case() drove most of the 65 green tests while producing 128
    schema violations, because every assertion read a computed NUMBER and none
    read the document's SHAPE. When the self-check landed, 26 tests went red -
    the correct reading is "the helper was always wrong", never "the check is
    too strict". Narrowing the instrument to restore green is the vice this
    workstream has already committed once.
  - >
    input_refs names the fact KEY (see _fact_ref) and the contract declares it
    uniqueItems, so the two facts of a pair must not share a key. Spelling both
    sides with one bare FACT_KEY_* constant published
    ["advertising_expense", "advertising_expense"] for every same-metric
    change. Pinned by test_the_two_facts_of_a_pair_never_share_a_key.
  - >
    native_ref and source_records[].record_id are spelled in two places and the
    contract validates each in isolation, so both patterns pass while the
    pointer dangles. Pinned by
    test_every_native_ref_resolves_to_a_declared_source_record.
  - >
    A test that mutates BOTH sides of a pair cannot observe a
    cause-versus-effect collision, because removing the metric entirely means
    _compose_changes never declares anything to collide with. The first version
    of test_a_refusal_names_its_cause_not_only_its_effect did that, passed
    against a mutant that deleted the behaviour it claimed to pin, and the same
    vacuity then made reverting the real engine fix look safe. Mutate one side.
  - >
    period_start must never be derived from period_end. Consumer Cyclical is
    retail: 4-5-4 fiscal quarters are offset from the calendar by design, so
    calendar-snapping produced valid-looking 32-day "quarters". The derivation
    was unreachable when deleted, which is exactly why it survived review.
do_not_redo:
  - "R1-R11, the independent reviews, R12/R13 verification, R14 reconciliation"
  - "The R8 native-staging denial: never retry, rephrase, re-home or delegate around it"
  - "The V1 boundary adjudication itself - see DEC:CONSUMER-CYCLICAL-V1-CORE-EXTENDS-INCUMBENT-NOT-TRANSPORT"
next_action: >
  Nothing ungated remains at this seat. Both cases the projection can be handed
  - the synthetic _plnt_case() and the committed fixture - now validate at zero
  violations against the contract this module authors, with the R6 7.1 golden
  oracle exact on both. The remaining V1 legs are all owner-gated.
  .
  Returned to Sol on carrier #7804 (comment 5814888647, 2026-09-24) naming the
  four blockers below and correcting that carrier's standing
  RECEIVER_ASSIGNMENT NONE, which would otherwise have licensed a second Fable
  receiver onto the same operation. Nothing further is executable at this seat:
  the remaining V1 legs are all owner-gated. Do not widen into V2 LTH / V3 LULU
  / V4 theme journey - R15 forbids self-authorizing them on a V1 pass, and the
  next modifying wave takes its own continuation edge.
---

## Scope

V1-CORE is the maximal lawful V1 subset under current custody, not `V1 PROVEN_LIVE`.
It is the artifact the blocked transport and page legs will later publish unchanged.
