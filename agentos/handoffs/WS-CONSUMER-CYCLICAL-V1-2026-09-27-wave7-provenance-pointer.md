---
workstream: "WS:CONSUMER-CYCLICAL-V1"
session: claude/consumer-cyclical-wave7-provenance-pointer
model: opus
ended_because: complete
mission: >
  Continue the V1 correctness lane the wave-6 closeout left open, after #8103
  (declared-basis binding) and #8104 (records) both merged. Take the next honest
  unswept surface and either find a real defect or report a null.
state_before: >
  Wave 6 merged and proven from main's bytes. The closeout named the unswept remainder
  as the explanation object, source_records, and availability/state derivation.
  Suspicion going in was that source_records is an unvalidated passthrough.
state_after: >
  That suspicion was REFUTED by measurement and a different, real defect was found next
  to it. PR #8106 opened, armed merge-on-green, in CI under watcher bvi544uch at 180s.
changed:
  - path: engine/sector_intelligence/consumer_cyclical_projection.py
    what: >
      New _assert_provenance_pointers_resolve (line 1284), wired at line 1757 after the
      contract-shape check: refuses any emitted fact whose non-null native_ref names no
      declared source record. Document level, because _fact_admission_failure sees one
      fact and structurally cannot see source_records. Also corrects the _compose_changes
      docstring, which claimed a native_admitted suppression gate the code refuses.
  - path: contracts/sector_intelligence/consumer_cyclical_intelligence_read_model.v1.schema.json
    what: >
      fact.native_ref gains pattern ^src_[a-z0-9_]+$ (line 343), the same grammar
      source_record.record_id already carried (line 645). Both ends of one pointer.
  - path: tests/test_consumer_cyclical_projection.py
    what: >
      test_every_native_ref_resolves_to_a_declared_source_record upgraded to drive the
      MODULE rather than only assert its own fixture; +3 tests (null still admitted,
      out-of-vocabulary refused, native_admitted False is not a suppression gate); 22
      hyphenated native_ref fixtures swept to the record their own _plnt_case() declares.
  - path: agentos/discoveries/DSC-TWO-ENDS-OF-ONE-POINTER-VALIDATED-IN-ISOLATION-BOTH-PASS-WHILE-IT-DANGLES.md
    what: >
      New landmine DSC: one relation spelled in two schema locations is invisible to
      per-field validation, and a test can state a module guarantee while checking only
      its fixture.
  - path: agentos/workstreams/WS-CONSUMER-CYCLICAL-V1.md
    what: >
      Registers the new discovery key; next_action carries the wave-7 record, the
      corrected remainder, and the standing warning not to "repair" toward 4a's stale
      native_ref prose.
verified:
  - claim: "Before the repair a grammar-legal dangling native_ref was emitted at availability 'ready' with zero schema errors."
    command: "python3 scratchpad/dangling_ref.py (ARM1; guarded by assert old != newval) -> ORPHAN POINTERS IN EMITTED DOC: ['src_this_record_was_never_declared']"
  - claim: "No vocabulary gate existed on native_ref at all -- the positive control did not fire, which is how the missing pattern was found."
    command: "python3 scratchpad/dangling_ref.py (ARM2, 'SRC-NOT-LEGAL') -> 'NOT REFUSED - instrument did not fire'"
  - claim: "After the repair both arms refuse with the DECLARED REASON naming the intended gate."
    command: "python3 scratchpad/dangling_ref.py -> 'resolves to no declared source record: src_this_record_was_never_declared' and \"facts.0.native_ref: 'SRC-NOT-LEGAL' does not match '^src_[a-z0-9_]+$'\""
  - claim: "114 passed (111 baseline + 3 new) on the exact command the CI gate runs."
    command: "python3 -m pytest tests/test_consumer_cyclical_projection.py tests/test_consumer_cyclical_intelligence_read_model_contract.py -q  # == .github/ci/legacy-jobs.yml:5951"
  - claim: "Oracle held on BOTH cases and the envelope sweep is unchanged."
    command: "python3 proof8078.py -> schema_errors=0 availability=ready degraded=[] oracle_exact=True (x2); python3 sweep3.py -> 17 REFUSED / 4 MINTED, SCHEMA-VALID"
  - claim: "Repair safety was measured BEFORE writing it: the two real cases cover the resolve path and the null-allowed path respectively."
    command: "python3 -c over _plnt_case/_fixture_case -> _plnt_case: nonnull_refs=6 DANGLING=[]; _fixture_case: nonnull_refs=0 DANGLING=[]"
  - claim: "Blast radius is confined: nothing outside this module's own suite consumes the contract."
    command: "git grep -ln consumer_cyclical_intelligence_read_model -- ':!tests/test_consumer_cyclical*' ':!contracts/*'  # CI job entry + agentos prose only"
  - claim: "#8104 (wave-6 records) MERGED and all four records are present in origin/main's bytes."
    command: "tail tasks/bfzlr0efl.output -> STATE=MERGED 2026-09-27T22:54:23Z CHECKS=16 UNCONCLUDED=0; git rev-parse --short origin/main:<each of the 4 paths>"
