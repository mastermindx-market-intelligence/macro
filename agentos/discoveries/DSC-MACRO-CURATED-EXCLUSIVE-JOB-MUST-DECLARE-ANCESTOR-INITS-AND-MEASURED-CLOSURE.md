---
key: MACRO-CURATED-EXCLUSIVE-JOB-MUST-DECLARE-ANCESTOR-INITS-AND-MEASURED-CLOSURE
claim: >
  A new `scope: exclusive` job in Macro `.github/ci/legacy-jobs.yml` goes red on
  `test_ancestor_init_census_does_not_grow` unless its `paths:` names every ancestor
  package `__init__.py` its tests import (engine/codex_lane, engine/signal_foundry,
  lib/dataos, scripts, tests for a job that reads `scripts/build_sector_central.py`), and
  red on `test_curated_exclusive_scopes_cover_their_own_import_closure` whenever the
  import closure of a file it reads grows on `main` (e.g. `lib/shared_shell.py` and
  `lib/site_assets.py` after a rebase), because exclusive scope replaces inference and a
  closure file with no matching pattern is a job that silently stops running.
falsifier: >
  Add an exclusive job whose `paths:` omit an imported ancestor `__init__.py` or a
  closure file and watch `python3 -m pytest tests/test_ci_pack.py -k "ancestor_init_census
  or curated_exclusive_scopes_cover"` pass.
so_what: >
  Before pushing a lane branch that adds a legacy job, measure with
  `scripts.run_ci_pack.ancestor_init_census` and
  `curated_exclusive_closure_findings(Path(".github/ci/legacy-jobs.yml"))` (closure
  misses must be 0) and re-measure after every rebase onto `main`; widening `paths:` is
  always the safe direction. A guarded `if str(ROOT) not in sys.path: sys.path.insert`
  in a `scripts/build_*.py` entry script is not a pin for
  `test_unpinned_entry_scripts_only_shrink`; the insert must be unconditional.
kind: constraint
verified_at: 2026-10-21
verified_by: >
  Macro PRs #9991 and #9992 (Options R1 W2B / W2A): ci-pack-0/1 red on the census
  (349 rows vs the 344 ceiling, five undeclared inits per job), ci-pack-3 red on the
  script pin, closure test red after rebasing onto `origin/main` (2 misses per job);
  all green locally after declaring the paths and making the pin unconditional
  (closure misses 0; `tests/test_check_script_import_pinning.py` 11 passed).
scope:
  - macro
  - .github/ci/legacy-jobs.yml
  - scripts/run_ci_pack.py
  - tests/test_ci_pack.py
  - WS:OPTIONS-R1
confidence: verified
---

The census and closure tests are the same functions `scripts/check_contract_delta.py`
runs on the head side of a PR, so a local measurement predicts the gate exactly.
