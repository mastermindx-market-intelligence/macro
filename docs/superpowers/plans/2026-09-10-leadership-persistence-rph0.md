# Leadership Persistence RPH-0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, research-only harness that measures the persistence, transitions and survival of the existing published US theme-leadership archive without creating a new signal or authority plane.

**Architecture:** A strict archive loader converts keep-first basket snapshots into typed session-indexed theme frames. Pure metrics compute exact-session pair surfaces, transition matrices, right-censored leader episodes, an honest-null half-life and a frozen descriptive shape. A CLI writes strict JSON plus Markdown only to an explicitly supplied research output directory.

**Tech Stack:** Python 3.12+, standard library, pandas, numpy, pytest, existing `lib.nyse_calendar`.

**Spec:** `research/rotation_persistence/LEADERSHIP_PERSISTENCE_RPH0_ARCHITECTURE_FREEZE_2026-09-10.md`

## Global Constraints

- Operation is `leadership-persistence-rph0-20260910-sol-001`.
- Read only `data/signal_archive/baskets.parquet`; no network or production writer.
- Do not modify Temporal Grain PR #6803, Signal Commons half-life, Sector Pulse, Rotation Events, Subsector Turn, Prophet, Oracle, TrialLedger or production data.
- All authority fields remain false except `is_context_only=true`.
- Use exact NYSE-session horizons; never positional row offsets.
- Missing archive rows are absence, not zero or forward-fill.
- Write tests before implementation and witness each intended RED.
- Generated research outputs stay under `research/rotation_persistence/results/`.

---

### Task 1: Strict contracts and archive normalization

**Files:**
- Create: `scripts/research/rotation_persistence/__init__.py`
- Create: `scripts/research/rotation_persistence/contracts.py`
- Create: `scripts/research/rotation_persistence/archive.py`
- Create: `tests/test_rotation_persistence_archive.py`

**Interfaces:**
- Produces `ContractError`, `strict_json_dumps`, `atomic_write_json`, `ArchiveReceipt`, `load_basket_archive(path: Path) -> tuple[dict[date, pd.DataFrame], ArchiveReceipt]`.
- Consumes `lib.nyse_calendar.is_session`.

- [ ] **Step 1: Write failing tests for strict archive behavior**

Test a valid two-session parquet, duplicate `asof` keep-first, non-session removal, snapshot/date mismatch, duplicate theme id, invalid rank/score, optional breadth null, and deterministic source SHA-256.

- [ ] **Step 2: Run the archive tests and verify RED**

Run:

```bash
python -m pytest tests/test_rotation_persistence_archive.py -q --tb=short
```

Expected: import failure because the package does not exist.

- [ ] **Step 3: Implement minimal contracts and loader**

Use frozen dataclasses for `ArchiveReceipt`; canonical JSON uses `sort_keys=True`, compact separators and `allow_nan=False`. Normalize each valid snapshot to a DataFrame indexed by unique theme id with columns `rank`, `score`, `label`, `breadth`.

- [ ] **Step 4: Run the archive tests and verify GREEN**

