---
key: AN-ENUMERATED-GUARD-IS-BLIND-OUTSIDE-ITS-ENUMERATION
claim: >
  A guard that HAND-ENUMERATES what it checks is scoped by its enumeration, never by the
  authority it believes it mirrors, and the gap is invisible to the guard, to its own
  falsifier test, and to a green suite. Measured on merged Consumer Cyclical V1-CORE
  (`edf7f0add1b1`), on two guards at once. (1) `_assert_document_matches_contract_shape`
  iterates `facts`, `results` and `degraded_dependencies` and reads ZERO root fields:
  of the five root scalars the published contract constrains — `availability`,
  `comparison_basis`, `contract_id`, `generated_at`, `schema_version` — it guarded
  0 of 5, measured by minting a violation of each, confirming the SCHEMA rejects it,
  then asking whether the guard raises. (2) `test_module_constants_mirror_the_published_contract`
  names five constants and, by naming them, omitted the two it did not name:
  `_ALLOWED_COMPARISON_BASIS` had already drifted to three words against the contract's
  enum of one, so a case declaring `explicit_same_year_prior_year` was ADMITTED by the
  module, projected, and emitted as a document whose root enum the contract rejects;
  `_ALLOWED_KIND` matched but was free to drift the same way. Replacing enumeration with
  derivation — validate the document against the schema, and assert reflectively that
  every `_ALLOWED_*` frozenset is pinned — found a third, independent live defect nobody
  was looking for: `results[*].input_refs` published duplicate provenance
  (`['advertising_revenue','advertising_revenue']`) against `uniqueItems: true` in five
  of the module's own tests, green on main for the module's whole life.
falsifier: >
  Re-extract `origin/main` before `edf7f0add1b1`'s successor and bolt
  `jsonschema.Draft202012Validator(<the published schema>)` onto main's own
  `_assert_document_matches_contract_shape` (positive control first: the clean fixture
  must still pass). If `pytest tests/test_consumer_cyclical_projection.py -k "ratio or
  withheld_is_never_zero"` then passes, the duplicate-`input_refs` half is refuted. For
  the root half, mint a violation of each constrained root scalar and assert the
  hand-rolled guard raises; if it raises on any of the five, that field was not blind.
so_what: >
  When a guard's coverage matters, do not extend its list — replace the enumeration with
  a derivation from the authority itself, then add ONE reflective test that fails when a
  new item is unpinned. Extending the list reproduces the defect at the next field. The
  concrete moves, each already paid for here: validate the emitted document against the
  contract rather than mirroring its constraints (the house idiom — 39 `engine/` modules
  already do this, nearest sibling `engine/capital_structure/projection.py`); keep a
  mirrored constant ONLY where a non-schema reader needs it (input admission, which runs
  before a document exists) and delete the rest; and assert `{n for n in dir(mod) if
  n.startswith("_ALLOWED_") and isinstance(getattr(mod, n), frozenset)} == pinned`, which
  caught an unpinned vocabulary on its first run. Sector verticals copying this projector
  inherit both guards and therefore both blind spots. Admission may be NARROWER than the
  contract; it may never be WIDER — a gate wider than the thing it gates for does not
  refuse an invalid publication, it authors one.
kind: landmine
verified_at: 2026-09-27
verified_by: >
  `origin/main` at `edf7f0add1b1`, re-extracted with `git archive` and sha256-confirmed
  byte-identical. Root sweep: mint-a-violation-per-field probe over
  `schema["properties"]`, 0 of 5 guarded before, 5 of 5 after. Drift: `python3 -c` diff of
  `_ALLOWED_COMPARISON_BASIS` against `schema["properties"]["comparison_basis"]["enum"]`
  (3 vs 1), and the emitted document validated at 1 root enum violation. Duplicate
  provenance reproduced against MAIN's unpatched engine via a conftest that calls main's
  own guard then the schema — same five tests, same violations. Mutation round, 13
  mutants with a `MUTATION WAS A NO-OP` assert on each: 12 killed, 1 equivalent
  (`start < end`, unreachable because every span band's lower bound exceeds zero — itself
  now pinned). Owned suite 102 -> 111 passed.
scope:
  - macro
  - engine/sector_intelligence/
  - contracts/sector_intelligence/
  - research/consumer_cyclical/v1/
confidence: verified
---

Wave 5 recorded that an admission gate is scoped by what each READER does on absence
([[a-minting-default-is-invisible-to-an-emptiness-gate]] —
`DSC:A-MINTING-DEFAULT-IS-INVISIBLE-TO-AN-EMPTINESS-GATE`). This is the same disease one
level up and in the other direction: not what the readers do, but what the GUARD was
written to look at. Both guards here were correct about every item on their list. Neither
list was the contract.

The ordering matters and is the reusable part: **part C found parts A-adjacent D.** The
duplicate `input_refs` defect was not suspected, not searched for, and not reachable by
reading the code — it appeared the moment the guard stopped enumerating and started
deriving, and five tests that had been green for the module's whole life went red at once.
A derivation does not only close the holes you know about; it is an instrument for the
ones you do not.

Two failed predictions are recorded here because both would have shipped a vacuous test.
A mutant that drops the declared-basis/period-kind binding SURVIVED twice. The first fix
relabelled one side of the pair — but `_select_pair` already requires both sides to agree
on `period_kind`, so the pair collapsed for a pre-existing reason and the new check was
never reached. The second still failed because the test filtered results on
`comparison_basis`, which `_emit_result` deliberately strips as an internal carrier; the
contract field is `basis`. Both tests PASSED throughout. A test that passes proves nothing
about the line it was written for until a mutant kills it.

See also [[a-value-only-suite-never-validates-its-own-fixture]] and
[[a-suite-can-bind-values-and-leave-provenance-unbound]] — the same suite had already been
shown to bind values while leaving shape and provenance unbound; `input_refs` is that
prediction coming true in a field nobody had named.
