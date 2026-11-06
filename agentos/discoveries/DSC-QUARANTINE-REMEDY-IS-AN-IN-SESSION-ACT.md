---
key: QUARANTINE-REMEDY-IS-AN-IN-SESSION-ACT
claim: >
  A session-root quarantine (the ship-loop guard's SESSION ROOT QUARANTINE on a root
  that is not a linked claude/* worktree) is cleared from inside the same conversation
  with no human act: mint an admissible tree through the host storage helper (or the
  project hook), call ExitWorktree keeping the tree when the conversation sits in a
  native .claude/worktrees tree, then EnterWorktree on the printed path — and the
  guard admits that mint shape while quarantined.
falsifier: >
  From a quarantined root, run the mint the guard's deny reason prints (the command
  between the backticks after "with"), then ExitWorktree (keep) and
  EnterWorktree(<printed path>); if the guard still denies Bash in the new root, or
  denies the printed mint itself, this claim is false. Also:
  `python3 -m pytest tests/test_ship_loop_semantic.py -q -k "remedy or exitworktree"`.
so_what: >
  A session that reads SESSION ROOT QUARANTINE performs the three-step remedy and
  continues; it never ends on EXACT_HUMAN_GATE, never asks the operator to run the
  mint, and never starts a "fresh worktree-backed session" as the first resort —
  that is the fallback only when EnterWorktree is unavailable.
kind: runtime
verified_at: 2026-10-10
verified_by: >
  Session 5ec0472d-5ff6-4e83-a190-dbe14ccc863d: minted
  /Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/rs-leader-meta-ceo-8655d9451bf8c77a
  (branch claude/ssd-rs-leader-meta-ceo-8655d9451bf8c77a) with the host helper from the
  quarantined Macro Dashboard/.claude/worktrees/rs-leader-end-to-end-eaa0cf tree, then
  ExitWorktree + EnterWorktree; guard admitted the new root. Pinned by
  tests/test_ship_loop_semantic.py::test_quarantined_root_allows_the_remedy_mint_and_denies_other_bash
  and ::test_native_session_tree_remedy_adds_the_exitworktree_step (143 passed across
  the four hook test files).
scope:
  - ".claude/hooks/ship_loop_guard.py"
  - ".claude/hooks/worktree_create_sparse.py"
  - "macro"
  - "charting-app"
  - "mastermind"
confidence: verified
---

## Evidence qualification

The receipt is one Desktop session on the Mac Studio with the SSD policy installed
(`~/.config/mastermind/worktree-storage.json`) and the helper present. On a host
without the policy the guard prints the project-hook variant of the mint
(`printf '%s' '{...}' | python3 <checkout>/.claude/hooks/worktree_create_sparse.py`),
which plants under `<checkout>/.claude/worktrees/<name>` on `claude/<name>` — the
same admissible shape. ExitWorktree/EnterWorktree are Claude Code tools; a Codex or
Cursor session in the same state performs the mint and reopens its workspace at the
printed path with its own client's mechanism.

## Continuation

Cited by `DEC:ADMIN-BLOCKERS-ARE-SELF-REMEDIED-NEVER-HANDED-TO-THE-OPERATOR`, the
repository CLAUDE.md/AGENTS.md "Administrative blockers are self-remedied" law and the
account-level `~/.claude/CLAUDE.md` self-remedy block.
