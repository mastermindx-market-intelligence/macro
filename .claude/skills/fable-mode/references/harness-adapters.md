# Harness adapters — the same doctrine on different machinery

The doctrine names six primitives. Discover which bindings the current harness actually provides; a named primitive is not proof it exists. Verify the exact action, permission and return mechanism before relying on it. This file maps the primitives to the surfaces this fleet actually uses as of 2026-09-24. **Every seat reads it once per session, Claude Code seats included** — section 2 carries the binding lane, labor, quota, and Stop-hook mechanics of this fleet, and a seat that skips it fans out native children for census and build in exactly the way the standing law forbids. A seat that is not running inside Claude Code — Sol or Astra on a GPT-class harness, Grok, GLM, MiniMax, a Codex or Cursor lane — finds its bindings in sections 3–6. **Where a binding here disagrees with the repository's `CLAUDE.md` / `AGENTS.md`, the live kit brief, or the fabric's own documentation, those win; update this file rather than the doctrine.**

Contents: 1 The six primitives · 2 Claude Code (this fleet) · 3 External labor lanes (`ext/sub.sh`) · 4 The Mastermind Executive / Subagent Fabric · 5 Codex, Cursor, Grok, Warp sessions · 6 GPT-class seats (Sol, Astra) and any harness without a Skill tool · 7 The loader line for packets

---

## 1. The six primitives

| primitive | what the doctrine needs from it | rules that depend on it |
|---|---|---|
| **delegate** | send a packet to a worker with an explicit tier; get a packet back | O.5, O.6, S.5–S.6 |
| **watch** | a durable, model-turn-free wait keyed on an artifact, with a budget | O.9, L.8, S.2 |
| **durable store** | a place a cold successor is guaranteed to read | L.1, L.12, S.4, S.8 |
| **carrier** | where the counterpart's rulings arrive and where once-per-operation acts live | S.1, O.17, A.6, L.3 |
| **checkpoint** | a one-command revert point before wide or irreversible acts | §5.4, §7.8 |
| **identity** | which seat, which session, which operation you are — verifiable | L.10, O.16, O.17 |

If a needed primitive is unavailable, record the exact missing action and freeze only the dependent lane. A missing watcher does not establish a **verified return path**; verify any existing native event/wake binding instead of assuming re-invocation. A Web turn is not a daemon. Continue useful independent authorized work; before yielding, preserve the checkpoint and truthful resume boundary under the governing continuation law. Durable execution requires a proven started executor plus a supported return path. A repository is a durable store only when the write is permitted, persisted and read back; do not invent persistence when that write fails.

## 2. Claude Code (this fleet)

- **delegate:** the `Agent` tool with a semantic `ROUTE:` line; `.claude/agent-routing.json` maps each route to one pinned agent and model (`extract→extractor`, `census→scout`, `research→researcher`, `draft→drafter`, `analysis→analyst`, `debug→debugger`, `build→builder`, `review→reviewer`, `design→designer`, `judgment→` main loop only, `orchestration→orchestrator`). Hooks enforce it: `.claude/hooks/model_routing_guard.py` denies missing routes, route/model mismatches, under-specified commissions, and bypass via generic agents; `.claude/hooks/agent_return_guard.py` blocks a worker once for a missing return packet, then lets the second stop through — which is why the turn-ending clause belongs in the *original* packet. The Opus orchestrator seat is `ROUTE: orchestration` + explicit `model: 'opus'` + a directive to load this skill; the Fable form needs `FABLE-WHY`. **Standing fleet law (Chairman, 2026-09-14/17): native Claude children are not labor lanes** — census, building, reviewing, and shepherding go to external lanes (section 3) or the fabric (section 4); native Opus children are for bounded orchestration or an independent read-only audit only, and a global guard fails closed otherwise.
- **watch:** a bounded background shell loop keyed on a sentinel file or line (`perl -e 'alarm N; exec @ARGV' bash -c 'until grep -q "^LANE: " out; do sleep 30; done'` — macOS has no `timeout`); `Monitor`; cron/scheduled tasks; the merge sweeper (`merge-on-green`). `gh` quota is one shared bucket: `--interval 60`+, no loops sleeping under 90s, one watcher per endpoint, never `--paginate` check runs, never re-dispatch a proof workflow over an in-flight run.
- **durable store:** the repository — `research/<PROGRAM>_CONTINUATION_HANDOFF_<date>.md` for program state, `agentos/` for `WS-*` / `DEC-*` / `DSC-*` / handoff records (`python3 scripts/agentos.py validate` must pass), account-local memory only for account-local facts.
- **carrier:** the operation's Slack thread first (rulings arrive there), then the PR/issue. Read from the last consumed counterpart edge before every act; labels and review decisions are counterpart-mutable, never assert them from memory.
- **checkpoint:** a WIP commit in a per-lane worktree; never bare `git stash` (the stash stack is repo-global and shared).
- **identity:** your session id, the worktree you were launched in, and the operation key on the carrier. The Slack seat is shared by several sessions; verify *your* uuid before claiming an ACK.
- **harness pressure:** the Stop hook (`.claude/hooks/ship_loop_guard.py`) blocks every turn while a PR is unmerged; it is satisfied by a one-line hold note during a watched wait, and its escape ladder (`SHIP LOOP BLOCKED:` evidence report after the counted blocks) is used once, after which the seat stays quiet. Waiting on CI is not a qualifying blocker.

