---
key: A-MINTING-DEFAULT-IS-INVISIBLE-TO-AN-EMPTINESS-GATE
claim: >
  An admission gate grown from sentinel-returning readers cannot guard readers that MINT
  a plausible value, and the blind spot is invisible to the gate's own logic AND to the
  contract. Measured on merged Consumer Cyclical V1-CORE: `_fact_admission_failure`
  guarded exactly the four fields whose `_envelope_*` reader answers an absent source
  value with an EMPTY sentinel (`value_text`, `period_start`, `period_end`,
  `period_kind`). Sweeping all 21 contract-required fact fields — plant a distinctive
  value, confirm it propagates, then drop it — measured the other seventeen. NINE
  (`basis`, `definition`, `display_quantum`, `evidence`, `key`, `kind`, `metric`,
  `perimeter`, `role`) produced a document the module declared `availability: ready`
  while it carried schema violations: `key` published the literal string `'None'`,
  `kind` published `"financial"`, a value its own enum does not contain. SEVEN produced
  a `ready` document that VALIDATES — four by publishing the contract's own "unknown"
  (`native_ref`, `published_at`, `target` -> `null`; `native_admitted` -> `False`), and
  THREE BY LYING: `_envelope_unit` -> `"USD"` for an issuer that may not report in USD,
  `_envelope_sign_convention` -> `"signed_as_reported"` assumed rather than read, and
  `_envelope_scale` -> `0`, publishing thousands as units. ONE (`event`) killed the whole
  case with `CaseShapeError`. The schema cannot catch the three liars: `0` and `"USD"`
  are legal values, and only the source's silence distinguishes a read one from a minted
  one — which the reader had already destroyed.
falsifier: >
  `python3 -m pytest tests/test_consumer_cyclical_projection.py -k "minted or fabrication
  or empty_envelope or vocabulary"` passing while any `_envelope_*` reader in
  `engine/sector_intelligence/consumer_cyclical_projection.py` still returns a
  non-sentinel literal for an absent source value; or deleting any name from
  `_REQUIRED_SOURCE_TEXT_FIELDS` / `_ALLOWED_KIND`, or either the `scale_power10` or
  `evidence` arm of `_fact_admission_failure`, without a test going red; or
  `project_economic_change` emitting any fact whose `unit`, `sign_convention` or
  `scale_power10` the source never spelled.
so_what: >
  Four things change. (1) When auditing a refusal gate, enumerate the fields it must
  cover by what each READER does on absence, never by what the gate already lists — a
  gate grown from sentinel cases silently defines its own scope as "the fields that have
  sentinels", and the minting readers are exactly the ones it will never reach. Same
  shape as DSC:A-UNIVERSAL-FALLBACK-BRANCH-IS-INVISIBLE-TO-A-VALUE-ONLY-SUITE: the
  defect and its camouflage are one property. (2) A contract is not a backstop for
  fabrication. An enum catches `"financial"` loudly, but a minted value inside the legal
  domain (`0` for a scale, `"USD"` for a unit) validates perfectly and is undetectable
  downstream forever — so the refusal must happen at ADMISSION, while the source's
  silence is still observable. (3) Absence and malformedness are two tests, not one: a
  reason named `missing_or_malformed` exercised only by deleting the key stays green
  after the emptiness half of its own check is deleted — measured, mutant M6 survived
  every one of the fourteen absence tests that existed at that point and died only once
  present-but-empty cases were added. (4) The line
  this repair draws, and the one to copy: a minted default that ASSERTS something the
  source did not say gets refused; a minted default that is the contract's own "unknown"
  (`null` for `native_ref`/`published_at`/`target`, `False` for the `native_admitted`
  provenance label, whose wrong direction under-claims) is left alone — tightening those
  would refuse otherwise-complete facts to gain nothing. Binds every GMI sector vertical
  that copies this envelope-reader shape (`engine/sector_intelligence/*_projection.py`).
