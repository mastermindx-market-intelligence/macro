---
key: A-CLOSED-SET-ASSERTION-MUST-PIN-ITS-NAMED-ADDITIONS
claim: >
  An instrument that asserts a closed set "is still exactly the incumbent members" becomes
  unsatisfiable the moment the same programme deliberately adds one member - and it then reports
  the worker as wrong. Measured 2026-09-25 in the Mastermind IAC-P1 B2 slice: my pre-written
  instrument held both `PACKET_OVER_CEILING in ERROR_CODES` and `set(ERROR_CODES) == <the
  incumbent eight>`. Those are mutually unsatisfiable, and the brief I had myself dispatched
  ordered the addition. The instrument was wrong, not the returned head. The correct assertion
  pins the incumbent set PLUS exactly the named additions - `set(ERROR_CODES) == INCUMBENT |
  {"PACKET_OVER_CEILING"}` - so any OTHER widening still fails.
falsifier: >
  When an instrument contradicts itself, re-read the dispatched brief before attributing the
  failure to the worker. If the brief ordered the change the instrument forbids, the instrument
  is the defect. If the brief did not, the worker widened a closed set and the finding stands.
so_what: >
  Write closed-set fences as `INCUMBENT | {named additions}`, never as bare equality to a
  remembered set, and pair each with a test that the new member did NOT leak into a SIBLING
  closed set - a code added to a service error set must be provably absent from the engine's,
  or the two sets have quietly merged. More generally: an instrument is an artefact under the
  same review as the code, and "my test fails" is not yet evidence about the code. Check the
  instrument against the specification you actually sent.
kind: landmine
verified_at: 2026-09-25
verified_by: >
  Mastermind IAC-P1 at `f7ffc9cf`: the instrument's two assertions could not both hold; my
  dispatched brief (`brief_p1_B2_service.md`, item ordering the addition) resolved it against the
  instrument. Repaired to pin the eight incumbent codes plus that one name, and a companion test
  asserts `"PACKET_OVER_CEILING" not in set(DialogueEngineErrorCodes)`. Instrument then reported
  12 passed on the returned head and still failed on three deliberate mutations.
scope:
  - verification instruments
  - closed enum / frozenset fences
  - any brief that adds a member to a closed set
confidence: verified
---

The failure mode is asymmetric in a way that matters: a self-contradictory fence produces a
FALSE POSITIVE against a correct worker, which is the expensive direction. A reviewer who trusts
the instrument rejects good work and asks for a repair that cannot be written.
