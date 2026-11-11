# Docs fast lane (narrative-only PRs)

Extension of the same `WS:CI-MERGE-CONTROL-PLANE` scoped-planner work as
[scoped pack compaction](CI_SCOPED_PACK_COMPACTION.md). This is a tier inside
`build_plan` (`scripts/run_ci_pack.py`), not a second planner, scheduler,
evidence store, release controller, or review gate.

## Behavior

A pull request whose every changed path is an **add/modify of `.md` under
`docs/`, `research/` or `agentos/`** may select **zero legacy jobs**: the plan
publishes twelve empty packs, `has_work: false`, `ci-pack` skips entirely, and
`ci-gate` publishes the affirmative proven-no-work success that
`merge_on_green.py` requires (absence of red is not a pass). `fences.yml`,
`ci-authority.yml` and `contract-delta` still run on the head, unchanged.

Why this exists (measured 2026-11-11): a one-file markdown edit (PR #10997)
still planned 7 jobs into 2 packs — one for the unscoped always-on jobs and one
because a hand-written scope declares `research/**/*.md` while its suite reads
no markdown. Compaction already avoids 10 of 12 packs; the fast lane removes
the other 2, the ~4-minute `infer_job_scopes` pass, and both hosted pack
runners. The remaining floor for a docs PR is `contract-delta` (~9–10 min),
which is outside the planner.

## The two halves

1. **Trusted-base classifier** — `scripts/ci_docs_tier.py`, executed by
   `ci-plan` from a checkout of the **default branch** (the ci-authority.yml
   shape: pinned action SHA, `ref: default_branch`, depth 1, sparse `scripts`,
   `persist-credentials: false`, parked under `runner.temp`). A candidate merge
   tree never judges itself: a PR cannot edit the tier rules it benefits from.
   The classifier reads only real git objects — the exact tested merge tree and
   its first parent — plus the BASE tree's manifest. It never fails the job:
   any trouble publishes `docs_tier: false` and exits 0.
2. **Planner binding** — `build_plan(..., docs_tier_verdict=...)`; admission
   lives in `docs_tier_eligible` and every arm fails closed to the incumbent
   scoped selection (see `tests/test_ci_pack_docs_tier.py`, which pins each arm
   by plan-hash equality with the no-verdict plan).

## Fail-closed arms (all refuse the tier)

- No verdict file, unreadable, oversize (>65,536 bytes), non-object, wrong
  `schema`, `docs_tier` false or missing — including the classifier's own
  `classifier-error:` token.
- Any status other than **A/M** in the diff: delete, rename, copy, typechange,
  unresolved. Renames are refused before the both-sides path expansion.
- Any path that is not `.md` under `docs/`, `research/` or `agentos/` (root
  `README.md`, `engine/notes/x.md`, `.json`, `.markdown` all refuse).
- A path in the classifier's `CONSUMED_MARKDOWN` (files suites read as data:
  `HOUSE_LAW_CI_GUARD_SUITE.md`, `INTELLIGENCE_REGISTRY.md`) or any literal
  `.md` path a job declares in the base manifest's `paths`/`scope` rows.
- Base manifest unreadable, or no YAML reader in the classifier's interpreter.
- Binding mismatch: verdict `base_sha`/`merge_sha` must equal the planner's
  `changed_from`/`tested_tree_sha`, and `paths_sha256`/`paths_count` must match
  the planner's own resolved changed-file list (order-sensitive digest — the
  classifier's `changed_paths_digest` is byte-identical to
  `run_ci_pack.changed_files_digest`).
- Planner-side: role `main`, scope mode `shadow`/`off`, empty/absent diff, any
  global invalidator in the diff (workflow, script, config, packaging), or a
  manifest delta.

## Adding a suite that reads markdown

If a new suite starts reading a specific markdown file as data, add that file
to `CONSUMED_MARKDOWN` (with the consumer named in a comment) or declare it as
a literal `paths:` row in `.github/ci/legacy-jobs.yml` — literal manifest rows
are picked up automatically. `tests/test_ci_docs_tier.py` re-pins the curated
set; that list is the one hand-maintained fail-closed surface.

## Residuals

- Suites that construct markdown paths dynamically (not literal, not curated)
  could in principle read a tier-eligible file; none were found when the lane
  shipped (grep census, 2026-11-11). `contract-delta` still censuses the whole
  repo on every PR and remains the backstop for content-level drift.
- The classifier's scope-inference skip applies only inside the tier; every
  other plan pays inference as before.
