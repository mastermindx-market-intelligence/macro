---
key: THE-CASE-A-SUITE-USES-MOST-IS-THE-ONE-IT-NEVER-VALIDATES
claim: >
  When a module publishes a contract and its suite owns two cases — a small committed
  fixture and a large hand-built synthetic one — schema validation attaches to the
  fixture and the synthetic case runs unvalidated, because the fixture is the one that
  arrived with a schema next to it. Measured in Consumer Cyclical V1-CORE: on
  `origin/main` at `90f9fcbe31ff`, `_plnt_case()` — the synthetic case carrying the
  frozen R6 §7.1 golden oracle and used by roughly 40 of the 49 projection tests —
  produced a document with 128 violations of
  `consumer_cyclical_intelligence_read_model.v1`: every fact wrong on `basis`,
  `definition`, `display_quantum`, `event`, `kind` and `perimeter`, plus `source_records`
  missing a required property and `results[].input_refs` carrying duplicate entries. All
  65 tests were green. The five or so fixture-based tests were the only ones that ever
  called the validator, and the fixture was clean, so the validator never saw the case
  the suite actually relies on.
falsifier: >
  `jsonschema.Draft202012Validator(<the v1 schema>).iter_errors(project_economic_change(_plnt_case()))`
  returning an empty list at a commit before this record's repair; or
  `tests/test_consumer_cyclical_projection.py` containing a schema assertion reached by
  a `_plnt_case()`-derived document at that commit; or the suite failing when
  `_plnt_case()` is mutated to emit a non-slug `event`.
so_what: >
  Three things change. (1) Count which case each contract assertion actually reaches
  before trusting "the contract is tested" — `grep` the validator's call sites and check
  the case factory feeding each one, because coverage of the *validator* is not coverage
  of the *cases*. (2) A hand-built case is a second, unversioned encoding of the
  contract, and it drifts the moment the schema moves; prefer deriving synthetic cases
  from the committed fixture (mutating copies) over hand-authoring a parallel one. (3)
  The drift is not random — here the test helper computed `period_start` as
  `period_end[:4] + "-01-01"`, the *same* calendar-snapping mistake the module's own
  dead fallback made, so the two agreed and the suite confirmed the bug rather than
  catching it. When a helper and the code under test share an assumption, the suite
  tests the assumption, not the code. Applies to every contract-bearing module here:
  `engine/sector_intelligence/*_projection.py` and anything under
  `contracts/sector_intelligence/`.
kind: landmine
verified_at: 2026-09-26
verified_by: >
  Validated `project_economic_change(_plnt_case())` from a pristine `origin/main`
  checkout at `90f9fcbe31ff` against
  `contracts/sector_intelligence/consumer_cyclical_intelligence_read_model.v1.schema.json`:
  128 errors while `pytest tests/test_consumer_cyclical_projection.py
  tests/test_consumer_cyclical_intelligence_read_model_contract.py` reported 65 passed.
  Line-coverage audit of the module under that same suite (stdlib `trace`, positive-
  controlled by confirming the pre-repair advertising branch showed dead) reported
  110 of 723 executable lines never executed, including two zero-caller functions.
  Sibling of DSC:A-UNIVERSAL-FALLBACK-BRANCH-IS-INVISIBLE-TO-A-VALUE-ONLY-SUITE, which
  is the same blindness one level down (branch not reached vs case not validated).
scope: [macro, engine/sector_intelligence/, contracts/sector_intelligence/, tests/]
confidence: verified
---

## Detail

The two cases had different jobs and only one had a guardian. The committed fixture
exists to be validated — it is literally named `.valid.json` and sits beside the schema —
so the contract test picked it up. `_plnt_case()` exists to carry the golden oracle, and
the oracle is a set of six numbers, so every assertion built on it read numbers. Nobody
decided the synthetic case should be exempt from the contract; it simply never came up.

What makes this worth a record rather than a bug report is the direction of the error.
The synthetic case was not sloppy in random ways — it was sloppy in *plausible* ways:
`role: "REPORTED_FACT"`, `basis: "REPORTED"`, `sign_convention: "SIGNED"`,
`display_quantum: "USD thousands"`, `event: "PLNT Q2 2026, quarter ended 2026-06-30"`.
Each reads like a correct value for its field. The contract wanted `actual`,
`as_reported_period_value`, `signed_as_reported`, `1_thousand` and a slug. A human
reviewer scanning the helper sees nothing wrong, because nothing is wrong *as English* —
only as contract.

The repair does not attempt to make `_plnt_case()` fully conformant; that is a larger
reconciliation (it needs `source_records`, `subject` and de-duplicated fact keys) and is
recorded as the open follow-up in the workstream. What shipped is the envelope subset
that the module itself must honour regardless of which case feeds it, plus a runtime
self-check so the module refuses to publish a document that breaks its own contract.
