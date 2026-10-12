---
key: CI-RUN-BLOCK-COMMENT-QUOTE-BLINDS-CLOSURE-INFERENCE
claim: >
  One apostrophe (or unbalanced double quote) in a TRAILING inline `#` comment,
  or anywhere on a command line, of a .github/ci/legacy-jobs.yml `run:` block
  still makes that job's closure un-derivable. That is deliberate and
  fail-closed. A FULL-LINE comment (first non-blank character `#`) no longer
  does. scripts/ci_scope_dependencies.py pytest_invocation_ambiguities now drops
  full-line comment lines before shlex.split(comments=False, posix=True). Before
  that repair, one apostrophe in any comment line made the function return
  ('unparseable pytest invocation: No closing quotation',), and the job lost its
  inferred import closure. For a curated exclusive job that was loud:
  tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure
  raised "<job> derives no closure — curation cannot be checked"
  (scripts/run_ci_pack.py:1729, and check_contract_delta.py:595). Measured on
  PR #8114. For a non-exclusive job, or one step of several, the loss was silent,
  and for an inline-comment quote it still is.
falsifier: >
  python3 -c "from scripts.ci_scope_dependencies import pytest_invocation_ambiguities as f; print(f('python3 -m pytest tests/test_x.py  '+chr(35)+' the planner'+chr(39)+'s token'))"
  printing () instead of ('unparseable pytest invocation: No closing quotation',)
  would mean inline comments are stripped too. Also a falsifier: the full-line
  form
  python3 -c "from scripts.ci_scope_dependencies import pytest_invocation_ambiguities as f; print(f(chr(35)+' the planner'+chr(39)+'s token'+chr(10)+'python3 -m pytest tests/test_x.py'))"
  printing that ambiguity instead of ().
so_what: >
  Write run-block prose on its own comment line. There apostrophes are safe.
  Never write a quote in a comment after a command on the same line, because
  that still blinds the job's closure. When a curated exclusive job suddenly
  "derives no closure", grep its command lines and trailing comments for an
  unbalanced quote before suspecting its paths list. The fast probe takes about
  90 s, against about 9 minutes for test_ci_pack.py:
  python3 -c "from pathlib import Path; from scripts.run_ci_pack import curated_exclusive_closure_findings as f; print(f(Path('.github/ci/legacy-jobs.yml')))"
  prints {} on a healthy manifest. Do not switch the tokenizer to
  comments=True, because shlex then also ends a word at a mid-word # and
  truncates ${VAR#pattern}. Do not widen the strip to inline comments. The tests
  in tests/test_ci_pack.py pin both. The p0b block's "Keep apostrophes out of
  this block" warning is now stricter than needed but still right for its
  command lines, so leave it.
kind: landmine
verified_at: 2026-09-28
verified_by: >
  scripts/ci_scope_dependencies.py pytest_invocation_ambiguities (the full-line
  comment strip just before its shlex.split call). Pinned by
  tests/test_ci_pack.py::test_full_line_comment_apostrophe_resolves_the_comment_free_targets
  (both a top-level and an indented comment; a positive control proves each
  fixture still breaks a whole-block shlex; the commented job derives exactly
  the comment-free job's infer_job_scopes scope),
  ::test_run_block_quote_outside_a_full_line_comment_still_fails_closed,
  ::test_a_comment_that_names_pytest_is_not_the_invocation, and
  ::test_comment_stripping_keeps_a_mid_word_hash_expansion_whole. An in-memory
  mutation probe showed that reverting the strip, comments=True,
  dropping every line containing #, stripping only column-0 comments, and also
  cutting inline comments each fail at least one of them. Both falsifier
  one-liners print as the claim says on the repaired tree.
  curated_exclusive_closure_findings(Path('.github/ci/legacy-jobs.yml')) returns {}.
scope: [macro, ".github/ci/legacy-jobs.yml", "scripts/ci_scope_dependencies.py", "scripts/run_ci_pack.py"]
confidence: verified
---

# A quote in a `run:`-block comment blinds closure inference

The CI planner infers which files each legacy job depends on by reading the
job's `run:` text and resolving its pytest targets. `pytest_invocation_ambiguities`
tokenizes the block with `shlex.split(..., comments=False, posix=True)`. With
comments disabled, a shell comment is just more words, so an apostrophe in
"planner's" opened a string that never closed. The tokenizer gave up, and the job
was marked ambiguous.

That failure was loud only when it blinded an entire **curated exclusive** job,
because the curation test then refuses to check a closure it cannot derive.
Anywhere else it was quiet: a non-exclusive job, or one step among several,
simply lost its inferred closure, and nothing reported it.

## The repair, and what it deliberately leaves

The tokenizer now drops every line whose first non-blank character is `#`
before calling shlex. Full-line comments are therefore safe to write in plain
English, including indented ones inside `if` blocks.

Two tempting "complete" fixes are wrong:

- `comments=True` makes shlex end a word at a mid-word `#` as well. It would
  cut `${PYTEST_TARGET#./}` to `${PYTEST_TARGET` and silently drop the rest of
  that line, including any pytest target after it.
- Stripping trailing inline comments needs a shell-grade parser to tell a
  comment from a `#` inside a word or a quoted string. A quote in an inline
  comment is rare, and leaving it ambiguous fails closed: the job runs
  unscoped instead of being mis-scoped.

The p0b block's original author wrote "planner exact" with no apostrophe, most
likely on purpose, and the block still carries a "Keep apostrophes out of this
block" warning. That warning is now stricter than it needs to be for full-line
comments, but it remains correct for command lines and inline comments.

## One live job changed scope: self-mod-fence

Comments were also read as argv, so a comment naming `pytest` could be taken as
the invocation. `self-mod-fence`'s agent-os step opens with "the pytest suite
skips itself / when agentos/ is outside a sparse cone". That made `agentos/` a
directory target, so the job was unscoped and ran on every PR by accident. Its
own `paths:` comments show the authors believed it was scoped. Across the whole
manifest the repair changes exactly this one job: 185 → 186 of 237 jobs scoped,
with 1113 owned plus 153 fallback paths (measured by running `infer_job_scopes`
under the old and the new tokenizer).

Its two always-on duties stay always-on, because `.github/workflows/fences.yml`
has no paths filter. On every PR it runs the live self-mod fence and the
whole-store `python3 scripts/agentos.py validate`, and it publishes the
`self-mod-fence` context. A PR touching only brand-new agentos records now
skips the legacy job's pytest suites (`test_agentos_{schema,status,compile}`)
until a main proof runs them. The validator still gates it.

Scoping the job also exposed a gap that its always-on status had hidden.
`tests/test_ci_pack.py::test_derived_scopes_are_startable_by_the_ci_workflow`
audits only scoped jobs, and the job's declared `.cursor/rules/**` (the
continuation law's fourth surface) had no `ci.yml` trigger.
`scope_pattern_is_startable` in `scripts/run_ci_pack.py` accepts a glob scope
only through its own entry or an ancestor subtree entry. It never lets the
`"**"` catch-all stand in, which is why `engine/**`, `.claude/**` and the other
roots each carry their own entry. The same repair added `.cursor/rules/**` to
`ci.yml`'s `on.pull_request.paths`. When a job goes
from unscoped to scoped, run that test: it audits only scoped jobs, so an
unscoped job's declared paths are never checked.
