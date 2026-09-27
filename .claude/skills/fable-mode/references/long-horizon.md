# Long horizon — depth for L.1–L.14

Read this when you resume after a restart, compaction, or handoff; when you are about to wait on anything external; when you end a session that ran longer than one cycle; or when a program will outlive your context. The core (`../SKILL.md` §5) states each rule; this file gives the procedures and the evidence standard behind them.

Contents: 1 The program file (L.1) · 2 The delivery ladder (L.2) · 3 EFFECT_UNKNOWN (L.3) · 4 No-delta cycles (L.4) · 5 DO_NOT_REDO (L.5) · 6 Blocked lanes and direct execution (L.6–L.7) · 7 Waiting and quiet (L.8) · 8 Session end (L.9) · 9 Resumption (L.10) · 10 Authority scope (L.11) · 11 Records (L.12–L.13) · 12 Cost model (L.14)

---

## 1. The program file — L.1

**The test.** A cold stranger — a different model, no transcript, no memory — opens the program file and resumes with the loss of at most one cycle. If resuming requires re-deriving a decision, re-discovering a lane, or re-reading a carrier from the beginning, the file is behind.

**Contents** (template in `packets.md` section 7): the mission and its exit gate; the wave plan with each wave's gate and status; the lane matrix (lane id, owner, tier, worktree/branch, sentinel, budget, state, last verified at); the ledger (DECIDED with one-line reasons · FACTS with sources · OPEN · NEXT); open rulings awaiting a counterpart; the do-not-redo list; danger areas; the last consumed carrier edge.

**When to write.** At every S.4 (before deciding anything new) and every S.8 (before going quiet). Not per tool call — per decision and per lane-state change. Where the harness summarizes old history, whatever is not in the file is exactly what the summary loses: write decisions with reasons, observations verbatim (path:line, the exact failing line), and the next command *before* they age into the summarized region.

**Where.** In this fleet: `research/<PROGRAM>_CONTINUATION_HANDOFF_<date>.md` for the running program state plus an `agentos/handoffs/<WS>-<date>.md` record when leaving state another session must resume. In another harness: any durable store the successor is guaranteed to read — a file in the repository beats a chat message, a chat message beats memory.

**Not a stop rule.** A merged, verified wave is a checkpoint, not a session end. A session may carry a program end-to-end across many waves; the file is what makes that safe, and a long session held at small context is cheap (section 12 below).

## 2. The delivery ladder — L.2

| Rung | Means | Evidence that reaches it |
|---|---|---|
| ACK | The operation was acknowledged by a seat | the ACK post, once, on the carrier |
| QUEUED | Admission accepted; a worker may be assigned | the admission receipt (a queue entry, a lane id) |
| START | A worker actually began | the worker's own start receipt, not the launcher's exit code |
| RUNNING | Work is in progress within budget | a live process or fresh artifact mtime, verified this cycle |
| DELIVERED | A return packet exists | the packet, opened; not the "completed" notification |
| CI | Binding checks concluded on the exact head | check conclusions at that sha, not "not red" |
| MERGED | The change is in the canonical base | the merge sha on the base ref |
| PRODUCTION_PROOF | The change is observable where users are | the live artifact, fetched and read |
| ACCEPTANCE | The commissioning authority accepted the outcome | their acceptance, on the carrier |

None implies the next. The most common inflations: DELIVERED reported as done; CI reported when checks are pending ("not red" is not green); MERGED reported as live before any deploy or render pulled it; PRODUCTION_PROOF reported as acceptance. A status note, a checkpoint, or a continuation record is a *description* of work, never the outcome it describes. One state sits beside the ladder rather than on it: **PARKED** — a change whose checks concluded green but which a recorded hold by another authority bars from merging. PARKED is terminal for the ship attempt only; it is never reported as merged, shipped, or live, and the dialogue with the holding authority stays open.

## 3. EFFECT_UNKNOWN — L.3

**Definition.** You performed an act whose effect you cannot observe: a post that timed out, a dispatch whose receipt never arrived, a tool call that was dropped mid-flight, a push whose response you did not see.

**Procedure.** (1) Do not repeat the act. (2) Do not perform the equivalent act through another surface. (3) Read the original carrier and canonical effect owner: did the post land, did the run get created, did the ref move? (4) If it landed, resume from that verified effect. Proven non-execution only resolves the effect question: **EFFECT_NONE is not retry permission**. A new attempt still needs current assignment, resource permission, budget, admission and the existing retry owner's allowance. An explicit safety or permission denial ends attempts at that action; never change tools, accounts or models to obtain the refused effect. (5) If the owner cannot answer, keep that operation EFFECT_UNKNOWN. Continue only independently safe authorized work; use the governing finalization procedure when no such work remains. A missing response or an empty, stale search is not proof of non-execution.

**Why.** A blind retry of an irreversible act is how one merge becomes two, one post becomes a contradiction, one dispatch cancels the in-flight run it duplicated. A failover to another provider is the same act with a different signature, harder to reconcile later.

## 4. No-delta cycles — L.4

