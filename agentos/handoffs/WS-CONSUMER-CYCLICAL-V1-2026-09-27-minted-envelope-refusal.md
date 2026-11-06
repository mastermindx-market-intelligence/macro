---
workstream: "WS:CONSUMER-CYCLICAL-V1"
session: claude/ssd-consumer-cyclical-admission-gate-completes-the-class
model: opus
ended_because: complete
mission: >
  Re-test the standing claim "nothing ungated remains at this seat" by observation
  rather than by memory, and execute whatever it turns up inside owns_paths.
state_before: >
  PR #8078 merged (squash 5ed5357db1b9) and proven from main's own extracted bytes:
  both cases 0 schema violations, R6 7.1 golden oracle exact, 76 tests green. The
  workstream's next_action read "Nothing ungated remains at this seat". Re-tested:
  all four external gates (#7426 / #7462 / #7669 / #7780 / #7870) are still OPEN or
  DRAFT, and `git grep -n consumer_cyclical_projection` outside the module's own
  suite returns nothing on main - V1-CORE is merged, correct and inert until #7780
  rules on the mount. So no ungated WIRING lane exists. The claim was nonetheless
  too strong: it silently covered ungated CORRECTNESS work inside owns_paths, and
  there was some.
changed:
  - path: engine/sector_intelligence/consumer_cyclical_projection.py
    what: >
      Completed _fact_admission_failure's own class, +60 lines in the module's
      existing idiom. The wave-3 gate was generalized from four readers that answer
      an absent source value with an EMPTY sentinel, so it asks "is this field
      empty?" - a question that is unanswerable for a reader whose purpose is to
      never be empty. Added: nine spelled text fields via
      _REQUIRED_SOURCE_TEXT_FIELDS (basis, definition, display_quantum, event, key,
      metric, perimeter, role, unit), kind checked against _ALLOWED_KIND by VALUE
      rather than for presence, sign_convention against its enum, a scale_power10
      arm that accepts exactly what _envelope_scale can already read unambiguously
      (an int or a digit string - the source grammar is not tightened), and an
      evidence Mapping arm. `event` moved into the gate on purpose: its absence used
      to raise CaseShapeError and kill the whole case, where every sibling omission
      withholds one fact and declares it. One bad fact is not a bad case.
  - path: tests/test_consumer_cyclical_projection.py
    what: >
      60 -> 86 tests. test_no_required_envelope_field_is_ever_minted (13
      parametrizations) asserts 0 schema errors, a non-empty degraded_dependencies,
      AND `len(document["facts"]) == admitted` - that count assertion is
      load-bearing, see the do_not_redo note below.
      test_the_three_silent_fabrications_are_refused_not_published pins the three
      that validate while lying. test_a_present_but_empty_envelope_field_is_refused_
      too (11 parametrizations) pins the malformed half of a reason spelled
      missing_or_malformed. test_a_kind_outside_the_contract_enum_is_refused_by_value
      pins the enum check as a value check.
  - path: agentos/discoveries/DSC-A-MINTING-DEFAULT-IS-INVISIBLE-TO-AN-EMPTINESS-GATE.md
    what: "New. The durable finding, its falsifier, and the line the repair draws."
  - path: agentos/workstreams/WS-CONSUMER-CYCLICAL-V1.md
    what: >
      Added wave CC-V1-MINTED-ENVELOPE-REFUSAL (done), one landmine, the discovery
      link, and replaced the too-strong "nothing ungated remains" next_action with
      what was actually measured.
verified:
  - claim: >
      On merged main, 17 of the 21 contract-required fact fields were unguarded, and
      three of them let the module publish a schema-VALID document that lies.
    command: >
      Positive-controlled sweep (scratchpad sweep3.py) over main's extracted bytes at
      386c98edda2c - for each field plant a distinctive value, assert it reaches the
      published fact, then drop it and validate the emitted document with
      jsonschema.Draft202012Validator against
      contracts/sector_intelligence/consumer_cyclical_intelligence_read_model.v1.schema.json
    result: >
      9 READY+VIOLATIONS (basis, definition, display_quantum, evidence, key, kind,
      metric, perimeter, role - key published the literal string 'None', kind
      published "financial", outside its own enum); 7 ready-and-schema-valid, of
      which 4 publish the contract's own unknown (native_ref / published_at / target
      -> null, native_admitted -> False) and 3 LIE (unit -> "USD", sign_convention ->
      "signed_as_reported", scale_power10 -> 0, publishing thousands as units); 4
      correctly refused; 1 (event) killed the case with CaseShapeError. Positive
      control passed on 20 of 21 fields.
  - claim: "The same instrument on this branch finds nothing left to mint that asserts anything."
    command: "the identical sweep3.py run from this worktree"
    result: >
      17 REFUSED / 4 minted-and-honest (the nullable pointers plus the
      native_admitted provenance label) / 0 schema violations / 0 cases killed.
  - claim: "Both cases the projection can be handed still validate, with the golden oracle exact."
    command: >
      python3 harness running project_economic_change over t._plnt_case() and
      t._fixture_case(), counting Draft202012Validator errors and comparing the six
      non-withheld result value_texts as a key->value mapping
    result: >
      both: errors=0 availability=ready degraded=[] oracle_exact=True
      (total_revenue_change 24344, advertising_revenue_change 10141,
      advertising_expense_change 10145, advertising_net_change -4,
      advertising_current_period_net 0, advertising_share_of_revenue_change_pct 41.66).
  - claim: "Owned suite green."
    command: >
      python3 -m pytest tests/test_consumer_cyclical_projection.py
      tests/test_consumer_cyclical_intelligence_read_model_contract.py -q
    result: "102 passed (projection 86, contract 16); was 76."
  - claim: "The new tests are non-vacuous, and nothing else depends on the change."
    command: >
      git checkout origin/main -- engine/sector_intelligence/consumer_cyclical_projection.py
      then the same pytest invocation, then restore
    result: >
      26 failed, 76 passed - and all 26 are the four new test functions (13 + 11 + 1
      + 1), no collateral. Restored head re-runs 102 passed.
  - claim: "The gate arms are individually pinned."
    command: >
      8 mutants applied one at a time to the real engine, suite re-run after each,
      each restore verified by re-running the suite
    result: >
      all 8 killed. M1 (kind enum admits 'financial') killed 1; M6 (the emptiness
      half of the check removed) killed 9; M7 ('event' dropped from the tuple only)
      killed 2; M8 (kind check weakened from value to presence) killed 1.
  - claim: "The CI job inventory still resolves this suite."
    command: "python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --validate-only"
    result: "consumer-cyclical-economic-change present in the selected jobs."
  - claim: "The Agent OS store validates."
    command: "python3 scripts/agentos.py validate"
    result: "0 errors, 118 warnings (all pre-existing review-overdue notices on other records)."
