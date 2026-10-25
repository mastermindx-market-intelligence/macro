---
key: LAUNCHER-RELOCATION-IS-A-CAPABILITY-GRANT
question: >
  When a target workspace carries a blanket `Bash` deny in its `.claude/settings.json`, should the
  kit launcher attempt to grant the lane the capability it would otherwise have been denied by
  relocating its cwd to the checkout's parent (with a prompt preamble telling the lane to `cd`
  back in), or should it refuse the launch and preserve the project boundary?
answer: >
  Worktree relocation is a capability grant by relocation; the only lawful launcher shapes are
  refuse-before-launch or launch-with-denial-preserved.
rationale: >
  A Claude harness resolves permissions from the project it is launched in. `ext/sub.sh::_compute_placement`
  used to detect a blanket `Bash` deny in the target workspace's `.claude/settings.json` and
  RELOCATE the lane cwd to the checkout's parent (`RELOCATED=1`), prepending prompt text telling
  the lane to `cd` back in — handing the lane a shell the denied project had withheld. That is a
  capability grant by relocation: the project boundary that said "no Bash" was silently crossed
  by leaving the project. A blanket deny is an explicit operator policy signal; the launcher has no
  authority to grant back the very capability the deny withholds. The repaired behaviour refuses
  the launch (`LAUNCH_REFUSED: project_bash_denied`, rc 78) on both the launch path and the plan-
  only path for all three Claude-harness pools, so the deny holds whether the launcher runs the
  shell or merely plans against it.
alternatives:
  - option: Keep the relocation stopgap
    why_not: >
      It is a capability grant by relocation. A blanket `Bash` deny is an explicit operator policy
      signal that the launcher has no authority to override by leaving the project. Preserving it
      preserves a class of unrequested capability that the deny was put in place to refuse.
  - option: Rewrite the prompt preamble instead of the launcher
    why_not: >
      The harness resolves permissions from the launched project, not from prompt text. Telling
      the lane to `cd` back in does not un-relocate the permission check — the very shell the lane
      runs in is the granted shell. A prompt preamble cannot restore the boundary the relocation
      already crossed.
  - option: Do nothing because Mastermind #661 (5ffa643d) removed the blanket deny
    why_not: >
      Mastermind #661 removed one specific instance of a blanket deny. The launcher must hold
      for any blanket `Bash` deny in any target workspace's `.claude/settings.json` at any future
      time; a removed instance does not retire the policy, and a future re-introduction would
      silently re-enable the stopgap if it were still in place.
evidence:
  - "ext/sub.sh full sha256 BEFORE the repair: 67953b2a007ab57a6f0c74d98ac15b62ac78426d51b6dfb6fee1316cbc43b28a (computed via `shasum -a 256`)."
  - "ext/sub.sh full sha256 AFTER the repair: 8d79229797f30e7c8bd89178f3dc2cbc7bfafa2a0ccd05a89423903c4c19f999 (`shasum -a 256`)."
  - "Repair record at ~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08/orch/fabric/SUBSH_DENY_REPAIR.md (sha256[:12] f92a14fc5bc9): `STATE: REPAIRED 8d792297…` and `VERDICT: REPAIRED — relocation removed`."
  - "Sol ruling 2026-09-15 2300Z, §(2), recorded at ~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08/orch/fabric/SOL_RULINGS_2026-09-15_2300Z.md: 'preserve the originating permission boundary in the launcher — an unavailable shell must not become available by leaving the denied project.'"
  - "Mastermind #661 (5ffa643d) removed the Mastermind blanket deny that had been the original justification for the stopgap; the stopgap has no remaining legitimate use."
affects:
  - WS:EXECUTIVE-CAPACITY-FABRIC
  - kit launcher path (ext/sub.sh::_compute_placement and downstream)
confidence: high
reversibility: easy
decided_by: coo-fable
decided_at: 2026-09-16
---

## Why this is a capability grant

A project-level `Bash` deny in `.claude/settings.json` is the operator's signal that the lane
should not have shell access inside that project. The Claude harness resolves permissions
from the project the lane is launched in, so relaunching from the parent directory gives the
lane a different permission context — and that different context hands back exactly the shell
the deny was put in place to refuse. The relocation's prompt preamble ("`cd` back into the
checkout") does not restore the boundary, because the boundary is the project the shell was
launched in, and the launch already crossed it. Refuse-before-launch and launch-with-denial-
preserved both keep the boundary intact: either the lane never runs, or the deny travels with
the launch.

## Operational consequence

The repaired `ext/sub.sh::_compute_placement` (sha256[:12] `8d792297`) refuses any target
workspace whose `.claude/settings.json` carries a blanket `Bash` deny, on both the launch path
and the plan-only path, returning `LAUNCH_REFUSED: project_bash_denied` with rc 78. The
refusal holds for every Claude-harness pool; plan-only refusal prevents a denied project
from being inspected or summarized by the planner either. The repaired launcher preserves
every other lawful launcher shape; only the relocation stopgap is removed.