kind: landmine
verified_at: 2026-09-27
verified_by: >
  Positive-controlled sweep of all 21 contract-required `$defs/fact` fields, run against
  `origin/main`'s own extracted bytes at `386c98edda2c` (engine + tests + contracts + the
  committed fixture
  `data/sector_intelligence/fixtures/consumer_cyclical_intelligence_read_model.v1.valid.json`),
  each trial planting a distinctive value, asserting it reaches the published fact, then
  dropping it and validating the emitted document against
  `contracts/sector_intelligence/consumer_cyclical_intelligence_read_model.v1.schema.json`:
  9 -> `ready` with schema violations, 7 -> `ready` and schema-valid (3 of them false),
  4 -> correctly refused and declared, 1 (`event`) -> `CaseShapeError`. The same
  instrument on the repaired branch reads 17 REFUSED / 4 minted-and-honest / 0 schema
  violations / 0 cases killed. The positive control passed on 20 of 21 fields; `event`'s
  planted probe value is itself contract-invalid, so its control is void, but its
  measured behaviour — `CaseShapeError` before, fact withheld after — is direct and
  unambiguous. Value comparison alone could not have settled `unit`, `sign_convention`
  and `native_admitted`, whose minted defaults happen to equal this fixture's true
  values; only the plant-then-drop control separates "read" from "minted and
  coincidentally right". Non-vacuity, re-measured on the final suite: with only the
  engine reverted to main's bytes, 26 fail and 76 pass, and all 26 are the four new test
  functions (13 minted-field parametrizations, 11 present-but-empty, the
  three-fabrications case, the kind-by-value case) — no collateral. Mutation control: 8 mutants, all killed (M1 kind enum admits 'financial'; M6
  emptiness half removed; M7 'event' dropped from the tuple; M8 kind check weakened to
  presence), each restore re-verified green.
  `tests/test_consumer_cyclical_projection.py` 60 -> 86; owned suite 76 -> 102 passed.
scope: [macro, engine/sector_intelligence/, contracts/sector_intelligence/, research/consumer_cyclical/v1/]
confidence: verified
---

## Detail

The wave-3 gate was correct and incomplete in the same act. It was written from four
observed defects, all of which happened to be readers that hand back `""` when the
source is silent — so generalizing from them produced a gate that asks "is this field
empty?". That question is unanswerable for a reader whose whole purpose is to never be
empty. `_envelope_period_start`'s docstring even says its `""` "is an admission failure
handled by `_fact_admission_failure`, not a published value"; `_envelope_unit` has no
such note, because there is nothing for it to say — it returns `"USD"`, and the
distinction that docstring draws has already been erased one line above the gate.

The three that validate while lying are the load-bearing half of this record. A reader
that mints `"financial"` for `kind` is caught by the contract's enum the moment the
document is checked, so the damage is loud and local. A reader that mints `0` for
`scale_power10` produces a number the schema was always going to accept, and the
resulting document is not merely wrong but *confidently* wrong: `availability: ready`,
`degraded_dependencies: []`, every value exact against the golden oracle, and the
magnitude off by a factor of a thousand. No downstream consumer can recover the truth,
because the only evidence of the defect — the absence of the field in the source — was
consumed by the reader.

The instrument needed its own control before any of this counted. A first pass compared
the published value against the fixture's real value and reported `unit`,
`sign_convention` and `native_admitted` as "survived the pop, so presumably read from
source" — wrong in all three cases: those readers mint defaults that happen to equal
what this particular fixture says. Planting a distinctive value first, and requiring it
to reach the published fact, is what makes the drop result mean anything.

The repair stays inside the module's existing idiom: one more arm per field in
`_fact_admission_failure`, returning `fact_<field>_missing_or_malformed`, which
`degraded_dependencies` already accepts (its `reason` is an open
`{"type": ["string","null"], "minLength": 1}` vocabulary, so no contract change was
owed). One bad fact is withheld and declared; the case survives. That is why `event`
moved into the gate rather than staying with `_assert_document_matches_contract_shape`:
an absent `event` used to raise `CaseShapeError` and kill the whole case, where every
sibling omission withholds one fact and says so. One bad fact is not a bad case.
