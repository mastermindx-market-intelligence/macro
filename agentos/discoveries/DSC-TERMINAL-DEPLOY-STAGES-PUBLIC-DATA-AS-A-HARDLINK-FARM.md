---
key: TERMINAL-DEPLOY-STAGES-PUBLIC-DATA-AS-A-HARDLINK-FARM
claim: >
  The Terminal release path excludes terminal/public/data from both of its rsyncs and
  instead hardlink-copies the LIVE data directory into the build stage (`cp -al`). Staged
  and live data files therefore share inodes, so served market data sits outside the deploy
  generation transaction in both directions: a code deploy cannot change it, and an in-place
  write from the staged build would change it immediately, before any swap or health gate.
falsifier: >
  Read ops/terminal-build.sh: if either release rsync (:1098-1099, :1234-1236) stopped
  excluding 'public/data', or :1106 used `cp -a`/`rsync` rather than `cp -al`, the coupling
  described here would not exist. Empirically: during a build, `stat -c %h` on a live
  terminal/public/data/*.json returns 2 (two links) rather than 1. Conversely, adding a
  build-time writer that opens a file under public/data with mode 'w' and observing the LIVE
  file change before the .next swap would confirm the write-through.
so_what: >
  Three operational consequences. (1) A code revert needs no data revert, and a rollback
  receipt should not claim to restore market data. (2) A build overlapping the nightly holds
  pre-stamp bytes in the stage that never propagate, because the final rsync excludes the
  path -- so the two lanes do not corrupt each other. (3) Any build-time writer into
  public/data MUST write tmp + os.replace, never in place: the path exclusion alone does NOT
  protect live data, because the hardlink bypasses it. Exactly one build step writes there
  today (terminal/package.json `prebuild` -> scripts/build_data_coverage.py), and its
  write_atomic docstring names this hazard. A future non-atomic writer would silently mutate
  served data on every deploy with no transaction covering it.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  Read at mastermind-terminal origin/master d28449368: ops/terminal-build.sh:1098-1099
  (build rsync, --exclude='public/data'), :1106 (cp -al hardlink stage), :1234-1236 (final
  overlay rsync, same exclusion); scripts/build_data_coverage.py:27-33 and :78-89
  (write_atomic, which documents the hardlink write-through by name); terminal/package.json
  prebuild. Independently surfaced by the concurrent TERMINAL-01 session while establishing
  that a code revert needs no data revert.
scope: mastermind-terminal release path and nightly data lane
confidence: verified
---

## Why the exclusion alone is not the safety property

It is tempting to read the two `--exclude='public/data'` flags as the whole story and
conclude the release path "structurally cannot touch served data". That is very nearly true
and the conclusion drawn from it is correct, but the mechanism is weaker than it looks: the
exclusions only stop the stage from propagating *back*. The `cp -al` at `:1106` points the
staged tree at the **same inodes** as the live tree, so a staged build that truncates a file
in place has already written to production before any rsync, swap or health check runs.

What actually holds the invariant is write discipline at the one place that writes there.
`scripts/build_data_coverage.py` is run by `prebuild`, and its `write_atomic` exists for
exactly this reason — `os.replace` installs a new inode in the same directory and leaves the
other link untouched. Its docstring says so outright.

So the correct statement is conditional: the release path cannot touch served data **so long
as every build-time writer into `public/data` replaces rather than mutates.** That is a
property of the writers, not of the deploy script, and nothing enforces it mechanically —
which is what makes it a landmine rather than a design note.

## Relationship to the deploy generation transaction

`deploy_generation_begin/commit/rollback` cover `.next` and `.deployment-id` only. Market
data is deliberately outside that transaction, which is why the revert story is clean: see
[[DEC:TERMINAL-05-RETARGETED-OFF-THE-PINNED-CARRIER]] for the rollback anchor, where the same
separation is what makes a git-gated re-deploy a complete restore of everything the
transaction owns.
