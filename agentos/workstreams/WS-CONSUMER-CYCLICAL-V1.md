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
      OPEN: the synthetic _plnt_case() still carries 102 violations on fields
      the gate does not police - see the follow-up in next_action.
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
    period_start must never be derived from period_end. Consumer Cyclical is
    retail: 4-5-4 fiscal quarters are offset from the calendar by design, so
    calendar-snapping produced valid-looking 32-day "quarters". The derivation
    was unreachable when deleted, which is exactly why it survived review.
do_not_redo:
  - "R1-R11, the independent reviews, R12/R13 verification, R14 reconciliation"
  - "The R8 native-staging denial: never retry, rephrase, re-home or delegate around it"
  - "The V1 boundary adjudication itself - see DEC:CONSUMER-CYCLICAL-V1-CORE-EXTENDS-INCUMBENT-NOT-TRANSPORT"
next_action: >
  OPEN AND OWNED BY THIS WORKSTREAM (does not need any external gate): reconcile
  the synthetic _plnt_case() with its own contract. 102 violations remain on
  fields the admission gate deliberately does not police - definition,
  display_quantum, kind, perimeter, source_records, subject, and duplicate
  input_refs from two facts sharing a key. Measured, not estimated: run
  `python3 -c` over jsonschema Draft202012Validator against
  contracts/sector_intelligence/consumer_cyclical_intelligence_read_model.v1.schema.json.
  It ripples into ~40 assertions, which is why it was deferred rather than
  rushed in behind the admission gate.
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
