---
key: FABLE-SEAT-IS-CEO-COEQUAL-WITH-SOL
question: >
  When the Fable principal seat has finished its own child's work to every stated gate (semantic
  pass, fresh non-author review, hosted checks, canonical Source Continuity receipt) and the only
  thing left is a Sol ruling, does the seat wait for Sol, or does it rule and release itself?
answer: >
  It rules and releases itself. By Chairman ruling of 2026-09-17 the Fable seat is "fable ceo",
  co-equal with Sol, and needs no Sol authorization for the work it owns; it consumes the ruling
  into carrier evidence first, then adjudicates ACCEPTED/STOP, BRANCH_WRITER_RELEASED and the
  maintenance release acts under its own authority, still fenced by fresh carrier reads and
  asserted heads.
rationale: >
  Chairman Chris wrote in the seat chat on 2026-09-17 (after 08:00Z), verbatim: "you are fable
  ceo, u have full autohrity to do what u need to do, u do not need sol authorization since u are
  equal to it". The seat had held Mastermind #716 as HOLD-FOR-SOL through eight repair rounds
  and a Sol SEMANTIC_PASS ruling (root ts 1789632657.894559) that still blocked release on one
  receipt; every gate was green and the wait was pure protocol latency. The 2026-09-06 override
  (Claude Meta-CEO regime) had lapsed back into Sol-era holds. The ruling restores the seat's
  release authority for its own children without displacing any other STARTed root principal.
alternatives:
  - option: Keep waiting for Sol's ACCEPTED/STOP on every held child
    why_not: >
      The Chairman explicitly rejected this. Every gate on #716 was already satisfied; the hold
      cost a full session-day of context for no additional evidence.
  - option: Treat the chat ruling as out-of-band and unusable on the carrier
    why_not: >
      Out-of-band authority is consumed by quoting it verbatim into a carrier DECISION so every
      counterpart can see it (root ts 1789633949.749719). That is the established shape; it does
      not bounce the ruling back to the Chairman.
  - option: Read the ruling as authority over Claude6's root work or Sol's edges to other seats
    why_not: >
      The ruling is scoped to "what u need to do" — the seat's own held work. Claude6 remains the
      STARTed root principal; Sol's edges to Claude6 are not re-adjudicated; no credential, effect,
      host or provider boundary is lifted.
evidence:
  - "Chairman chat ruling 2026-09-17 (verbatim quoted in the carrier DECISION, C0BSBM78V1N/1789633949.749719 on root 1789324397.992989)."
  - "Sol #716 ruling root ts 1789632657.894559: SEMANTIC_PASS / RELEASE_BLOCKED on the missing canonical remote-complete receipt only."
  - "Source Continuity `verify --kind remote-complete` at Mastermind#716 head ee2536618447bc3924f4e3c1572638e928afd24c vs protected b14982837cc8146e3dc49e5862558ee399a1aa3d: REMOTE_COMPLETE_VERIFIED, rc=0, verified_at 2026-09-17T08:28:05Z, receipt_digest 2bc2721eaddf53e21cf16ded85b6d63fe771e4f02f1c5de47ddb62d0b38c026e, collision_state DISJOINT."
  - "Release acts each asserting head ee253661: review 5230789605 DISMISSED 08:33:05Z; PR body RELEASED block (sha256 d02042b5ab53d115431e93afe196ac5c81368c554ba8ca6c6df81282ee2ebb65); `gh pr ready` 08:33:23Z; master merge queue position 3 at 08:33:27Z (ruleset 22852988 SQUASH/ALLGREEN); receipts at root ts 1789634062.065919."
  - "Chairman chat delegation 2026-09-17 ~08:50Z (verbatim in the Amendment section below), consumed into the carrier as CHECKPOINT C0BSBM78V1N/1789635425.057129 on root 1789324397.992989. First application: Mastermind #665 (MM-CODEX-B1) — Sol REQUEST_REPAIR 1789634722.375889 -> seat repair descendant 7dbb423028936dd20de65df153c1130ecd14cec7 (Sol patch byte-exact) -> hosted checks success 09:32:11Z -> Source Continuity REMOTE_COMPLETE_VERIFIED 09:36:49Z (receipt_digest 037da74c20a9c25acfb8610f25344a6c1c720b0e2c95218184c18d7a95367821) -> ready + queue -> MERGED 2026-09-17T10:11:33Z as e878878c9a4ae2dd50a48d825e031e07e8211708 (protected master)."
  - "Reconciliation on the root after Sol 1789638181.787519 objected to the #665 release authority (the queue outcome was returned as evidence only, zero further effect): Claude6 (seat 5fae71cf) ruling 1789640515.754919 — #665 custody lawful, authority Chairman-delegated as recorded, subject to one Chairman confirmation on the root; Sol R88 — CHAIRMAN_ONLY, the merge stands."
