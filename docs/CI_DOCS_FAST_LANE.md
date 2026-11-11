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

1. **Trusted-base classifier** — `scripts/ci_docs_tier.py`. `ci-plan` runs
   the **default branch's** copy, read as a git object (`git fetch origin
   refs/heads/<default>` then `git show FETCH_HEAD:scripts/ci_docs_tier.py`
   into `RUNNER_TEMP`). There is no second checkout: `actions/checkout`
   refuses a path outside the workspace, and a nested checkout inside it would
   dirty the untracked-path inventory the planner binds. The fetch adds objects
   only; the candidate tree and index are untouched. A failed fetch, missing
   file, crash or absent verdict writes `docs_tier: false`, exits 0, and the
   planner runs normal scoped selection (never 0 jobs). The classifier reads
   only git objects: the exact tested merge, its first parent, and the BASE
   tree's manifest and code.
2. **Planner binding** — `build_plan(..., docs_tier_verdict=...)`; admission
   lives in `docs_tier_eligible` and every arm fails closed to the incumbent
   scoped selection (see `tests/test_ci_pack_docs_tier.py`, which pins each arm
   by plan-hash equality with the no-verdict plan).

## What "trusted base" does and does not protect

On `pull_request`, `ci.yml` itself and `scripts/run_ci_pack.py` come from the
**candidate head**. A PR that edits them could skip the classifier anyway (and
such a PR is not docs-only, so it never reaches the tier). Running the
default-branch classifier therefore guards against **honest mistakes** in a
PR's own classifier edit and keeps a docs PR from judging itself with rules it
just changed. It is not a security boundary against a hostile PR. That
boundary remains `ci-authority.yml` and `fences.yml`, which run from protected
code on every head.

## Fail-closed arms (all refuse the tier)

- No verdict file, unreadable, oversize (>65,536 bytes), non-object, wrong
  `schema`, `docs_tier` false or missing — including the classifier's own
  `classifier-error:` token.
- Any status other than **A/M** in the diff: delete, rename, copy, typechange,
  unresolved. Renames are refused before the both-sides path expansion.
- Any path that is not `.md` under `docs/`, `research/` or `agentos/` (root
  `README.md`, `engine/notes/x.md`, `.json`, `.markdown` all refuse).
- Any path **code reads**. The classifier derives this set at classify time
  from the BASE tree (never the candidate's files): it scans every
  first-party `*.py` blob, plus shell/JS/TS, the Makefile and `.github/`
  files, and claims
  - literal paths (`ROOT / "docs/RESTORE_RUNBOOK.md"`, `Path(..., "agentos",
    "workstreams", "WS-X.md")`, `os.path.join(...)`, plain strings);
  - any `*.md` basename named in a string (`DOCS / "RUNBOOK.md"`, even when
    `DOCS` cannot be resolved statically);
  - every directory a `glob`/`rglob`/`iterdir`/`os.walk`/`os.listdir`/
    `os.scandir`/`glob.glob` call enumerates under a root, when its pattern can
    yield `.md` (`research/winners/cases/*.md`, `research/` via
    `rglob("*.md")`), and the directory of a computed `<dir> / f"{x}.md"`;
  - the subtree of every Python file that itself lives under a root.
  Measured on the base this PR targets: of 6,706 narrative `.md` files, 163
  (all under `docs/`) remain eligible; `research/` and `agentos/` are
  enumerated by code and therefore always refuse. An over-claim costs a docs PR
  its fast lane; an under-claim would let a suite go unrun, so the scan errs
  wide. The scan only runs after every cheap check passes (~45 s on a full
  base).
- Plus the curated `CONSUMED_MARKDOWN` and any literal `.md` path a job
  declares in the base manifest's `paths`/`scope` rows.
- Consumer scan failure (unparseable base module, unreadable blob, git error).
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

Nothing to register for ordinary readers: a literal path, a basename, or a
glob/rglob/iterdir over a narrative directory is derived automatically from
the base tree. Only a reader the scanner cannot see (a path assembled from
values computed at run time, with no `.md` literal and no traversal of a
narrative directory) needs a `CONSUMED_MARKDOWN` entry or a literal `paths:`
row in `.github/ci/legacy-jobs.yml`. The guard test
`test_every_narrative_markdown_named_in_first_party_code_is_covered` reds if
the scanner stops claiming a literal reader.

## Residuals

- A reader whose path is fully computed at run time (no `.md` literal, no
  traversal of a narrative directory) is invisible to the static scan.
  `contract-delta` still censuses the whole repo on every PR and remains the
  backstop for content-level drift.
- The classifier's scope-inference skip applies only inside the tier; every
  other plan pays inference as before.
