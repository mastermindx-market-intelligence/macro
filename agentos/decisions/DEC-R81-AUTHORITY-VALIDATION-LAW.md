---
key: R81-AUTHORITY-VALIDATION-LAW
question: >
  After ten consecutive bounded repair rounds on the Mastermind W1-H3 CEO-submit sealed
  receipt (R9, R17, R18-B4, R36, R48, R50, R68, R76, R80, R80-B1/B2), each of which went
  green and each of which was followed by a new instance of the same acceptance failure,
  should the programme issue an eleventh instance repair or freeze a law that closes the class?
answer: >
  Freeze the class. R81 adds three scoped laws to the accepted Executive/autonomy architecture:
  (1) every invariant required to GRANT authority or eligibility must be asserted at the
  authority-granting read, from canonical current evidence or a separately authenticated
  authority source, through one shared owner - this binds authority/eligibility invariants
  only and imposes no writer/read assertion parity on provenance-only or audit fields;
  (2) any document or response crossing a trust boundary is parsed into a typed value with
  exact types and bounded domains and rejected wholesale on deviation - field-by-field `!=`
  against untyped input is not validation; (3) an unauthenticated, self-describing artifact
  whose only integrity evidence is a digest it computes over itself cannot supply its own
  authority facts - such a field is a label, not an authority fact, which does not forbid a
  future independently authenticated canonical attestation from carrying authority.
  W1-H3 must land B1, B2 and B3 as ONE consolidated repair under these laws rather than as
  three further sequential rounds.
