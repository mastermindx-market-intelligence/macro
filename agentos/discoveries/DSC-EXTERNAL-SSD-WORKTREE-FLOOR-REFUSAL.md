---
key: EXTERNAL-SSD-WORKTREE-FLOOR-REFUSAL
claim: >
  `worktree_storage.py create` refuses to create a new agent worktree when the external SSD
  policy volume has less free space than the configured floor (observed: 137 GiB free < 160 GiB
  floor), and the policy forbids falling back to internal disk; the only compliant options are
  to reuse the session's existing worktree (switching branches after its current branch is
  pushed) or to run the work on a remote lane host.
falsifier: >
  Run `python3 ~/.local/lib/mastermind/worktree-storage/worktree_storage.py create` (JSON stdin with
  cwd, name, session_id) while `df -g /Volumes/Mastermind` reports less free space than the floor in
  `~/.config/mastermind/worktree-storage.json` and have it print a path; or find an internal-disk
  fallback clause in that policy file. Either disproves the claim.
so_what: >
  When a programme needs a second local checkout (for example to recapture Mac-only evidence on
  one branch while another branch is in flight), sequence the work through one worktree:
  push the in-flight branch, switch, recapture, switch back. Budget the SSD before starting a
  multi-branch programme.
confidence: verified
kind: constraint
verified_at: 2026-10-13
verified_by: >
  `python3 ~/.local/lib/mastermind/worktree-storage/worktree_storage.py create` refusal output
  (137 GiB < 160 GiB floor) on 2026-10-13; policy file ~/.config/mastermind/worktree-storage.json;
  global CLAUDE.md § "External SSD worktree placement".
scope:
  - fabric
  - workspace
---

Consequence in the chart-engine programme: the migration-branch recapture is sequenced into
the seat worktree after PR #982 leaves it, via the staged runbook mig_seat.sh.