unverified:
  - claim: "#8106's CI concludes green and it merges."
    what_would_verify: >
      Watcher bvi544uch at 180s reports MERGED, or ALL CHECKS CONCLUDED followed by a
      hand merge on concluded-clean.
  - claim: "No OTHER GMI sector vertical has a dangling native_ref -> source_records pointer today."
    what_would_verify: >
      Run the DSC's falsifier against each engine/sector_intelligence/*_projection.py.
      The mechanism is generic but the measurement is Consumer Cyclical's only -- this is
      the falsifier to run, never an inherited result.
unresolved:
  - >
    The explanation object and availability/state derivation remain the honest unswept
    correctness remainder.
  - >
    CC-V1-ENTITLED still cannot start: five owner heads OPEN DRAFT, and the module still
    has zero production callers on main.
next_actions:
  - >
    Confirm #8106 merged; if the watcher reports ALL CHECKS CONCLUDED rather than MERGED,
    hand-merge on concluded-clean exactly as #8103 was merged.
  - >
    Optional next correctness wave: the explanation object. Predict before probing, and
    read the two mutation/minting DSCs first.
do_not_redo:
  - >
    source_records is NOT an unvalidated passthrough. _assert_document_matches_contract_shape
    runs FULL jsonschema validation over the whole document, so every record is deeply
    checked against the 12 required fields of $defs/source_record. Only the RELATION to
    native_ref was missing, and wave 7 closed it.
  - >
    input_refs cannot dangle by construction -- it is module-DERIVED from the paired facts
    (line 945), not caller-supplied. Measured: zero unresolved input_refs on the real case.
  - >
    A null native_ref is deliberately admissible per
    DSC:A-MINTING-DEFAULT-IS-INVISIBLE-TO-AN-EMPTINESS-GATE so_what (4). Do not tighten it.
  - >
    Everything in the wave-6 closeout's do_not_redo, unchanged, including the sticky R8
    native-staging denial.
danger_areas:
  - >
    Frozen-spec 4a's literal "native_ref is null" is STALE, not violated. V1-CORE points at
    a source record whose retention_state is not_retained -- strictly MORE honest than a
    bare null. Forcing null destroys information and breaks the golden oracle. Do not
    "repair" toward the prose.
  - >
    native_admitted must NEVER become a suppression gate (frozen-spec 4a). Every real
    V1-CORE fact carries False because PLNT's Q2 2026 exhibit is retained nowhere, so a
    gate makes the module structurally incapable of its own golden case. The docstring
    that claimed otherwise is corrected and pinned by a test, but this trap survived
    several waves in prose form.
  - >
    This is a sparse worktree. Do NOT run the full suite here; run the two named files.
  - >
    ACCEPTANCE is Sol's and must never be claimed by this seat. #8106 reaching MERGED is
    not acceptance.
---

## The shape of it

`fact.native_ref` and `source_records[].record_id` are two ends of ONE pointer,
spelled in two places. A per-field contract validates each end in isolation and is
STRUCTURALLY blind to the relation between them — every field passes, the document is
schema-valid, and the pointer dangles.

The part worth carrying forward is how it survived: a test named
`test_every_native_ref_resolves_to_a_declared_source_record` already existed, and its
docstring already said *"provenance must point at something that exists."* Its body read
`case = _plnt_case()` and asserted that property **of the fixture** — it never called the
module. A test can state a module guarantee in its name and its prose while checking only
its own fixture, and it will pass forever while guaranteeing nothing.

The second defect was found by the positive control failing. Probing the dangling
pointer, the control arm used a deliberately illegal value expecting a refusal — and got
none, because `native_ref` had no pattern at all while `record_id` was pinned. The
instrument's silence was the finding.
