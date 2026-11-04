# Macro Dashboard — agent instructions

Signal-engine + static-site repo (engines in `engine/`, builders in `scripts/`, rendered site in `site/`, programs/masterplans in `research/`). Nightly pipeline runs on a self-hosted Mac Studio via GitHub Actions; render budget is law (~67 min, 4-core-bound) — heavy compute goes off the render path, artifacts to R2.


Read the linked effect guide before the first relevant action. These are ordinary
repository links, not automatic imports: load the applicable workspace, release,
delegation or domain sections when the task needs them. The relocation does not
weaken any permission, source-custody, review, hold or runtime control. Current
protected Mastermind procedure and actual installed admission remain controlling;
a historical model name, department label or command example is not a new grant.

An architectural owner is not a live session. Data OS is a system boundary, not an
AI approver to locate. The current assigned session resolves authorized technical
contracts through existing interfaces. Preserve actual live writers, rights,
reserved decisions and EFFECT_UNKNOWN; do not invent a registry or an owner.

## Permanent visual rule

Chairman design rule (2026-10-18): never add a colored left edge or equivalent
accent stripe to a container; do not relocate it to another edge. Use neutral
surface hierarchy, even borders, typography and labeled semantic ink. Preserve
complete focus outlines and meaningful chart series. The canonical rule lives in
`docs/DESIGN_DOCTRINE.md`; the shared component specimen must follow it.

## Shared workspace + completion (STANDING)

Read [Shared workspace + completion (STANDING)](docs/agent_guides/CLAUDE_WORKSPACE_COMPLETION.md) before the relevant action.

The canonical source is the exact observed GitHub default revision, not a stale
folder. Use the admitted isolated-workspace route; never modify the occupied
primary checkout, repo-global stash or another session's Git state. The linked
`macro-main` checkout shares `Macro Dashboard/.git`: never delete or move the
object store. Preserve host placement, ownership, lock and unresolved-effect rules.
Read `config/sparse_worktree.json` before materializing omitted generated/data paths;
a missing directory is not proof that the source does not exist. Never stage an
unexpected data/site truncation or run a full-data suite on an unqualified sparse tree.

A recorded HOLD binds every merge path under `DEC:SOL-HOLD-IS-A-MERGE-BARRIER`;
never infer release permission from missing labels. A fully qualified PARKED hold
is terminal for the current ship/merge attempt, not shipped or production-proven.
Its reciprocal dialogue remains nonterminal until an explicit same-carrier Sol STOP
or equivalent terminal edge; a hold never fabricates a watcher or consumed return.
Use the linked procedure for the exact green-check, draft, no-arm and release rules.

