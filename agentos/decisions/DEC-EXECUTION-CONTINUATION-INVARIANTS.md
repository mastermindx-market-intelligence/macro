---
key: EXECUTION-CONTINUATION-INVARIANTS
question: >
  Fleet law enforced the SHIP CHAIN of a session that produced a commit and said nothing
  about the family of failures that ends missions before that chain is reached: one
  blocked lane ending a whole mission, a checkpoint or status note reported as the
  outcome it only describes, principal capacity spent re-polling a queue a watcher
  already owns, a delegation surface being unavailable read as "execution is
  impossible", accepted work redone with no material invalidator, an explicit Chairman
  program delegation overridden by default role assumptions, the delivery rungs
  conflated, and sessions stopping while authorized work remained. Where is the
  canonical owner of that law, and how much of it may be machine-enforced without
  turning the Stop hook into a second control plane?
answer: >
  The canonical owner is the existing Macro fleet-law pair, CLAUDE.md and AGENTS.md,
  mirrored onto the Cursor rule surface and recorded here; the enforcement owner is the
  existing Stop authority, .claude/hooks/ship_loop_guard.py. No new instruction plane,
  control plane, lifecycle store, queue, watcher or memory system is created, and the
  Mastermind authority map is restated rather than copied.
  Three things became law. (1) The authority model keeps its defaults - Chairman final,
  Sol the default AI CEO / system owner, ordinary Claude and Codex sessions bounded
  workers, Fable scarce principal capacity - and gains the scope rule they lacked: an
  explicit Chairman delegation overrides those defaults inside its stated scope, a
  default role assumption never overrides it back, and delegated authority never leaks
  outside its stated scope. (2) Six execution invariants bind every session: freeze the
  blocked lane and continue independent lanes; direct bounded execution may continue
  when no worker started and lawful principal tools/custody, no conflicting owner and no
  EFFECT_UNKNOWN hold; hand an external wait to a durable watcher and never burn
  principal capacity polling; two equivalent no-delta cycles force a change of tactic,
  lane or owner; accepted work is DO_NOT_REDO unless materially invalidated; and
  EFFECT_UNKNOWN reconciles on the same carrier, never by blind retry or failover.
  (3) ACK, QUEUED, START, RUNNING, DELIVERED, CI, MERGED, PRODUCTION_PROOF and
  ACCEPTANCE are nine distinct facts and none implies the next; a substantial session
  ends by classifying itself into the closed set PROVEN_OUTCOME, EXACT_HUMAN_GATE,
  EFFECT_UNKNOWN, ALL_SCOPED_LANES_BLOCKED, DURABLE_EXECUTION_RUNNING, MORE_WORK_EXISTS,
  and MORE_WORK_EXISTS is never a valid stopping state.
  The hook enforces exactly the part it can observe without inference: it refuses a
  self-declared MORE_WORK_EXISTS end state, and it composes each block's continuation
  directive from its own ledger instead of repeating one unchanging sentence. Everything
  that would require inferring lanes, custody, delegation scope or carrier state stays
  law and is pinned by cross-surface parity tests.
