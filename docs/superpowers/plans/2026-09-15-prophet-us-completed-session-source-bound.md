# Prophet US Completed-Session and Immutable-Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore valid pre-close US Prophet origination by scoring one completed-session panel and bind every Prophet index to immutable exact source bytes without taking ownership of the independently current customer board.

**Architecture:** `build_site` captures one UTC observation timestamp and passes its completed-session cutoff into residual alpha and the stock-library producer. Live and Arena origination validate against that timestamp. `scripts.build_prophet` writes a content-addressed source snapshot at `data/prophet/origination_sources/<raw_sha256>.json.gz`; the narrow checkpoint publishes that immutable provenance with Prophet outputs, while the live `us_standouts.json` board remains on its existing product publication paths.

**Tech Stack:** Python 3.12, pandas, pytest, Bash, Git, GitHub Actions YAML.

**Spec:** `docs/superpowers/specs/2026-09-15-prophet-us-completed-session-source-bound-design.md`

## Global Constraints

- Preserve the existing mixed-vintage refusal and chronology fail-closed behavior.
- Preserve plan identity, ranking, admission, geometry, scoring weights, and trade authority.
- Use `lib.nyse_calendar.expected_last_session` as the completed-session authority.
- Keep crypto on its continuous calendar and retain raw provisional reach in receipts.
- Keep the live `site/factordata/us_standouts.json` board independently current.
- Keep correction ledgers input-only and outside the output manifest.
- Extend the existing `data/prophet` provenance plane; create no parallel authority.
- Do not retry or mutate the cancelled China recovery operation in this plan.
- Production acceptance requires a real nightly-path result after merge; tests establish only `BUILT_NOT_PROVEN`.

---

### Task 1: Completed-session scoring plane

**Files:**
- Modify: `scripts/build_site.py`
- Modify: `scripts/build_stock_library.py`
- Modify: `engine/residual_alpha.py`
- Test: `tests/test_us_completed_session_panel.py`

**Interfaces:**
- Produces: `_normalise_us_equity_universe(uni, observed_at_utc)` returning clipped rows plus raw and completed-session receipts.
- Produces: `_clip_daily_to_completed_session(values, completed_session)`.
- Consumes: `lib.nyse_calendar.expected_last_session(observed_at_utc)`.

- [x] **Step 1: Write failing completed-session regressions**

Cover pre-close provisional rows, genuine completed-session tears, crypto continuity, benchmark clipping, and one timestamp shared between residual alpha and the stock library.

- [x] **Step 2: Normalize every equity input before scoring**

Apply the completed-session cutoff to benchmark, universe close/high series, and per-name OHLC before extension, dispersion, lottery, technical, signal, entry, and ranking consumers. Exempt configured crypto tickers.

- [x] **Step 3: Bind residual alpha and staleness to the same clock**

Pass the completed session to residual alpha, pass the exact observation timestamp to the stock-library build, and write `observed_at_utc`, `expected_session`, and the normalization receipt into board staleness.

- [x] **Step 4: Verify focused producer behavior**

Run:
```bash
python -m pytest -q tests/test_us_completed_session_panel.py
```
Expected: all scenarios pass, including genuine tear refusal.

### Task 2: Timestamp-aware live and Arena clocks

**Files:**
- Modify: `engine/prophet_bridge.py`
- Modify: `engine/prophet_arena.py`
- Test: `tests/test_prophet_bridge.py`
- Test: `tests/test_prophet_arena_clock_parity.py`

**Interfaces:**
- Consumes: `staleness.observed_at_utc` from Task 1.
- Produces: timestamp-aware `_resolve_origination_clocks` with date-only replay compatibility.

- [x] **Step 1: Write timestamp-discriminating tests**

Pin:
```python
preclose = "2026-09-15T15:09:00+00:00"   # accepts 2026-09-14
postclose = "2026-09-15T22:00:00+00:00"  # rejects 2026-09-14
```

- [x] **Step 2: Implement timestamp-aware validation**

When `recorded_asof` includes time, parse it and call `expected_last_session(observed)`. Otherwise retain `last_session_on_or_before(date)` for historical and fixture compatibility. Live and Arena pass `staleness.observed_at_utc or asof`.

- [x] **Step 3: Verify live/Arena parity**

Run:
```bash
python -m pytest -q tests/test_prophet_bridge.py tests/test_prophet_arena_clock_parity.py
```
Expected: identical clocks, errors, and plan identities.

### Task 3: Immutable source provenance

**Files:**
- Modify: `scripts/build_prophet.py`
- Modify: `scripts/ci/daily_engine_prophet_nightly.sh`
- Modify: `scripts/ci/daily_engine_prophet_checkpoint.sh`
- Modify: `.github/workflows/daily.yml`
- Modify: `scripts/ci/daily_engine_commit_outputs.sh`
- Test: `tests/test_prophet_bridge.py`
- Test: `tests/test_prophet_durable_checkpoint.py`

**Interfaces:**
- Consumes: exact frozen `site/factordata/us_standouts.json` bytes.
- Produces: `data/prophet/origination_sources/<sha256>.json.gz`.
- Produces index fields: `source_board_sha256`, `source_board_snapshot_path`, `source_board_snapshot_encoding`.
- Preserves: independently current live customer board.