Run the same command. Expected: all archive tests pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add scripts/research/rotation_persistence tests/test_rotation_persistence_archive.py
git commit -m "feat(research): normalize theme leadership archive"
```

### Task 2: Exact-session persistence surface

**Files:**
- Create: `scripts/research/rotation_persistence/metrics.py`
- Create: `tests/test_rotation_persistence_metrics.py`

**Interfaces:**
- Consumes normalized frames from Task 1.
- Produces `eligible_pair`, `pair_metrics`, `build_surface`, `moving_block_ci`, `derive_half_life`, and `classify_temporal_shape`.

- [ ] **Step 1: Write failing metric tests**

Cover exact NYSE-session target lookup, endpoint gaps, 80% common-set gate, tied-rank determinism, rank persistence, top-quartile overlap/churn, score-continuation sign, breadth-coverage null, bootstrap determinism, minimum-n null, monotone half-life interpolation and all honest-null reasons.

- [ ] **Step 2: Run the metric tests and verify RED**

```bash
python -m pytest tests/test_rotation_persistence_metrics.py -q --tb=short
```

Expected: import failure for `metrics`.

- [ ] **Step 3: Implement minimal pair and surface calculations**

Use exact `sessions_between()` arithmetic from `lib.nyse_calendar`; use pandas average ranks; calculate one metric row per eligible anchor before aggregation; serialize every non-finite value as null.

- [ ] **Step 4: Run metric tests and verify GREEN**

Run the same command. Expected: all metric tests pass.

- [ ] **Step 5: Commit Task 2**

```bash
git add scripts/research/rotation_persistence/metrics.py tests/test_rotation_persistence_metrics.py
git commit -m "feat(research): measure leadership persistence surface"
```

### Task 3: Transition matrix and censored residency

**Files:**
- Create: `scripts/research/rotation_persistence/survival.py`
- Create: `tests/test_rotation_persistence_survival.py`

**Interfaces:**
- Consumes normalized session frames.
- Produces `quartile_transition_matrix`, `build_leader_episodes`, and `kaplan_meier`.

- [ ] **Step 1: Write failing transition/survival tests**

Cover exact one-session transitions only, deterministic quartile buckets, row-normalized matrices, observed exits, left censoring, archive-gap right censoring, archive-end censoring and the KM evidence floor.

- [ ] **Step 2: Run and verify RED**

```bash
python -m pytest tests/test_rotation_persistence_survival.py -q --tb=short
```

Expected: import failure for `survival`.

- [ ] **Step 3: Implement transition and survival functions**

Episodes carry `theme_id`, `start`, `end`, `duration_sessions`, `left_censored`, `right_censored`, and `end_reason`. KM uses only right-censor/event semantics and returns a null median below the frozen floor.

- [ ] **Step 4: Run and verify GREEN**

Run the same command. Expected: all survival tests pass.

- [ ] **Step 5: Commit Task 3**

```bash
git add scripts/research/rotation_persistence/survival.py tests/test_rotation_persistence_survival.py
git commit -m "feat(research): add leadership transition survival"
```

### Task 4: CLI, strict result and Markdown report

**Files:**
- Create: `scripts/research/run_rotation_persistence_rph0.py`
- Create: `scripts/research/rotation_persistence/report.py`
- Create: `tests/test_rotation_persistence_cli.py`

**Interfaces:**
- Consumes Tasks 1-3.
- Produces `research.rotation_persistence_rph0.v1` JSON and a deterministic Markdown report.

- [ ] **Step 1: Write failing CLI tests**

Cover successful local run, forbidden output roots, no NaN, all-false authority, deterministic payload under injected `produced_at`, malformed input returning exit 2 without a false result, and output files confined to the requested directory.

- [ ] **Step 2: Run and verify RED**

```bash
python -m pytest tests/test_rotation_persistence_cli.py -q --tb=short
```

Expected: script/module import failure.

- [ ] **Step 3: Implement the CLI and report**

CLI arguments: `--archive`, `--out-dir`, `--produced-at`, `--recent-sessions`, `--bootstrap-resamples`, `--bootstrap-seed`. Defaults match the frozen spec. Write `result.json` and `report.md` atomically.

- [ ] **Step 4: Run and verify GREEN**

Run the same command. Expected: all CLI tests pass.

- [ ] **Step 5: Commit Task 4**

```bash
git add scripts/research/run_rotation_persistence_rph0.py scripts/research/rotation_persistence/report.py tests/test_rotation_persistence_cli.py
git commit -m "feat(research): add leadership persistence RPH-0 CLI"
```

### Task 5: Execute the frozen study and publish durable research results

**Files:**
- Create: `research/rotation_persistence/results/result.json`
- Create: `research/rotation_persistence/results/report.md`
- Create: `research/rotation_persistence/RPH0_FINDINGS_2026-09-10.md`
- Create: `agentos/decisions/DEC-LEADERSHIP-PERSISTENCE-CROSS-OWNER-BOUNDARY.md`
- Create: `agentos/workstreams/WS-LEADERSHIP-PERSISTENCE-INTELLIGENCE.md`
- Create: `agentos/handoffs/LEADERSHIP-PERSISTENCE-INTELLIGENCE-2026-09-10-RPH0.md`

**Interfaces:**
- Consumes exact code and preregistration from Tasks 1-4.
- Produces immutable research evidence and organizational continuation; no product implementation.

- [ ] **Step 1: Run the full focused suite before reading the real result**

```bash
python -m pytest \
  tests/test_rotation_persistence_archive.py \
  tests/test_rotation_persistence_metrics.py \
  tests/test_rotation_persistence_survival.py \
  tests/test_rotation_persistence_cli.py -q --tb=short
```

Expected: all pass.

- [ ] **Step 2: Execute the preregistered CLI on the real archive**

```bash
python scripts/research/run_rotation_persistence_rph0.py \
  --archive data/signal_archive/baskets.parquet \
  --out-dir research/rotation_persistence/results \
  --produced-at 2026-09-10T21:00:00Z
```

Expected: exit 0 with exact source hash and honest measured/null cells.

- [ ] **Step 3: Adversarially interpret the result**

Write a findings memo that distinguishes measured published-output persistence from economic return, reconciles Signal Commons half-life and Temporal Grain ownership, and states whether the original multi-scale hypothesis survived this independent system-output test.

- [ ] **Step 4: Add Agent OS records**

Create one bounded workstream under `sector-rotation-intelligence`, one cross-owner decision, and one handoff. Mark RPH-0 `BUILT_NOT_PROVEN` or `PARTIAL` based on actual evidence; do not alter the active Temporal Grain workstream or PR #6803 paths.

- [ ] **Step 5: Validate records and focused regression suite**

```bash
python scripts/agentos.py validate
python -m pytest \
  tests/test_rotation_persistence_archive.py \
  tests/test_rotation_persistence_metrics.py \
  tests/test_rotation_persistence_survival.py \
  tests/test_rotation_persistence_cli.py \
  tests/test_sector_pulse.py tests/test_subsector_turn.py \
  tests/test_rotation_events.py tests/test_half_lives.py \
  tests/test_nyse_calendar.py -q --tb=short
git diff --check
```

- [ ] **Step 6: Commit Task 5**

```bash
git add research/rotation_persistence agentos/decisions agentos/workstreams agentos/handoffs
git commit -m "research(rotation): freeze leadership persistence findings"
```

### Task 6: Final source review and publication boundary

**Files:**
- Modify only if review finds a defect in the Task 1-5 paths.

- [ ] **Step 1: Inspect exact branch identity and changed paths**

Verify the branch descends from pickup base and owns only the planned paths.

- [ ] **Step 2: Run contract, trial-registration and CI-scope checks**

Use the repository's current `check_contract_delta.py`, `check_trial_registration.py`, `run_ci_pack.py --validate-only`, and applicable static guards.

- [ ] **Step 3: Perform a mutation-oriented self-review**

Confirm tests fail if session offsets replace exchange sessions, gaps are forward-filled, half-life is forced on a non-monotone curve, authority becomes true, or an output path enters `data/`.

- [ ] **Step 4: Publish one Draft/HOLD PR or stop with local-only evidence**

A PR remains research-only and must not claim product capability, production proof or authority. Do not merge or deploy in this operation.
