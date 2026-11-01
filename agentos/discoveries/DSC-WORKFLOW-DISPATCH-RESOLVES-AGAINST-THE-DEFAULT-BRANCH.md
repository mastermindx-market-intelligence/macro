---
key: WORKFLOW-DISPATCH-RESOLVES-AGAINST-THE-DEFAULT-BRANCH
claim: >
  `gh workflow run <file> --ref <branch>` (REST `POST /repos/{owner}/{repo}/actions/workflows/
  {file}/dispatches`) resolves the WORKFLOW FILE against the repository's default branch, not
  against `--ref`. A `workflow_dispatch` workflow that exists only on a feature branch answers
  HTTP 404 ("workflow not found") for every `--ref`, including the branch that carries it; the
  same command succeeds the moment the file is on `main` (seat-measured 2026-10-11: the dispatch
  of `.github/workflows/deploy-alpaca-secrets.yml` from PR #8838's branch returned 404 at 17:1xZ,
  and the identical dispatch returned run 38162037064 at 18:01:03Z, two minutes after the
  sweeper merged #8838 to main at 17:58:30Z). `--ref` only selects which commit's copy of an
  ALREADY-REGISTERED workflow runs.
falsifier: >
  A `gh workflow run <file> --ref <feature-branch>` that creates a run while `git ls-tree
  origin/main -- .github/workflows/<file>` is empty. GitHub documents the inverse ("the
  workflow must exist on the default branch to be dispatched"), so a success there would mean
  the platform changed the rule.
so_what: >
  A dispatch-only operational workflow (secret delivery, one-shot deploy helpers, manual
  proofs) cannot be smoke-tested from its own PR: ship it as its own small PR, merge it, and
  only then dispatch — never block a dependent production step on "dispatch from the branch
  first". For the Market-Intelligence program this is why the VPS Alpaca refresh (DEC:VPS-
  ALPACA-PAIR-REFRESHED-FROM-REPO-SECRETS-BY-DISPATCH-WORKFLOW) waited on the #8838 merge
  rather than running from the PR head. The authority-path freeze on `.github/workflows/**`
  still applies to that merge, so a dispatch-only workflow's PR owes a covering main proof like
  any other authority edit.
kind: constraint
scope: [macro, .github/workflows/**]
confidence: verified
verified_at: 2026-10-11
verified_by: >
  seat fd47d431: `gh workflow run deploy-alpaca-secrets.yml --ref claude/mi-alpaca-secret-sync-20261011`
  -> HTTP 404 while the file was absent from origin/main (`git ls-tree origin/main --
  .github/workflows/deploy-alpaca-secrets.yml` empty); after the sweeper merged #8838
  (0a47364446e6, 17:58:30Z) `gh workflow run deploy-alpaca-secrets.yml --ref main -f
  restart_press_feeds=false` -> run 38162037064 (18:01:03Z), concluded success 18:03Z.
affects:
  - WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
  - .github/workflows/deploy-alpaca-secrets.yml
---

Operational corollary: when a dispatch-only workflow must deliver something a production step
depends on, the merge of its PR IS the first production step — plan the wave with that
dependency explicit, and arm/merge that PR before the step that needs the run.
