---
key: BRIEF-FENCE-BY-NAME-DELETES-GUARD-PROPERTIES
claim: >
  A delegation brief that fences a new message/frame class out of an existing pipeline by
  NAMING the function it must skip deletes every property that function proved, not only
  the one the brief's author had in mind. Measured 2026-09-25 on IAC-P1-B1 (Mastermind
  `claude/iac1-p1-packet-carriage-20260925`): the brief said a consultation-packet frame
  must "never reach `_sender_is_eligible`", intending to keep packets out of LIFECYCLE-ACTOR
  semantics (correct, and still required). That same guard also carried PHYSICAL-ORIGIN
  authority - it is what proves the Slack writer was allowed to write at all. The worker
  implemented the instruction faithfully and emitted a code comment reading "never
  sender-screened". At the returned head 7e45b3ece51bbeb6 a canonically valid packet
  authored by an arbitrary Slack identity was returned by `read_consultation_packet` as
  `outcome=PACKET` WITH its body, and `prepare_send_message(frame_kind=CONSULTATION_PACKET)`
  returned `MessageReceipt(action='DUPLICATE')` credited to the untrusted timestamp - which
  suppresses a required legitimate send. Canonical-JSON validity and fingerprint integrity
  had silently been substituted for writer authority. Nothing was armed, so no production
  effect occurred.
falsifier: >
  An independent instrument, written before the repair returned and positive-controlled, that
  asserts the property rather than the implementation: an unauthorized-origin packet must not
  be served as PACKET, must carry no body, must not yield a DUPLICATE receipt, and must not
  satisfy post-effect recovery - plus a legitimate-origin control that must pass on BOTH
  heads. Result: 4 fail / 1 pass at defective 7e45b3ec, 5 pass at repaired 0603e1e09. Two
  mutation tests confirm teeth rather than coincidence: disabling the origin screen produces
  9 failures across two independent test sets, removing the malformed-frame raise produces 4.
  This record is falsified if the repaired head still serves an unauthorized packet, or if the
  legitimate-origin control ever fails (which would mean the instrument, not the code, is
  broken).
so_what: >
  When fencing a new class out of an existing pipeline, never name the functions it must skip.
  Enumerate what each bypassed step PROVES, and re-state which of those proofs the new class
  still owes. Cheap check before dispatch: for every guard named in a "never reaches"
  instruction, write the sentence "without this, an attacker can ___" - if that sentence has
  content, the fence is wrong and the new class needs its own equivalent. The second half of
  the same lesson is that the incumbent's STEP ORDER is itself a specification: the existing
  V2 branch runs discriminator -> sender screen -> parse, and that order is precisely why an
  unauthorized malformed frame is never parsed, so a foreign writer cannot force a raise in a
  lifecycle read. Mirroring the incumbent order closed both defects with no new error code, no
  second sender registry and no caller-supplied sender. A parallel branch that parses before
  (or without) screening reintroduces the exposure. Also: an existing test can encode the
  defect - here `test_packet_frame_is_never_parsed_as_a_v2_message` posted its packet as
  `author="U0UNKNOWN01"` and asserted `packet_count == 1`, creating live pressure to widen the
  authority rule rather than fix it. Repair the assertion, never the rule.
kind: landmine
verified_at: 2026-09-25
verified_by: >
  Defect confirmed by two independent methods that agreed: Sol proved `_scan_thread`,
  `_history`, `read_consultation_packet`, `_find_packet`, `prepare_send_message` and
  `_validate_outbound_packet` byte-identical between the tested intermediate 5e5c79ce and the
  returned 7e45b3ec; separately reproduced directly on the returned head, where ordinary
  `read_thread` also returned `packet_count=1 ineligible=0 mutated=0` for a malformed packet
  frame. Repair verified at 0603e1e09 by an independent six-suite gate on a second interpreter
  with a fresh PYTEST_DEBUG_TEMPROOT (419 passed, 0 failed = the worker's 418 plus the one
  venv-only MCP failure that passes on a current SDK), the pre-written instrument above, both
  mutation tests, and AST-extracted `status()` body sha256 58a0ebd399241516 identical at the
  accepted P1-0 head 7d46e301 and at 0603e1e0.
scope:
  - delegation brief authoring
  - any new frame/message class added to an existing validated pipeline
  - mastermind integrations/slack_agent_dialogue/engine_v2.py
confidence: verified
---

The tempting substitution is specific and worth naming: a frame class whose bodies are
independently fingerprinted is exactly where content integrity feels like authentication.
It is not. A fingerprint proves the bytes are well-formed and unaltered; it says nothing
about who was permitted to post them. Any design where the new class carries its own
canonical form should expect this confusion and state the origin rule explicitly.

The authorship point generalises past this codebase. The worker did nothing wrong - it
implemented a precise instruction precisely. Review that only asks "did the worker follow the
brief?" cannot catch this class of defect, because the brief is the defect. The only review
that catches it asks what each instruction REMOVES.
