# Prophet US Completed-Session and Source-Bound Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore valid pre-close US Prophet origination by scoring one completed-session panel and make the ranked board atomic with every derived Prophet publication.

**Architecture:** `build_site` captures one UTC observation timestamp and passes its completed-session cutoff into residual alpha and the stock-library producer. Live and Arena origination validate against that timestamp. The narrow checkpoint becomes the sole atomic publisher of `us_standouts.json` plus Prophet outputs, while R2, accepted-source restore, and the broad final commit enforce the same source/projection boundary.

**Tech Stack:** Python 3.12, pandas, pytest, Bash, Git, GitHub Actions YAML.

**Spec:** `docs/superpowers/specs/2026-09-15-prophet-us-completed-session-source-bound-design.md`

## Global Constraints

- Preserve the existing mixed-vintage refusal and all chronology fail-closed behavior.
- Preserve plan identity, ranking, admission, geometry, scoring weights, and trade authority.
- Use `lib.nyse_calendar.expected_last_session` as the existing completed-session authority.
- Keep crypto on its continuous calendar and retain raw provisional reach in receipts.
- Keep correction ledgers input-only and outside the output manifest.
- Do not retry or mutate the cancelled China recovery operation in this plan.
- One useful capability per PR: this plan owns the US producer and source-bound publication repair only.
- Production acceptance requires a real nightly-path result after merge; tests and merge establish only `BUILT_NOT_PROVEN`.

---

### Task 1: Completed-session scoring plane

**Files:**
- Modify: `scripts/build_site.py`
- Modify: `scripts/build_stock_library.py`
- Test: `tests/test_us_completed_session_panel.py`

**Interfaces:**
- Produces: `_normalise_us_equity_universe(uni, now) -> (clipped, panel_reach, clock_receipt)`.
- Produces: `_clip_daily_to_completed_session(values, completed_session)`.
- Consumes: `lib.nyse_calendar.expected_last_session(observed_at_utc)`.
- [ ] **Step 1: Run the completed-session tests and preserve the observed RED/GREEN evidence**

Run:
```bash
python -m pytest -q tests/test_us_completed_session_panel.py
```
Expected after implementation: all tests pass; before implementation the missing normalizer and clock wiring fail.

- [ ] **Step 2: Normalize every equity input before scoring**

Implement the minimal producer behavior:
```python
observed = now or datetime.now(timezone.utc)
completed = nyse_calendar.expected_last_session(observed)
clipped_close = close.loc[pd.to_datetime(close.index).normalize() <= pd.Timestamp(completed)]
```
Apply it to the benchmark, universe close/high series, and per-name OHLC before extension, dispersion, technical, signal, entry, and ranking consumers. Exempt configured crypto tickers.

- [ ] **Step 3: Bind residual alpha and staleness to the same clock**

Pass `asof=completed.isoformat()` to `build_alpha_data`, pass `now=observed` to the stock-library build, and write `observed_at_utc`, `expected_session`, and the completed-session normalization receipt into board staleness.

- [ ] **Step 4: Re-run the focused producer tests**

Run:
```bash
python -m pytest -q tests/test_us_completed_session_panel.py tests/test_csp_w5_board_staleness.py tests/test_extension.py
```
Expected: PASS, including genuine completed-session tear refusal.

### Task 2: Timestamp-aware live and Arena clocks

**Files:**
- Modify: `engine/prophet_bridge.py`
- Modify: `engine/prophet_arena.py`
- Test: `tests/test_prophet_bridge.py`
- Test: `tests/test_prophet_arena_clock_parity.py`

**Interfaces:**
- Consumes: `staleness.observed_at_utc` from Task 1.
- Produces: timestamp-aware `_resolve_origination_clocks` with date-only replay compatibility.
- [ ] **Step 1: Preserve failing timestamp scenarios**

Tests must distinguish:
```python
preclose = "2026-09-15T15:09:00+00:00"  # accepts 2026-09-14
postclose = "2026-09-15T22:00:00+00:00" # rejects 2026-09-14
```
Live and Arena must return identical clock errors and plan IDs.

- [ ] **Step 2: Implement timestamp-aware validation**

