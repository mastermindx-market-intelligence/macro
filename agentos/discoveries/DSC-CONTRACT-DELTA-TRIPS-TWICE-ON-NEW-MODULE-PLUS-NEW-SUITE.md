---
key: CONTRACT-DELTA-TRIPS-TWICE-ON-NEW-MODULE-PLUS-NEW-SUITE
claim: >
  `scripts/check_contract_delta.py` (the `contract-delta` check in ci.yml) has TWO
  independent red classes that a PR adding one new `engine/` module plus one new
  `tests/` suite trips in SEQUENCE, not at once: (a) the curated `scope: exclusive`
  jobs in `.github/ci/legacy-jobs.yml` whose inferred import closure gains the new
  module (Python imports transitively plus string literals naming tracked files) must
  declare it under `paths:`; (b) the unrun-suite gate (`scripts/audit_unrun_tests.py`
  logic) requires the new pytest suite to be named by a `run:` step of some workflow
  job, or by a reasoned row in `config/unrun_test_waivers.yml`. The checker reports
  class (a) first and surfaces class (b) only once (a) is clean, so a repair that only
  widens `paths:` goes red again on the next run. Measured on PR #8519 (2026-10-06):
  head 0a59999b red on (a); repair 7562fdcd widened three jobs and the local checker
  then reported `1 introduced` on (b); head 57f61d7f added `tests/test_leadership_receipt.py`
  to the `nw-lobe-unfreeze` job's `paths:` AND a `run: TZ=UTC python -m pytest
  tests/test_leadership_receipt.py -q` step, after which the checker read
  `0 introduced, 0 inherited`. A legacy job's `if: ${{ false }}` guard does not make
  the wiring hollow: `run_ci_pack.py` packs those jobs.
falsifier: >
  On a fresh branch off origin/main add an empty `engine/<new>.py` imported by a curated
  exclusive job's existing path and an empty `tests/test_<new>.py`, then run
  `python3 scripts/check_contract_delta.py --base origin/main` (about 195 s). If a single
  run reports BOTH the closure miss and the unrun-suite miss, the sequencing claim is
  false; if widening `paths:` alone makes the run exit 0, class (b) no longer exists.
so_what: >
  When a PR introduces a new module AND a new suite, repair both classes in ONE commit
  before the first CI round trip: widen `paths:` in every curated job the local checker
  names, and wire the suite into the `run:` of the job that owns the suite's subject
  (choose a job whose `paths:` already declare the suite's imports, e.g. one declaring
  `engine/` and `lib/`), then run the local checker to `0 introduced` before pushing.
  Each CI round trip here costs about 35-45 minutes of ci.yml plus a disarm/re-arm
  cycle on an armed PR; the local checker costs about 3 minutes.
kind: landmine
verified_at: 2026-10-06
verified_by: >
  PR #8519 heads 0a59999b (run 37430358222 red), 7562fdcd (local checker
  `1 introduced`, unrun-suite error), 57f61d7f (local checker `0 introduced, 0 inherited
  (base 1e3299d7b752)`); scripts/check_contract_delta.py; scripts/audit_unrun_tests.py
scope:
  - macro
  - .github/ci/legacy-jobs.yml
  - scripts/check_contract_delta.py
  - config/unrun_test_waivers.yml
confidence: verified
---

# contract-delta trips twice on a new module plus a new suite

The `contract-delta` check is differential (head minus base) and has two red
classes. It reports import-closure misses on curated `scope: exclusive` jobs first;
only a tree that is clean on that class reaches the unrun-suite gate. A PR adding
`engine/<module>.py` and `tests/test_<module>.py` therefore needs two repairs, and
a session that fixes only the first learns about the second from the next CI run.

Repair both in one commit, verified by the local checker
(`python3 scripts/check_contract_delta.py --base origin/main`, ~195 s) before pushing.
Pick the owning job for the `run:` step by what it already declares: the suite's
imports must be inside that job's `paths:`.
