---
key: CI-AUTHORITY-MERGE-QUEUE-PILOT-IS-A-STANDING-INACTIVE-CONTEXT
claim: >
  The check context ci-authority/codex/merge-queue-pilot reports FAILURE on
  every open pull request by design and is excluded by name as
  CI_AUTHORITY_INACTIVE_CONTEXT by the sweeper and the metabolism mergers, so it
  is never evidence that a head is red.
falsifier: >
  Read .github/workflows/ci-authority.yml:12 and scripts/merge_on_green.py:656
  (CI_AUTHORITY_INACTIVE_CONTEXT); or list check-runs on any open PR and find
  the context concluding success, or find a sweeper merge refused solely on it.
so_what: >
  When gating a body edit, a ready, or a manual merge on "fail == []", exclude
  this context by name alongside "Workers Builds: macro"; never re-run it,
  never wait on it, never file it as a red to heal.
kind: runtime
verified_at: 2026-10-02
verified_by: >
  gh api check-runs on 20/20 open PRs (all FAILURE on this context, 2026-10-02
  13:4xZ); .github/workflows/ci-authority.yml:12; scripts/merge_on_green.py:656;
  scripts/metabolism_merge.py:173; scripts/metabolism_immune.py:586.
scope:
  - macro
  - .github/workflows/ci-authority.yml
  - scripts/merge_on_green.py
  - scripts/metabolism_merge.py
  - scripts/metabolism_immune.py
confidence: verified
---

Measured 2026-10-02: a seat's body-edit gate keyed on `fail == []` blocked on this context
alone for #8278/#8280/#8279 until the context was excluded by name; the sweeper had already
been excluding it.
