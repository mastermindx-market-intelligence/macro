# Orchestration — depth for O.1–O.17

Read this when you are about to plan a program, split it into lanes, commission anyone, wait on a lane, judge a return, or integrate a wave. The core (`../SKILL.md` §4) states each rule in five lines; this file explains why each rule exists, how to execute it, and what it looks like when it fails. Templates for every artifact named here are in `packets.md`.

Contents: 1 Decomposition (O.1–O.2) · 2 Freezing and sizing (O.3–O.4) · 3 Routing (O.5) · 4 Commissioning (O.6) · 5 Gates and isolation (O.7–O.8) · 6 Waiting (O.9) · 7 Judging returns (O.10–O.12) · 8 Integration (O.13–O.14) · 9 Pre-mortem (O.15) · 10 Collisions (O.16–O.17) · 11 A worked program plan

---

## 1. Decomposition — O.1 ownership, O.2 critical path

**Why ownership, not topic.** A program's lanes will be built in parallel by workers who cannot see each other. The only thing that keeps their results composable is that no two of them write the same artifact. A split by topic ("data lane / API lane / UI lane") reads naturally in a plan and then produces three diffs that all touch the shared schema file, the shared fixture, and the shared config — and the seat spends the wave resolving conflicts it created. A split by ownership starts from the artifact inventory and asks, for each file, which lane owns it; the lanes are whatever partition of the inventory has no shared members.

**Procedure.**
1. Inventory the artifacts the program will touch (files, tables, configs, records, external registrations). A census lane can produce this; the seat partitions it.
2. Assign each artifact to exactly one lane. Where two lanes need the same artifact: (a) merge the lanes if the shared piece is most of both; (b) serialize them if one is clearly upstream; (c) hoist the shared piece into a preceding lane whose only job is to land the contract both will consume.
3. Write each lane's contract at its boundary: the interface it exposes, the interface it consumes, and the version of each it was frozen against.
4. Test the partition: could every lane's PR merge in any order without a conflict? If not, return to step 2.

**Critical path.** Draw the dependency graph of lanes (a lane depends on another when it consumes an artifact the other owns). The longest dependent chain is the program's wall-clock; no amount of parallelism elsewhere shortens it. Start the head of that chain first, and inside it, start the *fork-resolving* lane — the one whose result could invalidate the rest of the plan (a feasibility probe, a contract the whole program consumes, a data check that decides whether the program is even needed). A plan whose step 1 is the easiest lane has chosen by salience; a plan whose step 1 is the fork has chosen by information.

**Failure signature.** Wave 1 returns and the seat spends a day merging; or wave 3 discovers the premise wave 1 could have tested in an hour.

## 2. Freezing and sizing — O.3, O.4

**What "frozen" means.** A spec is frozen when a competent stranger could implement it without making a design decision: the interface (names, types, nullability, units, ordering) is written down; the acceptance gates are observable ("the new test fails on the old code and passes on the new"; "the page renders at 375px with no horizontal scroll"); the owned files are listed; the tests are named; out-of-scope is named. If any of those is "the builder will figure it out", the builder will — competently, silently, and in the direction that is easiest to build rather than the direction the program needs.

**Where unfrozen work goes.** Design questions go to the seat or to a design/analysis lane whose *deliverable is the frozen spec*. Only then does a build lane get a packet. Thawing a spec mid-wave (changing an interface after two lanes consumed it) restarts the wave for every consumer; if you must thaw, say so in the ledger and re-issue the consumers' packets, never patch them by message.

**Sizing to one review.** A lane's return must be judgeable in one sitting, from one artifact, by one reviewer. Heuristics: more than about ten numbered spec items, more than about five owned files, more than one subsystem, or more than one kind of deliverable (code *and* a migration *and* a doc) → split. Oversized packets do not fail loudly; they return the clean half — every item the worker got to, done well, and the rest silently absent. The seat that counts (S.3) catches it; the seat that reads the confident report does not.

## 3. Routing — O.5 the draft-and-review test

**The test.** For the work in front of you, would a cheap first draft plus a strong review recover the quality of a strong first draft? If yes, the work is draft-shaped: route it to the cheapest tier that can produce a reviewable draft, and spend the strong tier on the review. If no — because the draft's *choices* are the deliverable (a spec freeze, a ruling between conflicting findings, a design's palette and composition, the synthesis that steers the next wave) — the work is judgment-shaped and goes to the judgment tier, or stays in the seat.

**What does not promote tier.** Importance. A critical migration is still mechanical if its spec is frozen; a trivial-looking taste call is still judgment. Urgency does not promote tier either — it changes who is *available*, not what the work is.