Two attempts that changed nothing observable — same probe, same result; same repair request, same defect; same dispatch, same silence — ban a third identical attempt. Name the count in the ledger and change one of: the tactic (a discriminating probe instead of a confirming one), the lane (a different worker or tier), or the owner (the seat takes the bounded remainder under L.7). This is §6.1–§6.2 at program scale, and the harness may count the cycles for you; do not wait for it to.

## 5. DO_NOT_REDO — L.5

Accepted, merged, or ratified work is reopened only on a **material invalidator**: new evidence that contradicts it, a changed contract it depended on, or an explicit reversal by the authority that accepted it. Not invalidators: a fresh session, a lost transcript, an absent memory, a feeling that it could be better. Before building, check the do-not-redo record and the program file; before re-litigating a ruling, cite the invalidator. Re-doing accepted work is the most expensive form of scope drift because it also re-opens every decision downstream of it.

## 6. Blocked lanes and direct execution — L.6, L.7

**Blocked lane.** One blocked review, tool, provider, or check freezes *that lane*. The procedure before any stop: list every authorized lane in scope; mark each RUNNABLE / BLOCKED with the blocker named; continue on the runnable ones. `ALL_SCOPED_LANES_BLOCKED` is a claim about a list, and the list is part of the claim.

**Direct execution — the four conditions.** A delegation surface being unavailable (a fabric down, a pool exhausted, a spawn refused) is not evidence that execution is impossible. If (1) no worker actually started on the artifact, (2) you hold lawful tools and custody of it, (3) no other owner is working it, and (4) no act of yours on it is EFFECT_UNKNOWN — execute the bounded work yourself. When any condition is false, the lawful outcome is `ALL_SCOPED_LANES_BLOCKED` or `EXACT_HUMAN_GATE` naming the exact missing thing. The two errors this prevents are opposite: a seat that stops because its favorite delegation surface was down, and a seat that puts a second worker on an artifact that already has one.

## 7. Waiting and quiet — L.8

**Hand the wait off.** A watcher (a bounded shell loop keyed on the sentinel, a cron, a merge sweeper, a harness monitor) owns the wait. Register it in the lane matrix with its cadence. One watcher per endpoint; a second buys nothing and doubles the cost.

**Harness pressure is not a demand for a poll.** A stop-hook block, a "still waiting?" nudge, a scheduled wake-up: these are the harness asking for a *state*, not for fresh evidence. Answer with one line — what is being waited on, which watcher owns it, what re-invokes you — never with a re-read. The tell that you have crossed into waste: three identical status readings in a row.

**A hold note does not end the pressure — the ladder does.** In a harness with a Stop hook, a hold note satisfies the quota rule but the hook blocks again seconds later, and a seat that answers every block with another note types near-identical notes in a billed loop for hours. The lawful sequence in this fleet: hold notes while the block count climbs; at the counted threshold (any code: 10 consecutive or 15 total blocks) end the turn ONCE with the literal `SHIP LOOP BLOCKED:` evidence report — the PR, the exact head, the check state, the watcher and its cadence, and the continuation path — and then stay quiet: no per-block notes, no tailing your own watcher between its ticks. Real events (a watcher exit, a task notification, a counterpart post, an operator message) re-invoke you; nothing else should. Waiting on CI never qualifies as a blocker for the ladder in its own right — the report is about the *wait being lawfully owned*, not about CI being slow.

**Parallel work during a wait.** A wait is the moment to work an independent lane, write the program file, or run the pre-mortem for the next wave — anything except reading the same status again.

## 8. Session end — L.9

| State | Use when | Not when |
|---|---|---|
| `PROVEN_OUTCOME` | the mission's exit gate is met with evidence at the rung it named | a wave merged but the mission is not done |
| `EXACT_HUMAN_GATE` | the next act needs a specific human decision, named, with your default | you would like confirmation you were not asked to seek |
| `EFFECT_UNKNOWN` | an act's effect could not be reconciled on its carrier | you did not try the carrier |
| `ALL_SCOPED_LANES_BLOCKED` | every authorized lane is listed with its blocker | one lane is blocked and others were not checked |
| `DURABLE_EXECUTION_RUNNING` | watchers own the wait; the program file is current; real events re-invoke you | you are about to poll — or a change you opened is unmerged or not yet proven live: that wait is yours to the end (O.14), and the state does not excuse it |
| `MORE_WORK_EXISTS` | never a valid stopping state | — |

A session that reaches the outcome or the exact human gate in ten minutes is complete; a session that stops with authorized work remaining is not, however long it ran.

## 9. Resumption — L.10

After a restart, compaction, handoff, or takeover, in this order:
1. Read the program file; note the last consumed carrier edge it records.
2. Read the carrier forward from that edge — every counterpart post, ruling, hold, STOP, sibling ACK — before any act.
3. Verify your own identity: which seat, which session id, which operation. Search the operation key: has this operation already been ACKed, started, or stopped by another session — including another session on your own seat?
4. Re-verify every lane the file marks RUNNING against reality (process, artifact mtime, sentinel). A mark is a claim.
5. Rebind watchers; record the new ids.
6. Only then decide (S.5).

