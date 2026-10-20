# Intraday Options Root Coverage Producer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every configured live-flow root discoverable and every successful current-cycle root with real drill state publishable, without creating a second data plane.

**Architecture:** Extend the existing session day-state with per-root source receipts and extend `live_flow.meta/v2` with a deterministic catalog. Replace top-40 publication gating with a pure current-cycle success-and-data selector, while preserving the existing two-tier cadence and concurrency ceiling.

**Tech Stack:** Python 3, pytest, YAML config, existing Macro live-flow engine and R2 staging.

**Spec:** `docs/superpowers/specs/2026-09-20-intraday-options-root-coverage-producer-design.md`

## Global Constraints

- Preserve the existing `live_flow` collector, scheduler, day-state, `meta` object and R2 publication plane.
- Keep `max_concurrent=2` and existing two-tier bucket selection unchanged.
- Raise only `live_flow.top_names` from 100 to 128.
- Missing data remains missing; never publish an empty root or freshen a failed root.
- Catalog data is display-only and has no signal, score, gate, sizing or trade authority.
- Source paths are based on Macro `78ef3b7b9d50deb02ac06ec7e655b7e892bfd40c` and Skillpack `bceb5e1593b1dd7e9e34c3bccbceb02e6ccd5a26`.

## Review Focus

- A root succeeds after other futures complete: success names must still follow configured request order.
- A cycle is fully failed: prior per-root receipts and source clock must survive unchanged.
- A quiet root ranks outside the old top 40: it must still publish when it has real session data.
- A current-cycle fetch fails after earlier session data exists: it must not be republished with a fresh timestamp.
- A configured rotating root has never succeeded: it remains cataloged with a null receipt.

---

### Task 1: Pure coverage catalog and publish selection

**Files:**
- Modify: `scripts/live_flow_poller.py`
- Modify: `tests/test_live_flow_tiering.py`

**Interfaces:**
- Produces: `_roots_with_ticker_data(day_state: dict) -> set[str]`
- Produces: `_select_ticker_publish_roots(cycle_roots: list[str], successful_roots: list[str], day_state: dict) -> list[str]`
- Produces: `_build_root_catalog(configured_roots: list[str], cycle_roots: list[str], successful_roots: list[str], receipts: dict, day_state: dict) -> list[dict]`
- Consumes: existing `TIER1_ROOTS` and accumulated root maps.

- [ ] **Step 1: Write failing helper tests**

Add tests equivalent to:

```python
class TestRootCatalog:
    def test_orders_activity_then_core_then_rotating(self):
        lf = _import_poller()
        catalog = lf._build_root_catalog(
            configured_roots=["SPY", "TLT", "AMD", "PLTR"],
            cycle_roots=["SPY", "AMD"],
            successful_roots=["AMD", "SPY"],
            receipts={"SPY": "2026-09-20T14:00:00Z", "AMD": "2026-09-20T14:01:00Z"},
            day_state={
                "root_gross_today": {"AMD": 200.0, "SPY": 100.0},
                "root_minutes": {"AMD": {"10:00": {}}, "SPY": {"10:00": {}}},
                "root_strikes": {},
            },
        )
        assert [row["root"] for row in catalog] == ["AMD", "SPY", "TLT", "PLTR"]
        assert catalog[0]["activity_rank"] == 1
        assert catalog[2]["tier"] == "core"
        assert catalog[3]["tier"] == "rotating"
        assert catalog[3]["last_source_success"] is None

class TestTickerPublishRoots:
    def test_quiet_root_beyond_old_top40_is_selected_when_real_data_exists(self):
        lf = _import_poller()
        roots = [f"T{i:02d}" for i in range(41)] + ["AMD"]
        day_state = {"root_minutes": {"AMD": {"11:00": {}}}, "root_strikes": {}}
        assert lf._select_ticker_publish_roots(roots, ["AMD"], day_state) == ["AMD"]

    def test_excludes_failed_and_empty_roots(self):
        lf = _import_poller()
        day_state = {"root_minutes": {"AMD": {"11:00": {}}}, "root_strikes": {}}
        assert lf._select_ticker_publish_roots(["AMD", "PLTR"], ["PLTR"], day_state) == []
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python3 -m pytest tests/test_live_flow_tiering.py -q -k 'RootCatalog or TickerPublishRoots'`

Expected: FAIL because the three helper functions do not exist.

- [ ] **Step 3: Implement the minimal pure helpers**

Normalize roots once, reject malformed receipt values, define real ticker data as at least one minute or strike entry, preserve configured/cycle order, and produce the exact schema from the spec. Do not read files, clocks or environment variables inside these helpers.

- [ ] **Step 4: Run helper tests GREEN**

