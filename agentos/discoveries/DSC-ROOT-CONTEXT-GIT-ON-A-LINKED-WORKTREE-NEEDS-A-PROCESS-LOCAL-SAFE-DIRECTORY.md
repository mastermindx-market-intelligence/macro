---
key: ROOT-CONTEXT-GIT-ON-A-LINKED-WORKTREE-NEEDS-A-PROCESS-LOCAL-SAFE-DIRECTORY
claim: >
  A root-context installer `git` read on a linked worktree checked out on the new SSD volume is refused by
  git's dubious-ownership source-policy gate BEFORE the installer takes any install action, and the
  working repair is a process-local `safe.directory` tuple exported for that single process
  (`GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=safe.directory`, `GIT_CONFIG_VALUE_0=<checkout path>`) rather
  than a global-config mutation.
falsifier: >
  Run the same root-context installer/`git` read on that checkout with no `safe.directory` configuration
  anywhere — no global entry, no process-local tuple — and observe it succeed; or show the observed
  refusal came from a cause other than dubious ownership (for example a missing binary, a permission
  error, or a path that does not exist). Either result disproves the claim.
so_what: >
  When a root/system-context git operation refuses with "dubious ownership" on a linked worktree or an
  external volume, repair it for that process only with the `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_0`/
  `GIT_CONFIG_VALUE_0` tuple and leave global git config untouched: a global `safe.directory` write is a
  host-wide trust widening and must never be used to unblock one install. Also treat the refusal as
  happening BEFORE any install action — the interrupted attempt's control/relay restart must be reconciled
  to the unchanged prior baseline and reported as "no install occurred", never as a partial install.
kind: landmine
verified_at: 2026-09-17
verified_by: >
  Sol ruling edge `1789680829.787409`, which records the 2026-09-17 21:02Z first install attempt refused at
  the installer's root-context source-policy gate (git dubious-ownership on the new SSD checkout) before
  any install action, its control/relay restart reconciled to the unchanged `4c148709` baseline, and the
  corrected attempt using a process-local `GIT_CONFIG_COUNT` safe.directory tuple with no global config
  mutation. Carried, not re-run: this records-only fold ran no installer and no root-context git read.
scope:
  - mastermind
  - ops/executive_os/install.sh
confidence: verified
---

## The failure shape

The canonical installer resolves its source tree with `git` from a root context. Git refuses to operate in
a repository whose directory ownership does not match the invoking uid unless the path is declared safe —
the message names dubious ownership and the operation stops at that gate. On the new SSD volume the
installer's linked worktree is not owned by root, so the read is refused even though nothing about the
release source is wrong. The refusal is a **source-policy** gate: it fires before the installer has taken
any install action, so no partial install, no half-moved release directory and no credential effect can
result from it.

## The repair that is and is not acceptable

`safe.directory` can be supplied per-process through git's environment-config channel — `GIT_CONFIG_COUNT`,
`GIT_CONFIG_KEY_0`, `GIT_CONFIG_VALUE_0` — which declares the trust for that one invocation only. The
rejected alternative is `git config --global --add safe.directory <path>`: that writes a machine-wide trust
entry so that every future root git operation on the host accepts the path, trading a host-wide property
for one install. A host-wide trust widening is not a fix for an install-time read.

## Currentness

2026-09-17: the corrected attempt ran with the process-local tuple and the install of generation
`8b231e82` completed (rc=0, verify ok), accepted by Sol as UNARMED / STOPPED. The 21:02Z refusal remains
the recorded reproduction of this discovery.