**Tiers, generically.** Judgment (seat / frontier child, rare and short) · review and hard analysis (strong reviewer) · build and census (capable, cheap, plentiful) · extraction and formatting (cheapest). In this fleet the registry maps semantic routes to pinned agents and models; in another harness the mapping is yours to declare — but declare it in every commission. A child that inherits the seat's model is a silent tier promotion and, at scale, the single largest avoidable cost.

**Fan-out arithmetic.** Before launching N lanes at a tier, multiply: N × (turns per lane) × (context per turn). A frontier child in a wait loop is the worst product in the table — many turns, no judgment.

## 4. Commissioning — O.6 the commission is the only channel

The delegate's context contains exactly what the packet contains plus whatever the target repository's agent file says. Nothing else travels: not your session's context, not the discussion above, not the screenshot you looked at, not the doc you meant to attach. Everything the worker needs to *decide correctly* must be in the packet, and everything it needs to *know it is done* must be in the packet's `NOT DONE UNLESS`.

**Inline, never by pointer.** Acceptance gates as sentences the worker can check; inputs as exact paths or pasted content; reference images as committed files with paths; the interface the lane consumes, pasted. "See the masterplan" arrives as nothing.

**The turn-ending contract, in the original packet.** Workers stop on status notes ("now let me read those sections…") because they believe an incomplete answer is worse than none. Remove that belief in the packet: *"Do not end a turn until you are emitting the return packet. If you catch yourself writing 'now let me…' or 'next I'll…', either keep going in the same turn or stop and return what you have. A partial packet with honest, specific GAPS is useful and I can act on it; another status note is not."* Naming the self-observable trigger phrase is the load-bearing part. Putting it in the nudge instead of the packet is paying full price to say it late.

**Front-load the gating question.** If one answer decides your next act, put it first: "Answer this first, because it decides the verdict." A worker that stalls on its second turn has then already delivered the thing you needed.

**Audit the target's agent file before spawning.** A worker in another repository inherits that repository's laws, not this one's. If those laws carry no verification or design standard, fix that first; a packet cannot compensate for a missing floor.

## 5. Gates and isolation — O.7, O.8

**Gate multiplication.** A gate reads as per-lane and executes as fleet-wide load: "run the baseline suite, then run it again after your change" handed to six builders is twelve concurrent suite runs competing for the same cores, every lane's wall-clock inflated, every transcript silent for minutes — which looks exactly like six stalled agents and invites a kill-and-restart that pays for everything twice. Measure the baseline once, yourself, before fanning out; hand it down as a constant; give each lane the narrowest gate that still sees its own regression (its touched test files and its subsystem's suite, after-run only); run the full suite once, at integration, where contention is zero.

**Isolation.** One worktree per parallel lane, one writer per branch, never the primary checkout. A lane that "reuses" a worktree keeps the previous round's checkout and may truthfully report absence from a tree that never fetched the new head — while quoting the new head from the remote. Fresh tree per round, or an explicit fetch-and-checkout step whose success the packet must prove.

## 6. Waiting — O.9

**Key on the artifact, bound the wait, hand it off.** Wait for the thing you actually need — a sentinel line, a record file, a PR state — not for a process id; bound every wait with a budget; and give the wait to something that costs no model turns (a shell loop with a timeout, a cron, a sweeper, a harness watcher). The seat is re-invoked by the watcher's exit or the notification; between those, the seat does other lanes' work or ends its turn.

**Classify before acting** (S.2): RUNNING (alive, within budget) → nothing. DELIVERED → judge. SILENT (alive, past budget, no packet, no new output) → check process state before diagnosing: a lane under a long mandated command shows exactly the signature of a stall, and a slow lane is not a thrashing one. DEAD (process gone, no packet) → read its last output; relaunch only with a changed input or a named reason the outcome will differ (§6.1). THRASHING (alive, repeating the same actions — hundreds of identical exec lines — with its record untouched across two cycles) → report it with evidence and stop it through the sanctioned path; never kill by pattern.

## 7. Judging returns — O.10, O.11, O.12

**Open the artifact.** The report says what the worker believes; the artifact says what happened. Open the diff, read the test output, view the image at realistic density (one glowing card is a highlight, twelve is a wall), print the number the lane is about to have you repeat.

**Count.** Tests added versus tests named; items implemented versus items specified; files created versus files listed. `git diff <base> -- tests/ | grep -c '^+def test_'` is a one-line count that has caught a ten-of-ten-items, one-of-eleven-tests return whose every other signal said done.

