---
workstream: "WS:CONSUMER-CYCLICAL-V1"
session: claude/consumer-cyclical-wave10-degraded-state-pin
model: opus
ended_because: complete
mission: >
  Sweep the last two unmeasured surfaces of the Consumer Cyclical v1 read model -- the
  explanation object and the `degraded_dependency.state` derivation -- against the wave
  6/7/8 thesis that "the module states things it does not check", and close the
  correctness sweep either with a repair or with a bounded null.
state_before: >
  Waves 6-9 all MERGED and verified from main's bytes (#8103, #8104, #8106, #8111, #8115).
  Wave 8 found and repaired a real authority-guard defect; wave 9 found a dead guard in
  another seat's module and routed it as knowledge rather than editing it. Two Consumer
  surfaces had never been measured: the explanation object, and how
  `degraded_dependencies[].state` is derived.
state_after: >
  Both surfaces measured. The wave-8 thesis does NOT hold on either -- recording that null
  is the result. The explanation object is a closed set of two module-owned documents with
  no caller text, already covered in both directions, and its forbidden-conclusion guard
  reads every key the builder emits (zero uncovered). The `state` field is a three-value
  contract enum with exactly one producible value and zero readers: LOOSE, not false. One
  mutation-probed pin now makes that looseness visible instead of assumed. Suite 103
  passed in the projection file (119 with the sibling contract file).
changed:
  - path: tests/test_consumer_cyclical_projection.py
    what: >
      NEW pin `test_a_degraded_entry_only_ever_reports_the_unavailable_state` at :1911. It
      drives two independent degradation branches, asserts each mutation actually changed
      the case, and requires more than one distinct `reason` before asserting the state set
      -- so a stale fact-key filter fails loudly instead of passing on an empty list.
  - path: agentos/discoveries/DSC-A-REQUIRED-ENUM-FIELD-CAN-HAVE-ONE-PRODUCIBLE-VALUE-AND-ZERO-READERS.md
    what: >
      NEW landmine. A required enum field can admit three values, produce exactly one, and
      have no readers at all -- and one of the permitted values is self-contradictory for
      the list it sits in. Classified LOOSE, not false, on purpose.
  - path: agentos/workstreams/WS-CONSUMER-CYCLICAL-V1.md
    what: >
      Registered the new DSC key in `discoveries` and appended the wave-10 record to
      `next_action`, including the closure of the correctness sweep.
verified:
  - claim: the new pin exists in main's bytes and passes there
    command: git fetch origin main -q && git show origin/main:tests/test_consumer_cyclical_projection.py | grep -c 'def test_a_degraded_entry_only_ever_reports_the_unavailable_state'
  - claim: the whole projection suite is green with the pin in place
    command: python3 -m pytest tests/test_consumer_cyclical_projection.py -q 2>&1 | tail -1
  - claim: no call site passes a state, so `unavailable` is the only producible value
    command: grep -n '_degraded(' engine/sector_intelligence/consumer_cyclical_projection.py | grep -v 'def _degraded' | grep -c ', *"[a-z_]*" *, *"'
  - claim: positive control for the grep above -- one definition plus seven call sites
    command: grep -c '_degraded(' engine/sector_intelligence/consumer_cyclical_projection.py
  - claim: the contract admits three states while the producer emits one
    command: python3 -c "import json;print(json.load(open('contracts/sector_intelligence/consumer_cyclical_intelligence_read_model.v1.schema.json'))['\$defs']['degraded_dependency']['properties']['state']['enum'])"
  - claim: state is the only module-authored enum the producer cannot fully exercise
    command: grep -c '_degraded(' engine/sector_intelligence/consumer_cyclical_projection.py
  - claim: the other narrow-looking enums are CALLER-authored passthroughs, not looseness
    command: grep -c 'fact.get("basis")\|fact.get("role")\|fact.get("perimeter")\|source_records = case.get' engine/sector_intelligence/consumer_cyclical_projection.py
  - claim: zero non-test code readers of degraded_dependencies outside the producer
    command: grep -rl 'degraded_dependencies' --include='*.py' --include='*.js' --include='*.j2' . | grep -v '^tests/'
  - claim: the forbidden-conclusion guard reads every key _build_explanation emits
    command: python3 -c "import re;s=open('engine/sector_intelligence/consumer_cyclical_projection.py').read();g=set(re.findall(r'\"(\w+)\"',re.search(r'_check_explanation_for_forbidden.*?for k in \(([^)]*)\)',s,re.S).group(1)));b=set(re.findall(r'\"(\w+)\":',re.search(r'def _build_explanation.*?return \{(.*?)\n    \}',s,re.S).group(1)));print('uncovered:',sorted(b-g) or 'NONE')"
  - claim: the pin fails when a call site starts emitting a second state (mutation-probed)
    command: |
      cp engine/sector_intelligence/consumer_cyclical_projection.py /tmp/ccp.bak
      perl -0pi -e 's/_degraded\(_key, "inputs_absent_result_omitted"\)/_degraded(_key, "inputs_absent_result_omitted", "partial")/' engine/sector_intelligence/consumer_cyclical_projection.py
      python3 -m pytest tests/test_consumer_cyclical_projection.py::test_a_degraded_entry_only_ever_reports_the_unavailable_state -q; echo "expect: 1 failed"
      cp /tmp/ccp.bak engine/sector_intelligence/consumer_cyclical_projection.py
