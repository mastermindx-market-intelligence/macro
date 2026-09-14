# Sector Rotation Daily-Control RPH-1 Review Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair every immutable-head review blocker on Macro PR #7095 while preserving its preregistered research-only authority ceiling and Draft/HOLD lifecycle.

**Architecture:** Keep the same linked worktree, branch, PR, operation key, source bytes and result contract. Tighten source identity and path normalization at the loader/CLI boundary, make the frozen statistical units and sample spans explicit in JSON and Markdown, split live archive regeneration into a data-gated CI lane, then regenerate and independently review one new immutable head.

**Tech Stack:** Python 3.12, pandas, NumPy, PyArrow, pytest, strict canonical JSON, GitHub Actions legacy job manifest, Agent OS records.

**Spec:** `research/rotation_persistence/LEADERSHIP_PERSISTENCE_SECTOR_CONTROL_RPH1_PREREGISTRATION_2026-09-12.md`

## Global Constraints

- Continue only `sol/rotation-persistence-sector-control-rph1-20260912` and PR #7095; never create a sibling carrier, rebase, reset, force-push or rewrite RPH-0.
- Keep PR #7095 Draft/HOLD. Do not mark Ready, merge, deploy, add `merge-on-green`, or connect a product/Prophet/Oracle/portfolio consumer.
- Preserve operation key `leadership-persistence-sector-control-rph1-20260912-sol-001` and injected clock `2026-09-12T21:00:00Z`.
- Authority remains research/display context only: rank, gate, size, trade, entry, exit, Prophet, Oracle and portfolio authority are false.
- Every production-code change follows RED → observed expected failure → minimal GREEN → focused regression.
- Live `data/yahoo/**` byte regeneration belongs to `gate: data`; synthetic contract tests remain `gate: code`.
- JSON remains sorted, deterministic and strict: NaN/Infinity are forbidden.
- All phase-pooled rows remain explicitly non-independent; phase-specific evidence remains primary.

---
### Task 1: Fail-closed source labels and canonical CLI paths

**Files:**
- Modify: `tests/test_rotation_persistence_sector_cli.py`
- Modify: `scripts/research/rotation_persistence/sector_control.py`
- Modify: `scripts/research/run_sector_control_rph1.py`

**Interfaces:**
- `load_price_panel(data_dir: Path, symbols: tuple[str, ...] = ALL_SYMBOLS, repo_root: Path | None = None) -> tuple[pd.DataFrame, dict[str, Any]]`
- Relative input/output paths resolve against `repo_root`; source receipt paths are canonical repo-relative paths when contained by that root, otherwise canonical absolute paths.
- Parquet indexes must already be `DatetimeIndex`; timezone removal preserves each stored local date label rather than converting through UTC.

- [x] **Step 1: Write loader RED tests**

Add tests that create one-symbol parquet fixtures and assert:

```python
with pytest.raises(ContractError, match="DatetimeIndex"):
    load_price_panel(tmp_path, symbols=("XLB",))
```

for a `RangeIndex`, and that `2026-01-02 23:30-05:00` remains session date `2026-01-02` after normalization.

- [x] **Step 2: Write canonical-path RED tests**

Run from a directory outside `repo_root`; pass `Path("data/../data/yahoo")` and assert receipt fields are exactly `data/yahoo` and `data/yahoo/XLB.parquet`. Exercise `main(..., repo_root=repo_root)` with relative input/output paths and assert both are resolved against `repo_root`.

- [x] **Step 3: Verify expected RED**

Run the new tests individually. Expected failures: non-datetime index is accepted, timezone-aware label shifts through UTC, and relative paths depend on process CWD or retain `..`.

- [x] **Step 4: Implement minimal path/index repair**

Require `DatetimeIndex` before conversion; normalize timezone-aware labels with `tz_localize(None).normalize()`. Add one canonical resolver/logical-path helper, thread `repo_root` through `load_price_panel`, and resolve both CLI paths against the same root.

- [x] **Step 5: Verify GREEN**

Run `tests/test_rotation_persistence_sector_cli.py` and confirm all synthetic boundary cases pass.

---
### Task 2: Pin statistical endpoints, units and phase evidence

**Files:**
- Modify: `tests/test_rotation_persistence_sector_control.py`
- Modify: `scripts/research/rotation_persistence/sector_control.py`
- Regenerate: `research/rotation_persistence/sector_control_rph1/result.json`
- Regenerate: `research/rotation_persistence/sector_control_rph1/report.md`

**Interfaces:**
- Leadership anchors include the final matured anchor at `len(panel) - horizon - 1`.
- Signal cells identify `observation_unit: sector_signal_date`, `sector_date_observations`, unique signal dates and exact start/end dates.
- Hierarchy descriptors carry the six phase samples used for the label, not only medians.
- Quality reports `first_eligible_signal_position_by_phase`; the misleading old key is absent.

- [x] **Step 1: Write direct metric RED tests**

Add exact tests for `_spearman` (+1, -1 and average-ranked ties), `_top_three` lexicographic tie resolution, leadership endpoint anchor count/end date, and predictive persistence from a hand-computable synthetic panel.

- [x] **Step 2: Write sample-disclosure RED tests**

Construct multi-sector rows across more than 20 unique signal dates and assert `recent_20` selects all sector rows on those dates while publishing explicit observation unit, sector-date observation count, unique-date count and exact span.

- [x] **Step 3: Write hierarchy/quality RED tests**

Assert every hierarchy descriptor contains phase samples for `1D.p0`, `2D.p0`, `2D.p1`, `3D.p0`, `3D.p1`, `3D.p2`, each with state/count/date fields. Assert the new quality key exists, the old key is absent, and a 311-session panel remains `INSUFFICIENT_HISTORY`.

