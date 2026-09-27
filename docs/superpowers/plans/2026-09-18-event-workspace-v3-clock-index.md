# Event-Workspace v3 Clock + Revision Index Implementation Plan

> **Operation:** `event-workspace-clock-index-k4g-20260918-sol-001`
> **Carrier:** issue #7331, ruling comment 5737546551
> **Base:** `d58225eccef124f9617726cdf690939b4af91deb`
> **Branch:** `sol/event-workspace-clock-index-k4g-20260918`
> **Ruling procedure pin:** Mastermind `20dc89a201b9dfa65c2b6a2366072f45d885cb5c`, Skillpack 1.0.1
> **Fresh execution pin (2026-09-18):** Mastermind `b9884f7d3f99f33c6ceecb5007628ac84b5147f6`, Skillpack 1.0.1/bootstrap1

**Goal:** Preserve immutable full event-workspace history while giving the shared reader a manifest-authenticated, bounded semantic-revision path and correcting the generated/observed clock collapse. The real AAPL D5 read must preserve correction lineage and fit the existing client budget before production acceptance.

**Non-goals:** No Prophet ranking/B1/B4/auth/trade edits, no market reaction/frontier/FIF-7 implementation, no second store/cache/service/publisher, no +1y expectation-revision evaluation, no merge/deployment from this wave.

## Frozen architecture

1. Keep workspace v1 and manifest v1/v2 byte/validation laws unchanged.
2. Add manifest v3 = v2 exact fields plus one `revision_index` receipt.
3. Keep `files` workspace-only and `event_count == len(files)`.
4. Add exact-schema `revision_index.json`, keyed by canonical event id, rows oldest first.
5. Historical rows carry absolute generation/clock/receipt; the final current row may carry typed `workspace_generation_ref: self` with null clock/receipt resolved from the enclosing manifest.
6. v3 generation identity binds one stable mint clock, predecessor id, semantic workspace bodies excluding envelope fields, and canonical index bytes.
7. No-op preview reuses the incumbent v3 mint clock/predecessor/index; changed content chooses one fresh mint clock once.
8. Current v3 readers use the index fast path; current v1/v2 retains the existing verified full-chain path.
9. The incumbent R2 publisher uploads workspaces, index, immutable manifest, then marker last.
## Task 1 — RED contract tests for v3 construction

**Files:**
- Create `tests/test_company_intelligence_workspace_v3.py`
- Modify `tests/test_refresh_event_workspaces.py`

**RED cases:**
- v3 construction terminates without a hash/receipt fixed point.
- exact same mint clock + content + predecessor + index yields identical immutable bytes.
- later wall-clock no-op reuses the incumbent generation and emits no new publish.
- one correction mints exactly one successor with later `generated_at`; `source_available_at` stays unchanged.
- current `self` resolves only as the final row through the enclosing manifest.
- duplicate, historical, or non-final `self` fails closed.
- A→B→A remains three rows; A→A→A remains one.

**Command:**
```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_company_intelligence_workspace_chain.py \
  tests/test_refresh_event_workspaces.py \
  --basetemp=/Users/chriswong/t/k4g-red
```

Expected first result: failures caused by absent v3 constants, constructors, and reader validation—not fixture mistakes.

## Task 2 — Implement v3 schemas and pure validators

**File:** `engine/company_intelligence/event_workspace.py`

- Add manifest-v3 and revision-index schema constants and exact key sets.
- Add row/index validators with typed `self` rules and timestamp/receipt validation.
- Add a v3 identity helper with an explicit domain tag; exclude workspace `generation_id` and `generated_at` from semantic bodies.
- Add pure helpers to materialize prior `self` rows and evolve an index by consecutive source-SHA semantics.
- Keep every v1/v2 branch byte-identical and behaviorally unchanged.
## Task 3 — Write v3 generations without changing legacy writers

**File:** `engine/company_intelligence/event_workspace.py`

- Add a dedicated v3 writer; do not alter v2 identity semantics.
- Accept an explicit mint clock and validated candidate index.
- Compute generation id before stamping workspace envelope fields.
- Write workspace objects, then `revision_index.json`, then immutable v3 manifest, then local marker.
- Validate index + manifest together after workspace receipts exist.
- Refuse immutable same-id/different-byte collisions.

## Task 4 — Shared indexed reader with legacy fallback

**File:** `engine/neuralweb/company_intelligence_reader.py`

- Bind the current marker byte-for-byte to its immutable v3 manifest, recompute the v3 generation identity, and validate the authenticated index receipt.
- Resolve a final `self` row from the enclosing manifest only.
- Fetch only referenced workspace bodies and verify exact receipts.
- Re-derive source SHA/form/clocks/state from each body and compare to the index row.
- Emit the existing revision receipt shape unchanged.
- Preserve the incumbent v1/v2 full-chain walk exactly; invalid v3 is a typed integrity error, never fallback.

## Task 5 — Refresh migration, truthful mint clock, and no-op

**File:** `scripts/refresh_event_workspaces.py`

- Choose one operation mint clock at refresh entry and pass it through every changed v3 write.
- Seed the first v3 index from one verified legacy read.
- For v3 current, load the authenticated index and materialize prior `self` rows before changes.
- Preview unchanged content using the incumbent mint clock/predecessor/index and skip all writes/publishes on equality.
- Append a new `self` row only for a consecutive source-SHA change.
- Preserve observation persistence and never mutate the legal source clock.
## Task 6 — Publish the authenticated index on the incumbent plane

**Files:**
- Modify `scripts/publish_company_intelligence_r2.py`
- Modify `tests/test_refresh_event_workspaces.py`

- Upload all workspace files first.
- For v3 only, verify and upload `revision_index.json` next.
- Upload the immutable generation manifest after every payload.
- Promote the marker last under the existing compare-and-swap condition.
- Add a discriminating upload-order test and a missing/corrupt-index refusal test.

## Task 7 — Adversarial parity and correction tests

**Files:**
- Modify `tests/test_company_intelligence_workspace_v3.py`
- Modify `tests/test_refresh_event_workspaces.py`
- Modify `.github/ci/legacy-jobs.yml`
- Modify `tests/test_ci_pack.py`

Add failures for corrupt index receipt/body, reordered rows, dropped middle correction, wrong historical receipt, wrong clock, and mismatched self workspace. Prove indexed output equals legacy output on the canonical fixture chain and all-false authority remains intact.

## Task 8 — Fresh verification and source continuity

Run, in order:

```bash
python3 -m pytest -q tests/test_company_intelligence_event_workspace.py \
  tests/test_company_intelligence_workspace_chain.py \
  tests/test_company_intelligence_workspace_v3.py \
  tests/test_refresh_event_workspaces.py \
  tests/test_publish_company_intelligence_r2.py
python3 -m pytest -q tests/test_ci_pack.py
python3 scripts/agentos.py validate
```

Then inspect `git diff --check`, run `ruff check` and Python compilation on the changed Python files, verify exact changed paths, branch cleanliness, ancestry, remote head, and current `origin/main` movement. Record a command-backed source-continuity checkpoint from the incumbent worktree and authenticated GitHub facts; this repository currently exposes no dedicated K4-G checkpoint helper. Commit only after the focused and CI-plan suites are green. Push the one branch normally, create one DRAFT/HOLD-FOR-SOL PR, and request independent exact-head review. Do not merge or deploy.
