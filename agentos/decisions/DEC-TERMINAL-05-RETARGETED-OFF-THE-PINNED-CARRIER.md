---
key: TERMINAL-05-RETARGETED-OFF-THE-PINNED-CARRIER
question: >
  The TERMINAL-05 handoff packet ("reproducible and transactional deployment") pinned
  mastermind-terminal#622 as the carrier to adopt and forbade starting a duplicate
  implementation. Reconciliation showed most of what #622 carries was already merged.
  Continue #622 anyway to honour the pin, or retarget?
answer: >
  Retargeted to the single named open defect, mastermind-terminal#483 (bytecode-cache
  residue self-blocking the canonical preflight bundle), shipped as #771, merged
  541330e4c90593f0ec60918347330d3194c2c5ab and deployed 2026-09-29 19:03:07 UTC.
  #622 was left open and unmodified, with a field note recording what it still uniquely
  carries. No second deploy path, lifecycle, queue or controller was created.
rationale: >
  The packet's own rule is "adopt the existing carrier after current source/ownership
  reconciliation" -- reconciliation is a precondition, not a formality, and it showed the
  pin was stale. The W2B-C transaction #622 was pinned to deliver is already live on master
  via #752/#504: deploy_generation_begin/commit/rollback/abort, deploy_identity_verified,
  recover_canonical_head_mismatch and cleanup_deploy_attempt are all in
  ops/terminal-build.sh today. Continuing #622 would have re-landed merged work and
  produced a second implementation of the thing the packet forbids duplicating -- the
  opposite of what the pin exists to prevent. #483 was the one open defect in the brief's
  scope with a live production cost.
alternatives:
  - option: Continue #622 as pinned and rebase it onto master
    why_not: >
      Most of its diff is already merged, so the rebase is mostly conflict resolution
      against your own shipped code, and the result re-asserts a transaction that is
      already live. High risk, no new capability.
  - option: Ship #483 AND finish #622's remaining mutex in one PR
    why_not: >
      The mutex is a separate, larger change to release serialisation with its own
      failure modes. Bundling it would have made the residue fix un-reviewable and
      un-revertable independently, and #622 is the correct home for it.
  - option: Report BLOCKED because the pinned carrier is stale
    why_not: >
      The packet explicitly asks for implementation rather than a plan, and a named,
      reproducible, production-costing defect was in scope and fixable.
evidence:
  - "mastermind-terminal ops/terminal-build.sh:808-950 — the generation transaction already on master"
  - "mastermind-terminal#752, #504 — the merges that landed it"
  - "mastermind-terminal#483 — the named open defect, closed by #771"
  - "mastermind-terminal#622 — left open; field note records the remaining deploy-mutex gap"
  - "DSC:PYCACHE-RESIDUE-ABORTS-TERMINAL-DEPLOY-AT-GATE-ZERO — what the defect actually cost"
affects: ["mastermind-terminal/ops/terminal-build.sh", "mastermind-terminal/tests/test_terminal_build_admission.py", "mastermind-terminal#622", "mastermind-terminal#483"]
reversibility: easy
decided_by: terminal-05-transactional-deploy
decided_at: 2026-09-29
confidence: high
---

## What remains open, and where

The one thing #622 still uniquely carries is a **deploy mutex**. Verified against the
generation live in production (`541330e4c`, installed owner sha256
`5aa7b776800ec7fa19044b4350ba07eaa64f9b5175f66086c2b82f5f2247054a`):

```
git show origin/master:ops/terminal-build.sh | grep -n 'flock\|deploy\.lock'   -> no output
on the host: grep -c flock /opt/terminal/terminal-build.sh                     -> 0
             ls -ld /run/mastermind-terminal                                   -> No such file or directory
```

`LOCK_BEFORE`/`LOCK_AFTER` in the merged script hash `hub/package-lock.json` — a
dependency-drift check, not a mutex, and the naming invites exactly that misreading.
So two concurrent `terminal-build.sh` runs can interleave the `.next` swap, the overlay
rsync and the `install`s of `terminal-data` and `terminal-build.sh` itself. The generation
transaction is correct *within* one run and has no notion of a second. This is not
hypothetical: three sessions queued for this host on 2026-09-29 and serialised by hand over
chat, which is the manual workaround for a missing lock.

## Rollback anchor moves with every deploy, and carries no identity

Recorded because a session reported a stale rollback target on the strength of it. Line
numbers below are `ops/terminal-build.sh` at mastermind-terminal `origin/master`
`d28449368`; the live readings are `ssh root@146.190.142.17` at 2026-09-29T20:46:21Z.

The prior build is retained whole at `/opt/terminal/terminal/.next.bak`, but the directory
only ever holds ONE generation back and each deploy overwrites it. The identity half is
worse than stale — after a successful deploy it is **gone**. `deploy_generation_begin`
(`:842`) records exactly one of two rollback facts: `.deployment-id.bak` when a marker
existed (`:846`), or an empty `.deployment-id.absent` when none did (`:848`).
`deploy_generation_rollback` (`:874`) consumes them in that order (`:889-890`, `:891-892`)
and otherwise sets `rc=1   # no rollback record — the marker cannot be proven correct`
(`:894`). On success `deploy_generation_commit` (`:855`) calls `deploy_generation_reset`,
whose `rm -f` (`:838`) removes **both** records at once. So the absence of `.bak` alone
would not prove anything — `.absent` is a valid second record — but commit clears the pair,
which is what makes a post-commit rollback attempt a guaranteed `rc=1`.

That is the live state now, one generation after this decision shipped:

```
ls -la /opt/terminal/terminal/ | grep -E 'deployment-id|\.next'
-rw-r--r-- 1 root root   41 Sep 29 19:43 .deployment-id     -> d284493688...
drwxr-xr-x 8 root root 4096 Sep 29 19:43 .next
drwxr-xr-x 8 root root 4096 Sep 29 19:03 .next.bak
                                          (no .deployment-id.bak, no .absent)
```

`.next.bak` is the build this decision's own deploy installed at 19:03 (`541330e4c`),
displaced by the 19:43 deploy and now sitting under a marker that reads `d284493688`. Nothing on the host records
that pairing: its mtime is the only thing linking the retained directory to a source SHA,
and `.next/BUILD_ID` cannot help because `deploymentId` pins it to a constant literal. So
`.next.bak` is not a degraded rollback anchor; it is not an anchor. It is a build with no
name.

The supported post-commit mechanism is therefore the git-gated re-deploy to an explicit
accepted SHA, which restores identity and build together:
`/opt/terminal/terminal-build.sh --target-sha <40-hex>`. Any rollback receipt naming
`.next.bak` is naming a moving, unnamed target.

The live reading and the `:874`/`:889-890`/`:894` anchors were independently taken on the
host by the concurrent TERMINAL-02 session and re-verified here before recording; the
`:838` purge sits in `deploy_generation_reset`, one call below `deploy_generation_commit`,
and the `.absent` second record is the leg that reading added.