## 3. External labor lanes (`ext/sub.sh` in the seat's handoff kit)

The kit launcher sends a *prompt string* to an external pool (`glm`, `glm-codex`, `minimax`, `minimax-codex`, `grok`, `qwen`, `cursor`, `go-codex`, `go-claude`, `oc-free`) with a cwd and a model. Consequences for the doctrine:

- **delegate:** the packet (`packets.md` §1) *is* the prompt. Nothing else travels — not this skill unless the packet says to read it (section 7 below), not the seat's context. Model is the fourth argument: name it every time. Append the turn-ending clause (`packets.md` §2) to every packet; the kit keeps it in a file for exactly that purpose.
- **watch:** the lane's stdout file and its single final sentinel line (`<LANE>: <VERDICT> <sha>`). Key waits on the sentinel or the worktree token, never on the `nohup` pid. Bound each wait; each shell call in this harness has its own ceiling, so chain bounded waits rather than one long one.
- **durable store / carrier / identity:** the lane has none of its own; the seat owns all three. A lane never posts to the carrier, never labels, never marks ready, never merges — those are seat-only acts the lane *recommends* under `NEXT SEAT ACT`.
- **isolation:** one worktree per lane, created through the fleet's worktree helper; a lane told to "continue the branch" may attest from a stale tree unless the packet makes it prove the checkout.
- **pools have admission and quota of their own** (window pacing, slot limits, per-realm receipts); an admission refusal is a delegation surface being down — apply L.7, do not route around the admission.

The live paths, pool names, model tiers, and hard laws are in the kit's `orch/fabric/OPUS_ORCHESTRATOR_BRIEF.md` and `MODEL_EFFICIENCY_RULING_*.md`; they change weekly and are deliberately not copied here.

## 4. The Mastermind Executive / Subagent Fabric

- **delegate:** admission through the authenticated Executive connector or ingress only, when current Chairman/user intent and every authority/admission/effect gate authorize the exact operation. Never the legacy raw control socket, never an ad-hoc queue beside the fabric. Executive OS owns lifecycle; the Capacity/Model Router owns worker placement; Agent OS owns continuity — do not build a parallel queue, retry system, lifecycle, or identity plane in a session.
- **the ladder is literal here:** a successful admission means `QUEUED` only — never `STARTED`, never completed. A worker's start is its own receipt. An ambiguous modifying effect is reconciled on the same carrier (L.3), never retried.
- **carrier:** the operation thread plus the fabric's own receipts; both are read before any modifying act.

## 5. Codex, Cursor, Grok, Warp sessions

These harnesses read the repository's `AGENTS.md`. The existing `.agents/skills/fable-mode/SKILL.md` is a discovery pointer to this canonical package, not a second doctrine. Verify the actual checkout, selected path and content revision: a merged skill is not installed until the workspace receives it. A sparse checkout may omit `.agents` or the referenced `.claude` directory. Discover and repair that through the existing workspace owner without resetting the shared primary or another writer's tree.

