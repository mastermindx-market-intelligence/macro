---
key: RELEASE-PREFLIGHT-PINS-PUBLIC-DATA-TREE
claim: >
  ops/terminal_source_audit.production.json pins the git TREE hash of
  terminal/public/data, so any charting-app PR that changes a served OHLC
  document reds the PROTECTED "Ingest + signal-layer tests" context until the
  pin is updated in the same PR — and the failure names only two opaque hashes,
  with nothing pointing at public/data or at the one-line fix.
falsifier: >
  Change any terminal/public/data/*.json, leave ops/terminal_source_audit.production.json
  alone, and observe
  tests/test_terminal_release_preflight.py::test_production_policy_is_complete_narrow_and_tree_pinned
  pass.
so_what: >
  Re-pin in the SAME PR that moves the data — this is the gate working, never
  weaken or skip it. Get the value with `git rev-parse HEAD:terminal/public/data`.
  Critically, run `PR_NUMBER=<n> python3 -m pytest tests/ -q` from the repo root
  before pushing any data change: the Terminal's own `npx vitest run` is fully
  green while this is broken, because the pin lives in the PYTHON suite. The same
  policy also pins canonical_git_blob for terminal/.env.example and
  ingest/hk_universe_cache.json, so those have the same shape.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  charting-app PR #772, which published session_anchor onto 33 OHLC documents and
  moved the tree b427e879f0e47c2fa9a78909ecbf6717893b16af ->
  6c4e397331dab962510c5e3b18d5d8b1cbd145bf; CI red was reproduced locally with
  `PR_NUMBER=772 python3 -m pytest tests/ -q` and fixed by re-pinning in the same
  PR (1269 passed / 8 skipped). Assertion at
  tests/test_terminal_release_preflight.py:289-290.
scope:
  - charting-app
  - ops/terminal_source_audit.production.json
  - tests/test_terminal_release_preflight.py
  - WS:TERMINAL-GITHUB-CANONICAL-DEPLOYMENT
confidence: verified
---

**The pin is evaluated at the ACCEPTED SHA, not at your branch tip** — but that does
not make it a hazard for whoever deploys next, because two mechanisms catch it first:
the "Ingest + signal-layer tests" job runs a bare `actions/checkout@v4` with no `ref:`
override (ci.yml:297), so on a pull_request event it checks out `refs/pull/N/merge` —
master already merged with the branch — and branch protection is `strict: true`, which
forces a stale branch to update and regenerate that merge ref. An interleaving
data-touching merge therefore reds the PR and blocks auto-merge, before any accepted
SHA exists.

That reasoning is circular for the cases where protection itself is bypassed, so a
pre-deploy check remains worth two commands: compare `git rev-parse <sha>:terminal/public/data`
against the pin inside `git show <sha>:ops/terminal_source_audit.production.json`.
Note that some workflows in this repo DO pin `ref: github.event.pull_request.head.sha`
(f11-thesis-postgres-canary.yml:39, f12-tenancy-postgres-canary.yml:36) — if that
override is ever added to the python job, the assertion moves back onto the branch tip
and this protection silently disappears.
