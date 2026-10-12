---
key: ADMIN-BLOCKERS-ARE-SELF-REMEDIED-NEVER-HANDED-TO-THE-OPERATOR
question: >
  When a Claude session hits an administrative blocker it has the tools to clear —
  a quarantined session root, a worktree that must be minted on the external SSD, a
  stale hook copy, a stale ref, a helper lock, a missing directory, a permission
  prompt — may it end the session on EXACT_HUMAN_GATE and hand the Chairman the
  command, or must it perform the remedy itself in the same session?
answer: >
  It performs the remedy itself. An administrative blocker is never a human gate;
  EXACT_HUMAN_GATE now requires three proofs (tool/permission evidence the act is
  unavailable to the session, two no-delta attempts with a changed tactic, and a
  named exact human action), and the guard, the project hook, the repository laws
  and the account-level instructions all carry the filled-in remedy.
rationale: >
  On 2026-10-10 the RS LEADER Meta-CEO seat (session 5ec0472d) ended on
  EXACT_HUMAN_GATE handing the Chairman the SSD worktree-mint command. The Chairman
  rejected the stop: the session could run that command itself. The root cause was
  structural, not a judgment slip. The ship-loop guard quarantined EVERY execution
  tool on an inadmissible root, including the Bash mint its own remedy needs, and
  its denial text read as "start a fresh worktree-backed session" — a human act.
  The user-level WorktreeCreate hook defers to any project hook, and the project
  hook planted internally, so a Desktop session launched from a macro checkout never
  reached the SSD the global placement law mandates; the primary checkout's stale
  hook copy minted worktree-<name> trees the guard quarantined. No instruction or
  memory told a session to self-remedy, so the stop looked lawful. The remedy —
  helper mint, ExitWorktree keeping the tree, EnterWorktree on the printed path —
  was then proven from inside the quarantined session with no human act: this seat
  is the receipt. The fix therefore has to live in four places at once: the guard
  (admit the remedy shape, print the filled-in recipe), the project hook (delegate to
  the host storage helper whenever the policy exists), the repository laws (CLAUDE.md
  and AGENTS.md, so Codex and other accounts inherit it) and the account-level
  CLAUDE.md plus memory (so the next Claude session recalls it before it stalls).
alternatives:
  - option: Keep the quarantine total and tell sessions to start a fresh worktree-backed session.
    why_not: >
      That is the exact failure: a Desktop conversation cannot relaunch itself, so the
      instruction becomes a request to the human. The remedy is a mint plus
      ExitWorktree/EnterWorktree, all of which the session can perform.
  - option: Have the guard mint the admissible tree itself on SessionStart.
    why_not: >
      A SessionStart hook cannot move the conversation (EnterWorktree is a tool the
      model calls), and silently minting on every quarantined start would plant trees
      for read-only visits. Printing the exact recipe and admitting its shape keeps the
      act visible and auditable.
  - option: Widen the quarantine to allow all Bash while quarantined.
    why_not: >
      The quarantine exists so a stale or shared checkout is never written through.
      The allow-list admits only the mint, read-only inspection and git
      worktree/fetch/branch/rev-parse/status — no chaining, substitution or redirects.
  - option: Fall back to internal disk when the SSD helper refuses.
    why_not: >
      The global placement law forbids it and a silent fallback hides the real cause
      (mount, free space, policy, receipt). The refusal is relayed with its cause and the
      session fixes that cause and reruns the mint.