unverified:
  - >
    Whether the sibling sector projection modules declare the same over-wide
    `degraded_dependency.state` enum. NOT checked, and deliberately not implied by this
    record -- `finance_projection.py` is seat 938d17d6's custody and was not opened for
    this. A roster is not a census; enumerate from the filesystem before probing any of it.
unresolved:
  - >
    The contract enum stays wider than the producer. Narrowing a published v1 enum is a
    shared-owner contract change with zero present consumers to benefit, so it was NOT
    done on aesthetics. The right moment to decide is when CC-V1-ENTITLED wires a real
    consumer -- at which point `state` is either narrowed to what is produced, or a second
    state becomes genuinely producible and the pin surfaces the decision.
next_actions:
  - >
    V1 PLNT has not returned to Sol. ACCEPTANCE is Sol's and must never be claimed by this
    seat; MERGED plus production proof is the highest rung this work reaches on its own.
  - >
    When CC-V1-ENTITLED starts (it has NOT -- five owner heads OPEN DRAFT, zero production
    callers), branch consumer code on `reason`, never on `state`, and re-run the reader
    census in the DSC falsifier because its zero-reader half goes stale that moment.
do_not_redo:
  - >
    Do NOT re-probe the explanation object for the wave-8 "states what it does not check"
    defect. Measured wave 10: `_build_explanation` selects between exactly two
    module-owned documents (`_LEAD_FULL`, `_LEAD_GENERIC`), no caller text enters, both
    directions have named tests (:1029 full, :1043 degraded), and
    `_check_explanation_for_forbidden` reads all four emitted keys with zero uncovered.
    A closed module-owned input set is exhaustively verifiable -- the thesis cannot apply.
  - >
    Do NOT re-probe `degraded_dependency.state` for a false-claim defect. It is LOOSE, not
    false: the document never says anything untrue, the contract merely permits more than
    the producer emits. Do not escalate it as a vulnerability and do not open a contract
    narrowing PR over it without a consumer.
  - >
    Do NOT re-run the Consumer correctness sweep as a whole. Waves 6-10 closed it: envelope
    integrity, declared basis, authority vocabulary, the native_ref pointer pair, the
    explanation object, and the degraded-state derivation are all measured. SEARCH BOUND,
    because a do_not_redo is read as permission to skip: "closed" means every one of the
    eleven top-level contract properties has had at least one derive-don't-enumerate pass
    (5 root scalars incl. availability, 21 fact fields, results via basis binding /
    input_refs / pair agreement / authority vocabulary, source_records via the wave-7
    pointer, subject via case reconciliation, and explanation + degraded_dependencies in
    wave 10). It is NOT a proof that no defect remains, and it says nothing about the
    entitled/browser legs, which are externally blocked and were never in this sweep. A
    NEW class of probe -- one no wave has run -- is legitimate; re-running a wave's own
    probe is not.
danger_areas:
  - >
    A degradation probe MUST filter on the real fact keys, which are suffixed
    `_current` / `_prior` (`advertising_expense_current`, `total_revenue_prior`, ...), never
    on the bare metric name. A bare-name filter mutates nothing, the case degrades nothing,
    and every downstream assertion passes on an empty list. This cost a full probe cycle in
    wave 10 and is now pinned by the distinct-`reason` guard inside the test itself.
  - >
    `grep -rl ... .` in this repo emits paths with NO leading `./`, so a `^./tests/` filter
    excludes nothing and a reader census silently reports test files as consumers. Use
    `^tests/`. This misfired twice in one wave before it was caught by a positive control.
  - >
    `engine/sector_intelligence/finance_projection.py` is seat 938d17d6's custody. Route
    findings there as knowledge (#7786); never edit it and never open a repair PR on it.
---

Wave 10 closes the Consumer Cyclical v1 correctness sweep. Both remaining
surfaces were measured and both returned a null against the wave-8 thesis --
the explanation object because its input set is closed and module-owned, the
`degraded_dependency.state` field because a loose contract is not a false
claim. The single shipped artifact is the mutation-probed pin that converts
that looseness from an assumption into a measurement.
