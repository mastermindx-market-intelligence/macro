# Harness adapters — the same doctrine on different machinery

The doctrine names six primitives. Every harness has some binding for each; the bindings rot, the doctrine does not. This file maps the primitives to the surfaces this fleet actually uses as of 2026-09-24, so a seat that is not running inside Claude Code — Sol or Astra on a GPT-class harness, Grok, GLM, MiniMax, a Codex or Cursor lane — can apply the same rules. **Where a binding here disagrees with the repository's `CLAUDE.md` / `AGENTS.md`, the live kit brief, or the fabric's own documentation, those win; update this file rather than the doctrine.**

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

If a harness lacks a primitive (no watcher, no durable store), the rules that depend on it do not lapse — they get more expensive. A seat with no watcher primitive still may not poll; it ends its turn on a state and is re-invoked by the event. A seat with no durable store writes to the repository.

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

These harnesses read the repository's `AGENTS.md` and may discover skills under `.agents/skills/` — this skill is mirrored there. They have no `Agent` tool with a routing registry; a Codex or Cursor session acting as a seat delegates through sections 3 or 4 of this file and applies the same packet shapes. Their worktree hygiene is handled by the repository's sparse-worktree hooks (`scripts/worktree_sparse.py auto`); their carrier and identity rules are unchanged. A Grok session launched by an external secretary must treat its launch prompt as a stale relay (L.10) exactly as a Claude session does.

## 6. GPT-class seats (Sol, Astra) and any harness without a Skill tool

- **Loading:** read `.claude/skills/fable-mode/SKILL.md` by path, then the reference the phase table names. Nothing in the doctrine requires a tool you lack.
- **delegate:** whatever surface your harness gives you (a fabric ingress, an external lane launcher, a message to a worker session). The packet shape does not change. Name the tier explicitly even if your harness has one model — the next seat may not.
- **watch:** if you have no watcher primitive, end the turn on a state and let the event re-invoke you; do not poll from the seat. If you have cron-like scheduling, use it at the cadence the awaited state actually changes.
- **durable store:** the repository. Program file per `long-horizon.md` section 1; records per `packets.md` sections 10–11; the Agent OS record shapes are plain YAML/markdown and need no tooling to write.
- **carrier / identity:** identical. Read from the last consumed counterpart edge; search the operation key before any ACK; one seat may be several sessions.
- **pre-send gate:** run it by hand — it is a checklist, not a hook. Item 12 (`SESSION END: <STATE>`) is what lets a Claude or Codex successor resume you.

## 7. The loader line for packets

When a commissioned worker or an orchestration lane should hold itself to this doctrine, put this in the packet (adjust the path to the repository root the lane runs in):

```
DOCTRINE: before acting, read .claude/skills/fable-mode/SKILL.md, then
.claude/skills/fable-mode/references/engineering.md (you are doing bounded work) — or
.claude/skills/fable-mode/references/orchestration.md and long-horizon.md (you are orchestrating).
Your final message must be the return packet in packets.md section 3.
```

A lane that cannot read the repository (a hosted model with no file access) gets the six commitments and the return packet pasted into the prompt instead — `config/fable_mode_core.md` is the maintained distillation for exactly that case.
