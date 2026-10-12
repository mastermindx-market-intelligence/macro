---
key: PYTEST-EXPLAINS-A-FAILED-NOT-IN-OVER-A-LONG-STRING-WITH-A-SUPERLINEAR-DIFF
claim: >-
  When `assert needle not in haystack` fails under pytest's assertion rewriting, pytest
  explains it with `_pytest.assertion.util._notin_text`. That function diffs the haystack
  against a copy with the needle removed, and the cost grows superlinearly with length.
  Measured on a one-line `json.dumps` of a composed Finance read model (148,514 characters),
  one failing test took 130.8 s under `pytest -q` when written as
  `assert "zz_planted" not in json.dumps(document)`. The same failure written as a bare
  boolean took 4.1 s. Called alone, `_notin_text` took 0.09 s at 32,000 characters and
  18.4 s at 148,514. Six such failures in one parametrized leak test held a core at 100 %
  CPU with no output until the run was killed at nine minutes. That reads as a hang, not a
  failure.
falsifier: >-
  Write one test that composes `_default_8slice_inputs()` from
  tests/test_finance_intelligence_projection.py, with a key planted in rights_snapshot
  (whose family names are published in generation.rights_profile, so the assertion fails),
  and asserts `"zz_planted" not in json.dumps(document, default=str)`. Write a twin that
  asserts `not leaked` on a precomputed bool. The claim is false if the two runs under
  `pytest -q` take about the same time.
so_what: >-
  Assert a bare boolean whenever the haystack is large. For example, write
  `leaked = needle in blob` and then `assert not leaked, <short label>`. The rewriter then
  explains a plain name, and a failure costs nothing. In CI, a few failing `not in`
  assertions over large blobs can run a pack to its timeout instead of failing fast, and
  that reads as runner trouble. When a local pytest run sits at 100 % CPU with no progress,
  suspect the explanation of a failure, not the code under test. Running the same steps as
  a plain script is the discriminating probe.
kind: runtime
verified_at: 2026-09-28
verified_by: "seat measurement, pytest on Python 3.14: twin tests over one composed document, not-in form 130.84 s vs bool form 4.11 s (both 1 failed); _notin_text alone at 2,000 / 8,000 / 32,000 / 148,514 characters took 0.00 / 0.01 / 0.09 / 18.44 s (the call returns a generator, so it must be consumed with list() to measure)"
scope:
  - macro
  - tests/
confidence: verified
---