evidence:
  - "Session 5ec0472d-5ff6-4e83-a190-dbe14ccc863d (2026-10-10): launched in Macro Dashboard/.claude/worktrees/rs-leader-end-to-end-eaa0cf on a quarantined worktree-<name> branch; minted /Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/rs-leader-meta-ceo-8655d9451bf8c77a on claude/ssd-rs-leader-meta-ceo-8655d9451bf8c77a via `printf '%s' '{...}' | python3 ~/.local/lib/mastermind/worktree-storage/worktree_storage.py create`, then ExitWorktree (keep) and EnterWorktree(<printed path>); the guard admitted the new root with no human act."
  - ".claude/hooks/ship_loop_guard.py: _ROOT_QUARANTINE_REPAIR_TOOLS gains ExitWorktree; _ROOT_QUARANTINE_REMEDY_BASH admits the mint/inspection shapes; _quarantine_remedy_text() prints the filled-in recipe in both the SessionStart context and every deny reason."
  - ".claude/hooks/worktree_create_sparse.py: delegate_to_storage_helper() forwards {cwd,name,session_id} to the host helper with --config <policy> create whenever ~/.config/mastermind/worktree-storage.json exists; a refusal is final."
  - "tests/test_ship_loop_semantic.py (remedy shapes allowed/denied, remedy text, native-tree ExitWorktree step) and tests/test_worktree_branch_name.py (hermetic fake-helper delegation, refusal, missing helper): `python3 -m pytest tests/test_ship_loop_semantic.py tests/test_worktree_branch_name.py tests/test_worktree_placement.py tests/test_agent_worktree_roots.py -q` -> 143 passed (2026-10-10)."
  - "Host-side: ~/.claude/CLAUDE.md block mastermind-autonomous-blocker-self-remedy-v1; ~/.local/lib/mastermind/worktree-storage/worktree_create_hook.py docstring (DEFER semantics); account memory administrative-blockers-are-self-remedied-never-handed-to-the-chairman.md."
affects:
  - ".claude/hooks/ship_loop_guard.py"
  - ".claude/hooks/worktree_create_sparse.py"
  - "CLAUDE.md"
  - "AGENTS.md"
  - "tests/test_ship_loop_semantic.py"
  - "tests/test_worktree_branch_name.py"
  - "tests/test_worktree_placement.py"
  - "WS:EXECUTION-CONTINUATION-LAW"
confidence: high
reversibility: easy
decided_by: chairman
decided_at: 2026-10-10
---

## Decision scope

This record governs ADMINISTRATIVE blockers only: session-root quarantine, external
SSD worktree placement, stale hook copies in a host checkout, stale refs, helper
locks, missing directories, and permission prompts that `defaultMode=bypassPermissions`
already answers. It widens no credential, security setting, purchase, money-movement,
production-deployment or safety boundary, and an explicit safety/permission refusal
still ends that effect's retry. A real human gate is unchanged: MFA / Touch ID /
passkey / CAPTCHA, a provider refusal, a physical device, a money or security-setting
change, or a Sol/Chairman ruling the seat does not hold.

## What is true now

- A quarantined session reads its own remedy in the guard's SessionStart context and
  in every deny reason: mint on the SSD through the host storage helper (or through
  the project hook where no host policy is installed), `ExitWorktree` keeping the tree
  when the conversation sits in a native `.claude/worktrees` tree, then
  `EnterWorktree(<printed path>)`. The guard admits exactly that Bash shape while
  quarantined.
- The project hook plants on the SSD whenever the host policy exists; without a policy
  the internal mint is unchanged. A helper refusal names its cause and aborts the spawn.
- A host checkout whose `.claude/hooks/` bytes predate this change still mints the old
  way; keep them current by file overwrite only — never git operations on the primary.
- `EXACT_HUMAN_GATE` requires the three proofs named above. "I cannot find a path" is
  not one of them; two no-delta attempts must have changed tactic.

## Exact next action

Future sessions: when any tool denial names a remedy, perform the remedy. When a
blocker is not named, troubleshoot it (read the hook or helper source, run its check
command, inspect the mount/policy/receipt) before classifying it. Hand the Chairman
nothing the session can run.

## Do not redo

- Do not widen the quarantine allow-list to general Bash; the shapes are the remedy.
- Do not add an internal-disk fallback to the storage delegation.
- Do not re-audit whether the remedy works from inside a quarantined session — the
  seat in `evidence` is the receipt.