- [x] **Step 4: Write strict-JSON RED test**

Call `strict_json_dumps({"bad": float("nan")})` and assert `ValueError` with `strict JSON refuses`.

- [x] **Step 5: Verify expected RED**

Run each new test by node ID and confirm it fails for the named missing behavior rather than fixture or import errors.
- [x] **Step 6: Implement minimal endpoint and disclosure repair**

Include the final matured leadership anchor. Extend signal cells and hierarchy descriptors with the declared unit/count/span fields. Rename the quality field without changing its zero-based value.

- [x] **Step 7: Expand the deterministic Markdown report**

For every lookback/horizon publish recent and all-history anchors, measured N, mean and sample standard deviation plus recent-minus-all mean. Add a phase-evidence table for every forward horizon/window/phase with state, date span, unique signal dates, sector-date observations and median SPY-relative return.

- [x] **Step 8: Verify GREEN**

Run `tests/test_rotation_persistence_sector_control.py` and the strict-JSON test. Confirm old tests and all new direct formula/disclosure tests pass.

---

### Task 3: Separate data proof and regenerate the frozen archive

**Files:**
- Modify: `tests/test_rotation_persistence_sector_cli.py`
- Create: `tests/test_rotation_persistence_sector_archive.py`
- Modify: `.github/ci/legacy-jobs.yml`
- Regenerate: `research/rotation_persistence/sector_control_rph1/result.json`
- Regenerate: `research/rotation_persistence/sector_control_rph1/report.md`

**Interfaces:**
- Code-gated suites use only synthetic `tmp_path` sources.
- The archive suite alone reads the twelve committed `data/yahoo/*.parquet` files and regenerates both committed outputs byte-for-byte.

- [x] **Step 1: Move the real-archive regeneration test**

Move `test_committed_real_archive_result_regenerates_byte_for_byte` unchanged into `tests/test_rotation_persistence_sector_archive.py`; leave helper-free code or duplicate only the small invocation needed by that file.

- [x] **Step 2: Add a data-gated legacy job**

Add `sector-control-archive-regeneration` with `gate: data`, Python 3.12, the existing minimal pytest/pandas/numpy/pyarrow/pyyaml install line, and an explicit run step naming only the new archive suite.

- [x] **Step 3: Keep the code gate synthetic**

Ensure `research-price-panel` names only `test_rotation_persistence_sector_control.py` and `test_rotation_persistence_sector_cli.py` for RPH-1.
- [x] **Step 4: Regenerate exact source outputs**

From the worktree root run:

```bash
python scripts/research/run_sector_control_rph1.py \
  --data-dir data/yahoo \
  --output-dir research/rotation_persistence/sector_control_rph1 \
  --produced-at 2026-09-12T21:00:00Z
```

- [x] **Step 5: Verify both CI ownership paths**

Run the two synthetic suites together, then run the archive suite separately. Validate the legacy job manifest and contract-delta coverage so the new file is named by a real data-gated step.

---

### Task 4: Preserve exact-head verification, Agent OS state and rereview

**Files:**
- Create: `research/rotation_persistence/sector_control_rph1/verification.json`
- Create: `agentos/handoffs/LEADERSHIP-PERSISTENCE-INTELLIGENCE-2026-09-14-RPH1.md`
- Modify: `agentos/workstreams/WS-LEADERSHIP-PERSISTENCE-INTELLIGENCE.md`
- Update: PR #7095 body on GitHub

**Interfaces:**
- Verification binds exact candidate head, source hashes, output hashes, focused commands, mutation outcomes, CI gate ownership and authority ceiling.
- Agent OS records describe RPH-1 as implemented/review-pending or accepted/HOLD without creating execution authority.

- [x] **Step 1: Run adversarial mutation proof**

Demonstrate targeted failure for: forward-filled missing date, retained incomplete 3D tail, cross before 100 completed bars, non-future return endpoint, rank/trade authority, non-datetime index, UTC-shifted label and endpoint omission.

- [ ] **Step 2: Write verification receipt**

Use strict JSON and include exact commands/results, source/output SHA-256 values, `review_reuse: FULL_REREVIEW_REQUIRED`, zero-authority capability and known external/non-semantic CI blockers.

- [ ] **Step 3: Update durable records**

Update RPH-1 wave status/artifacts/next action, add a cold-stranger handoff with verified and unverified claims, and run `python scripts/agentos.py validate`.

- [ ] **Step 4: Commit and push the same branch**

Commit all repair/test/result/record files, push normally to the existing branch, confirm clean status and freeze the new exact head.
- [ ] **Step 5: Refresh the PR record**

Replace stale RED-phase prose with the exact implemented capability, source/result identities, separated data/code gates, review history, HOLD authority and explicit release condition. Confirm Draft, no `merge-on-green`, and native auto-merge null.

- [ ] **Step 6: Obtain immutable-head independent review**

Commission a read-only review of the new exact SHA covering formulas, source identity, phase completeness, disclosure, owner boundaries, tests and current checks. Because candidate-owned blobs changed after `c962235`, classify this as `FULL_REREVIEW_REQUIRED` rather than reusing the earlier verdict.

- [ ] **Step 7: Close only on accepted HOLD**

When the rereview accepts the exact head, update `verification.json` and the handoff with the verdict identity, commit/push that record-only closure if required, and obtain review of the final record head. Leave PR #7095 Draft/HOLD and report `PARKED / HOLD-FOR-SOL`, never shipped or deployed.

## Self-Review

- Spec coverage: source identity, all frozen metrics/windows/phases, strict output, data-gate ownership, authority and exact-head review each map to a task above.
- Placeholder scan: no TBD/TODO/later placeholders remain.
- Type consistency: `load_price_panel`, signal-cell fields, hierarchy phase samples and renamed quality key are defined once and used consistently.
