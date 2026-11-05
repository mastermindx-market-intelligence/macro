# Sector Intelligence Freshness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish US Sector Intelligence through an independent, self-healing lane whose semantic dates are coherent and monitored.

**Architecture:** Reuse the existing basket, sector-timing, action-board, and Sector Central producers in strict order. Add a hard validator, a focused workflow, and coverage in the existing GitHub-hosted nightly-liveness watchdog. No new scorer or deploy plane is introduced.

**Tech Stack:** Python 3.12, pytest, GitHub Actions YAML, existing `scripts/ci/push_retry.sh` publication contract.

**Spec:** `docs/superpowers/specs/2026-09-16-sector-intelligence-freshness-design.md`

## Global Constraints

- Preserve existing action-board consumer shape under the `action_board` key.
- All four semantic dates must agree exactly.
- Permit at most one completed NYSE session of lag.
- Fail closed on missing, malformed, unstamped, empty, split, or overly stale output.
- Do not modify `daily.yml`, `render.yml`, `engine-render.yml`, or `scripts/build_site.py` while Prophet PRs overlap those paths.
- Use only the existing Git/main publication path and push retry library.

---
### Task 1: Pin the semantic and generation failures

**Files:**
- Modify: `tests/test_sector_intelligence_page.py`
- Test: `tests/test_sector_intelligence_page.py`

**Interfaces:**
- Consumes: temporary `site/` trees created by tests.
- Produces: expected public API for `scripts.check_sector_intelligence_freshness.evaluate(root, now, max_sessions_behind=1)`.

- [ ] **Step 1: Add failing tests for split dates, missing action-board stamp, hash mismatch, and coherent one-session lag**

