---
key: POST-COMMIT-SEND-AMBIGUITY-IS-NEVER-SERVICE-UNAVAILABLE
claim: >
  When a send has passed COMMIT and the outcome is then unknown, the failure code a service
  returns is not a diagnostic detail - it is a claim about effect. `SERVICE_UNAVAILABLE` asserts
  nothing happened; `SEND_EFFECT_UNKNOWN` asserts the caller must reconcile. Returning the first
  where the second is true invites a duplicate send. Measured 2026-09-25 in the Mastermind
  IAC-P1 packet-carriage slice (`integrations/slack_agent_dialogue/service.py`): the code is
  selected by a two-part guard - `request_snapshot.get("version") == CONTROL_VERSION_V2 and
  exact_send_operation is not None` - so a NEW send operation that is not registered in the
  exact-send operation set silently degrades every post-COMMIT ambiguity on that operation to
  `SERVICE_UNAVAILABLE`. Adding a send operation therefore has a correctness obligation that
  lives nowhere near the code being written.
falsifier: >
  Drive the new send operation to a post-COMMIT ambiguity (kill the peer after COMMIT) and read
  the error frame. If it is `SEND_EFFECT_UNKNOWN`, the operation is registered and this record
  does not apply. If it is `SERVICE_UNAVAILABLE`, the guard has silently excluded it. A unit test
  that asserts the code for the INCUMBENT operation only cannot distinguish these.
so_what: >
  Any slice that adds a send operation must add a discriminator that drives the NEW operation to
  post-COMMIT ambiguity, not merely assert the incumbent's code still works. Two corollaries
  measured in the same slice: (1) a connection funnel of `except Exception: await
  self._error(writer, "INTERNAL_ERROR")` is what keeps an unregistered-operation `KeyError` from
  becoming a false effect claim, so read the funnel before asserting a consequence - a
  hypothesised false `SEND_EFFECT_UNKNOWN` turned out to be merely a worse diagnostic; and (2)
  parallel per-operation lookup maps must be read with the SAME guard style, because one bare
  subscript among `.get()`-guarded siblings converts a typed refusal into an internal error.
kind: landmine
verified_at: 2026-09-25
verified_by: >
  Historical author-recorded verification dated 2026-09-25; supporting receipt: https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5825891875.
  Source read at Mastermind `f7ffc9cf` and `87117418` on branch
  claude/iac1-p1-packet-carriage-20260925: the `send_effect_code` conditional, the three
  `_EXACT_SEND_OPERATION_*` maps (two read via `.get()` with an `is None` guard, one via a bare
  subscript), and `_handle_connection`'s `except Exception -> INTERNAL_ERROR` funnel which does
  send the error frame. A 12-test instrument drove four post-request ambiguities over real UNIX
  sockets: 8 failed / 4 passed before the repair, 12 passed after.
scope:
  - integrations/slack_agent_dialogue/service.py
  - any exact-send service seam with a closed operation set
  - post-COMMIT effect reconciliation
confidence: verified
---

The reason this is a landmine and not a style note is that the wrong code is the *safer-looking*
one. `SERVICE_UNAVAILABLE` reads like an honest admission of trouble, and a reviewer scanning for
overclaims will not flag it. It is in fact the stronger claim: it tells the caller the send did
not happen. The weaker, correct claim is the one that sounds worse.

## Historical provenance — 2026-09-25

The measurements, confidence and verification date above describe the original September 25 observation. The November 6 record repair validates document structure and preserves source references; it does not rerun the historical experiment or establish current runtime behavior. The supporting [original receipt](https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5825891875) records the historical evidence.

The [later canonical lineage ruling](https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5841164702) designated claude/iac1-p1-packet-carriage-20260925 as **DONOR_TEST_EVIDENCE / DO_NOT_PUBLISH_AS_P1**, with [Mastermind #986](https://github.com/mastermindx-market-intelligence/Mastermind/pull/986) the canonical P1 carrier. Its held C-D child remained STOP / DO_NOT_PUBLISH. These knowledge records grant no transplantation, installation, live-packet or replay authority; all original refused or uncertain effects retain their original target and reconciliation boundary.
