# Sector Rotation Daily-Control RPH-1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the frozen eleven-sector daily-price control that separates rank memory, subsequent return persistence, dispersion/correlation and phase-complete 1D/2D/3D MACD outcomes without creating trading authority.

**Architecture:** Extend the existing `research/rotation_persistence` surface with one pure research module and one CLI. The loader binds exact parquet bytes and produces a complete common-session panel; deterministic metric functions return strict JSON-ready structures; the CLI writes only to research-safe output paths. Existing RPH-0 and Temporal Grain carriers remain untouched.

**Tech Stack:** Python 3.12+, pandas, NumPy, PyArrow, pytest, existing `scripts.research.rotation_persistence.contracts` strict JSON utilities.

**Spec:** `research/rotation_persistence/LEADERSHIP_PERSISTENCE_SECTOR_CONTROL_RPH1_PREREGISTRATION_2026-09-12.md`

## Global Constraints

- Parent exact head is `8d198b42f6bff491a49b1f3467b56ca4bb673f80`; this is a stacked Draft/HOLD child, not a rewrite of PR #7064.
- No network access, production writer, new regime/state/event/membership plane, product page, rank/gate/size/trade authority or Prophet/Oracle mutation.
- Read only `data/yahoo/{XLB,XLC,XLE,XLF,XLI,XLK,XLP,XLRE,XLU,XLV,XLY,SPY}.parquet`; bind byte SHA-256 and never fill missing observations.
- Test all 2D and 3D phase anchors, discard incomplete tail bars and require 100 completed bars before a MACD cross is eligible.
- All outputs are deterministic except an explicitly injected `produced_at`; strict JSON rejects NaN and Infinity.

---

### Task 1: Freeze the outcome-blind contract

**Files:**
- Create: `research/rotation_persistence/LEADERSHIP_PERSISTENCE_SECTOR_CONTROL_RPH1_PREREGISTRATION_2026-09-12.md`
- Create: `docs/superpowers/plans/2026-09-12-sector-rotation-daily-control-rph1.md`

**Interfaces:**
- Consumes: accepted RPH-0 boundary and the prior uploaded protocol.
- Produces: immutable operation identity, estimands, windows, phase rules, output contract and authority ceiling.

- [ ] Commit both files before running or inspecting any RPH-1 outcome.
- [ ] Record the exact commit SHA as the preregistration freeze.

### Task 2: Establish RED contracts and hosted execution ownership

**Files:**
- Create: `tests/test_rotation_persistence_sector_control.py`
- Create: `tests/test_rotation_persistence_sector_cli.py`
- Modify: `.github/ci/legacy-jobs.yml` inside the existing `research-price-panel` logical job.

**Interfaces:**
- Consumes: functions declared below from the not-yet-created module.
- Produces: discriminating failures for data normalization, rank/return separation, completed phase bars, MACD warm-up, future-only marks, authority and output boundaries.

- [ ] Write tests importing `scripts.research.rotation_persistence.sector_control` and `scripts.research.run_sector_control_rph1` before either file exists.
- [ ] Add an explicit pytest step naming both suites to the existing `research-price-panel` job.
- [ ] Open a Draft/HOLD stacked pull request against `sol/rotation-persistence-rph0-20260910`.
- [ ] Observe the exact hosted RED caused by the missing implementation, not by an unrelated syntax or collection defect.
- [ ] Preserve the RED run/job identity in the pull-request record.

### Task 3: Implement the minimal deterministic research engine

**Files:**
- Create: `scripts/research/rotation_persistence/sector_control.py`
- Create: `scripts/research/run_sector_control_rph1.py`

**Interfaces:**
- Produces:
  - `load_price_panel(data_dir: Path, symbols: tuple[str, ...] = ALL_SYMBOLS) -> tuple[pd.DataFrame, dict]`
  - `aggregate_completed_bars(panel: pd.DataFrame, sessions: int, phase: int) -> pd.DataFrame`
  - `leadership_surface(panel: pd.DataFrame, lookback: int, horizons: tuple[int, ...]) -> dict`
  - `dispersion_control(panel: pd.DataFrame) -> dict`
  - `correlation_control(panel: pd.DataFrame, window: int = 20) -> dict`
  - `macd_control(panel: pd.DataFrame) -> tuple[dict, dict]`
  - `build_result(panel: pd.DataFrame, receipt: dict, produced_at: str) -> dict`
  - `render_markdown(result: dict) -> str`

- [ ] Implement byte hashing, stable duplicate-date handling, finite positive close validation and exact complete-case intersection.
- [ ] Implement 5D and 21D rank/predictive/top-three surfaces with the four frozen windows and eight-observation floor.
- [ ] Implement daily return dispersion and trailing-20 average pairwise correlation.
- [ ] Implement positional completed bars for 1D/2D/3D and every phase; discard incomplete tails.
- [ ] Implement standard 12/26/9 histogram crosses with the 100-completed-bar eligibility floor.
- [ ] Implement future close and SPY-relative marks at 1/3/5/10 daily sessions and the predeclared phase hierarchy.
- [ ] Implement strict result composition, bounded Markdown and research-safe atomic output.
- [ ] Run the focused suites and retain the first GREEN result.

### Task 4: Execute the frozen real archive and preserve the result

**Files:**
- Create after the first real run: `research/rotation_persistence/sector_control_rph1/result.json`
- Create after the first real run: `research/rotation_persistence/sector_control_rph1/report.md`
- Extend: `tests/test_rotation_persistence_sector_cli.py`

**Interfaces:**
- Consumes: exact twelve repository parquet files at the immutable RPH-1 result head.
- Produces: source-pinned strict JSON and a bounded human report.

- [ ] Run the CLI in hosted CI with `produced_at=2026-09-12T21:00:00Z` into a temporary directory and emit an artifact/log receipt.
- [ ] Verify all twelve file hashes, common-panel coverage, actual last date and every phase's completed-bar count.
- [ ] Preserve the exact generated JSON and Markdown without hand-editing numerical fields.
- [ ] Add a regeneration test that reproduces both committed files byte-for-byte from the same source bytes and injected clock.
- [ ] Re-run focused tests and the real-data generation step on the exact result head.

### Task 5: Adversarial verification and durable handoff

**Files:**
- Create: `research/rotation_persistence/sector_control_rph1/verification.json`
- Create or update: `agentos/handoffs/LEADERSHIP-PERSISTENCE-INTELLIGENCE-2026-09-12-RPH1.md`
- Modify: `agentos/workstreams/WS-LEADERSHIP-PERSISTENCE-INTELLIGENCE.md`

**Interfaces:**
- Consumes: immutable result head, hosted jobs and current default-branch compatibility evidence.
- Produces: exact-head capability classification, limitations and next dependency.

- [ ] Kill at least these false greens: forward-fill a missing date; retain an incomplete 3D tail; allow a cross before 100 bars; use a non-future outcome; permit rank/trade authority.
- [ ] Compare candidate-owned paths against current `main` and classify integration/review reuse without rewriting the RPH-0 parent.
- [ ] Record hosted focused-suite status separately from inherited unrelated aggregate reds.
- [ ] Keep the pull request Draft/HOLD; do not mark Ready, merge, deploy or connect a product consumer.
- [ ] Leave the exact next action at the Temporal Grain evidence gate for lower-grain identity and utility/latency diagnosis.
