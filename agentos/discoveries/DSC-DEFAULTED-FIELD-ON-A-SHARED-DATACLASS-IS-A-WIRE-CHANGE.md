---
key: DEFAULTED-FIELD-ON-A-SHARED-DATACLASS-IS-A-WIRE-CHANGE
claim: >
  Adding a DEFAULTED field to a dataclass that is serialized onto a service wire changes the
  public response shape of every operation that returns it, even for callers and engine
  versions that never write the field. A brief that fences the new field's BEHAVIOUR
  ("the V1 engine does not classify packets, so its counters stay 0") has not fenced the
  field's WIRE, and any consumer that validates the response by exact key set breaks.
  Measured 2026-09-25 in the Mastermind IAC-P1 packet-carriage lane: slice B1 added
  `packet_count` and `packet_ineligible_count` as `int = 0` to the shared
  `integrations/slack_agent_dialogue/engine.py::ThreadRead`. `AgentDialogueService.engine_result`
  is `jsonable(value)` and `jsonable` serializes every dataclass field, so both keys appeared in
  the public AF_UNIX `read_thread` response for BOTH engine versions.
  `ExecutiveTerminalReturnProjector._read_committed_result` validates that response with
  `set(result) != expected_keys` against the five incumbent keys and calls
  `_refuse("EFFECT_UNKNOWN")` on any mismatch - so a valid lifecycle read began refusing, which
  can suppress a legitimate terminal send. Three of the eight resulting failures are on the V1
  path, whose engine never classifies a packet and always reports 0.
falsifier: >
  Run the owner-seam consumer at four ordered heads of one branch. At the head before the field
  was added the suite passes; at the head that adds the two defaulted fields - whose only
  `ThreadRead` delta IS those two fields - it fails, including on the engine version that never
  writes them. Measured: `7d46e301` 25 passed / `b127f96f` 25 passed / `7e45b3ec` 8 failed,
  17 passed / `0603e1e0` 8 failed, 17 passed. If the pre-field head failed too, the break is
  older and this record does not apply.
so_what: >
  When a brief adds a field to a type that crosses a service boundary, the brief must name the
  wire, not only the behaviour: which operations serialize this type, which consumers validate
  those responses by exact key set, and where the field is stripped before it becomes public.
  Two operational consequences that cost a full accept-then-retract cycle here. First, a gate's
  suite list bounds what the gate can detect, and a list inherited from the same brief that
  authored the change is structurally incapable of catching a consumer outside it - derive the
  gate from the type's consumers (`grep -rln <module> tests/`), not from the brief. Second, a
  test double that returns a plain dict where production returns a dataclass cannot see additive
  field drift at all, and per-key assertions are blind to it; only an exact-key-set assertion
  against a REAL engine response detects it. Third, do not let a `-k` filter that a reviewer coined
  to NAME the defect become the acceptance gate: here `-k owner_seam` reported 8 failures while the
  whole suite reported 9, and the hidden ninth
  (`test_terminal_candidate_posts_one_result_and_one_persisted_wake_across_replay`) is the test that
  states the consequence directly - greening the eight against that filter would have accepted the
  slice with the real-world case still red. The repair belongs at the service projection - strip the
  internal fields at the specific operation whose public shape is contractual - never in the shared
  serializer, which every other operation also uses.
kind: landmine
verified_at: 2026-09-25
verified_by: >
  Four-head execution of `tests/test_slack_agent_dialogue_executive_terminal_return_projector.py
  -k owner_seam` on `~/.venvs/mastermind-workbench-modern-mcp-test/bin/python`, fresh `mktemp -d`
  temproot per invocation, in a read-only detached worktree: 25 passed at `7d46e301` and
  `b127f96f`, 8 failed / 17 passed at `7e45b3ec` and `0603e1e0`. `git show
  7d46e301:...engine.py` confirms `ThreadRead` carried exactly the five incumbent fields before
  the slice. Exact-key-set mechanism read at the owner
  (`executive_terminal_return_projector.py:869-874`), not inferred. The six-suite gate that
  accepted the slice did not include this consumer; the 43-suite set derived from
  `grep -rln slack_agent_dialogue tests/` does. Differential over that whole set with
  `-p no:randomly`: `b127f96f` = 1898 passed / 2 skipped / 0 failed, `0603e1e0` = 9 failed / 1914
  passed / 2 skipped, the nine new failures all in the one projector file and nothing fixed - so the
  blast radius is one consumer, and the filter-vs-whole-suite gap (8 vs 9) is measured rather than
  argued. Whole projector suite alone: 81 passed at `b127f96f`, 9 failed / 72 passed at `0603e1e0`.
scope:
  - mastermind slack_agent_dialogue service wire
  - any dataclass serialized by jsonable onto a service response
  - dispatched worker briefs that add a field to a shared type
  - acceptance gate suite selection
confidence: verified
---

The trap is that every local signal says the change is safe. The field is defaulted, so no
constructor breaks. The new engine is the only one that writes it, so the fence on behaviour
reads as complete. The slice's own suite passes, and so do dozens of neighbouring suites -
because their doubles return plain dicts and their assertions are per-key. The only instrument
that fails is a consumer three seams away that happens to validate by exact key set, and it
fails with `EFFECT_UNKNOWN` - a refusal code, not a shape error - so the symptom does not name
its cause either.

Worth separating two things a reviewer conflates under "I fenced the V1 engine". Fencing
behaviour means V1 never populates the field. Fencing the wire means V1's response never
carries the key. The first does not imply the second, and only the second is what an exact-shape
consumer is asserting about.