unverified:
  - claim: >
      Leaving native_admitted / native_ref / published_at / target unguarded is
      correct rather than merely convenient.
    what_would_verify: >
      A source document that omits one of them where the minted value asserts
      something false. Three of the four mint the contract's own null, which is the
      honest representation of "not available"; native_admitted mints False, whose
      wrong direction UNDER-claims provenance. No such document exists in this
      repository to test against. The reasoning, not a measurement, is what carries
      this one.
  - claim: "The three liars would actually lie on a real PLNT-class exhibit."
    what_would_verify: >
      A source record that reports in a non-USD unit, or in thousands with the scale
      unspelled. Only the mechanism was measured - that a silent source yields "USD"
      / "signed_as_reported" / 0 with no trace - not a live case where the minted
      value is wrong.
unresolved:
  - >
    All four external V1 gates remain unmoved: #7870 T09 rights correction, #7780
    mount ruling, #7669 page custody, and native source admission of the PLNT Q2 2026
    exhibit. The two gate PRs that moved on 2026-09-27 carry Semiconductor traffic,
    not a Consumer release.
  - >
    ACCEPTANCE of the returned V1-CORE is Sol's and has not been given. MERGED and
    PRODUCTION_PROOF are the rungs this seat can reach; it may not claim the one above.
next_actions:
  - "Watch this PR to merge, then verify from main's extracted bytes as #8054 and #8078 were."
  - >
    Before ever repeating "nothing ungated remains", re-run the observation: gate PR
    states, `git grep -n consumer_cyclical_projection` for runtime callers, and one
    correctness sweep of owns_paths. The claim was true about wiring and false about
    correctness.
  - >
    Only on a fresh Sol edge on #7804: consume the #7870 T09 rights correction and the
    #7780 mount ruling for the entitled/browser legs.