Run: `python3 -m pytest tests/test_live_flow_tiering.py -q -k 'RootCatalog or TickerPublishRoots'`

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add scripts/live_flow_poller.py tests/test_live_flow_tiering.py
git commit -m "feat(options): define live root coverage catalog"
```

### Task 2: Persist per-root source receipts in run_cycle

**Files:**
- Modify: `scripts/live_flow_poller.py`
- Modify: `tests/test_live_flow.py`

**Interfaces:**
- Consumes: current fetch-result map and existing session `day_state`.
- Produces: ordered source-success and ticker-state-success names plus their separate receipt maps.

- [ ] **Step 1: Write failing run-cycle tests**

Add tests that stub two roots completing out of order and assert names follow requested order, then assert receipts update only successful roots. Extend the fully failed-cycle test with:

```python
prior_receipts = {"SPY": "2026-07-02T17:40:00Z"}
# run a fully failed cycle with prior state
assert state["root_source_receipts"] == prior_receipts
assert meta["roots_with_source_payload_names"] == []
```

Add a partial-cycle assertion:

```python
assert meta["roots_with_source_payload_names"] == ["SPY", "AMD"]
assert state["root_source_receipts"]["SPY"] == meta["source_response_at_first"]
assert "FAILED" not in state["root_source_receipts"]
```

- [ ] **Step 2: Run and verify RED**

Run: `python3 -m pytest tests/test_live_flow.py -q -k 'source_payload_names or root_source_receipts or fully_failed_cycle_retains_prior_source_clock'`

Expected: FAIL on missing fields.

- [ ] **Step 3: Implement receipt persistence**

Copy only valid prior receipt entries, derive ordered source-success roots from `fetch_results`, and update their source receipts. After `process_batch` succeeds and state merges, update the distinct ticker-state names and receipts. Existing source-clock behavior remains untouched, and an engine failure must retain the prior ticker receipt.

- [ ] **Step 4: Run receipt and clock tests GREEN**

Run: `python3 -m pytest tests/test_live_flow.py -q -k 'source_payload_names or root_source_receipts or fully_failed_cycle_retains_prior_source_clock or meta_v2_separates_poll_source_and_compute_clocks'`

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add scripts/live_flow_poller.py tests/test_live_flow.py
git commit -m "feat(options): retain per-root live source receipts"
```

### Task 3: Wire catalog, broaden universe and remove top-40 gating

**Files:**
- Modify: `scripts/live_flow_poller.py`
- Modify: `config.yml`
- Modify: `tests/test_live_flow_tiering.py`

**Interfaces:**
- Consumes: Task 1 helpers and Task 2 receipt/success fields.
- Produces: `meta.root_catalog`, `meta.roots_configured`, and current-cycle ticker artifact staging for all eligible roots.

- [ ] **Step 1: Write failing configuration and integration-contract tests**

Add a config test that loads `config.yml` and asserts:

```python
cfg = yaml.safe_load((repo_root / "config.yml").read_text())["live_flow"]
assert cfg["top_names"] == 128
assert cfg["max_concurrent"] == 2
```

Add a test that composes catalog rows from full configured roots while `roots_requested` remains the current cycle size. Add a selection test proving source-failed roots with prior data are excluded from current publication.

- [ ] **Step 2: Run and verify RED**

Run: `python3 -m pytest tests/test_live_flow_tiering.py -q -k 'production_live_flow_config or RootCatalog or TickerPublishRoots'`

Expected: FAIL because `top_names` is 100 and the main contract is not wired.

- [ ] **Step 3: Wire the main loop**

After `run_cycle()` and durable state save, build the catalog from full `roots`, exact `cycle_roots`, ordered source-success names, persisted source receipts and accumulated session state. Set `meta["root_catalog"]` and `meta["roots_configured"]` before writing `meta.json`. Replace top-40/pinned selection with `_select_ticker_publish_roots(...)` driven by ticker-state-success names. Pass each root's ticker-state receipt as the ticker payload `asof`. Remove the obsolete top-40/pinned gate constants and tests if they have no remaining consumer.

- [ ] **Step 4: Raise the bounded universe**

Change only `live_flow.top_names: 100` to `128`. Leave chain-snapshot configuration and concurrency unchanged.

- [ ] **Step 5: Run focused suites**

Run: `python3 -m pytest tests/test_live_flow_tiering.py tests/test_live_flow.py -q`

Expected: all tests PASS.

- [ ] **Step 6: Run syntax and diff checks**

Run:

```bash
python3 -m py_compile scripts/live_flow_poller.py
git diff --check
```

Expected: both PASS.

- [ ] **Step 7: Commit Task 3**

```bash
git add scripts/live_flow_poller.py config.yml tests/test_live_flow_tiering.py tests/test_live_flow.py
git commit -m "feat(options): publish the covered intraday root universe"
```

### Task 4: Producer branch verification and PR evidence

**Files:**
- Modify: `docs/superpowers/specs/2026-09-20-intraday-options-root-coverage-producer-design.md` only if implementation exposed a contract correction.
- Modify: PR body after push; no product code in this task.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: immutable branch head, exact test receipt and linked Macro PR.

- [ ] **Step 1: Run the relevant whole producer suite**

Run: `python3 -m pytest tests/test_live_flow_tiering.py tests/test_live_flow.py -q`

Expected: PASS with exact test count recorded.

- [ ] **Step 2: Inspect the complete branch diff**

Run:

```bash
git diff --stat origin/main...HEAD
git diff --check origin/main...HEAD
git status --short --branch
```

Expected: only owned files, clean diff and clean worktree.

- [ ] **Step 3: Push and open the Macro PR**

Push `sol/intraday-options-root-coverage-20260920` and open a PR linked to Terminal issue #681. The PR body must distinguish local proof, CI, merge, deployment and production proof.
