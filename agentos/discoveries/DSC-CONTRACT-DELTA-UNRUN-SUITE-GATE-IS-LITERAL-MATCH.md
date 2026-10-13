---
key: CONTRACT-DELTA-UNRUN-SUITE-GATE-IS-LITERAL-MATCH
claim: >
  `scripts/audit_unrun_tests.py` (whose `gated_unrun_suites` drives the
  `contract-delta` check in `scripts/check_contract_delta.py`) treats a new
  `tests/*.py` suite as "named by a run step" ONLY when the suite's full
  repo-relative path appears as a LITERAL substring of a workflow `run:`
  step's text — with a basename fallback only when that basename is
  unambiguous across the suite census. No glob, wildcard, or pattern form of
  reference counts as naming.
falsifier: >
  Add a suite `tests/test_probe_xyz.py` and reference it in a run step ONLY
  via a glob (e.g. `python -m pytest tests/test_probe_*.py`), then run
  `python3 -c "from scripts.audit_unrun_tests import _named_by_a_run_step,
  _workflow_blob; print(_named_by_a_run_step('tests/test_probe_xyz.py',
  _workflow_blob(), frozenset()))"` — if it prints True, or
  `python3 scripts/check_contract_delta.py --base origin/main` exits clean
  with the glob as the only reference, the literal-match claim is false.
so_what: >
  Every new test file must be listed LITERALLY, in the SAME PR that adds it,
  inside the `run:` step of the job that owns its subject — a glob reference
  leaves contract-delta red regardless of how fresh or green the base is.
  Corollary: eight same-night lane PRs each editing the shared
  `engine-render-guards` list need staggered anchors (see
  DEC:FIF-PER-PR-CI-WIRING-STAGGERED-ANCHORS) because every one of them is a
  literal-line insertion into the same folded scalar.
kind: constraint
verified_at: 2026-10-12
verified_by: >
  scripts/audit_unrun_tests.py:591-607 — _named_by_a_run_step(): `if rel in
  blob: return True` then basename fallback guarded by the ambiguity set;
  scripts/audit_unrun_tests.py:432-473 — _workflow_blob(): YAML-parsed
  concatenation of `run:` scalars (and `with:` values) ONLY, never comments;
  scripts/check_contract_delta.py:203,262 — contract-delta imports and gates
  on gated_unrun_suites. Adjacent but distinct facts already recorded:
  DSC:CONTRACT-DELTA-TRIPS-TWICE-ON-NEW-MODULE-PLUS-NEW-SUITE (the two red
  classes' SEQUENCING) and DSC:FINANCE-T8-SUITES-LANDED-UNWIRED-OVER-A-RED-CONTRACT-DELTA
  (a merged-while-red incident); this record is the naming MECHANISM itself.
scope:
  - macro
  - scripts/audit_unrun_tests.py
  - scripts/check_contract_delta.py
  - .github/ci/legacy-jobs.yml
  - .github/workflows/
confidence: verified
---

# The unrun-suite gate is a literal substring match, not a pattern match

`_named_by_a_run_step` is one `in` test against a blob built only from
`run:` scalars (comments deliberately excluded — a suite named in a YAML
comment historically read as covered). The basename fallback exists for
steps that cd into a directory, and is disabled whenever two suites share a
basename (measured: `test_price_ladder.py` lives in both `tests/` and
`research/prophet_us_audit/`). So the audit's coverage vocabulary is exactly
"the path (or unambiguous basename) appears as text in a run step" — a glob
like `tests/test_foo_*.py` is invisible to it, which both keeps the gate
strict (you cannot satisfy it with a pattern that would silently widen) and
forces literal-line wiring (which is why same-night multi-PR wiring needs
staggered anchors to merge cleanly).