Use fixtures with these four semantic fields: basket `as_of`, `theme_intel.as_of`, action-board `as_of`, and sector payload `as_of`. Include `baskets_sha256` on the action board and matching source hashes on the page-generation payload/HTML.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python -m pytest tests/test_sector_intelligence_page.py -q`

Expected: collection/import failure because `scripts.check_sector_intelligence_freshness` does not exist.

- [ ] **Step 3: Commit only after the implementation tasks make these tests green**

---

### Task 2: Build the semantic freshness validator

**Files:**
- Create: `scripts/check_sector_intelligence_freshness.py`
- Modify: `tests/test_sector_intelligence_page.py`

**Interfaces:**
- Produces: `evaluate(root: Path, now: datetime | None = None, max_sessions_behind: int = 1) -> dict` with `ok`, `errors`, `warnings`, and `facts`.
- CLI: `python -m scripts.check_sector_intelligence_freshness [--root PATH] [--max-sessions-behind N] [--quiet]`.

- [ ] **Step 1: Parse all required JSON and the public HTML generation attributes**
- [ ] **Step 2: Verify exact date agreement, non-empty action lanes, source hashes, and NYSE lag**
- [ ] **Step 3: Return exit 1 on any error and print GitHub annotations**
- [ ] **Step 4: Run focused tests until GREEN**

Run: `python -m pytest tests/test_sector_intelligence_page.py -q`

---
### Task 3: Produce a source-bound action board

**Files:**
- Create: `scripts/build_sector_action_board.py`
- Modify: `tests/test_sector_intelligence_page.py`

**Interfaces:**
- Consumes: fresh `site/basketdata/baskets.json`, regime state, existing sector inputs, and reusable functions from `scripts.build_site`.
- Produces: `site/basketdata/action_board.json` with schema, `as_of`, `generated_utc`, `baskets_sha256`, and unchanged nested `action_board`.

- [ ] **Step 1: Add a failing test for additive metadata and exact basket-byte hash**
- [ ] **Step 2: Verify RED against the current bare action-board writer**
- [ ] **Step 3: Implement the focused builder without changing `scripts/build_site.py`**
- [ ] **Step 4: Reuse sector timing, setup lookup, basket actions, and two-read attachment semantics**
- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `python -m pytest tests/test_sector_intelligence_page.py -q`

---

### Task 4: Bind the rendered overview to the exact sources

**Files:**
- Modify: `scripts/build_sector_central.py`
- Modify: `templates/sector_central.html.j2`
- Modify: `tests/test_sector_central_gate.py`
- Modify: `tests/test_sector_intelligence_page.py`

**Interfaces:**
- Consumes: source-bound basket and action-board files.
- Produces: premium payload and HTML carrying `as_of`, `baskets_sha256`, and `action_board_sha256`.

- [ ] **Step 1: Add failing payload and template contract tests**
- [ ] **Step 2: Compute exact source-byte SHA-256 digests in the builder**
- [ ] **Step 3: Add metadata to `write_payload` without changing its gated-row behavior**
- [ ] **Step 4: Render nonvisual `data-si-*` generation attributes on the overview hero**
- [ ] **Step 5: Run gate and Sector Intelligence tests until GREEN**

Run: `python -m pytest tests/test_sector_central_gate.py tests/test_sector_intelligence_page.py -q`

---

### Task 5: Create the independent build and publication lane

**Files:**
- Create: `scripts/build_sector_intelligence.py`
- Create: `.github/workflows/sector-intelligence.yml`
- Modify: `tests/test_sector_intelligence_page.py` (workflow ownership checks stay in the existing CI-owned suite)

**Interfaces:**
- Orchestrator order: baskets → action board → Sector Central → validator.
- Workflow publishes only the approved generated paths through existing Git/main retry helpers.

- [ ] **Step 1: Write failing workflow tests for triggers, concurrency, builder order, validation, and scoped publication**
- [ ] **Step 2: Verify RED because the workflow and orchestrator do not exist**
- [ ] **Step 3: Implement the orchestrator with nonzero propagation**
- [ ] **Step 4: Implement push, scheduled reconciliation, and manual dispatch triggers**
- [ ] **Step 5: Add scheduled preflight skip and own-publication loop suppression**
- [ ] **Step 6: Use `ADMIN_GH_TOKEN`, `push_retry.sh`, and metadata replay for the scoped commit**
- [ ] **Step 7: Run workflow contract tests until GREEN**

Run: `python -m pytest tests/test_sector_intelligence_page.py -q`

---
### Task 6: Extend the existing external watchdog

**Files:**
- Modify: `scripts/check_nightly_liveness.py`
- Modify: `.github/workflows/nightly-liveness.yml`
- Modify: `tests/test_nightly_liveness.py`

**Interfaces:**
- Adds three `MARKET_BOARDS` rows for baskets, action board, and sector payload.
- Adds one cross-artifact vintage check; no new monitor or transport.

- [ ] **Step 1: Add failing tests for sparse coverage, missing stamp, stale date, and fresh-but-split dates**
- [ ] **Step 2: Verify RED on current watchdog behavior**
- [ ] **Step 3: Add exact artifact paths to the GitHub-hosted sparse checkout**
- [ ] **Step 4: Add NYSE-governed board registrations and split-date failure**
- [ ] **Step 5: Run liveness tests and selftest until GREEN**

Run: `python -m pytest tests/test_nightly_liveness.py -q`
Run: `python scripts/check_nightly_liveness.py --selftest`

---

### Task 7: Prove the recovery end to end

**Files:**
- Modify only when test evidence requires a bounded repair.

- [ ] **Step 1: Run all focused suites**

Run: `python -m pytest tests/test_sector_intelligence_page.py tests/test_sector_central_gate.py tests/test_nightly_liveness.py -q`

- [ ] **Step 2: Run the real targeted build in the worktree**

Run: `python -m scripts.build_sector_intelligence`

Expected: coherent common `as_of`, matching hashes, non-empty action board, validator exit 0.

- [ ] **Step 3: Inspect exact generated-path diff and reject any scope expansion**
- [ ] **Step 4: Push the feature branch and open a PR with root cause, proof, and rollback**
- [ ] **Step 5: Obtain current-base CI and independent review, repair bounded findings, then merge**
- [ ] **Step 6: Dispatch `sector-intelligence.yml` on `main` and record run/commit identity**
- [ ] **Step 7: Verify deployed HTTP generation and authenticated common `as_of`**
- [ ] **Step 8: Record durable closeout with exact next action if production proof is incomplete**