For Codex, use the installed app-server's `skills/list` with the intended `cwds` and `forceReload: true` to inspect `fable-mode`, its enabled state, exact path and loader errors. A version-matched schema governs optional extra-root support. A successful directory read is not discovery; successful discovery is not model-behavior proof. Test from the real intended scope, not only a temporary extra root. Invoke the exact returned skill path when name collisions exist; do not assume same-name skills merge. Preserve one maintained canonical package and thin discovery pointers.

**User-wide Codex installation.** Do not copy the checkout-relative stub into `~/.agents/skills/fable-mode`: its relative path would resolve to the home-directory Claude copy, which can be stale. Deploy the reviewed complete canonical package (core and all relative references) into the authorized user-scope directory, with a source revision and per-file digests in the installation receipt. This is a versioned deployment of the one repository source, not a separately maintained doctrine. Check existing contents and custody before replacing them; never overwrite unrelated files or broaden permissions. Verify `skills/list` from actual intended workspaces, and distinguish source review, discovery, model consumption and orchestration acceptance.

Native tools vary by version; do not claim that Codex lacks subagents or copy Claude's `Agent` arguments into it. A Codex Astra/Sol principal must verify the selected child model **and reasoning effort**: omitted fields can inherit the parent's expensive configuration. Model, harness, role, requested settings and observed served identity remain separate; unknown values stay unknown. Skills do not select a principal model, change credentials, arm a provider, or grant nested fan-out. Delegate through the currently approved lanes/admission in sections 3–4; the existence of a native spawn tool never overrides that policy.

Their worktree hygiene remains with the existing sparse-worktree hooks and placement owner; this adapter creates no installer, runtime or queue. A Grok session launched by an external secretary applies L.10 to historical launch context while preserving the current direct assignment and current authority.

## 6. GPT-class seats (Sol, Astra) and any harness without a Skill tool

- **Loading:** read `.claude/skills/fable-mode/SKILL.md` by path, then the reference the phase table names. Nothing in the doctrine requires a tool you lack.
- **delegate:** use an existing approved route whose current admission, scope, capacity and budget cover the exact outcome. A visible ingress, launcher or messaging tool is not authority. Keep the existing packet shape and explicit eligible tier; never use a new surface to evade an admission or permission denial.
- **watch:** rely only on an actually registered watcher or another verified return path bound to the correct parent and operation. Without one, no automatic re-invocation is claimed: continue useful independent work and preserve the exact held/resume boundary when governing procedure permits yielding. Do not create a polling principal or duplicate watcher.
- **durable store:** use the existing authorized repository/Agent OS owner and verify persistence. Program file per `long-horizon.md` section 1; records per `packets.md` sections 10–11. A local note, a failed write, or a chat reply is not a published organizational checkpoint.
- **carrier / identity:** identical. Read from the last consumed counterpart edge; search the operation key before any ACK; one seat may be several sessions.
- **pre-send gate:** run it by hand — it is a checklist, not a hook. Item 12 (`SESSION END: <STATE>`) is what lets a Claude or Codex successor resume you.

## 7. The loader line for packets

Scope the doctrine to the tier — resident doctrine is context every lane pays for on every turn. Put the matching line in the packet (adjust the path to the repository root the lane runs in):

```
# build / debug / analysis / review lanes:
DOCTRINE: before acting, read .claude/skills/fable-mode/references/engineering.md in full.
Your final message must be the return packet in .claude/skills/fable-mode/references/packets.md section 3.

# orchestration lanes:
DOCTRINE: before acting, read .claude/skills/fable-mode/SKILL.md, then
.claude/skills/fable-mode/references/orchestration.md, long-horizon.md, and harness-adapters.md.
Your final message must be the return packet in packets.md section 3.

# extract / draft / census lanes: no doctrine read — paste the return packet shape and the
# turn-ending clause (packets.md sections 2–3) into the packet instead.
```

A lane that cannot read the repository (a hosted model with no file access) gets the ten commitments and the return packet pasted into the prompt instead — `config/fable_mode_core.md` is the maintained distillation for exactly that case.
