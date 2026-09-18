# Options Matrix Coherent Session Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent the scheduled options-matrix lane from publishing zero-cell payloads when ThetaData OI advances one session ahead of Greeks/EOD during the daily refresh.

**Architecture:** Add one canonical narrow resolver for the latest session shared by OI and positive-spot Greeks. Use it in both `build_matrix(asof=None)` and the launchd freshness gate so scheduling and production logic agree. Preserve explicit `--date` behavior and the existing OI[t-1] / OI[t-2] calculation.

**Tech Stack:** Python 3.12, pandas, pyarrow parquet, pytest, POSIX shell, launchd.

**Spec:** `ops/launchd/run_options_matrix.sh` OI timing law and the production M1 incident evidence from September 17–18, 2026.

## Global Constraints

- The latest OI date alone is not a publishable matrix session.
- A coherent session requires OI rows and at least one finite positive `underlying_price` in Greeks for the same root/date.
- The resolver must use projected parquet columns and must not load complete chain history merely for freshness.
- Explicit `build_matrix(..., asof="YYYY-MM-DD")` semantics remain unchanged.
- No new lifecycle, store, scheduler, or publication authority is introduced.

---

### Task 1: Reproduce the partial-tier incident

**Files:**
- Modify: `tests/test_options_matrix.py`
- Test: `tests/test_options_matrix.py`

**Interfaces:**
- Consumes: `engine.options_matrix.build_matrix(root, store, asof=None)`.
- Produces: A regression test proving automatic as-of selection ignores a newer OI-only date.

- [x] **Step 1: Write the failing test**

Create a temporary SPY store with OI on `2026-07-07` and `2026-07-08`, but Greeks and EOD only on `2026-07-07`. Call `build_matrix(..., asof=None)` and assert `payload["_build_meta"]["asof_date"] == "2026-07-07"` and `payload["cells"]` is non-empty.

- [x] **Step 2: Verify RED**

Run: `python -m pytest tests/test_options_matrix.py::test_auto_asof_uses_latest_coherent_oi_greeks_session -q`

Observed: FAIL because current code selected `2026-07-08` from OI alone and returned `spot unavailable on 2026-07-08`.

### Task 2: Add the canonical coherent-session resolver

**Files:**
- Modify: `engine/thetadata_store.py`
- Modify: `engine/options_matrix.py`
- Test: `tests/test_options_matrix.py`
- Test: `tests/test_thetadata_store.py`

**Interfaces:**
- Produces: `latest_options_matrix_session(root: str, store: str | Path | None = None) -> str | None`.
- Consumes: projected `date` from OI and projected `date, underlying_price` from Greeks.

- [x] **Step 1: Implement the narrow resolver**

Scan shared OI/Greeks year shards newest-first. Normalize dates, retain finite positive Greeks spot rows, and return the maximum common ISO session date. Return `None` on absent, malformed, or unmatched data.

- [x] **Step 2: Use it for automatic matrix as-of**

When `asof is None`, call the resolver before loading the selected OI and Greeks session. Return a conforming null payload with reason `no coherent OI/Greeks session in store` only when the resolver returns `None`.

- [x] **Step 3: Verify GREEN**

Run: `python -m pytest tests/test_options_matrix.py::test_auto_asof_uses_latest_coherent_oi_greeks_session tests/test_thetadata_store.py::test_latest_options_matrix_session_requires_shared_positive_spot -q`

Observed: PASS.

### Task 3: Make the launchd gate use the same truth

**Files:**
- Modify: `ops/launchd/run_options_matrix.sh`
- Create: `tests/test_options_matrix_runtime_guard.py`

**Interfaces:**
- Consumes: `engine.thetadata_store.latest_options_matrix_session`.
- Produces: A freshness gate that compares the coherent SPY session to the existing required settled-session floor.

- [x] **Step 1: Write the failing source-contract test**

Assert the runner imports and calls `latest_options_matrix_session`, and no longer decides freshness by reading only the SPY OI date column.

- [x] **Step 2: Verify RED**

Run: `python -m pytest tests/test_options_matrix_runtime_guard.py -q`

Observed: FAIL because the runner gated on OI alone.

- [x] **Step 3: Replace the OI-only gate**

Keep `required = last_session_on_or_before(expected - timedelta(days=1))`, but compare it with the canonical coherent session. Emit `fresh` only when the coherent date exists and is at least `required`.

- [x] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_options_matrix_runtime_guard.py -q`

Observed: PASS.

### Task 4: Verify, publish, and prove the live repair

**Files:**
- Verify only: changed files and operational receipts.

- [x] **Step 1: Run targeted regression suites**

Run: `python -m pytest tests/test_options_matrix.py tests/test_options_matrix_runtime_guard.py tests/test_thetadata_store.py -q`

Observed: 84 passed.

- [x] **Step 2: Run shell syntax validation**

Run: `/bin/sh -n ops/launchd/run_options_matrix.sh`

Observed: PASS.

- [x] **Step 3: Review the diff and commit**

Commit only the coherent-session implementation, tests, runner update, and this plan.

- [ ] **Step 4: Push a branch and open the PR**

Use branch `sol/options-matrix-coherent-session-20260918`; record immutable head SHA and PR URL.

- [ ] **Step 5: After accepted merge, update the M1 operational clone and run one live publish**

Require launchd exit code 0, nonzero cells for SPY/QQQ/IWM, coherent `_build_meta.asof_date`, and successful R2 uploads. Do not overwrite live operational source from an unmerged candidate.