When `recorded_asof` includes a time, parse it and call `expected_last_session(observed)`. Otherwise retain `last_session_on_or_before(date)` for historical and fixture compatibility. Live and Arena both pass `staleness.observed_at_utc or asof`.

- [ ] **Step 3: Verify clock parity**

Run:
```bash
python -m pytest -q tests/test_prophet_bridge.py tests/test_prophet_arena_clock_parity.py
```
Expected: PASS with no live/Arena divergence.

### Task 3: Atomic source-board checkpoint

**Files:**
- Modify: `scripts/ci/daily_engine_prophet_nightly.sh`
- Modify: `scripts/ci/daily_engine_prophet_checkpoint.sh`
- Modify: `.github/workflows/daily.yml`
- Modify: `scripts/ci/daily_engine_commit_outputs.sh`
- Test: `tests/test_prophet_durable_checkpoint.py`

**Interfaces:**
- Consumes: exact frozen `site/factordata/us_standouts.json` bytes.
- Produces: one delta manifest and guarded commit containing source board plus derived Prophet outputs.

- [ ] **Step 1: Update workflow-contract tests before production scripts**

Update the stale split-R2 step names, add the unconditional tombstone as its own asserted step, and extend the source-bound test to require the board in checkpoint, R2, accepted-source, and broad-commit fences. Add the board to the accepted-source fixture.

- [ ] **Step 2: Verify RED is specific to missing source fences**

Run:
```bash
python -m pytest -q tests/test_prophet_durable_checkpoint.py
```
Expected before production edits: failures name the absent board path in checkpoint and broad-commit proof blocks; stale step-name failures are gone.
- [ ] **Step 3: Complete every source/projection fence**

Add `site/factordata/us_standouts.json` to:
```text
PROTECTED_PROPHET_PATHS
checkpoint manifest case allowlist
post-push current-main diff proof
R2 shell and embedded-Python current-main proofs
accepted-source checkout/diff/reset
final broad-commit checkout/reset refusal fence
```
Do not broad-add or broad-clean `data/prophet`; preserve correction ledgers.

- [ ] **Step 4: Verify the atomic publication contract**

Run:
```bash
python -m pytest -q tests/test_prophet_durable_checkpoint.py
bash -n scripts/ci/daily_engine_prophet_nightly.sh
bash -n scripts/ci/daily_engine_prophet_checkpoint.sh
bash -n scripts/ci/daily_engine_commit_outputs.sh
python -c 'import yaml; yaml.safe_load(open(".github/workflows/daily.yml"))'
```
Expected: all pass.

### Task 4: Regression, review, and immutable candidate

**Files:**
- Review all files changed by Tasks 1–3.
- Create no unrelated refactor.

- [ ] **Step 1: Run the bounded regression suite**

Run:
```bash
python -m pytest -q tests/test_us_completed_session_panel.py tests/test_prophet_bridge.py tests/test_prophet_arena_clock_parity.py tests/test_prophet_durable_checkpoint.py tests/test_csp_w5_board_staleness.py tests/test_extension.py tests/test_us_board_fail_closed_freshness.py tests/test_workflow_file_size.py
```

- [ ] **Step 2: Inspect authority and collision boundaries**

Fetch current `origin/main`, compare movement against all owned paths, inspect PR #7161 without modifying it, and run an integrated merge-tree proof. Any owned-path or governing-source movement requires re-review before publishing.

- [ ] **Step 3: Commit one bounded candidate**

Stage only the spec, plan, implementation, and discriminating tests. Commit with:
```bash
git commit -m "fix(prophet): score completed US sessions and bind source board"
```

- [ ] **Step 4: Publish and prove the exact head**

Push the existing branch, create or update its PR, confirm required CI/security checks on the exact head, and classify the capability `BUILT_NOT_PROVEN` until a real nightly run proves coherent source, non-mixed completed-session scoring, and lawful origination.

- [ ] **Step 5: Reconcile China separately**

Read the cancelled run `35019907027`, current main China artifacts, R2 freshness, and landed commits. Never retry until the original carrier’s effects are known. Record the exact remaining China recovery action without mixing it into the US PR.