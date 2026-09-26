# Terminal Tactical R1-A implementation plan

> For agentic workers: execute tasks in this file with the executing-plans workflow and test-first development.

**Goal:** Turn the approved extended-hours hypothesis into a measured, reproducible existing-owner research result rather than another coverage report.
**Architecture:** Existing Terminal D0 clock/parser feeds a pure Radar-owned feature module; one research consumer computes fixed preregistered comparisons. Existing TrialLedger records the full grid. No production event/replay/calibration owner changes.
**Tech stack:** Python standard library, installed numpy/pandas/pytest; no provider or new dependency.
**Spec:** research/species/TTI_R1A_PREREG.md; research/species/tti_r1/config.json.

## Task 1: Freeze first
- Commit the immutable prereg/config and log all 84 cells through TrialLedger.log_grid(family='entry_radar') before outcome computation; verify append-only prefix and save the grid hash.

## Task 2: Pure feature and outcome primitives
Files: engine/entry_radar/tactical_research.py; tests/test_tactical_research.py.
Interfaces: segment_features(frame) -> dict; select_arms(feature_row) -> tuple[str,...]; first_touch(frame,entry,atr) -> str; fixed_outcome(stock,benchmark,entry_epoch,end_epoch,beta,atr,expected_epochs) -> dict.
- Write tests proving absent implementation fails.
- Implement exactly the preregistered formulas with explicit null/censoring and no network/clock/filesystem.
- Test strict bar cutoff, no future mutation, sample-vs-time weighting, monotone/oscillating paths, same-bar touch ambiguity, empty/constant data and benchmark missingness.

## Task 3: Real offline consumer
Files: scripts/research/terminal_tactical_r1_study.py; tests/test_tactical_research_cli.py.
- CLI accepts --input-dir, --manifest, --terminal-root, --output-dir, and --register-only. Verify fixed config, Terminal source and input fingerprints before any feature/outcome read.
- Preserve source inputs; create-only output directory. Registration uses the existing ledger; regular execution must find the exact full grid already present and the committed prereg/config bytes unchanged.
- Build prior-only daily baselines and exact scheduled-session chains. Emit panel metadata, all 84 aggregate rows, primary comparisons and source/censor counts; never emit a live alert.
- Test actual subprocess, date filtering, missing source/benchmark, existing output refusal, phase cutoff and no secret requirement.

## Task 4: Execute once and adjudicate
- Run focused tests and imported first-party suites; do not run all Macro tests in a sparse tree.
- Run the frozen recipe on original D0 private inputs, inspect outcome denominators and complete negative results.
- Publish aggregate report with source, grid, input and output hashes. No threshold tuning after seeing results.
- Push one research PR, update the existing Agent OS continuity carrier and leave exact independent-review/current-data/prospective gates visible.