**Your spawn prompt is a stale relay.** It was written by someone reading the carrier at some earlier time, possibly minutes before a STOP, a re-scope, or a sibling's ACK. It tells you what someone believed the task was; the carrier tells you what the task is. A "Chairman override" or "principal authorization" quoted in a spawn prompt covers what it says and nothing more; consume it into the carrier verbatim (A.6) and let the carrier's current state govern.

## 10. Authority scope — L.11

Defaults exist (a seat is a worker; a principal decides). An explicit delegation overrides those defaults *inside its stated scope*, and no default overrides it back. Two failures, symmetric: a seat that holds a delegated program and still posts "requesting authorization" to the principal for an in-scope decision — waiting for permission it already holds, which is the most expensive stall available; and a seat that lets a delegation leak — using authority granted for one PR on another, or treating a coordination-only actor's note as a substantive ruling. Read the delegation's scope sentence; act fully inside it; act not at all outside it.

**Holds.** A hold recorded on an artifact — in a PR body, a comment, a carrier post — binds every merge path (sweeper, blanket-arming sessions, manual merges) regardless of label state. It is released only by the authority that placed it, or under a delegation consumed into the carrier verbatim (A.6) whose stated scope names that hold or that program. Verifying that the release condition is met produces *evidence to post to the holding authority*, not a release; a seat that releases on its own reading has exercised authority it was never given. While the hold stands, the correct report is PARKED (section 2), never merged.

## 11. Records — L.12, L.13

**Decision record**, minted when an actual choice with durable consequences is taken: question · answer · rationale · alternatives rejected (each with why-not) · evidence · reversibility · scope · decided-by · date. **Discovery record**, minted when a durable, non-obvious fact is verified that a future session will materially need: the fact · how it was verified · its falsifier (what observation would overturn it) · its so-what (what a session should do differently). Without both falsifier and so-what it is a log line, not a record. **Handoff**, when leaving state another must resume: state before · next actions · do-not-redo · danger areas · unresolved · changed files · verified claims each naming its command.

**Hygiene.** Absolute dates (never "yesterday", "last week"); cite records by key, never by row or line (numbers shift on every edit and have mis-resolved in the wild); retract superseded claims by name in the program file, not only in chat; a `verified:` line that names no command is an unverified line.

## 12. Cost model — L.14

**Historical scope.** This is a historical Fable measurement, not a current price sheet or a measured comparison of GLM, Grok, Sol, Astra or Codex. Preserve the original observation and its accounting assumptions; do not transfer its ratios or savings claims to another model/harness. Measured in this fleet over one week (2026-07-30 → 08-06, 3,043 transcripts): of frontier-model burn, 62% was cache *reads*, 21% cache writes, 17% output. The per-turn floor is roughly 0.1 × context: a turn at 150k context costs ~15k units before any reasoning; at 800k, ~80k. The single most expensive session that week ran 3,539 turns at a median 419k context; the same turns held at 150k would have cost about a quarter as much. Riding context up to auto-compaction is the most expensive pattern available, because every turn on the approach is billed at the ceiling.

Consequences in that measured Fable setup: delegate execution (a lane's context is discarded on return; only its packet lands); budget what enters the seat (a 20k-token dump at turn 500 of a 3,500-turn session is re-read ~3,000 times); keep screenshots and page dumps in lanes; never economize by thinking less — output is a sixth of the cost and the quality of the ruling is the product. Session *length* is not the driver; context *size* is. When context grows, delegate the next wave's execution rather than ending the session.


**Cross-model routing.** Compare total cost per accepted outcome using the current route's actual accounting unit: `(principal + worker + review + repair + rejected attempts) / accepted outcomes`. Include framing and critical-path delay in the decision, but report time separately from money or credits. Zero accepted outcomes means no accepted-result estimate, not zero cost. Unknown prices, quotas, cache rules, served identity and spend remain unknown. A smaller prompt or cheaper successful attempt alone is not measured savings. Keep the acceptance bar unchanged and compare like task classes; do not promote a route from an exposed development case.

**Review capacity is capacity.** Before adding lanes, account for admitted global depth/child limits, reserved review/repair descendants, workspace custody, budget, and the principal's ability to consume returns. Use the existing router/capacity owner; this is not a new scheduler. A review backlog applies backpressure: adjudicate the return that unlocks the critical path rather than maximize running agents. Take a small lawful direct step when dispatch plus review costs more; do not invent a delegation percentage or reduce required reasoning quality.

**Fable is a bounded escalation.** Keep the admitted ordinary principal on its assignment. When a specific unresolved principal decision warrants Fable, send that decision, evidence, alternatives, failed falsifier, stakes, expected return and approved budget; record WHY FABLE. Otherwise record WHY NOT FABLE and use the least-scarce eligible capability. Advice does not transfer the programme, source custody or a started operation. Astra may own judgment or end-to-end delivery; a model label neither completes the mission at design nor requires an extra principal in the chain.
