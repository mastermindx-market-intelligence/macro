---
key: EXECUTIVE-ATTENTION-ADMISSION-SOURCES-ARE-DARK
claim: >
  The Executive Attention Frontier's lawful admission sources have ZERO live coverage on the
  current host, so a correct allocator over them yields an empty frontier. Measured 2026-09-20 on
  Mac-Studio against a real `build_control_room()` composition: 69 work cards presented, 0 carrying
  any `attention_ids`, 0 carrying executive runtime jobs, and no `needs_ceo` field in the
  projection at all. Both backing stores are absent from the filesystem entirely — not merely from
  the worktree: `data/control_plane/executive.sqlite3` and
  `macro-agentos-canon/data/governance/agent_os_state.json` do not exist anywhere under
  `~/Documents/Cluade`. The Control Room reports `attention: chairman=0 ceo=0 coo=0`. This confirms
  the F0G section 16 ledger entry "Wake/Executive Inbox attention source | PARTIAL end-to-end
  organizational coverage" and sharpens it to zero for this host.
falsifier: >
  Falsify by exhibiting a populated executive runtime database or Agent OS state file on a fleet
  host such that `build_control_room()` reports a non-zero `attention` count, or by showing another
  protected owner that publishes explicit attention obligations. Re-measure with
  `python3 scripts/chairman_control_room.py --check` and inspect `doc["work"][*]["attention_ids"]`.
so_what: >
  The current binding constraint on executive cognition allocation is SOURCE POPULATION, not the
  allocator. A2 shadow, A3 Control Room and A5 calibration are all built and provable, but
  prospective real-data calibration cannot run until explicit attention demand exists to admit, so
  no promotion decision can be reached on evidence. A projection over dark sources MUST announce
  that fact: an empty frontier with an empty degraded list reads as "nothing needs your attention"
  when the truth is "no source answered", which is the exact reading the do_not_redo rule "do not
  silently treat incomplete source admission as reduced executive load" forbids. The shipped
  projection therefore reports `admission_confidence` as NO_SOURCE / GATES_ONLY / SOURCED. Admitting
  the 69 cards' prose `state`/`next_action` instead would manufacture demand and is refused: any
  new admission source is a versioned architecture change owned by Sol/Chairman, not a worker.
verified_at: 2026-09-20
verified_by: >
  Real composition on Mac-Studio: control_plane.chairman_control_room.build_control_room() over the
  live repo, plus `python3 scripts/chairman_control_room.py --check`. Censused all 69 returned work
  cards for attention_ids, executive jobs, PRs, bindings, disagreements, agent_os state/reason_code
  and needs_ceo. Confirmed both backing stores absent via `find ~/Documents/Cluade -maxdepth 5 -name
  executive.sqlite3 -o -name agent_os_state.json` returning nothing. Ran the A2 projection
  end-to-end over the live snapshot and over the Control Room fixtures.
scope:
  - WS:EXECUTIVE-ATTENTION-ECONOMICS
  - mastermind:control_plane/executive_attention_shadow.py
  - mastermind:control_plane/executive_attention_calibration.py
  - mastermind:scripts/chairman_control_room.py
confidence: verified
kind: constraint
---

Measured 2026-09-20 on Mac-Studio. Baseline scanning burden: 69 cards presented, 69 requiring a
manual read because none carries an explicit attention obligation.
