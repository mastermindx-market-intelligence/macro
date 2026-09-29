---
key: A-DATA-GATED-JOB-IS-DARK-ON-EVERY-PULL-REQUEST
claim: >
  A `gate: data` job in `.github/ci/legacy-jobs.yml` cannot block a merge, and a
  registry that claims otherwise is not contradicted by anything: `lane:` in
  `config/house_law_checks.yml` is unvalidated prose. `ci.yml` is the only
  pack workflow with a `pull_request` trigger and it plans `--gate code` at three
  sites, so `load_legacy_jobs(gate="code")` filters the 238-job manifest to 166
  before any path decision — a `gate: data` job appears in NEITHER the eligible
  nor the skipped list of a PR plan. `--gate data` is planned only by
  `data-health.yml`, whose triggers are `workflow_run` / `workflow_dispatch` /
  `schedule`. Measured 2026-09-28: the `house-law-registry` job carried
  `gate: data`, so pass B's census — whose own finding text reads "add an entry
  in config/house_law_checks.yml before merging" — never ran on a pull request,
  and TEN `scripts/check_*.py` files sat unregistered in a green `origin/main`
  (run 36409416568, head 5296f07aa70d, all 12 packs green). The same measurement
  over the whole registry found 27 more rows claiming `lane: pr_ci` on a
  `gate: data` job, across 26 laws and 17 distinct jobs.
falsifier: >
  Run the planner the way ci.yml does and look for the job in BOTH lists:
  `python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --gate code
  --plan-only --changed-from origin/main`. A job absent from the eligible list AND
  from the skipped list was filtered by gate, not by scope — that is the signature.
  To disprove the general claim, find a workflow with a `pull_request` trigger whose
  text contains `--gate data`:
  `grep -l -- "--gate data" .github/workflows/*.yml` then read each file's `on:` keys.
  To disprove a specific row, show its named job with `gate: code` in the manifest.
  Note what does NOT falsify it: the job's `if: ${{ false }}` is the file's
  convention (238 of 238 jobs carry it, because `run_ci_pack.py` executes these
  definitions inside `ci-pack-*` rather than GitHub scheduling them directly), and
  a `--plan-only` run with NO `--gate` flag shows the job ELIGIBLE, which is the
  answer to a question ci.yml never asks.
so_what: >
  Never read a registry `lane:` field as evidence that a law is enforced on pull
  requests — resolve the named job in `.github/ci/legacy-jobs.yml` and read its
  `gate:`. Pass C proves only that the named job's `run:` bodies INVOKE the
  script; no pass validates the lane, so a false `lane: pr_ci` is invisible to the
  meta-guard by construction. When a guard must block a merge, its home must be a
  `gate: code` job, and moving a law there is a second home rather than a
  relocation when the existing job genuinely reads committed `data/` (the
  house-law job does, via tests/test_dataos_security_master.py). The 27 measured
  dark rows are ratcheted in
  `tests/test_house_law_registry.py::TestLanePrCiIsNotSelfEvident` — a new one
  reds with the law named — and the generalization is that any "is this enforced?"
  question in this repo is answered by the gate, never by a label.
kind: landmine
verified_at: 2026-09-28
verified_by: >
  `python3 -m pytest tests/test_house_law_registry.py -q` reproduced the ten HARD
  CENSUS findings against a worktree off fresh origin/main (5 failed, 4 passed);
  the ten names confirmed present in origin/main via `git ls-tree`. ci.yml passes
  `--gate code` at .github/workflows/ci.yml:4679, :5020, :5043; a
  `load_legacy_jobs(gate="code")` call returns 165 of 237 jobs on main and
  `house-law-registry` is not among them. Trigger census: of the six workflows
  whose text contains `run_ci_pack`, only ci.yml has a `pull_request` trigger and
  only data-health.yml plans `--gate data`
  (pinned by TestCensusRunsInTheMergeGate::test_the_data_gate_is_never_reachable_from_a_pull_request).
  The 27-row population was measured by joining every `lane: pr_ci` row in
  config/house_law_checks.yml against the manifest's `gate:` field.
scope:
  - macro
  - .github/ci/legacy-jobs.yml
  - .github/workflows/ci.yml
  - config/house_law_checks.yml
  - scripts/run_ci_pack.py
  - any "is this law enforced on a PR?" question
confidence: verified
---

## The hypothesis this replaces was FALSIFIED by measurement

The natural explanation for the census going blind is a scope gap: the
`house-law-registry` job declares a `paths:` list naming four literal check
scripts and no `scripts/check_*.py` glob, while pass B globs that pattern AT
RUNTIME — a construct static inference cannot model. That hypothesis is wrong,
and a future session will form it again, so it is recorded here rather than
silently dropped.

`infer_job_scopes` already derives `scripts/**` and `scripts/**/*.py` for this
job and promotes them into the OWNED tier, because the job's commands perform
opaque filesystem traversal and opaque constructs widen to whole scan roots. An
empirical probe settled it: with a temporary commit adding
`scripts/check_zzz_scope_probe.py`, a `--plan-only --changed-from origin/main`
run with no `--gate` flag listed `house-law-registry` as ELIGIBLE. Scope
inference sees the new file fine. The gate filter, which runs first, is what
removes the job.

The glob was still added to the job's `paths:`, for a different and narrower
reason: inference's `scripts/**` coverage here is an accidental side effect of
opaque-traversal widening in this job's other commands, so a future narrowing of
the guard would silently remove it. Declaring the glob makes selection-by-a-new-
check-script a stated property instead of a lucky one, and
`_glob_to_regex`'s single `*` does not cross `/`, which correctly mirrors pass
B's own non-recursive runtime glob.

## Why this is the same blindness the job's comment already documented

The `house-law-registry` job's own comment records that its scope cannot see
repository-root `config.yml`. The repo carries three further independent
write-ups of the code/data gate split — `check_contract_delta.py`'s docstring,
the conviction-profile comment referencing #6023, and `data-health.yml`'s header
— so the mechanism was known four times over and still cost ten unregistered
guards. What was missing was not knowledge but a pin: nothing asserted that the
census executes in the gate whose name appears in its own finding text.
