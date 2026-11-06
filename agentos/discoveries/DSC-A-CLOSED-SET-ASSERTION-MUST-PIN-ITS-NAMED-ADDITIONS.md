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
  Historical source comparison: read integrations/slack_agent_dialogue/service.py and integrations/slack_agent_dialogue/engine.py at Mastermind f7ffc9cfed0cdecbbcc6468796dedab52db74856; compare the service's incumbent eight plus PACKET_OVER_CEILING with the engine's unchanged closed set. Supporting receipt: https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5827320369.
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
  Historical author-recorded verification dated 2026-09-25; supporting receipt: https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5827320369.
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

## Historical provenance — 2026-09-25

The measurements, confidence and verification date above describe the original September 25 observation. The November 6 record repair validates document structure and preserves source references; it does not rerun the historical experiment or establish current runtime behavior. The supporting [original receipt](https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5827320369) records the historical evidence.

The [later canonical lineage ruling](https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5841164702) designated claude/iac1-p1-packet-carriage-20260925 as **DONOR_TEST_EVIDENCE / DO_NOT_PUBLISH_AS_P1**, with [Mastermind #986](https://github.com/mastermindx-market-intelligence/Mastermind/pull/986) the canonical P1 carrier. Its held C-D child remained STOP / DO_NOT_PUBLISH. These knowledge records grant no transplantation, installation, live-packet or replay authority; all original refused or uncertain effects retain their original target and reconciliation boundary.

The pinned service/engine source corroborates the closed-set distinction. The original local brief and instrument are retained as the author's recorded episode; this repair did not reacquire those local artifacts or independently rerun them.
