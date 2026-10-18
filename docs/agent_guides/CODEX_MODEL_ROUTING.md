## Model routing

Every Agent/Task spawn and every Workflow `agent()` call must carry an explicit
model — a PreToolUse hook (`.claude/hooks/model_routing_guard.py`, wired in
`.claude/settings.json`) denies spawns that would silently inherit the session
model, `fable` spawns outside the `orchestrator` + FABLE-WHY gate, fable-pinned
agent frontmatter outside that gate, and Workflow scripts whose `agent()`
calls carry no `model:`/`agentType` routing.

Current tiers: Sonnet builds shipping code — writing code, PRs, refactors,
tests — via the `builder` agent type (model-pinned `sonnet`; spawns using it
pass the guard without a `model:` param), alongside its existing role in
census/exploration/mechanical non-code fan-out. Opus reviews (`reviewer`),
handles hard debugging, judge/red-team critics, and stats/math review, and
owns user-facing design (`designer`) — design is judgment work and is never
routed to a sonnet builder, a separate 2026-07-18 ruling that this build-lane
change does not touch. Fable (the main loop) plans, adjudicates, and merges,
and may be spawned only as the triple `subagent_type: 'orchestrator'` +
explicit `model: 'fable'` + a `FABLE-WHY: <orchestration|brainstorm|creative>:
<specific reason>` line — reserved for work that fails the draft-and-review
test, never bulk ×N mechanical fan-outs. Haiku handles trivial
extraction/format sweeps.

The build-lane tier was reversed 2026-08-17 (operator instruction) from the
2026-07-21 "no more sonnet building code" order, and the `builder` agent type
is re-pinned `sonnet` accordingly. The autonomous metabolism build loop
(`scripts/metabolism_build.py`, R-V4-2) is a separate system and stays
Opus-pinned unless amended on its own terms. See Macro `CLAUDE.md` §Model
routing for the full tier table, and
`agentos/decisions/DEC-SONNET-BUILDS-AGAIN.md` (supersedes
`DEC-OPUS-BUILDS-SONNET-EXPLORES-FABLE-GATED`) for the decision record.

**Direct-spawn routing (hook-enforced amendment, 2026-08-17 — semantic ROUTE contract):** every direct Agent/Task spawn declares a semantic `ROUTE: <class>` line; `.claude/agent-routing.json` (execution-policy registry, NOT a strategic control plane) maps each route to its ONE canonical custom agent and model — `extract`→`extractor`(haiku), `census`→`scout`(sonnet), `research`→`researcher`(sonnet), `draft`→`drafter`(sonnet), `analysis`→`analyst`(opus), `debug`→`debugger`(opus), `build`→`builder`(sonnet), `review`→`reviewer`(opus), `design`→`designer`(opus), `judgment`→main loop ONLY (never spawned), `orchestration`→`orchestrator`. The orchestrator seat runs either explicit `model: 'fable'` + FABLE-WHY (unchanged gate, work failing the draft-and-review test) or — for easier orchestration that does not need frontier judgment — explicit `model: 'opus'` with a prompt directive to load the `fable-mode` skill (`.claude/skills/fable-mode`), at roughly half Fable's price and with no FABLE-WHY because no fable is spent; the same skill lets an Opus MAIN session hold the orchestrator role. `model_routing_guard.py` denies missing/unknown routes, route↔agent/model mismatches, under-specified commissions (each route's required `SECTION:` labels live in the registry), and bypass via `general-purpose`/`Explore`/`Plan`/`fork`; a `SubagentStop` hook (`.claude/hooks/agent_return_guard.py`) blocks a routed worker ONCE if its final message misses the STATUS/RESULT/EVIDENCE/GAPS/DEVIATIONS packet, then lets the second stop through (no loops). Treat a guard rejection as feedback — fix the route or commission, never evade the registry to obtain a different model. Frontmatter pins are the runtime truth; `tests/test_agent_routing_control.py` keeps registry↔frontmatter from drifting.


<!-- Repository-root-relative paths and controls are unchanged by relocation. -->
