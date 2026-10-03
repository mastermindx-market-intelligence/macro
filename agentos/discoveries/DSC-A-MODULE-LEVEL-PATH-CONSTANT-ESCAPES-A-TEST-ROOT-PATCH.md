---
key: A-MODULE-LEVEL-PATH-CONSTANT-ESCAPES-A-TEST-ROOT-PATCH
claim: >
  A module-level `Path` constant derived from a repo-root variable is frozen at IMPORT
  time, so a test that redirects the root variable does not redirect the constant, and the
  code under test writes into the REAL checkout. Measured 2026-09-18 in
  `scripts/import_equitydesk_full.py`: `tests/test_import_equitydesk.py` patches
  `imp._REPO_ROOT = tmp_path` but a newly added
  `TRANSPORT_EARNINGS_HISTORY_PATH = _REPO_ROOT / "data" / "earnings_calls" /
  "history.parquet"` still pointed at the worktree, so one `pytest` run wrote a
  21KB fixture-derived parquet into it. The run reported `8 passed`. It was invisible in
  `git status` because `data/earnings_calls/` is gitignored — and in a SPARSE worktree the
  same write also creates a `data/` husk where the real tree was deliberately omitted,
  which is the documented truncation trap. The existing sibling constants were safe only
  because the test patches each of them BY NAME (`SEED_DIR`, `MANIFEST_PATH`,
  `EARNINGS_RECONCILIATION_PATH`); any constant added later inherits none of that.
falsifier: >
  `python3 -m pytest tests/test_prophet_earnings_source_restore.py::test_the_importer_writes_nothing_outside_the_root_it_was_given`
  passing against a module that re-freezes the transport path at import time. Or, directly:
  run the importer suite and check `ls data/earnings_calls/` in the checkout afterwards.
so_what: >
  In any module whose tests redirect a root by reassigning a module attribute, derive
  every path from that root INSIDE a function, not at module scope — `def
  transport_earnings_history_path(): return _REPO_ROOT / ...`. When adding a new output
  path to a script that already has patched-by-name constants, assume the test harness
  will NOT patch yours. And when auditing whether a test suite leaks writes, `git status`
  is the wrong instrument: it is blind to exactly the directories most likely to be
  written (caches, data stores, transport staging), because those are the ones that are
  gitignored. Check the filesystem, and prefer a test that asserts containment
  (`path.is_relative_to(root)`) over one that asserts the happy path.
kind: landmine
verified_at: 2026-09-18
verified_by: >
  direct observation — `ls -la data/earnings_calls/` showed `history.parquet` (21094 B)
  after a green `tests/test_import_equitydesk.py` run in a sparse worktree that has no
  `data/` tree at all; clean after moving the derivation into a call-time function; PR #7294
scope:
  - mastermindx-market-intelligence/macro
  - scripts/import_equitydesk_full.py
  - tests/test_import_equitydesk.py
confidence: verified
---
