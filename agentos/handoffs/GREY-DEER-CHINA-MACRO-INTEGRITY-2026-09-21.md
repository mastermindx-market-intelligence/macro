---
workstream: WS:GREY-DEER-RISK-INTELLIGENCE
session: claude/china-breadth-current-coverage-20260921-sol
model: sol
ended_because: ci_handoff
mission: Repair China macro input integrity and interpretation without manufacturing risk probabilities or duplicating the existing radar programme.
state_before: China breadth accepted historical-only coverage and could publish an older computed row after accepting a newer partial batch.
changed:
  - path: collectors/china_breadth.py
    what: Bind coverage to configured names, valid latest prices and sufficient moving-average history; reject dropped latest rows before cache writes.
  - path: tests/test_china_breadth_coverage.py
    what: Exercise the real fetch, inherited calculation, runner, stored output and existing regional summary reader.
  - path: .github/ci/legacy-jobs.yml
    what: Include the new suite and its existing yfinance dependency in the existing China breadth CI job.
verified:
  - claim: The original implementation failed the nine initial negative cases while two valid controls passed.
    command: python -m pytest tests/test_china_breadth_coverage.py -q --tb=short
    result: Initial RED 9 failed / 2 passed; expanded edge RED 2 failed / 13 passed.
  - claim: The repaired producer and adjacent collector/heatmap suites pass.
    command: python -m pytest tests/test_china_breadth_coverage.py tests/test_china_board_breadth.py tests/test_market_heatmap.py tests/test_breadth_constituents_repair.py tests/test_breadth_split_seam.py -q
    result: 84 passed; one inherited pandas Timestamp.utcnow deprecation warning.
  - claim: An existing stored close matrix retains identical breadth math on valid inputs.
    command: python research/grey_deer/china_breadth_coverage_20260921/real_input_probe.py --source /Users/chriswong/Documents/Cluade/macro-main/data/china_search/closes.parquet
    result: 1270 rows; 76 of 82 configured names present; 75 latest and MA-eligible names; exact output equality. Artifact ends 2026-09-04, not a current-production proof.
unverified:
  - claim: Hosted CI, independent review, merge and production collector deployment.
    what_would_verify: Exact-head checks/review followed by the normal production owner and actual run/status/artifact receipts.
  - claim: The 94 screenshot value or its predictive calibration is corrected.
    what_would_verify: Reconcile PR 6989, its original custody, same-input source clocks, current consumer compatibility and independently reviewed calibration/authority evidence.
unresolved:
  - Whole-frame session age remains with the existing runner/freshness owner; this change does not invent a venue calendar or certify current data from a build timestamp.
  - Shared radar arithmetic/calibration repairs remain on PR 6989 at d775a6c40c9f12c8411cd87100ac7dbfcd664870, Draft/HOLD; this branch is not a replacement.
  - China template writers 7481, 7485 and 7383 overlap; action-board writer 7567 is independent. None is overwritten or released here.
  - No admitted independent reviewer or Executive worker START has been proven in this session.
next_actions:
  - Finish current-head source/CI review and release the bounded breadth producer repair through its own PR; no admin or immediate auto-merge over pending checks.
  - Reconcile the original PR 6989 custody and obtain a new lawful independent review; do not retry its terminal empty review or denied result inspection.
  - Complete per-input clocks and coverage disclosure through existing freshness/health owners, then same-input numeric replay.
  - Reconcile the China template writers before adding participation versus change, relative versus absolute returns, mainland versus offshore scope and coherent horizon-aware copy.
do_not_redo:
  - Do not lower the displayed risk score by judgment or replace old calibration with the tiny live sample.
  - Do not rebuild PR 6989's already tested composition/reference/cohort/authority/adapter repairs.
  - Preserve merged China freshness 7156 and renderer 7463; do not claim merge alone is live proof.
  - Never interpret the stored-input canary's 2026-09-04 endpoint as the current market session.
  - Never modify the shared macro-main checkout, foreign worktrees, production data or historical risk ledgers in this repair.
danger_areas:
  - The inherited breadth calculation can drop partial newest rows; checking fetch coverage alone is insufficient.
  - Current quotes without enough valid history cannot support a representative moving-average breadth denominator.
  - This is curated large-cap breadth, not all A-shares; no all-boats inference follows.
  - Initial all-open-PR GraphQL census failed; only bounded relevant filename/source checks were completed, not an exhaustive 403-PR census.
---

## Current commission and source identity
Chairman explicitly directed Sol to take over and improve china.html on 2026-09-21.
Mission remains incomplete. This is a working implementation checkpoint, not acceptance.
Protected Skillpack: Mastermind@3e66e43258f34db240d5bff76f54148c7af84ee4, v1.0.1/bootstrap1.
Macro acquisition: cf2aae0beefb3e7dbb15e4ec672d8c288492dd13. Current pre-commit check:
fbdd7ae4e3db10868be4f86bef4edd067e478cb3; only unrelated CI hunks moved among checked dependencies.