- [x] **Step 1: Write red tests for the corrected ownership boundary**

Tests must fail while the mutable board is Prophet-owned, while hash/path linkage is absent, and while accepted-source restore overwrites a fresher live board.

- [x] **Step 2: Persist the exact source bytes content-addressably**

Implement `_freeze_origination_source_board` to:
- refuse symlinks;
- hash exact bytes with SHA-256;
- gzip exact bytes with `mtime=0`, while keying identity on the uncompressed SHA-256;
- write under `data/prophet/origination_sources/` using the raw SHA-256 as identity;
- be idempotent for identical decompressed bytes, including cross-platform gzip-header variation;
- fail closed with explicit domain errors on missing, unreadable, malformed, non-object, symlinked, or colliding inputs;
- publish through a randomized same-directory temp file so stale PID-derived temp names cannot block a later run;
- return the parsed document, hash, and repository-relative path.

- [x] **Step 3: Bind the index and zero-origin path**

Write the source hash/path into `site/prophet/index.json`. Extend both nightly snapshots with `data/prophet/origination_sources/*.json.gz`, and verify the durable snapshot before the no-new-plan return.

- [x] **Step 4: Fence only immutable Prophet provenance**

Add source snapshots to the checkpoint closed allowlist. Keep the mutable live board out of:
```text
PROTECTED_PROPHET_PATHS
checkpoint manifest allowlist
R2 supersession proofs
accepted-source checkout/diff/reset
broad-engine safe restore/reset
```
Scoped broad cleanup removes uncheckpointed source snapshots but preserves correction ledgers.

- [x] **Step 5: Verify behavior and scripts**

Run:
```bash
python -m pytest -q tests/test_prophet_bridge.py tests/test_prophet_durable_checkpoint.py
bash -n scripts/ci/daily_engine_prophet_nightly.sh
bash -n scripts/ci/daily_engine_prophet_checkpoint.sh
bash -n scripts/ci/daily_engine_commit_outputs.sh
python -c 'import yaml; yaml.safe_load(open(".github/workflows/daily.yml"))'
```
Expected: exact-byte, zero-origin, missing/malformed fail-closed, stale-temp recovery, collision, path-ownership, syntax, and YAML contracts pass.

### Task 4: Regression and immutable candidate

**Files:**
- Review all Task 1–3 files and these design/plan documents.
- Create no unrelated refactor or baseline-test repair.

- [x] **Step 1: Run the bounded regression suite**

Run:
```bash
python -m pytest -q   tests/test_us_completed_session_panel.py   tests/test_prophet_bridge.py   tests/test_prophet_arena_clock_parity.py   tests/test_prophet_durable_checkpoint.py   tests/test_prophet_r2_boundary.py   tests/test_prophet_plan_chronology_audit.py   tests/test_workflow_file_size.py
```

Run adjacent staleness/extension suites separately. Any failure outside the owned delta must be reproduced against the candidate parent or current `main` and recorded rather than silently repaired in this PR.

- [x] **Step 2: Inspect authority and collision boundaries**

Fetch current `origin/main`, compare movement on every owned path, inspect PR #7161 without modifying it, and run a merge-tree proof. Owned-path movement requires re-review before publishing.

- [x] **Step 3: Commit the bounded follow-up**

Preserve the existing candidate commit and add one review correction commit:
```bash
git commit -m "fix(prophet): preserve immutable source without owning live board"
```

- [x] **Step 4: Request independent code review**

Review against the approved outcome, source/projection integrity, product-board freshness, authority boundaries, and exact test evidence. Repair only substantiated findings.

Two Cursor Codex High review passes were completed. The first identified one Important ABA defect and one Minor ISO-datetime parser gap. Both were proven RED first and repaired in `aef3120e4ce12616d99869045e07279c27847238`. The exact repaired head then received a clean re-review with zero Critical, Important, or Minor findings. Its three sandbox-blocked nested-Git checks passed on the host.

- [ ] **Step 5: Publish and prove the exact head**

Push the existing branch, create or update its PR, confirm required CI/security checks on the exact head, and classify the capability `BUILT_NOT_PROVEN` until a real nightly proves coherent scoring and lawful origination.

PR #7180 was opened from the reviewed carrier. The branch is published; exact final-head CI/security proof remains before this step can close.

### Task 5: Separate continuation after this PR

- [x] Reconcile the cancelled China run `35019907027` from main, run logs, store tips, and R2 effects before any retry. The subsequent same-program carrier `35021696056` completed successfully on a descendant of repair commit `4ec24e0f4745`; current main reports source/session `2026-09-15`, reversal exact-date `true`, available `true`, degraded `false`, 99.6% scored coverage, 100% actionable coverage, no outage flag, and fresh CN/HK R2 manifests. No duplicate retry is owed.
- [ ] Rebase or integrate PR #7161 as the separate rescue/acceptance cohort-truth slice.
- [ ] After merge, observe a real US nightly and record whether valid candidates originate from a non-mixed completed-session board.
