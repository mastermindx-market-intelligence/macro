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
status: active
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
waves:
  - id: CC-V1-CORE
    title: "V1-CORE deterministic composition"
    status: awaiting_ci
    next_action: >
      Carry PR #7942 to squash-merge on concluded-green. Contract + fixture +
      contract tests + pure projection + tests + exclusive CI gate, under the
      merged contracts/sector_intelligence family, carrying no transport mount
      identity.
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
    A new contracts/sector_intelligence/*.schema.json must expose
    properties.contract_id.const or the shared registry enumeration reds; a new
    exclusive CI job name must be added to CURATED_EXCLUSIVE in
    tests/test_ci_pack.py, which asserts exact set equality.
do_not_redo:
  - "R1-R11, the independent reviews, R12/R13 verification, R14 reconciliation"
  - "The R8 native-staging denial: never retry, rephrase, re-home or delegate around it"
  - "The V1 boundary adjudication itself - see DEC:CONSUMER-CYCLICAL-V1-CORE-EXTENDS-INCUMBENT-NOT-TRANSPORT"
next_action: >
  Carry PR #7942 to squash-merge on concluded-green, then return the four
  external blockers above to Sol. Do not widen into V2/V3/V4.
---

## Scope

V1-CORE is the maximal lawful V1 subset under current custody, not `V1 PROVEN_LIVE`.
It is the artifact the blocked transport and page legs will later publish unchanged.