**The two lens checks** for any "none found" / "all clean": (1) what was the worker *instructed* to look for — a finder shaped for bugs returns bugs; one scoped to a directory found nothing *in that directory*; (2) what bounds did its searches actually cover — patterns, directories, alternative surfaces (§3.5 applies to its greps exactly as to yours).

**Notifications and nudges.** A "completed" notification is at most DELIVERED and often less: read the actual artifact and current attempt state. If a packet is missing, send at most one lawful same-carrier request for it; do not duplicate the live assignment. Parallel principal probes must be read-only, independently useful and disjoint from the worker's assigned outcome and any uncertain effect. Silence never releases a writer. Taking over the bounded remainder requires L.7 and canonical effect/custody reconciliation first; a missing final message does not authorize a replacement worker, repeated request, or concurrent repair.

**Repair rounds.** `REQUEST_REPAIR` carries a numbered defect list and, per defect, the exact re-check that closes it. Number the rounds. Two rounds without observable delta ban a third identical one: change the tier, split the packet, change the owner, or take the bounded remainder yourself under L.7.

**Late reviews.** Silence from a commissioned reviewer is absence of evidence. Before accepting or arming anything, ask whether every sub-review CONCLUDED; a task that never reported is open, and resuming it is one message. When a late finding lands after you approved, sweep every surface where the refuted claim was repeated — comments, records, the program file, memory — in the same cycle as the amendment, because approval texts propagate and a receipt's flaw copied into a ruling survives the receipt being fixed.

## 8. Integration — O.13, O.14

**Fresh base, dependency order.** Re-fetch before every push, merge, or composition check. Compare a branch against `merge-base(base, head)`, never against a moving base — a path that differs from newer base but is untouched between merge-base and head is "not yet merged", not a ghost edit. Merge in dependency order (the lane whose contract others consume lands first). A conflict on a fix usually means the fix already landed behind you: diff against fresh base; if empty, close, do not force — forcing reverts the better version that arrived while you worked.

**The wave's exit gate is written first.** Before a wave launches: what merged, what proven live, what accepted, by what evidence, by when. A wave whose gate is written after it lands is graded on what happened to land. "Returned" is not a rung; "merged" is not "live"; "live" is not "accepted by the commissioning authority" — the ladder in `long-horizon.md` section 2 defines each with its evidence.

## 9. Pre-mortem — O.15

Before each wave, write: "It is one week later and this wave failed. Why?" and list four to six concrete mechanisms — a contract two lanes read differently; a base that moved under the wave; a gate that multiplied; a reviewer that never returned; a data dependency that was stale when the wave started; a permission the seat assumed it had. For each, write the tripwire: a clause in a packet, a watcher, a check at integration. The mechanisms that appear only in the pre-mortem were invisible to the plan; that is the point of writing it.

## 10. Collisions — O.16 contested artifacts, O.17 once-per-operation acts

**Contested artifact.** Two writers on one file, branch, PR, carrier, or seat → freeze that artifact, name one owner in the ledger and on the carrier, and never add a second worker to "help". The second worker is not help; it is a second uncoordinated writer. This includes another session of *your own* seat: two placements minutes apart produce two live worktrees and two ACKs from one identity, and the carrier cannot tell which is real. ACK precedence decides the incumbent; the later session withdraws.

**Once-per-operation acts.** ACK, START, a shared-contract registration, a claim, a watcher arm: each exists once per operation. Before performing one, search the operation key across the carrier and the durable store. A duplicate is two contradictory facts, and everything downstream (watchers, owners, rulings) forks on it.

## 11. A worked program plan

Program: "ship the sector-intelligence dossier: producer, schema, two consumers, live page." Inventory: `engine/sector/producer.py`, `schemas/dossier.v1.json`, `engine/consumers/{a,b}.py`, `templates/sector.html.j2`, `tests/test_sector_*.py`, one external registration.

Ownership partition: L0 schema+registration (contract lane, hoisted because three lanes consume it) · L1 producer · L2 consumer A · L3 consumer B · L4 page. Dependency graph: L0 → {L1, L2, L3} → L4 (page consumes L1's artifact and renders L2/L3's fields). Critical path: L0 → L1 → L4. Fork: does the upstream feed carry the field the whole dossier is built on? — a one-hour census lane before L0, because "no" cancels the program.

Waves: W0 = fork census + L0 (frozen contract merged). W1 = L1 ∥ L2 ∥ L3, each with the narrow gate (`-k sector_<lane>`, after-run only; baseline count handed down). W2 = L4 against merged W1, full suite once at integration, live verification. Pre-mortem tripwires: schema version pinned in every W1 packet; a composition check against merge-base at W2; a watcher on the review lane so silence is noticed at the wave gate, not after.