rationale: >
  The three open W1-H3 blockers are one defect: the design compares where it must assert and
  checks where it must parse. `ceo_submit_sink_eligible()` copies the live App validity flags,
  the App peer user and both COO arm flags into its recomputed projection and digest-compares
  them instead of asserting them, so it is a DRIFT DETECTOR ("did anything change since the
  receipt was written?") and not an AUTHORITY VALIDATOR ("is the current state one the
  architecture authorizes?"). Those two questions diverge exactly when the receipt is minted
  in an unauthorized state. Because the receipt carries no authenticator - no key, nonce,
  counter or witness - and because writing `control.json` (0440 root) and
  `ceo-submit-state-v1.json` (0444 root, in a 0755 root directory) require the SAME privilege,
  the party the receipt exists to stop can always mint one. The set of documents that
  compare-equal-but-must-not-be-authorized is therefore unbounded, and instance-by-instance
  repair cannot terminate; a monotonically growing green suite (65 -> 110 -> 155 -> 171 ->
  248 -> 274 -> 350) is what that looks like from inside. Laws 1 and 3 are deliberately scoped
  so the freeze constrains authority grants without taxing provenance/audit fields or
  foreclosing a properly authenticated attestation later.
alternatives:
  - option: Issue an eleventh bounded instance repair for B3 alone
    why_not: >
      Leaves the generating mechanism intact. B1, B2 and B3 were each found by a different
      reviewer using a different probe; nothing in the design stops a twelfth instance.
  - option: Add an authenticator (keyed MAC / signature) to the sealed receipt
    why_not: >
      Requires a key and a key-custody lifecycle - a new secret plane. Forbidden by Charter P7
      duplicate_control_planes, Skillpack INDEX hard law 2, and Sol R48's explicit prohibition
      on a replacement receipt, controller or validation plane.
  - option: Give `transaction_id` an independent durable owner so the receipt proves provenance
    why_not: >
      Its only independent owner, the transaction manifest, is unlinked by
      `complete_transaction` on success. Every replacement needs a durable transaction log or
      a key - both forbidden second stores. Accepted instead as a correlation label.
  - option: Change the frozen receipt shape (drop `transaction_id` from the digest-bound projection)
    why_not: >
      Cleaner in the abstract but breaks the R48-pinned projection field set for zero security
      gain - the digest over that field is already circular. Costs a re-review round.
  - option: Defer the whole class to W1-H4 as an integration concern
    why_not: >
      False. The shipped root-only `ceo-submit-status` verb consumes the predicate TODAY and
      reports CEO_SUBMIT_ARMED exit 0 in all eight states ARM refuses.
evidence:
  - "Mastermind PR #677 head 6dc2ea83bc738c2532745ef71dcde6c170c58d91, Draft/Hold, owning suite 274 passed"
  - "Ruling published as PR #677 comment 5706016890 (readback byte-identical modulo one appended trailing newline)"
  - "B3 hostile witness: 8/8 states that evaluate_ceo_submit_arm_admission REFUSES are minted-receipt ELIGIBLE, CLI CEO_SUBMIT_ARMED exit 0, writes=(0,0,0) - probe sha256 aa05cebe4b1a9cf3543bf8591cdf580f8074b619162e72ca66ba793638a17b8a"
  - "Candidate repair discriminator: 8/8 -> 0/8 with all four controls unmoved - probe sha256 332c401f359307904b1c1e9f3e8c13883494201d433bc3e2f58a9a09fbefda46"
  - "B2 falsifier: 9 RED (6 JSON-float identity facts, 3 malformed exec paths) against a passing positive control - probe sha256 d3f0ea0c029a3b8fff14e698386d37172b0996dc5e954b7d1089ad674f3f8d92"
  - "B1: ops/executive_os/autonomy_control.py _ceo_admission_probe assigns `control, _raw = _root_json(...)` and never hashes `_raw`"
  - "R48 malformed-document matrix independently re-run at this head: 0/8 open - B3 is a distinct class"
  - "Privilege equivalence: install.sh:1253-1254 (worker 0440 root:_mastermind_worker), install.sh:1275 (control runs as _mastermind_exec)"
  - "Prior same-carrier exact-head review 5705740434 independently co-reproduced B1 and B2"
affects:
  - WS:EXECUTIVE-CAPACITY-FABRIC
  - mastermind/ops/executive_os/autonomy_control.py
  - mastermind/scripts/executive_os_phase1c_control_wrapper.py
  - mastermind/control_plane/executive_service.py
confidence: high
reversibility: costly
decided_by: ceo-sol
decided_at: 2026-09-16
---

## Scope limits, stated so later waves do not over-apply this

Law 1 binds **authority/eligibility** invariants. A provenance or audit field may be recorded
at write without being re-asserted at read; that is not a violation.

Law 3 constrains **unauthenticated, self-describing** artifacts. If a later wave introduces an
independently authenticated canonical attestation, that attestation may carry authority facts.
R81 forbids self-certification, not attestation.

## What W1-H3 owes under this decision

One consolidated repair head on the same PR, branch and incumbent writer, inside the existing
four-path ceiling from Sol comment 5704046553:

1. **B3** - one shared private pure predicate `_ceo_submit_arm_state_authorized(control, binding)`
   asserting what `evaluate_ceo_submit_arm_admission` already owns (App peer user; binding/ACL/
   topology each `is True`; `ceo_ingress_app_armed is True`; both COO arm flags `is False`; both
   ingress uids exact `int`, distinct, and the host-observed App peer uid equal to the config's
   declared value), consumed at BOTH the ARM gate chain (behaviour-neutral refactor) and
   `ceo_submit_sink_eligible` (behavioural half, after the existing `binding.present` guard).
   Same shape already accepted for `_ceo_submit_binding_matches_control` in R36.
2. **B1** - hash the exact bounded raw bytes already returned by `_root_json` and require equality
   with `expected_control_sha256` before consuming the attestation path or control UID.
3. **B2** - in the wrapper owner: exact bounded `int` for pid/pgid/session/uid/gid rejecting `bool`
   and `float` by type; bounded non-empty safe strings for start/boot identity; bounded canonical
   absolute executable path rejecting NUL, control characters and traversal; 40-lowercase-hex
   release identity.
4. **One authority-parity test** asserting that every AUTHORITY invariant ARM refuses is also
   refused at the authority-granting read. This test is the falsifier for the whole class.

Safe-direction DISARM is untouched: the predicate never runs on the disarmed branch, and
DISARM/rollback build receipts through `validate_ceo_submit_receipt_document(armed=False)`.

`transaction_id` remains a correlation/provenance label. No receipt-shape change.

## What this decision does NOT authorize

No W1-H4 start, Ready transition, merge, enqueue, install, restart, ARM/DISARM, Job, provider,
credential or production effect. H3 capability remains `BUILT_NOT_PROVEN / SOURCE_ONLY`.
Source custody stays with the incumbent child/branch/writer; the repair being mechanical means
no further principal adjudication round is owed, not that custody moves.
