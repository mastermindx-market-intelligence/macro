---
key: A-DANGLING-CITATION-IS-FAIL-OPEN-TO-THE-COMPILER-AND-FAIL-CLOSED-TO-THE-VALIDATOR
claim: >
  One `dangling-ref` rule serves two consumers with opposite dispositions — `agentos.py
  compile-context` renders the citing record anyway and prints the dangling citation as a
  visible `DEGRADED` line (exit 0, fail-OPEN, invariant I4), while `agentos.py validate`
  marks the identical Problem `hard=True` and exits non-zero (fail-CLOSED) — so a record
  may cite a `DEC:`/`DSC:`/`WS:` that lands in a LATER pull request without breaking any
  session's context bundle, and still turn the store's own gate red.
falsifier: >
  Add a `discoveries:` entry naming a record not in the tree, then run both consumers.
  `python3 scripts/agentos.py validate` printing no `::error title=agentos-dangling-ref`,
  or `python3 scripts/agentos.py compile-context --workstream <KEY> --text` refusing to
  render / omitting the `DEGRADED` line, falsifies this. Measured 2026-09-29 on
  WS:FLEET-STORAGE-LIFECYCLE citing DSC:A-RAISED-TIMEOUT-… before #8176 landed.
so_what: >
  A citation may FOLLOW its record into main but never precede it, so a records PR
  splitting a wave from the record it mints must hold the citation back and add it in the
  first commit whose base contains the file — and a session must NOT read the compiler's
  tolerance as permission, nor read `validate`'s refusal as evidence that a sibling's
  in-flight rename has broken anybody's context. Concretely: do not "fix" a red
  `dangling-ref` by deleting the citation permanently, and do not cite CLAUDE.md §Agent OS
  ("schema is fail-closed; joins fail open") as licence to cite forward — that sentence is
  true of the COMPILATION target and sits, misleadingly, in a sentence about `validate`.
kind: constraint
verified_at: 2026-09-29
verified_by: >
  scripts/agentos.py:1098-1111 (the CROSS_RECORD_RULES comment stating invariant I4) versus
  scripts/agentos.py:1139 (`hard=True` on the same rule); positive control — with the
  citation present, `compile-context --workstream FLEET-STORAGE-LIFECYCLE --text` printed
  "DSC:A-RAISED-TIMEOUT-… · — — dangling citation — no such record" under "DEGRADED (3)"
  and exited 0, while `validate` printed the matching `::error` and reported 2 error(s).
scope:
  - macro
  - agentos/
  - scripts/agentos.py
confidence: verified
---

## Why this is worth a record rather than a log line

The two dispositions are **correct on purpose**, and the reasoning is written in the source
right above the rule: a join failure is attributed to the CITING record, not to a record that
is itself wrong, so refusing to compile hands a session nothing instead of a bundle with one
named hole. `validate` is the store's gate and answers a different question — may this land.

What makes it a trap is that only one of the two behaviours is documented in `CLAUDE.md`, and
it is documented inside a sentence about the other one:

> `python3 scripts/agentos.py validate` must exit 0 (schema is fail-closed; joins fail open)

Read as a whole that reads like "validate tolerates a dangling citation". It does not. The
parenthetical describes the compilation target. A session that trusts it will write a forward
citation, watch its own PR go red, and — this is the expensive part — may then conclude the
repo's own law text is wrong and "correct" it. That correction would itself be false.

## The shape, which is not specific to Agent OS

This is the same family as `DSC:TWO-INDEPENDENT-GATES-MAKE-A-REGRESSION-IN-EITHER-ONE-INVISIBLE`
seen from the other side, and the same shape as a green main being a BLAME signal to
`ship_loop_guard.py` and an ACTION trigger to the merge sweeper. **When one predicate feeds
two consumers, "what does it mean" has no answer until you say to whom.** Before quoting a
disposition — fail-open, tolerated, blocking, ignorable — name the consumer you measured, and
run the other one before generalizing.