do_not_redo:
  - "Everything in WS-CONSUMER-CYCLICAL-V1-2026-09-27.md's do_not_redo, unchanged."
  - >
    The `len(document["facts"]) == admitted` assertion in
    test_no_required_envelope_field_is_ever_minted. Without it the scale_power10
    parametrization PASSES on the unfixed engine, because dropping scale from one side
    of a pair already degrades that pair for an unrelated reason - the test read green
    while the fabricated 0 was still being published. Deleting the count assertion
    restores a vacuous test, not a simpler one.
  - >
    Widening the gate to native_admitted / native_ref / published_at / target. It was
    considered and declined on the stated line: refuse a minted default that ASSERTS
    something, leave one that is the contract's own "unknown".
  - >
    Changing the contract to add these reasons. $defs/degraded_dependency.reason is
    {"type": ["string","null"], "minLength": 1} - an OPEN vocabulary - so
    fact_<field>_missing_or_malformed needed no schema edit, and editing the schema
    would have crossed into shared registry territory for nothing.
danger_areas:
  - >
    Everything in the 2026-09-27 handoff's danger_areas, unchanged, plus the three
    below.
  - >
    Comparing a published value against the fixture's real value CANNOT tell a read
    value from a minted default that happens to equal it. A first pass reported unit,
    sign_convention and native_admitted as "survived the pop, so read from source" -
    wrong in all three. Plant a distinctive value and require it to reach the
    published fact before any drop result is allowed to mean anything.
  - >
    An instrument that locates the victim fact BY ITS KEY cannot observe the `key`
    field's own defect: popping `key` changes the identifier the lookup uses, so the
    fact reads as "withheld" when it was published with key 'None'. Locate the victim
    positionally when the field under test is the one you are searching by.
  - >
    A mutant that replaces a short literal can hit two sites. `"event",` also occurs
    in _CONTRACT_RESULT_KEYS, so M7's first form failed all 14 tests for the wrong
    reason. Every mutation now runs under an
    `assert s != open(p).read(), "MUTATION WAS A NO-OP"` guard, and a multi-line
    unique context is used for short literals.
prs: [8078]
discoveries:
  - "DSC:A-MINTING-DEFAULT-IS-INVISIBLE-TO-AN-EMPTINESS-GATE"
---

## The part worth reading

The wave-3 gate and this one were written by the same seat, four days apart, and the
first one is why the second was needed. Four defects were observed; all four happened
to involve a reader that hands back `""` when the source is silent; the gate
generalized from them and therefore asks *is this field empty?*. That question is
well-formed only for readers that can be empty. `_envelope_unit` returns `"USD"`. The
gate could run over it forever and never see anything wrong, because from where the
gate stands there is nothing wrong — the value is there, it is a string, it is
non-empty, and it is a legal unit.

So the scope of a refusal gate is not set by the list of arms it carries. It is set by
what each reader does when the source says nothing, and the readers that mint are
exactly the ones an emptiness gate is constitutionally unable to reach. Enumerating
`_envelope_*` rather than enumerating the existing arms is the whole move.

The three that validate while lying are why this is a landmine and not a tidy-up. A
minted `"financial"` for `kind` is caught by the contract's enum the instant the
document is checked — loud, local, cheap. A minted `0` for `scale_power10` is a legal
integer in a legal range; the document validates, reports `availability: ready` and
`degraded_dependencies: []`, every value matches the golden oracle exactly, and the
magnitude is off by a factor of a thousand. The only evidence that anything happened
was the absence of the field in the source, and the reader consumed it. There is no
later stage that can recover it, which is why the refusal has to happen at admission
or not at all.
