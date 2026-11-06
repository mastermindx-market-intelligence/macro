---
workstream: "WS:CONSUMER-CYCLICAL-V1"
session: claude/ssd-consumer-cyclical-plnt-case-reconciliation
model: opus
ended_because: complete
mission: >
  Close the one ungated item left after PR #8054 merged: reconcile the synthetic
  _plnt_case() with the contract the projection authors (102 violations), and
  repair the fidelity gap #8054's own live verification exposed.
state_before: >
  #8054 merged (squash 8d88ca16da48) and verified live from main: fixture case
  0 violations, R6 7.1 golden oracle exact. Two things were left open there.
  (1) _plnt_case() still emitted 102 violations on fields the admission gate
  does not police. (2) Live verification found the named admission reason never
  reached the document - the per-dependency dedup dropped it whenever
  _compose_changes had already declared a reason for the same dependency.
changed:
  - path: tests/test_consumer_cyclical_projection.py
    what: >
      Reconciled _plnt_case() with its contract. Six one-key source_record
      stubs became the single real Exhibit 99.1 record the committed fixture
      asserts. perimeter stopped holding the contract id; kind is stated per
      metric instead of defaulting to "financial" (outside its own enum);
      display_quantum became "1_thousand" instead of the unit label "USD
      thousands"; definition is a real sentence instead of ""; subject lost
      company_name/fiscal_period_end/comparison_basis (the object is closed)
      and gained subject_type; the evidence document filename typo
      plntq2202026... was corrected. A new period_role argument gives the two
      facts of a pair distinct keys, which is what input_refs names. Added four
      tests.
  - path: engine/sector_intelligence/consumer_cyclical_projection.py
    what: >
      A refusal now supersedes the no_compatible_pair_for_comparison_basis it
      caused, for the same dependency only. _compose_changes keys that reason
      on the METRIC, which is exactly what a refusal is keyed on, so the effect
      landed first and the cause was deduplicated away.
  - path: agentos/workstreams/WS-CONSUMER-CYCLICAL-V1.md
    what: >
      Added wave CC-V1-CASE-RECONCILIATION (done), three landmines, and cleared
      the open 102-violation next_action.
verified:
  - claim: "Both cases the projection can be handed now validate at zero violations."
    command: "python3 -c harness running Draft202012Validator over project_economic_change(_plnt_case()) and project_economic_change(_fixture_case())"
    result: "synthetic 102 -> 0; fixture 0 -> 0."
  - claim: "The R6 7.1 golden oracle is unchanged by the reconciliation."
    command: "same harness, comparing the six ready result value_texts"
    result: "24344 / 10141 / 10145 / -4 / 0 / 41.66 EXACT on both cases."
  - claim: "Owned suite green."
    command: "python3 -m pytest tests/test_consumer_cyclical_projection.py tests/test_consumer_cyclical_intelligence_read_model_contract.py -q"
    result: "76 passed (projection 60, contract 16); was 72."
  - claim: "The new tests are non-vacuous."
    command: "9 mutants applied to the real engine and helper, suite re-run after each"
    result: >
      8 killed (perimeter, display_quantum, subject_type, kind, pair-key
      collision, refusal-loses-to-effect, dangling native_ref, empty
      definition). M7 - widening the supersede guard from
      `== no_compatible_pair_for_comparison_basis` to unconditional - SURVIVED
      and is reported as EQUIVALENT, not as a gap: an exhaustive sweep of three
      refusal triggers x one-or-both sides x three metrics showed every
      reachable collision already resolves to the admission reason itself, so
      the overwrite writes the same value in every case the module can reach.
  - claim: "The CI job inventory still resolves this suite."
    command: "python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --validate-only"
    result: "consumer-cyclical-economic-change present in the selected jobs."
  - claim: "The Agent OS store validates."
    command: "python3 scripts/agentos.py validate"
    result: "0 errors."
unverified:
  - claim: "The supersede guard's narrowing is worth keeping despite M7 being equivalent."
    what_would_verify: >
      A reachable input where _compose_changes declares a reason for a metric
      dependency that is NEITHER no_compatible_pair_for_comparison_basis NOR
      the admission reason. None was found; the narrowing is defensive
      precision against a future third reason, not a behaviour anything
      observes today.
unresolved:
  - >
    All four external V1 gates remain unmoved: #7870 T09 rights correction,
    #7780 mount ruling, #7669 page custody, and native source admission of the
    PLNT Q2 2026 exhibit. Nothing ungated is left at this seat.
next_actions:
  - "Watch this PR to merge, then verify from main's bytes as #8054 was."
  - >
    Only on a fresh Sol edge on #7804: consume the #7870 T09 rights correction
    and the #7780 mount ruling for the entitled/browser legs.
do_not_redo:
  - "Everything in WS-CONSUMER-CYCLICAL-V1-2026-09-26.md's do_not_redo, unchanged."
  - >
    The _plnt_case() reconciliation. Both cases are at zero violations and the
    oracle is pinned; re-deriving the source_record fields risks inventing an
    accession, and the values used are the ones the committed fixture asserts.
  - >
    Reverting the supersede branch in project_economic_change. It was reverted
    once in this session on a false diagnosis - a vacuous test made it look
    redundant - and restored when a corrected test showed the collision is real
    on clean code.
danger_areas:
  - >
    Everything in the 2026-09-26 handoff's danger_areas, unchanged, plus: a
    mutation test is only as good as its mutant. `definition = "" or (...)` is
    a no-op, not a mutant, and it read as a surviving mutant until inspected.
  - >
    data/ can be materialised for the fixture alone with
    `git sparse-checkout add data/sector_intelligence` - 2.2 MB, against 4.6 GiB
    for `worktree_sparse.py add data`. The volume is an admission gate for every
    new worktree, so prefer the narrow path.
---

## The part worth reading

The reconciliation itself was mechanical. The instructive failure was in the tests
written to pin it.

`test_a_refusal_names_its_cause_not_only_its_effect` refused BOTH facts of a pair.
That removes the metric from `_compose_changes` entirely, so nothing is ever
declared for it, so no cause-versus-effect collision can form — the test passed
against a mutant that deleted the exact behaviour it claimed to pin. Worse, the
same vacuity made the wrong repair look right: reading "the mutant survived" as
"the engine fix is redundant", the engine fix was reverted. It took a corrected
test — one side refused, not both — to show the collision is real on clean code
and restore it.

Both halves of that are the same error the discovery record
`DSC:THE-CASE-A-SUITE-USES-MOST-IS-THE-ONE-IT-NEVER-VALIDATES` is about, committed
one wave later by the session that wrote it: an input chosen so the thing under
test cannot occur, and a green read as evidence.
