---
key: CI-RUN-BLOCK-COMMENT-QUOTE-BLINDS-CLOSURE-INFERENCE
claim: >
  One apostrophe (or unbalanced double quote) inside a `#` comment in a
  .github/ci/legacy-jobs.yml `run:` block makes that job's closure
  un-derivable. The cause is scripts/ci_scope_dependencies.py:959:
  pytest_invocation_ambiguities tokenizes the whole multi-line run text with
  shlex.split(comments=False, posix=True) before it looks for pytest. With
  comments off, the comment's quote is an unterminated string. The function
  returns ('unparseable pytest invocation: No closing quotation',), and the job
  loses its inferred import closure. For a curated exclusive job this is loud:
  tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure
  raises "ValueError: <job> derives no closure — curation cannot be checked"
  (scripts/run_ci_pack.py:1729). scripts/check_contract_delta.py:595 fails with
  the same text. Measured on PR #8114, where the only manifest change was a new
  flag plus a comment containing "planner's". For a non-exclusive job, or for
  one step of several, the loss is silent.
falsifier: >
  python3 -c "from scripts.ci_scope_dependencies import pytest_invocation_ambiguities as f; print(f(chr(35)+' the planner'+chr(39)+'s token'+chr(10)+'python3 -m pytest tests/test_x.py'))"
  printing () instead of ('unparseable pytest invocation: No closing quotation',).
  That would happen if the tokenizer began stripping full-line shell comments
  before shlex. Also a falsifier: a curated exclusive job with an apostrophe in a
  run-block comment whose closure curated_exclusive_closure_findings still
  derives.
so_what: >
  Keep ' and stray " out of comments inside legacy-jobs `run:` blocks; say
  "the planner token", not "the planner's token". When a curated exclusive job
  suddenly "derives no closure", grep its run text for an unbalanced quote
  before suspecting its paths list. The fast probe takes about 90 s, against
  about 9 minutes for test_ci_pack.py:
  python3 -c "from pathlib import Path; from scripts.run_ci_pack import curated_exclusive_closure_findings as f; print(f(Path('.github/ci/legacy-jobs.yml')))"
  prints {} on a healthy manifest. Do not "fix" this by switching to
  comments=True. shlex then treats a mid-word # as a comment too, which would
  truncate ${VAR#pattern} expansions that bash reads as one word. The safe
  repair strips only lines whose first non-blank character is #.
kind: landmine
verified_at: 2026-09-27
verified_by: >
  scripts/ci_scope_dependencies.py:952 (pytest_invocation_ambiguities) and :959
  (the shlex.split call). The falsifier one-liner above returns the ambiguity
  with the apostrophe and () without it, re-run 2026-09-28 on origin/main
  99e3e8100eb0. During PR #8114 the curated-closure test failed with
  "p0b-receipt-closure derives no closure" and passed after the comment was
  reworded; curated_exclusive_closure_findings(Path('.github/ci/legacy-jobs.yml'))
  returns {} on 99e3e8100eb0. For the comments=True caveat,
  shlex.split('echo ${x#y} z', comments=True) returns ['echo', '${x'], while
  comments=False returns ['echo', '${x#y}', 'z'].
scope: [macro, ".github/ci/legacy-jobs.yml", "scripts/ci_scope_dependencies.py", "scripts/run_ci_pack.py"]
confidence: verified
---

# A quote in a `run:`-block comment blinds closure inference

The CI planner infers which files each legacy job depends on by reading the
job's `run:` text and resolving its pytest targets. `pytest_invocation_ambiguities`
tokenizes the whole block with `shlex.split(..., comments=False, posix=True)`.
With comments disabled, a shell comment is just more words. An apostrophe in
"planner's" therefore opens a string that never closes. The tokenizer gives up,
and the job is marked ambiguous.

The failure is loud only when it blinds an entire **curated exclusive** job. The
curation test then refuses to check a closure it cannot derive. Anywhere else it
is quiet: a non-exclusive job, or one step among several, simply loses its
inferred closure, and nothing reports it.

The original author of the p0b step had written "planner exact" with no
apostrophe, most likely on purpose. The p0b block now carries a comment saying
"Keep apostrophes out of this block". Other blocks carry no such warning.
