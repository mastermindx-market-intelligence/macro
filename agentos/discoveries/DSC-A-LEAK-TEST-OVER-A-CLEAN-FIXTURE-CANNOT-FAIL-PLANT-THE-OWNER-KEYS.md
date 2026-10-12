---
key: A-LEAK-TEST-OVER-A-CLEAN-FIXTURE-CANNOT-FAIL-PLANT-THE-OWNER-KEYS
claim: >-
  Through main 740554259f51 the Finance composer copied an owner metric mapping
  wholesale (`metric = dict(metric_in)` in `_build_primary_metric`,
  engine/sector_intelligence/finance_projection.py). Any key an owner put on a financial
  packet's metric (a peer rank, a composite score, a private note) therefore reached
  `slices[].rerating.{operating,valuation}.primary_metric` in the emitted read model. It did
  so in 4 of the seat probe's 35 single-field plants across the six test fixtures. Three
  things looked like protection, and none of them fired. First, the docstring-advertised
  `_FORBIDDEN_KEY_RE` had no call site
  (DSC:A-GUARD-NAMED-IN-THE-DOCSTRING-CAN-HAVE-ZERO-CALL-SITES). Second, the test oracle
  `test_no_forbidden_keys` walked keys with fullmatch on a boundary-stem pattern
  (DSC:FULLMATCH-ON-A-BOUNDARY-STEM-PATTERN-IS-A-DEAD-GUARD-THAT-LOOKS-ALIVE), and it only
  ever walked an unplanted fixture. Third, the closed contract rejects such a document, but
  only where a test calls validate_contract, and no test composed an owner key that the
  contract does not know. The leak was latent: nothing serves the read model yet (T4-T7 are
  held). The composer now projects an owner metric onto `_METRIC_FIELDS` (pinned to the
  schema's `$defs/metric`) and runs `_FORBIDDEN_KEY_RE` over the whole document before it
  returns. It is still stdlib-only and validates nothing else at emit. The key plant this
  record introduced was itself blind to a second channel: an owner structure the composer
  turns into a string (27 leaks at 8 sites on the round-1 head, see
  DSC:A-SEALED-CONTRACT-CANNOT-SEE-A-STRUCTURE-STRINGIFIED-INTO-FREE-TEXT).
falsifier: >-
  Restore `metric = dict(metric_in)` in `_build_primary_metric`, then run
  `python3 -m pytest tests/test_finance_intelligence_projection.py -q -k owner_key_outside`.
  Exactly the four metric-routing fixtures (EARNINGS_UP_P_E_DOWN, BOOK_UP_P_B_DOWN,
  POLICY_SUPPORT_NIM_PRESSURE, REGULATORY_RATIO_DOWN_REGIME_BREAK) must fail, and the default
  and PRICE_UP_CAUSAL_EVENT_EFFECT_UNPROVEN fixtures must pass. If they all pass under the
  restored copy, this was not the leak path.
so_what: >-
  (1) A leak or authority test over a clean fixture cannot fail. It must plant keys the
  contract does not know into every owner record, one input field at a time, and assert
  two things: the document still validates, and it holds none of the planted keys. Every
  oracle also needs its own positive control, because a walk that finds nothing on a clean
  document looks exactly like a dead walk. Adding keys is necessary and not sufficient: it
  never runs a fallback, so the fence must also delete, empty and replace owner values. (2) A guard named in a docstring is a claim
  until it has a call site. The cheap check is to grep the constant and subtract the
  definition line. (3) The Finance integration wave's publish step (T6) must call
  validate_contract on the composed document before anything is served. The sealed contract
  is the only complete KEY check, and the composer does not run it. It is no check at all
  on content the composer has already turned into a string. (4) An owner mapping that
  crosses into the read model goes through a closed vocabulary, never through dict(), and
  owner text crosses only as a scalar, never through str() of a structure.
  (5) rights_snapshot is a map keyed by data (source family to rights class), and
  generation.rights_profile publishes its family names by design. A plant-based fence must
  skip maps keyed by data, or it reports its own plant as a leak.
kind: landmine
verified_at: 2026-09-28
verified_by: "tests/test_finance_intelligence_projection.py::test_an_owner_key_outside_the_contract_never_reaches_the_document (4 failed, 2 passed with dict(metric_in) restored; 6 passed with the fix); seat red-proof 6/6 RED (closed vocabulary reverted, emit guard removed, guard under fullmatch, oracle under fullmatch, vocabulary drops currency, guard skips nested lists); seat probe on main 740554259f51: 4 of 35 plants leaked, all through financial_packets"
scope:
  - macro
  - engine/sector_intelligence/finance_projection.py
  - tests/test_finance_intelligence_projection.py
  - contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json
confidence: verified
---

The leak was found by a reachability probe that planted a key into every owner record
under one `FinanceOwnerInputs` field at a time and composed. It was not found by reading
the guard. The probe is now a permanent test:
`test_an_owner_key_outside_the_contract_never_reaches_the_document`, parametrized over all
six fixtures. Its own positive control, `test_the_owner_key_fences_fire_on_a_key_the_composer_admits`,
makes the composer admit one more metric key. It then shows that the contract rejects a
private note, and that the emit guard refuses a peer rank while naming only the document
section, never the owner's key.
