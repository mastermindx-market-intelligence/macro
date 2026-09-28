# Reflex firing metadata integrity — Prophet risk-policy prerequisite

**BUILT_NOT_PROVEN / SOURCE REPAIR. No policy or production activation.**

Operation: `prophet-risk-reflex-record-integrity-20260928-sol-001`.
Parent: Prophet #6817 / existing Grey Deer risk intelligence. This is independent
of the frozen GD-6A PR #8141, whose R6 CI has passed and whose latest-base release
compatibility remains unqualified after an action-scoped read refusal.

## Source-bound finding

Native `engine/neuralweb/reflexes.py` at
`fd072295de2e9be1fcd8ed81284676187054e4a7`, blob
`0789f44d6a7875ebba63b67a4912f10a5d09f27e`, documents five writer-owned fields:
claim_id, reflex, claim_family, desk and is_context_only. Its actual constructor
placed `**payload` after those fields. A fictional payload persisted arbitrary
caller identity and is_context_only=False through the real module in a temporary
isolated root. This establishes a metadata-contract defect, NOT a real trade,
a demonstrated production incident or a claim of arbitrary trading authority.

## Minimal repair

Define the existing five fields once, merge the observation payload, then restore
the writer-owned values. Their original insertion order is retained. Ordinary
payloads therefore keep the original serialized bytes, ID formula, time handling,
append behavior and return structure. Matching redundant fields remain accepted.
The input mapping is not changed. Fail-soft write-error reporting is unchanged.

No registry, caller, stored historical firing, policy threshold, grant, schedule,
ranking, sizing, execution or user holding is changed. The writer still does not
establish financial-policy admission or enforce a global single-writer lease.
A context-only record is evidence, not proof of an earned/temporary policy grant.

## Actual qualification

Five new test methods include eight parametrized field/type override cases.
Together with the existing writer and load tests: **20 cases PASS** after repair.
The original writer produces **10 failed / 10 passed**, with all ten failures
being intended assertions, not missing dependencies. Ordinary-payload exact-byte
parity, all-five collision, matching metadata, input immutability, disk roundtrip
and canonical fields on a simulated write failure are covered.

These are synthetic module/temporary-filesystem tests, not market observations,
independent semantic review, whole-application tests or hosted CI. The existing
neural-web-core command gains the two exact TestRecordFiring/TestLoadFirings node
IDs. All other commands, jobs and scopes are unchanged; no new CI owner. Other
classes in test_reflexes.py are NOT claimed newly covered by this registration.

Seven named production source callers were inspected at the same commit. Literal
payloads examined carry no conflicting owner fields; three variable-payload call
sites remain only statically identified, not a proof of every dynamic input.
The contract—not a guess about callers—requires the metadata to remain owned.

Before/after logs and source hashes are retained in the existing host evidence
under release-r7/reflex-integrity. The primary author performed this audit under
the Chairman's explicit self-audit instruction; do not call it independent.

## Release boundary

Publish this minimal source repair on its own review carrier so PR #8141 stays
frozen. Require real current-base CI and normal release proof; do not bypass the
blocked GD-6A compatibility read through this operation. No existing historical
record is rewritten. The program is still missing qualified nonzero policy
adoption and ordinary served end-to-end risk-restriction proof.

Protected procedure: Mastermind
`7aa27814c65983932f466d7b79e293e24f5a69c7`, compatible Skillpack1.0.1/bootstrap1.
No worker, watcher, production firing, source-custody transfer or automatic wake.
MISSION_COMPLETE:false.
