# Macro Dashboard — shared agent operating rules

## Standing commercial data rights

Chris has directly confirmed approved existing commercial licensing with full commercial rights for the Research Factory Yahoo/yfinance route (including the fixed nine sector ETFs), Massive/Polygon, Tiingo and ThetaData options. Apply [DEC:COMMERCIAL-DATA-RIGHTS-CHAIRMAN-ATTESTATION-20261023](agentos/decisions/DEC-COMMERCIAL-DATA-RIGHTS-CHAIRMAN-ATTESTATION-20261023.md) and the [shared source law](https://github.com/mastermindx-market-intelligence/Mastermind/blob/master/docs/COMMERCIAL_DATA_RIGHTS.md). The commercial gate is `APPROVED_BY_CHAIRMAN_ATTESTATION`; no repeated approval, contract upload or public-terms re-proof. Preserve separately evidenced historical/PIT, access, quality, budget, scientific and unresolved-effect facts.

This repository is operated by multiple Claude accounts and Codex sessions. Repository files are the durable, shared source of instructions; promises or “memory” recorded only inside one chat do not carry to another session.


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

## Execution continuation law

A blocked lane is not a finished mission. This section governs when a session may
STOP; the "Definition of done" section below governs what the ship chain owes once a
session produces a commit. This law does not weaken the ordinary ship chain: both bind,
and neither releases the other. A blocked lane is a reason to keep working other lanes,
never a reason to leave an unmerged pull request.

### Authority model — restated here, duplicated nowhere

Chairman Chris is final authority. **Sol is the default AI CEO / system owner.**
Ordinary Claude and Codex sessions remain **bounded workers**. **Fable is scarce
principal capacity by default.** The governing authority map stays in Mastermind
(`config/authority_map.yml` + `control_plane/packet_gate.py`); the "Required context"
section above already forbids a second copy in this repository, and this section
creates none, dispatches nothing, and grants no one a permission they did not have.

What it adds is the scope rule the defaults were missing. **An explicit Chairman
delegation overrides those defaults inside its stated scope, and a default role
assumption never overrides it back.** A seat holding a Chairman-delegated program
decides in-scope matters itself and does not re-ask Sol for what it was already
delegated — the standing example is Meta-CEO Fable B owning the Agent Fabric program,
which repeatedly stalled waiting for a Sol authorization it did not need. The converse
binds just as hard: **delegated authority never leaks outside its stated scope**,
exactly as conditional merge authority granted for one pull request never transfers to
another (`DEC:SOL-HOLD-IS-A-MERGE-BARRIER`). This law promotes no worker to principal, widens no
credential, and changes no provider permission.

### Administrative blockers are self-remedied, never handed to the Chairman (2026-10-10)

`DEC:ADMIN-BLOCKERS-ARE-SELF-REMEDIED-NEVER-HANDED-TO-THE-OPERATOR`. The RS LEADER
Meta-CEO seat (5ec0472d) ended on `EXACT_HUMAN_GATE` handing the Chairman the SSD
worktree-mint command — a command the session could run itself. The Chairman rejected
the stop and ordered the defect fixed at the root.

A **quarantined session root, an SSD worktree mint, a stale hook copy in a host
checkout, a stale ref, a helper lock, or a missing directory** can be an
ADMINISTRATIVE blocker: diagnose and perform the permitted remedy in the same
conversation. A hook message is evidence to inspect, not authority to override a
control. **An actual permission or consent prompt remains a real boundary.**
A permissive local setting does not authorize bypassing OS/provider consent,
authentication, explicit refusals or another client's approval dialog. Identify
that exact action once and continue independent permitted work.

The quarantine recipe is three steps, printed filled-in by `ship_loop_guard.py` itself:

1. Mint an admissible tree:
   `printf '%s' '{"cwd":"<root>","name":"<name>","session_id":"<session_id>"}' | python3 ~/.local/lib/mastermind/worktree-storage/worktree_storage.py create`
   (external SSD under the host policy; `.claude/hooks/worktree_create_sparse.py` is the
   same mint where no host policy is installed). It prints the new path and is
   idempotent. A refusal names its cause (mount, free space, policy, receipt): fix that
   cause and rerun — never fall back to internal disk.
2. `ExitWorktree` keeping the tree when the conversation sits in a native
   `.claude/worktrees` tree (Codex/Cursor: reopen the workspace at the printed path).
3. `EnterWorktree(<printed path>)` and continue the ship loop there
   (`DSC:QUARANTINE-REMEDY-IS-AN-IN-SESSION-ACT`).

The guard admits exactly that mint shape plus read-only inspection and
`git worktree/fetch/branch/rev-parse/status` while quarantined
(`_ROOT_QUARANTINE_REMEDY_BASH`); the project hook delegates every mint to the host
storage helper whenever `~/.config/mastermind/worktree-storage.json` exists, so sessions
launched from a macro checkout plant on the SSD, and a helper refusal is FINAL. A host
checkout whose `.claude/hooks/` bytes predate this still mints the old way — keep them
current by file overwrite only, never by git operations on the primary.

**`EXACT_HUMAN_GATE` requires evidence, not a retry quota:** name the exact
blocked action, observed tool/permission facts, and the reachable human action.
A known human-only control requires no repeated probe. An explicit safety/permission
refusal ends that effect immediately; ordinary technical failures can receive bounded
permitted diagnosis. Real gates are MFA / Touch ID / passkey / CAPTCHA, a provider
refusal, a physical device, money or security-setting changes, and Sol/Chairman rulings
the seat does not hold. "I could not find a path" is not a gate: troubleshoot (read the
hook or helper source, run its check command, inspect the mount/policy/receipt) before
classifying. This law widens no credential, security setting, purchase, money-movement,
production-deployment or safety boundary, and an explicit safety/permission refusal
still ends that effect's retry.

### The six execution invariants

`BLOCKER -> freeze the affected lane -> check independent useful lanes -> continue`.
One blocked review, tool, provider or CI lane freezes that lane, never the mission.
Before any stop, enumerate the other authorized lanes and continue on them.
`ALL_SCOPED_LANES_BLOCKED` may describe the current lane census, but it is a
**nonterminal diagnostic**, not a principal/seat stopping state. For each internal
project blocker, the next act is to resolve it, route it to the canonical owner, or
prove that an already-running durable owner has a return path. "Another owner" or
"not my lane" can prevent direct mutation; neither makes the mission terminal.

`NO WORKER STARTED + lawful principal tools/custody + no conflict/EFFECT_UNKNOWN ->
direct bounded execution may continue`. A delegation surface being unavailable — the
Fabric down, a pool exhausted, a spawn refused — is not evidence that execution is
impossible. If no worker actually started, the principal still holds lawful tools and
custody, no other owner is working the same artifact, and no act sits in an
`EFFECT_UNKNOWN` state, the principal executes the bounded work itself. When any of
those four is false, do not create a second worker. Name the blocked lane and convert
it into an owned next action: route/reconcile through the canonical owner, or, if the
only remaining boundary is genuinely outside the project's controllable graph,
classify it exactly as `EXACT_HUMAN_GATE`, `PLATFORM_FAILURE`, or `EFFECT_UNKNOWN`.
A bounded worker may return `STATUS: BLOCKED` to its parent; that worker return does
not terminally classify the parent mission.

`WAITING EXTERNAL -> durable watcher/owner; do useful parallel principal work; do not
burn principal capacity polling`. Hand the wait to a durable watcher, a cron, or the
merge sweeper, then work an independent lane. A Stop-hook block during a wait is
satisfied by a one-line hold note, never by a fresh poll.

`2 equivalent no-delta cycles -> change tactic/lane/owner`. Two attempts that changed
nothing observable ban a third identical one. The Stop guard now names the cycle count
in its own block text rather than repeating one unchanging instruction.

`accepted work -> DO_NOT_REDO unless materially invalidated`. Accepted, merged or
ratified work reopens only on a material invalidator: new contradicting evidence, a
changed contract, or an explicit authority reversal. A fresh session, a lost
transcript, and an absent memory are none of those. Check the `agentos/`
`do_not_redo` entries and `research/DO_NOT_REBUILD.md` before re-opening anything.

`EFFECT_UNKNOWN -> same-carrier reconciliation; never blind retry/failover`. An act
whose effect cannot be observed — a timed-out post, an ambiguous dispatch, a dropped
tool call — is reconciled on the same carrier that performed it. A blind retry or a
failover to another provider is how one irreversible act becomes two.

### The delivery ladder

`ACK -> QUEUED -> START -> RUNNING -> DELIVERED -> CI -> MERGED -> PRODUCTION_PROOF ->
ACCEPTANCE` are nine distinct facts and none implies the next. An acknowledgement is
not a queue entry; a queue entry is not a started worker; a returned packet is not a
green check; a merge is not production proof; production proof is not acceptance by
the commissioning authority. Report the rung the evidence reaches and no higher. A
checkpoint, a status note, or a continuation record describes work; it is never the
outcome it describes.

### Session end classification

Every substantial session states one line before it ends: `SESSION END: <STATE>`,
where STATE is exactly one of `PROVEN_OUTCOME`, `EXACT_HUMAN_GATE`, `EFFECT_UNKNOWN`,
`PLATFORM_FAILURE`, `ALL_SCOPED_LANES_BLOCKED`, `DURABLE_EXECUTION_RUNNING`, or
`MORE_WORK_EXISTS`. The set is closed on purpose. **`MORE_WORK_EXISTS` and
`ALL_SCOPED_LANES_BLOCKED` are never valid stopping states**; the latter is a
diagnostic that forces blocker demolition/routing rather than bureaucratic exit.
The Stop guard refuses either self-declaration, with the ordinary any-code ladder
preserved as the unsatisfiable-gate escape.

The converse binds equally. Reaching the actual outcome or the exact human gate early
is a complete session however short or expensive it was: never pad a session to look
substantial, and never stop while authorized work remains. Context compaction,
rotation, or a `/clear` is a harness event and not an outcome — the guard's block
ledger deliberately survives `resume` and `compact`.

## Context economy (frontier burn is CONTEXT × TURNS)

Measured 2026-08-06 across 3,043 local transcripts (week of 07-30→08-06): of all
Fable burn, **62% was cache reads, 21% cache writes, only 17% output**. Cache
reads are the discount (0.1× fresh input), not the waste — never try to avoid
caching. The cost driver is `context size × turn count`, and the per-turn floor
is `0.1 × context`: ~15k units/turn at 150k context, ~80k at 800k.

The worst measured session ran 3,539 turns at a median 419k context (max 879k)
over 43h and 16 branches, costing 11.6% of the week's Fable burn on its own
(Fable was 26% of all model burn that week; Opus 62%). Its turns at ≥400k context were 52% of turns but 67% of its burn. Riding
context up to auto-compaction is the most expensive possible pattern: compaction
fires near the ceiling, so every turn on the approach bills at the ceiling rate.
Compaction controls are harness- and version-specific. Inspect the currently
exposed supported controls; old capability statements are not evidence that an
action exists or is impossible. A model may invoke compaction only when its
actual surface exposes that supported action.

- **Delegate execution; the orchestrator adjudicates.** 76% of Fable's
  main-loop tool calls that week were `Bash`/`Edit`/`Read`/`Write`, and
  delegation was 2.6%. A subagent's context is discarded on return — only its report lands — so
  delegating keeps tool output out of the orchestrator permanently.
- **Budget what enters context.** A tool result of size S landing at turn N is
  re-read on every remaining turn. Prefer targeted `grep`/line-ranged reads over
  whole files, cap command output (`head`, `--limit`, `--jq`), and keep browser
  screenshots and full page dumps inside a subagent.
- **Durable state on disk — and a session may run as long as it stays useful.**
  Operator 2026-09-01 REPEALED the former "one session = one task boundary" rule:
  it forced every long workflow into a relay of amnesiac sessions, and
  re-establishing context in each successor cost more than the stop ever saved.
  There is no task-boundary stop — a merged, live-verified wave is a checkpoint,
  not a session end, and one session may carry a program end-to-end across many
  waves and many merges. The durable-state half survives as a WRITE rule, not a
  STOP rule: keep program state in a
  `research/*_CONTINUATION_HANDOFF_<date>.md` and `agentos/handoffs/` as you go,
  so the work survives a clear, a crash, or an operator handoff. Cost control is
  the two bullets above and is unaffected — a long session held near 150k is
  cheap, a short one riding 800k is not, so when context grows, delegate the next
  wave's execution rather than shortening the session. Context figures are
  advisory targets, never a stop trigger.

Do NOT save tokens by reducing reasoning effort — output is only 17% of burn, so
cutting thinking degrades quality for at most a sixth of the cost. The savings
are in where work happens and how large the context is.

## Required context at the start of every task

1. Read only the task-relevant sections of this entrypoint and its linked guides.
   `CLAUDE.md` is the Claude entrypoint, not a mandatory full-file Codex import.
   Load the applicable effect guide before acting; do not waive its controls.
2. Account-local memory is optional task context, not a required second bootstrap.
   Consult a relevant note only when the current checkpoint and canonical source
   leave a material question unresolved. Historical delivery notes do not override
   the current assignment, existing effect guides, permissions or release controls.
3. Treat `/Users/chriswong/Documents/Cluade/charting-app` as the connected Terminal
   repository. Authentication, subscriptions, data contracts, APIs, and deployment
   changes may require checking both repositories.
4. **Company strategic state lives in the Mastermind repo**
   (`/Users/chriswong/Documents/Cluade/Mastermind`), not here:
   `config/strategic_state.yml` — current phase, north star, P0 objectives, resource
   policy, standing constraints — read via
   `control_plane.strategic_state.load_strategic_state()`. The worker contract
   (hierarchy Chairman Chris → AI CEO GPT-5.6 Sol → COO Fable → workers; the
   six-layer source-of-truth order; the completion rule) is Mastermind
   `AGENTS.md` § "Executive contract". Macro fleet law below is unchanged and still
   governs sessions here. **Never create a second strategic state, control plane, or
   authority map in this repository** — `duplicate_control_planes` is a standing
   prohibition. See `research/EXECUTIVE_OS_PHASE0_CENSUS.md` (PR #5356) and
   `Mastermind/research/EXECUTIVE_OS_STRATEGIC_STATE_BOOTSTRAP.md`.
5. **The Mastermind Agent OS knowledge plane lives in this repository at `agentos/`**
   — workstreams, decisions, discoveries, and handoffs, canonical for all three
   repos. When a task belongs to an existing workstream, read its `WS-*` record and
   latest handoff before starting. See § "Agent OS knowledge plane" below and
   `agentos/README.md`.

## Navigation source-of-truth

There are exactly two global navigation families:

- Authenticated/product pages use `templates/_site_nav.html.j2`. Its inventory
  lives in `templates/_navlinks.html.j2`; shared geometry, responsive behavior,
  mega menus, ticker search and motion live in
  `templates/navigation-refresh.css`, `templates/nav_market.js`, and
  `templates/theme.js`.
- Anonymous/corporate pages use `templates/_public_nav.html.j2` with
  `templates/_public_chrome_css.html.j2` and
  `templates/_public_chrome_js.html.j2`. The hand-authored landing page mirrors
  that family in `templates/index.html`/`templates/landing.css`, guarded by
  `tests/test_public_chrome.py`.

Do not hand-copy or restyle a third header inside a page template. A page may
provide a relative `nav_prefix`, but page CSS must not change the global
header's width, typography, menu dimensions, search behavior, breakpoints or
motion. Change the appropriate shared family and its parity tests instead.

## Design system (any user-facing surface)

`research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` is the binding visual/composition
law: archetype per route, canonical components (registry = the specimen at
`mockups/design_system/specimen.html`), tokens only (extend `templates/theme.css`,
never a parallel token root), density budgets, dark+light as two art directions,
EN/ZH parity. Content law stays with `docs/DESIGN_DOCTRINE.md` (wins on conflict).
Chairman design rule (2026-10-18): never add a colored left edge or equivalent
accent stripe to a container; do not relocate it to another edge. Use neutral
surface hierarchy, even borders, typography and labeled semantic ink. Preserve
complete focus outlines and meaningful chart series. The doctrine owns this rule.
Migration work follows `research/DESIGN_MIGRATION_FACTORY_V1.md`: builders execute
a committed migration packet exactly and never invent design language — a builder
that believes the packet is wrong stops and escalates.

### Theme art direction — required (TP-0, 2026-08-27)

Dark and light are **two deliberate art directions of one semantic system**, not
a design and its skin. They share information architecture, component semantics,
spacing/type scales, state meanings, user actions, data contracts, ordering and
density law, and interaction behavior. They do **not** have to share material
treatment: dark is a command center (luminance depth, instrument calm, restrained
glow); light is a research workspace (cool canvas, white material, hairline
discipline, shadow instead of glow).

**Token substitution alone is never proof of a light design.** "The same CSS
still renders once the tokens swap" is exactly the failure this law exists to
stop.

Every material UI packet must name: DARK TREATMENT; LIGHT TREATMENT; which
mechanisms intentionally differ and why; the reference/baseline; theme-specific
degraded states; and the evidence matrix (dark/light × EN/ZH × desktop 1440 /
mobile 390). A packet missing the light art direction or its evidence is
`PARTIAL/BLOCKED`, never `PASS`.

- **Designer:** state both art directions separately and supply both evidence
  sets; never approve "same CSS, tokens swap" without arguing why the mechanism
  genuinely works in both luminance environments.
- **Builder:** if a frozen spec lacks LIGHT TREATMENT or its required evidence,
  stop `PARTIAL/BLOCKED` — do not invent or silently translate one, and never
  add an opaque runtime stylesheet to escape a design-system constraint.
- **Reviewer:** `PASS` on a material UI change requires dark and light each
  adjudicated as designs — hierarchy, material depth, semantic color, responsive
  composition, EN/ZH parity. Functional browser success is necessary, never
  sufficient.

**Substantive product styling may not be authored as an opaque runtime
stylesheet system inside page/composer JavaScript** — no multi-kilobyte
`style.textContent` material system, no parallel palette/token family, no
duplicated light/dark stylesheet branches invisible to the design-system
checker. JavaScript may mount and recompose canonical DOM, set state
classes/attributes, select existing variants, and apply genuinely data-dependent
inline geometry; governed presentation source owns the material decisions.

Forward-only enforcement (inherited debt reports, but does not newly block):
`scripts/check_design_system.py --mode enforce-added` on changed lines,
`scripts/check_runtime_style_injection.py` as a ratcheted budget that may only
stay flat or shrink, and `scripts/check_ui_visual_evidence.py` for the committed
dual-theme evidence receipt. CI checks evidence existence and state identity
only — a human/Opus reviewer owns visual taste.

## Workspace and git

Read [Workspace and git](docs/agent_guides/CODEX_WORKSPACE.md) before the relevant action.

The canonical source is the exact observed GitHub default revision, not a stale
folder. Use the admitted isolated-workspace route; never modify the occupied
primary checkout, repo-global stash or another session's Git state. The linked
`macro-main` checkout shares `Macro Dashboard/.git`: never delete or move the
object store. Preserve host placement, ownership, lock and unresolved-effect rules.
Read `config/sparse_worktree.json` before materializing omitted generated/data paths;
a missing directory is not proof that the source does not exist. Never stage an
unexpected data/site truncation or run a full-data suite on an unqualified sparse tree.

## Signal-state interpretation (operator 2026-08-09)

An engine state machine's terminal verdict is an INSTRUMENT verdict, never a market verdict:
a transmission chain or cycle tripwire printing "failed" means its declared windows failed,
not that the thesis is false. Report the scope ("no 22d rolldown yet", never "no peak");
relay a falsifier's prose note only as far as its receipt supports; and when a display-tier
state disagrees with the terminal asset's tape or a scored organ (Prophet, Sector
Intelligence), lead with the dual-read. Receipts and the design seed:
`research/CASE_STUDY_GOLD_REAL_RATE_PEAK_2026_08.md`.

## Adjudication coverage gate (operator 2026-08-10)

Statistical rigor (prereg, held-out eras, clustered CIs) does NOT substitute for an adversarial
pass on the CONCLUSION. Before presenting any discovered rule or promotion-bearing adjudication:
(1) **coverage** — run the rule against the live exemplars that motivated the question AND the
current regime, and lead with that answer (a rule that refuses all of them is not the answer,
however clean its CIs — the SPY-altitude miss, blocked-entry study round 1); (2) **episode
honest-N** — for state-conditioned cells report distinct EPISODES, not fires or dates, and state
whether today's tape is in-sample of the winning cell; (3) **panel integrity** — name who is
missing (survivorship/delistings/coverage floors) before trusting a cohort mean; deep-drawdown
cohorts concentrate the dead; (4) **red-team** — make-or-break calls get an opus `reviewer` pass
briefed to break the conclusion against the operator's actual use-case BEFORE the main loop
presents it. The operator often cannot audit these calls and will not be the safety net.

## Kill-registry citations (DO_NOT_REBUILD.md)

Rows in `research/DO_NOT_REBUILD.md` carry a stable `Key` column (`KILL-…` §1–2,
`LAW-…` §3, `HOLD-…` §4). Cite rows as `DNR:<KEY>` — for example
`DNR:KILL-PROPHET-POP-MERGE` — never by row or line number: numbers shift on
every append/reflow, and row-number citations have already mis-resolved in the
wild (2026-08-05). An adjudication that kills, forbids, or defers a topic
appends its row inside sections 1–4 only, mints a new unique Key, and commits
the regenerated `config/compiled_kill_registry.yml` and
`config/signal_foundry_blocklist.yml` in the same PR (manual heal:
`python3 scripts/check_blocklist_drift.py --fix`).

## Agent OS knowledge plane

Read [Agent OS knowledge plane](docs/agent_guides/CODEX_AGENT_OS.md) before the relevant action.

`agentos/` in Macro is the existing organizational knowledge plane, not a live
session registry or dispatch authority. Recover the relevant workstream/latest
handoff when the task belongs to one; historical claims do not establish liveness.
Read `agentos/README.md` and the linked record guide before a material record write.
No second memory store, generated-view hand edit or per-tool paperwork is introduced.

## Model routing

Read [Model routing](docs/agent_guides/CODEX_MODEL_ROUTING.md) before the relevant action.

Before any worker spawn, read the linked routing guide and the current installed
admitted carrier procedure. Model, account, host, role and current availability are
separate facts. Do not silently inherit a frontier model, change provider settings,
bypass a refusal or duplicate a started worker. Resolve historical model examples
against current protected Mastermind and installed routing controls; these guides
never activate an unavailable route or waive the actual budget/root/return contract.

## Definition of done

Read [Definition of done](docs/agent_guides/CODEX_DELIVERY.md) before the relevant action.

Own the assigned delivery outcome through its actual acceptance boundary; a plan,
commit, open PR or green check alone is not product completion. Source-only work
must not restart an unrelated service. Reuse accepted unchanged evidence, continue
safe independent work while required CI/review runs, and keep one real observer
with an observed return path. Do not convert an observation request into background
execution or bypass a required check. Read the detailed delivery and render rules
before any PR arm, merge, release, CI recovery or shared-run cancellation decision.

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