Disarming is never silent (#5291): `gh pr edit <n> --remove-label merge-on-green`
requires, in the same act, a visible marker (`merge-blocked` or a comment naming the
session and intent) and responsibility through merged-or-handed-back. Never remove
another session's arm without the applicable custody and continuation evidence.

## Execution continuation law (STANDING — a blocked lane is not a finished mission)

This section governs when a session may STOP; §Shared workspace + completion above governs what the ship chain owes once a session produces a commit. This law does not weaken the ordinary ship chain: both bind, and neither releases the other. A blocked lane is a reason to keep working other lanes, never a reason to leave an unmerged pull request.

- **Authority model — restated, never duplicated.** Chairman Chris is final authority; **Sol is the default AI CEO / system owner**; ordinary Claude and Codex sessions stay **bounded workers**; **Fable is scarce principal capacity by default**. The governing authority map stays in Mastermind (`config/authority_map.yml` + `control_plane/packet_gate.py`) and §Executive OS below still forbids a second copy here — this section creates none and grants no one a new permission. What it adds is the SCOPE rule the defaults were missing: **an explicit Chairman delegation overrides those defaults inside its stated scope, and a default role assumption never overrides it back.** A seat holding a Chairman-delegated program decides in-scope matters itself and does not re-ask Sol for what it was already delegated — the standing example is Meta-CEO Fable B owning the Agent Fabric program, which repeatedly stalled waiting for Sol authorization it did not need. The converse binds equally: **delegated authority never leaks outside its stated scope**, exactly as conditional merge authority granted for one PR never transfers to another (`DEC:SOL-HOLD-IS-A-MERGE-BARRIER`). This law promotes no worker to principal, widens no credential, and changes no provider permission.
- **Administrative blockers are self-remedied, never handed to the Chairman (Chairman 2026-10-10, `DEC:ADMIN-BLOCKERS-ARE-SELF-REMEDIED-NEVER-HANDED-TO-THE-OPERATOR`).** The RS LEADER Meta-CEO seat (5ec0472d) ended on `EXACT_HUMAN_GATE` handing the Chairman the SSD worktree-mint command — a command the session could run itself; the Chairman rejected the stop and ordered the defect fixed at the root. A **quarantined session root, an SSD worktree mint, a stale hook copy in a host checkout, a stale ref, a helper lock, or a missing directory** can be an ADMINISTRATIVE blocker: diagnose and perform the permitted remedy in the same conversation. A hook message is evidence to inspect, not authority to override a control. **An actual permission or consent prompt remains a real boundary.** A permissive local setting does not authorize bypassing OS/provider consent, authentication, explicit refusals or another client's approval dialog. Identify that exact action once and continue independent permitted work. The quarantine recipe is three steps and is printed, filled in, by the guard itself: (1) mint an admissible tree with `printf '%s' '{"cwd":"<root>","name":"<name>","session_id":"<session_id>"}' | python3 ~/.local/lib/mastermind/worktree-storage/worktree_storage.py create` (SSD, under the host policy; the project hook `.claude/hooks/worktree_create_sparse.py` is the same mint where no host policy is installed) — it prints the new path, is idempotent, and a refusal names its cause (mount, free space, policy, receipt): fix that cause and rerun, never fall back to internal disk; (2) `ExitWorktree` keeping the tree when the conversation sits in a native `.claude/worktrees` tree; (3) `EnterWorktree(<printed path>)` and continue the ship loop there (`DSC:QUARANTINE-REMEDY-IS-AN-IN-SESSION-ACT`). `ship_loop_guard.py` admits exactly that mint shape plus read-only inspection and `git worktree/fetch/branch/rev-parse/status` while quarantined (`_ROOT_QUARANTINE_REMEDY_BASH`); `worktree_create_sparse.py` delegates every mint to the host storage helper whenever `~/.config/mastermind/worktree-storage.json` exists, so Desktop sessions launched from a macro checkout plant on the SSD, and a helper refusal is FINAL (no internal-disk fallback). A host checkout whose `.claude/hooks/` bytes predate this still mints the old way — keep them current by file overwrite only, never by git operations on the primary. **`EXACT_HUMAN_GATE` requires evidence, not a retry quota:** name the exact blocked action, observed tool/permission facts, and the reachable human action. A known human-only control requires no repeated probe. An explicit safety/permission refusal ends that effect immediately; ordinary technical failures can receive bounded permitted diagnosis. Real gates are MFA / Touch ID / passkey / CAPTCHA, a provider refusal, a physical device, money or security-setting changes, and Sol/Chairman rulings the seat does not hold. "I could not find a path" is not a gate: troubleshoot (read the hook or helper source, run its check command, inspect the mount/policy/receipt) before classifying. This law widens no credential, security setting, purchase, money-movement, production-deployment or safety boundary, and an explicit safety/permission refusal still ends that effect's retry.
- **Six execution invariants (hook-reinforced, `DEC:EXECUTION-CONTINUATION-INVARIANTS`).**
  - `BLOCKER -> freeze the affected lane -> check independent useful lanes -> continue`. One blocked review, tool, provider or CI lane freezes **that lane**, never the mission. `ALL_SCOPED_LANES_BLOCKED` may describe the current lane census, but it is a **nonterminal diagnostic**: each internal blocker must become an owned next action — resolve it, route it to the canonical owner, or prove a durable running owner + return path. "Another owner" / "not my lane" can forbid direct mutation; neither terminally ends the mission.
  - `NO WORKER STARTED + lawful principal tools/custody + no conflict/EFFECT_UNKNOWN -> direct bounded execution may continue`. A delegation surface being unavailable — Fabric down, a pool exhausted, a spawn refused — is **not** evidence that execution is impossible. If no worker actually started, the principal still holds lawful tools and custody, no other owner is working the same artifact, and no act is in an `EFFECT_UNKNOWN` state, the principal executes the bounded work itself. When any of those four is false, never add a second worker: route/reconcile the blocked dependency through its canonical owner. A bounded worker may return `STATUS: BLOCKED` to its parent; only a genuinely external final boundary may terminate the seat as `EXACT_HUMAN_GATE`, `PLATFORM_FAILURE`, or `EFFECT_UNKNOWN`.
  - `WAITING EXTERNAL -> durable watcher/owner; do useful parallel principal work; do not burn principal capacity polling`. Hand the wait to a durable watcher, cron, or the merge sweeper, then work an independent lane. A Stop-hook block during a wait is satisfied by a one-line hold note, never by a fresh poll (§House laws, `gh_quota_guard.py` shape 7).
  - `2 equivalent no-delta cycles -> change tactic/lane/owner`. Two attempts that changed nothing observable ban a third identical one. The Stop guard now names the cycle count in its own block text.
  - `accepted work -> DO_NOT_REDO unless materially invalidated`. Accepted, merged, or ratified work is re-opened only on a **material invalidator** — new contradicting evidence, a changed contract, or an explicit authority reversal. Neither a fresh session, a lost transcript, nor an absent memory is an invalidator; check `agentos/` `do_not_redo` and `research/DO_NOT_REBUILD.md` first.
  - `EFFECT_UNKNOWN -> same-carrier reconciliation; never blind retry/failover`. An act whose effect you cannot observe (a timed-out post, an ambiguous dispatch, a dropped tool call) is reconciled on the **same carrier** that performed it. A blind retry or a failover to another provider is how one irreversible act becomes two.
- **The delivery ladder is nine distinct facts and none implies the next**: `ACK -> QUEUED -> START -> RUNNING -> DELIVERED -> CI -> MERGED -> PRODUCTION_PROOF -> ACCEPTANCE`. An acknowledgement is not a queue entry; a queue entry is not a started worker; a returned packet is not a green check; a merge is not production proof; production proof is not acceptance by the commissioning authority. Report the rung the evidence reaches and no higher — a checkpoint, a status note, or a continuation record is a description of work, never the outcome it describes.
- **Every substantial session classifies its own end state** on one line, `SESSION END: <STATE>`, with STATE one of `PROVEN_OUTCOME` | `EXACT_HUMAN_GATE` | `EFFECT_UNKNOWN` | `PLATFORM_FAILURE` | `ALL_SCOPED_LANES_BLOCKED` | `DURABLE_EXECUTION_RUNNING` | `MORE_WORK_EXISTS`. The set is closed on purpose. **`MORE_WORK_EXISTS` and `ALL_SCOPED_LANES_BLOCKED` are never valid stopping states** and the Stop guard refuses either self-declaration; `ALL_SCOPED_LANES_BLOCKED` is retained only as an auditable mid-task diagnostic that forces blocker demolition/routing. The ordinary any-code ladder remains the unsatisfiable-gate escape. The converse is equally binding: reaching the actual outcome or an exact external terminal boundary early is a complete session however short or expensive it was — **never pad a session to look substantial, and never stop while authorized work remains**. Context compaction, rotation, or a `/clear` is a harness event, not an outcome; the block ledger deliberately survives `resume`/`compact`.

## Navigation source-of-truth (STANDING)

The site has exactly two global header families. Authenticated/product pages use
`templates/_site_nav.html.j2`; its inventory is
`templates/_navlinks.html.j2`, with behavior and appearance owned by
`templates/navigation-refresh.css`, `templates/nav_market.js`, and
`templates/theme.js`. Anonymous/corporate pages use
`templates/_public_nav.html.j2`, `_public_chrome_css.html.j2`, and
`_public_chrome_js.html.j2`; the hand-authored landing mirrors that family in
`templates/index.html`/`templates/landing.css` and is parity-guarded by
`tests/test_public_chrome.py`. Never create or locally resize a third page
header. `nav_prefix` may vary by directory depth; typography, geometry, menu
contents, search behavior, responsive breakpoints, and motion may vary only in
the shared family source.

## Model routing (STANDING — token economy)

Read [Model routing (STANDING — token economy)](docs/agent_guides/CLAUDE_MODEL_ROUTING.md) before the relevant action.

Before any worker spawn, read the linked routing guide and the current installed
admitted carrier procedure. Model, account, host, role and current availability are
separate facts. Do not silently inherit a frontier model, change provider settings,
bypass a refusal or duplicate a started worker. Resolve historical model examples
against current protected Mastermind and installed routing controls; these guides
never activate an unavailable route or waive the actual budget/root/return contract.

## Context economy (STANDING — Fable burn is CONTEXT × TURNS, not thinking; measured 2026-08-06)

**The expensive thing is re-reading context, not reasoning.** Week of 2026-07-30→08-06, measured across 3,043 local transcripts: Fable = 1,902M weighted units (26% of all model burn; Opus was 62%). Of that Fable burn, **62% was cache READS, 21% cache writes, and only 17% output.** Cache reads are the *discount* (0.1× fresh input) — never try to "avoid caching", the alternative is paying 10× for the same tokens. What costs money is the product **context size × turn count**.

Per-turn cost floor = `0.1 × context`. A turn at 150k context costs ~15k units before the model does anything; at 800k it costs ~80k. The top session that week (`bf6ce626`, 220M = 11.6% of the entire week's Fable) ran **3,539 turns at a median 419k context, max 879k, over 43h and 16 git branches**. Its turns at ≥400k context were 52% of turns but **67% of its burn**; the 700k+ band cost 92k units/turn, **3× a turn at 100–200k**. Those same 3,539 turns held at 150k would have cost ~53M instead of 196M.

**Riding context up to auto-compaction is the most expensive possible pattern.** Auto-compaction fires near the ceiling, so every turn on the approach is billed at the ceiling rate. Compaction controls are harness- and version-specific. Inspect currently exposed supported controls rather than treating an old client limitation as permanent. A model may invoke compaction only when its actual surface exposes that supported action; the two bullets below still govern context SIZE and turn count.

- **Delegate execution; the orchestrator adjudicates.** Measured: 76% of Fable's main-loop tool calls were `Bash`/`Edit`/`Read`/`Write` and delegation was **2.6%** of tool calls — Fable was grinding, not orchestrating. A subagent's context is **discarded on return** (only its report lands), so delegating keeps tool output out of the orchestrator permanently. Route per §Model routing: `ROUTE: build`→`builder` (sonnet), `ROUTE: review`→`reviewer` (opus), `ROUTE: census`→`scout` (sonnet) — direct spawns need the ROUTE contract; `Explore`/`general-purpose` are no longer routing homes.
- **Budget what enters context.** A tool result of size S landing at turn N is re-read on every one of the remaining turns. A 20k-token Bash dump at turn 500 of a 3,539-turn session costs ~6.1M weighted units downstream. Prefer targeted `grep`/line-ranged `Read` over whole-file reads; cap command output (`head`, `--limit`, `--jq`); never pull browser screenshots or full page dumps into an orchestrator — those belong in a subagent.
- **Durable state on disk — and a session may run as long as it stays useful (operator 2026-09-01; REPEALS "one session = one task boundary").** There is no task-boundary stop. A merged, live-verified wave is a CHECKPOINT, not a session end, and one session may carry a program end-to-end across many waves and many merges. The repealed rule forced every long workflow into a relay of amnesiac sessions, and re-establishing context in each successor cost more than the stop ever saved — the measured driver is context SIZE, which session length does not by itself determine. What survives is the durable-state half, now a WRITE rule rather than a STOP rule: keep program state in `research/*_CONTINUATION_HANDOFF_<date>.md` and `agentos/handoffs/` **as you go**, so the work survives a `/clear`, a crash, or an operator handoff — not so the session must end at one. Cost control is the two bullets above, and they are unaffected: a long session held near 150k is cheap, a short one riding 800k is not — so when context grows, delegate the next wave's execution rather than shortening the session. Context figures are advisory targets, never a stop trigger; checkpoint and hand off when context is genuinely heavy or when the operator clears. Reporting honesty is unchanged: a ratified `PARKED / HOLD-FOR-SOL` is still never described as merged, shipped, deployed, or live (§Shared workspace + completion), and DONE for ordinary work is still the merge.

**Explicit non-goal — do NOT save tokens by making Fable think less.** Output is only 17% of Fable burn, so cutting effort/reasoning degrades the model for at most a sixth of the cost. Keep `effort` where the task needs it. The savings are in *where work happens* and *how big the context is*, never in the quality of the thinking. Modelled on the measured top-12 sessions: delegating execution (−40% turns) plus holding context near 150k cuts those sessions ~66% — about **−28% of the week's Fable burn** — with the same work done.

## Spawn-handoff law (STANDING — quality does not travel by pointer; onboarding postmortem 2026-07-23)

Read [Spawn-handoff law (STANDING — quality does not travel by pointer; onboarding postmortem 2026-07-23)](docs/agent_guides/CLAUDE_SPAWN_HANDOFF.md) before the relevant action.

Read this guide before commissioning build work. A reference pointer alone is not
a complete worker commission: bind scope, acceptance gates, actual input artifacts,
source identity, permissions, return path and required visual proof. No child
self-merge or extra manager is authorized by a prose handoff.

## Agent OS — the company knowledge plane (STANDING)

Read [Agent OS — the company knowledge plane (STANDING)](docs/agent_guides/CLAUDE_AGENT_OS.md) before the relevant action.

`agentos/` in Macro is the existing organizational knowledge plane, not a live
session registry or dispatch authority. Recover the relevant workstream/latest
handoff when the task belongs to one; historical claims do not establish liveness.
Read `agentos/README.md` and the linked record guide before a material record write.
No second memory store, generated-view hand edit or per-tool paperwork is introduced.

## House laws (short list; details in research/ masterplans)

Read [House laws (short list; details in research/ masterplans)](docs/agent_guides/CLAUDE_HOUSE_LAWS.md) before the relevant action.

Read the relevant subsection before its action: design and dual-theme acceptance,
data/ledger mutation, statistical promotion, registry changes, CI observation or
recovery, worktree storage/reclaim, and release. Preserve no-invented signals/sizing,
explicit rights and identity, hold gates, human-only controls, protected shared
runs, canonical navigation, and required paired site artifacts. This entrypoint
is an index, not an exemption from those effect-specific controls.

## Memory frontmatter contract

Memory files (account-local, `~/.claude/projects/<project>/memory/`) are one fact per file with frontmatter: `name` (kebab slug), `description` (one line, drives recall), `metadata.type` ∈ user | feedback | project | reference. Link related memories with `[[name]]`. Index each file as one line in `MEMORY.md`. Update/delete rather than duplicate.

## Obsidian brain vault

`Macro Dashboard/ObsidianBrain/` is a live symlink view over memory + research (Dataview MOCs). It is a *view* — edit sources (memory files, research docs), never the vault copies.

<!-- Reconstructed 2026-07-05: PR #1215 shipped this file as 0 bytes (commit message described vault pointer + memory contract; content was lost — the #1052 zero-byte failure mode). Rebuilt from the memory index + program docs, with the model-routing standing rule added. -->
