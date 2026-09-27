---
key: TWO-ENDS-OF-ONE-POINTER-VALIDATED-IN-ISOLATION-BOTH-PASS-WHILE-IT-DANGLES
claim: >
  When one logical relation is spelled in two schema locations -- a reference field here,
  the record it names over there -- per-field validation is STRUCTURALLY blind to the
  relation between them. Every field passes, the document is schema-valid, and the
  pointer dangles. Measured on Consumer Cyclical V1
  (`engine/sector_intelligence/consumer_cyclical_projection.py`, contract
  `consumer_cyclical_intelligence_read_model.v1`): a fact whose `native_ref` named
  `src_this_record_was_never_declared` -- a record_id absent from the document's own
  `source_records` ledger -- was emitted inside a document reporting
  `availability: "ready"` at ZERO schema errors. Worse, the two ends did not even share
  a GRAMMAR: `source_record.record_id` was pinned to `^src_[a-z0-9_]+$` while
  `fact.native_ref` carried `{"type": ["string","null"], "minLength": 1}` and no pattern
  at all, so `"SRC-NOT-LEGAL"` -- uppercase, hyphenated, matching no record_id that
  could ever be declared -- was accepted and emitted too. Nothing in a per-field
  contract can notice either, because neither field is individually wrong.
falsifier: >
  Run `python3 -m pytest tests/test_consumer_cyclical_projection.py -k native_ref -q`
  against this repair (#8106); the guard lives at
  `engine/sector_intelligence/consumer_cyclical_projection.py:1284`
  (`_assert_provenance_pointers_resolve`) and the grammar at
  `contracts/sector_intelligence/consumer_cyclical_intelligence_read_model.v1.schema.json:343`.
  Generally: take any document contract with a reference field. Point it at an identifier that no
  record in the same document declares, choosing a value LEGAL under that field's own
  constraints (per DSC:A-MUTATION-THAT-DIES-UPSTREAM-NEVER-TESTS-THE-GATE-YOU-AIMED-AT,
  an illegal value dies at the vocabulary check and tests nothing). If the document
  still validates, the relation is unenforced. Refuted if the emitter raises and names
  the unresolved identifier. Second arm: compare the two ends' declared grammars --
  if the reference field accepts strings the identifier field could never produce, the
  pointer is unsatisfiable by construction and every such fixture is already dangling.
so_what: >
  Four things. (1) Enumerate a contract's RELATIONS, not just its fields, and enforce
  each relation at the level that can see both ends. `_fact_admission_failure` sees one
  fact and structurally CANNOT see `source_records`, so no amount of hardening there
  would ever have caught this; the guard has to live at document level. Absence of a
  place to put the check is why this class survives hardening waves that fix everything
  else. (2) Both ends of one pointer must share ONE grammar. Differing patterns across a
  reference and its referent is not a cosmetic inconsistency -- it silently makes some
  pointers unsatisfiable, and it is why a positive control on the dangling probe did not
  fire. (3) A TEST CAN STATE A MODULE GUARANTEE AND CHECK ONLY ITS OWN FIXTURE. Here
  `test_every_native_ref_resolves_to_a_declared_source_record` already existed, and its
  docstring already said "provenance must point at something that exists" -- but its
  body read `case = _plnt_case()` and asserted the property of that dict, never calling
  the module. It passed forever and guaranteed nothing about any other input. The tell
  is a test whose body never invokes the unit its NAME is about; grep a suspect suite
  for test functions that construct a fixture and never call the entry point. This is
  the dual of DSC:THE-CASE-A-SUITE-USES-MOST-IS-THE-ONE-IT-NEVER-VALIDATES -- there the
  fixture was never validated, here the fixture is the ONLY thing validated. (4) Sweep
  the whole convention when you fix one instance: 22 test refs still used a hyphenated
  ad-hoc spelling (`src-tr-c`) that could never resolve, because a prior wave corrected
  the main fixture and never swept the helpers. Binds every GMI sector vertical copying
  this envelope shape (`engine/sector_intelligence/*_projection.py`), all of which
  carry a `native_ref` / `source_records` pair.
kind: landmine
verified_at: 2026-09-27
verified_by: >
  Direct probe against the module with both arms and explicit no-op assertions
  (`assert old != newval`): the legal-but-dangling ref emitted with
  `availability: "ready"`, and the illegal-grammar ref ALSO emitted, proving no
  vocabulary gate existed. After the repair both refuse with declared reasons naming
  the intended gate ("resolves to no declared source record", and
  "does not match '^src_[a-z0-9_]+$'"). Regression-pinned by 3 new tests; 114 passed
  across the projection + contract suites (the exact command the
  ci-control-plane-contracts gate runs), both cases oracle-exact at 0 schema errors,
  envelope sweep unchanged at 17 REFUSED / 4 MINTED-SCHEMA-VALID. PR #8106.
scope: >
  Verified on Consumer Cyclical V1 only. The per-field-blindness mechanism is generic to
  JSON Schema and any validator without cross-field assertions; the specific field names
  are Consumer Cyclical's. Says nothing about whether other verticals' pointers are in
  fact dangling today -- that is the falsifier to run, not an inherited result.
confidence: verified
---

See `research/consumer_cyclical/v1/V1_PLNT_BOUNDARY_AND_FROZEN_SPEC.md` section 4a for
why `native_ref` is non-null at all in V1-CORE: the fact is bound to a source COORDINATE
whose `retention_state` is `not_retained`, which is strictly more honest than the bare
`null` that section's prose still describes. That staleness is recorded there rather than
corrected away -- forcing `null` would destroy information and break the golden oracle.

Related: [[DSC:A-MINTING-DEFAULT-IS-INVISIBLE-TO-AN-EMPTINESS-GATE]] (so_what 4 rules a
`null` `native_ref` deliberately admissible -- this guard must not over-tighten into it),
[[DSC:A-MUTATION-THAT-DIES-UPSTREAM-NEVER-TESTS-THE-GATE-YOU-AIMED-AT]] (why the probe
value had to be grammar-legal), and
[[DSC:THE-CASE-A-SUITE-USES-MOST-IS-THE-ONE-IT-NEVER-VALIDATES]].