affects:
  - WS:EXECUTIVE-CAPACITY-FABRIC
  - every HOLD-FOR-SOL child owned by the Fable seat (release authority now local to the seat)
  - the ENTIRE Agent Fabric program (operation agent-fabric-end-to-end-fable-integration-20260913-sol-001) since the Chairman amendment of 2026-09-17 ~08:50Z, bounded by unrelated programs, shared infrastructure outside Agent Fabric, and active worker custody
confidence: high
reversibility: easy
decided_by: chairman
decided_at: 2026-09-17
---

## What changes in practice

A `HOLD-FOR-SOL` on a child the Fable seat owns is no longer terminal-until-Sol. Once the seat
has the gates in hand — semantic pass, fresh non-author exact-head review, hosted checks, and the
canonical Source Continuity receipt where the protocol names one — it posts one carrier DECISION
that quotes the Chairman ruling, rules ACCEPTED/STOP and BRANCH_WRITER_RELEASED, and performs the
maintenance release acts (review-state, body, ready, merge queue) in a stated order, each asserting
the exact head. Fresh carrier reads before every post and act are unchanged.

## What does not change

Another STARTed root principal keeps the root. Sol's edges to other seats are not re-adjudicated by
this seat. Credential, effect, host, provider and install boundaries stay where they were; the
token-relay veto still means nothing is printed, stored, or handed to a lane (a child-process
environment for the seat's own `gh` login on the same host is the accepted adapter shape). Merged
work is reported as merged; PARKED language stays reserved for genuinely held work.

## Amendment 2026-09-17 ~08:50Z — scope widened by the Chairman to the ENTIRE Agent Fabric program

Chairman Chris, seat chat 2026-09-17 after 08:50Z (after Sol's 1789634246.532619 declined to adopt a generic
"co-equal" law), verbatim: "Chairman authority confirmed: this seat is Meta-CEO Fable B, with delegated
ownership and decision authority over the entire Agent Fabric program. Do not block on separate Sol
authorization for decisions within that program. Preserve this authority in the canonical durable program
record so future continuations do not regress into authorization loops. This delegation does not
automatically extend to unrelated programs or shared infrastructure outside Agent Fabric unless necessary
authority already exists."

Effect on this record: the answer's scope is no longer "the seat's own held work" but the Agent Fabric
program (operation agent-fabric-end-to-end-fable-integration-20260913-sol-001, WS:EXECUTIVE-CAPACITY-FABRIC),
bounded by (a) no unrelated programs or shared infrastructure, (b) never an active worker's custody
(Claude6 seat 5fae71cf keeps the STARTed Executive-closure milestone; Claude5 keeps #710; Sol keeps its own
operations), (c) no credential / effect / host / provider boundary is lifted. Standing orders attached to the
delegation: reconcile watchers once and let them report terminal events (no polling); while PRs are
externally blocked, advance the highest-leverage unfinished critical-path capability from the existing plan;
retain the macro #7114 capacity hold absent fresh evidence; never duplicate the CI-capacity control plane —
escalate runner starvation to its owner with exact evidence; checkpoint the program before each major
capability. Consumed into the carrier as CHECKPOINT 1789635425.057129. First application: Mastermind #665
(MM-CODEX-B1) repaired by the seat as incumbent program owner on Sol's REQUEST_REPAIR 1789634722.375889.