rationale: >
  The gap was structural, not a wording slip. ship_loop_guard._stop returns with zero
  enforcement when HEAD still equals the session's start_head, so every failure in this
  family - a session that delegated and got nothing back, wrote a checkpoint, rotated
  context, or declared victory on an upstream acknowledgement - escaped before the first
  gate. Adding a general gate there was rejected outright: a blanket block on a
  commitless Stop would trap every question-answering session in the fleet, and this
  repository's scar record is explicit that a tightened Stop gate without a reachable
  remedy is how "the remedy caused the block" (the .codex-worktrees exclude incident, the
  121 consecutive blocks on PR #6608, the 258x unmerged loop).
  So the enforcement is deliberately asymmetric. The single refusal is keyed to a token
  the session writes about itself, which makes a false positive unreachable by
  construction and keeps the ordinary any-code ladder (10 consecutive / 15 total) as the
  guaranteed exit. The larger lever is the block TEXT. gh_quota_guard.py shape 7 already
  documents, with the operator's own measurement of ~25 consecutive Stop cycles of single
  CI polls by a session that already had a watcher armed, that the identical closing
  sentence on every block is what teaches sessions to answer a wait with one more poll.
  An instruction that never changes invites a response that never changes. Composing the
  directive from the consecutive-block count the guard already keeps costs no request,
  cannot be wrong about a fact it did not measure, and makes the second identical block
  read as the no-delta cycle it is.
  Placement follows the same logic as DEC:HOLD-PARKS-SHIP-NOT-DIALOGUE. That repair
  corrected the ADVICE of a lawful state without widening permission, and pinned the
  correction with a six-file source-law parity test precisely because the same rule lives
  on several surfaces and a future edit to one silently reopens the conflation in
  another. This record reuses that mechanism rather than inventing a second one.
alternatives:
  - option: Put the law in CLAUDE.md alone
    why_not: Codex, Cursor, Grok and Warp sessions never read CLAUDE.md; the repository already requires durable operating rules in both CLAUDE.md and AGENTS.md, and the Cursor surface was the one that silently kept an obsolete rule the last time only five of six surfaces were corrected
  - option: Block every commitless Stop until the session proves no work remains
    why_not: unsatisfiable by construction for ordinary question-answering sessions and for any session whose remaining work is genuinely external; the repository's own incident record shows that an unreachable remedy produces hundreds of blocks and teaches sessions to distrust the guard
  - option: Have the Stop hook infer lanes, custody, delegation scope and carrier state
    why_not: that is a control plane, which repository law forbids the knowledge and hook layers from becoming; the hook cannot see a carrier and would have to fabricate state, and a false ALL_SCOPED_LANES_BLOCKED is worse than no claim
  - option: Add a continuation/lifecycle store so session state is durable and machine-checked
    why_not: explicitly out of scope - it duplicates the Executive OS lifecycle authority, and the obligation is enforceable as law plus one self-declared token without a new plane
  - option: Widen the delivery-claim detector to ACK and CI as well
    why_not: both occur constantly in ordinary prose about acknowledgements and check runs; the detector only ever appends an advisory line, so a false claim is cheap rather than free, and the ambiguous tokens stay out
  - option: Escalate the no-delta-cycle directive from advice to a deny
    why_not: the same ruling boundary gh_quota_guard.py shape 7 already records - the guard governs HOW a session works, never WHETHER it may read its own pull request; escalating is a ruling for the Chairman, not a refactor
evidence:
  - ".claude/hooks/ship_loop_guard.py _stop(): `if head == state.get(\"start_head\"): return` - the commitless early return through which this whole failure family escaped"
  - ".claude/hooks/ship_loop_guard.py _block(): pre-repair body was a fixed two-line string, identical on block 1 and block 25"
  - ".claude/hooks/gh_quota_guard.py shape 7 docstring: ~25 consecutive Stop cycles of single `gh pr checks` polls by a session that already had a watcher armed at 150s; operator order repeated 2026-08-24 and 2026-08-27"
  - "scripts/ship_loop_hold_wrapper.py _hold_block(): 121 consecutive blocks on PR #6608 from a correct-shaped block carrying unfollowable advice"
  - "tests/test_ship_loop_hold_wrapper.py PARITY_FILES/PARITY_TOKENS: the six-surface source-law parity mechanism this record reuses"
  - "grep over the repository on 2026-09-17: MORE_WORK_EXISTS, PROVEN_OUTCOME, EXACT_HUMAN_GATE, ALL_SCOPED_LANES_BLOCKED and DURABLE_EXECUTION_RUNNING appeared nowhere; EFFECT_UNKNOWN existed only in research and two decision records"
  - "tests/test_execution_continuation_law.py: ten scenario cases, each named for the observed failure it would catch"
  - "python3 -m pytest tests/test_ship_loop_guard.py: 253 passed, 1 skipped after the change"
affects:
  - CLAUDE.md
  - AGENTS.md
  - .cursor/rules/execution-continuation.mdc
  - .claude/hooks/ship_loop_guard.py
  - tests/test_execution_continuation_law.py
  - "DEC:SOL-HOLD-IS-A-MERGE-BARRIER"
  - "DEC:HOLD-PARKS-SHIP-NOT-DIALOGUE"
  - "DEC:SESSION-LENGTH-IS-NOT-A-COST-CONTROL"
  - "DEC:AGENT-ROUTING-CONTROL"
confidence: high
reversibility: easy
decided_by: chairman
decided_at: 2026-09-17
---

## Provenance

The Chairman's 2026-09-17 direct handoff named the eight recurring failures, stated the
six execution invariants and the six-member session-end classification verbatim, and
fixed the non-goals. Those are the Chairman's ruling and are recorded as such. What this
session decided is placement and enforcement depth: which surface owns the law, how much
of it a hook may enforce without becoming a control plane, and where the refusal line
falls.

## The binding clauses, verbatim

This law does not weaken the ordinary ship chain: both bind, and neither releases the
other. A blocked lane is a reason to keep working other lanes, never a reason to leave
an unmerged pull request; `merge-on-green`, `PARKED / HOLD-FOR-SOL`, the escape
ladders and the model-routing law are all untouched.

These are the exact sentences the law surfaces carry, and
`tests/test_execution_continuation_law.py` pins each of them on every surface. A
paraphrase on one surface and not another is how a fleet ends up with two rules.

- `BLOCKER -> freeze the affected lane -> check independent useful lanes -> continue`
- `NO WORKER STARTED + lawful principal tools/custody + no conflict/EFFECT_UNKNOWN -> direct bounded execution may continue`
- `WAITING EXTERNAL -> durable watcher/owner; do useful parallel principal work; do not burn principal capacity polling`
- `2 equivalent no-delta cycles -> change tactic/lane/owner`
- `accepted work -> DO_NOT_REDO unless materially invalidated`
- `EFFECT_UNKNOWN -> same-carrier reconciliation; never blind retry/failover`

The authority model each surface restates, and none of them owns: Chairman Chris is
final authority, **Sol is the default AI CEO / system owner**, ordinary Claude and Codex
sessions remain **bounded workers**, and **Fable is scarce principal capacity by
default**. The governing **authority map** stays in Mastermind. **An explicit Chairman
delegation overrides those defaults inside its stated scope, and a default role
assumption never overrides it back**, and delegated authority **never leaks outside its
stated scope**.

The clauses that carry each invariant's second half — the half that usually goes missing
when a rule is paraphrased:

- `ALL_SCOPED_LANES_BLOCKED` is honest only when every scoped lane is blocked, and that
  classification **must name the lanes it checked**.
- A delegation surface being unavailable **is not evidence that execution is
  impossible**: direct bounded execution continues when **no worker actually started**,
  the principal still holds **lawful tools and custody**, **no other owner is working
  the same artifact**, and no act sits in an `EFFECT_UNKNOWN` state.
- When any of those four is false the outcome is `ALL_SCOPED_LANES_BLOCKED` or
  `EXACT_HUMAN_GATE` **naming the exact missing thing** — **never a silent stop**, and
  never a **second worker on a contested artifact**.
- A Stop-hook block during a wait is **satisfied by a one-line hold note, never by a
  fresh poll**.
- The **material invalidator** is new contradicting evidence, a changed contract, or an
  explicit authority reversal; a fresh session, a **lost transcript**, and an **absent
  memory** are none of those. Check the `agentos/` `do_not_redo` entries and
  `research/DO_NOT_REBUILD.md` first.
- An act whose effect cannot be observed is reconciled on the **same carrier that
  performed it**.

`ACK -> QUEUED -> START -> RUNNING -> DELIVERED -> CI -> MERGED -> PRODUCTION_PROOF ->
ACCEPTANCE` are nine distinct facts and none implies the next. A checkpoint, a status
note, or a continuation record describes work and is **never the outcome it describes**.
Context compaction or rotation **is a harness event** and **not an outcome**, which is
why the guard's block ledger deliberately survives `resume` and `compact`.

Reaching the actual outcome or the exact human gate early is a complete session however
short it was: **never pad a session to look substantial, and never stop while authorized
work remains**.

## What is enforced, and what is only law

Enforced by `.claude/hooks/ship_loop_guard.py`, from facts the guard already holds:

- a self-declared `SESSION END: MORE_WORK_EXISTS` is refused (`more_work_exists`);
- every block's continuation directive is composed from the consecutive-block count:
  the lane rule always, the wait rule for blocks owned by outside machinery, the
  no-delta-cycle rule from the second identical block, and a delivery-conflation line
  when the final message claims a rung above what the block proves.

Law only, pinned by cross-surface parity rather than by a probe: lane enumeration,
custody and conflict checks, delegation scope, `DO_NOT_REDO`, and same-carrier
reconciliation. The hook cannot observe any of them and must not guess.

## What this record does not do

It creates no strategic state, authority map, control plane, lifecycle store, queue,
watcher or memory system, and it duplicates nothing from Mastermind. This law
promotes no worker to principal, widens no credential, and changes no provider
permission; it changes no product or trading architecture. `merge-on-green`, the ship chain, `PARKED / HOLD-FOR-SOL`, the
escape ladders and the model-routing law are all untouched.

## What would reopen this

Evidence that the `more_work_exists` refusal fires on a session that had genuinely
finished — which would mean the declaration is being written by something other than the
session's own judgement — or evidence that the composed directive changes nothing
measurable about polling volume and no-delta retries, in which case escalating the
no-delta clause from advice to a deny becomes a ruling to put to the Chairman.
