## Agent OS knowledge plane

`agentos/` in this repository is the canonical organizational memory shared across
sessions, models, and accounts — Claude and Codex alike: workstream records
(`agentos/workstreams/WS-<KEY>.md`), decision records (`agentos/decisions/DEC-<KEY>.md`),
discovery records (`agentos/discoveries/DSC-<KEY>.md`), and session handoffs
(`agentos/handoffs/<WS-KEY>-<YYYY-MM-DD>.md`). Read `agentos/README.md` before writing
any record; the machine schemas live in `agentos/schema/` and the handoff protocol in
`research/MASTERMIND_AGENT_HANDOFF_PROTOCOL.md`.

It is a knowledge plane, never a control plane. Nothing under `agentos/` decides
whether work may run: no gate, no dispatch, no scheduler, no lease with teeth. Execution
authority stays where it already lives — this repository's hook layer for
sessions, Mastermind `control_plane/` for worker processes.
A workstream `claim:` is an advisory author's note in git; never present one as evidence
that an agent is currently alive or working (`DEC:AGENTOS-CLAIMS-ARE-NOT-LIVE-ACTIVITY`;
live occupancy evidence is `git worktree list`). Do not create a second Agent OS store,
or a local Decision/Discovery mirror, in any other repository —
`DEC:AGENTOS-HOME-IS-MACRO`; if cross-repo write friction proves real, the route is to
supersede that decision with evidence, never to mirror silently.

When to read: at task start, if the task belongs to an existing workstream, read its
`WS-*` record, its most recent handoff, and the decisions/discoveries they cite before
writing code. `do_not_redo` entries are binding unless refuted with new evidence. The
records are context, not permission — the Charter, strategic state, authority map,
`DO_NOT_REBUILD.md`, and the fleet law in this file still govern.

When to write, and only then — this layer must stay low-friction, and a one-file fix
that merges clean with nothing learned needs no records:

- a **Discovery** (`DSC-*`) when the session verified a durable, non-obvious fact that
  future sessions materially benefit from and no canonical document already records.
  Both admission gates are required — a `falsifier` (what would disprove it) and a
  `so_what` (what a future session does differently). Account-local memory is not
  company memory; cross-session facts graduate here.
- a **Decision** (`DEC-*`) when an actual choice with durable consequences was taken:
  the question, the answer, the rationale, the alternatives rejected, the evidence, and
  what would cause reconsideration. Decisions are superseded, never deleted.
- a **Handoff** when the session claimed a workstream, minted records, or leaves work in
  a state another session must resume. Contract: a competent stranger continues from the
  text alone; every `verified:` claim names the command that backs it. The natural
  moment is immediately before the session stops, in the same PR.
- a **workstream update** when durable state materially changes — status and
  `next_action` at wave boundaries, not per commit.

Hygiene: `python3 scripts/agentos.py validate` must exit 0 on any PR touching records
(schema is fail-closed; cross-store joins fail open). Cite records as `WS:<KEY>`,
`DEC:<KEY>`, `DSC:<KEY>` — the colon form, never row or line numbers. Never hand-edit
the generated views `docs/AGENT_OS_STATE.md` and `data/governance/agent_os_state.json`
— the nightly is their only regenerator — and never author `created`/`updated` fields;
the generator derives both from git history.

<!-- Repository-root-relative paths and controls are unchanged by relocation. -->
