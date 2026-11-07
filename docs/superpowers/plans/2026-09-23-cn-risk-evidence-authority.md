# CN Risk Evidence Authority Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the CN/HK/CA Risk Radar authority path episode-aware without changing signals, rewriting ledgers, or expanding `can_force`.

**Architecture:** Add one pure derived-evidence helper over the canonical international forward rows. Keep shared constitution unchanged; a local adapter evaluates the exact legacy row gate and a conservative episode gate, and final authority is their conjunction.

**Tech Stack:** Python 3, pytest, existing JSONL forward ledgers, existing `engine.neuralweb.constitution` Wilson/grant primitives.

**Spec:** `docs/superpowers/specs/2026-09-23-cn-risk-evidence-authority-design.md`

## Global Constraints

- Base is `8db6896dab2199a4b7fc61a005c225380cac7cd6`; protected Skillpack pin is `a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`.
- Do not modify the Risk Radar signal, probability surface, UI, weights, `_GROSS`, Portfolio, Prophet, or historical forward rows.
- Existing forward JSONL remains the only evidence ledger; all episode state is derived in memory.
- Final `can_force` must imply the exact pre-repair gate would also grant.
- Preserve nightly sole-writer/PIT behavior and existing scorecard key meanings.
- One Draft/HOLD PR only; do not merge.

## Review Focus

- Sparse sessions use a 42-calendar-day two-horizon fallback; an alert reset still requires observed quiet, so a bare gap cannot manufacture a new episode.
- One long alert streak and alternating loud/quiet rows remain one episode until 21 consecutive observed non-loud rows or observed quiet plus 42 days.
- Zero observed base events at small N must not produce infinite lift or authority.
- Unmatured rows may define current state boundaries but must not count as graded authority trials.
- The migration must be mechanically monotone: no synthetic case may grant under the new contract when the old contract refuses.

---

### Task 1: Reproduce and pin the current contract mismatch

**Files:**
- Create: `tests/test_risk_radar_intl_audit_evidence.py`
- Modify: none

**Interfaces:**
- Consumes: current `engine.risk_radar_intl_audit.scorecard()` and shared `grant_authority()`.
- Produces: failing tests that demand explicit row/episode contracts and no ambiguous denominator handoff.

- [ ] **Step 1: Write a synthetic JSONL fixture helper**

Create `_write_rows(tmp_path, market, rows)` and `_graded_row(asof, state, hit, alert=None)` so tests exercise real scorecard IO rather than mocks of the scorecard itself.

- [ ] **Step 2: Write the mismatch falsifier**

Add `test_documented_total_and_loud_floors_do_not_map_to_shared_n_and_hits` with 30 graded rows, eight loud rows, and eight loud hits. Assert additive contract fields exist, final authority is false, and the reason names the preserved legacy 30-loud-row fence rather than reporting generic `insufficient-n` against an unexplained `n`.

- [ ] **Step 3: Verify RED**

Run: `python3 -m pytest -q tests/test_risk_radar_intl_audit_evidence.py::test_documented_total_and_loud_floors_do_not_map_to_shared_n_and_hits`

Expected: FAIL because current scorecard lacks the explicit contract fields/reason and delegates ambiguous floors directly.

- [ ] **Step 4: Record the exact baseline reproduction**

Capture current scorecard output for the fixture in `/private/tmp/cn-risk-p2-current-bug.json` for the PR evidence; do not commit generated scratch output.

### Task 2: Implement pure episode and independent-window evidence

**Files:**
- Create: `engine/risk_radar_intl_evidence.py`
- Modify: `tests/test_risk_radar_intl_audit_evidence.py`

**Interfaces:**
- Consumes: canonical row dicts with `asof`, `state`, `alert`, and optional `graded` outcome.
- Produces: `derive_evidence(rows: list[dict]) -> dict` with row metrics, independent blocks, loud episodes, Wilson bounds, and evidence dates.

- [ ] **Step 1: Write episode RED tests**

Add tests named:
`test_persistent_loud_rows_collapse_to_one_episode`,
`test_alternating_rows_do_not_rearm_before_21_quiet_observations`,
`test_repeated_hits_in_one_episode_count_once`,
`test_twenty_one_quiet_rows_rearm_a_genuinely_separated_episode`,
`test_unmatured_anchor_is_reported_but_not_counted`, and
`test_episode_replay_is_deterministic`.

- [ ] **Step 2: Run the episode tests and verify RED**

Run: `python3 -m pytest -q tests/test_risk_radar_intl_audit_evidence.py -k 'episode or rearm or deterministic'`

Expected: import/function failures because the helper does not exist.

- [ ] **Step 3: Implement deterministic ordering and loud episodes**

Implement valid/deduplicated `asof` ordering, loud classification, the 21-observed-quiet or observed-quiet-plus-42-days re-arm, immutable first-loud anchor, and anchor-only grading. Keep all functions pure and side-effect free.

- [ ] **Step 4: Implement independent base windows**

Greedily select the earliest graded anchor and then the earliest graded row at least 21 canonical positions or 42 calendar days later. Count ungraded rows for observed-position spacing but never as evidence.

- [ ] **Step 5: Implement conservative uncertainty metrics**

Reuse `constitution.wilson_lower`; derive the one-sided upper bound by complement. Return `None` rather than fabricated precision when denominator N is zero.

- [ ] **Step 6: Verify GREEN**

Run: `python3 -m pytest -q tests/test_risk_radar_intl_audit_evidence.py -k 'episode or rearm or deterministic or independent'`

Expected: all selected tests pass.

### Task 3: Repair the local authority adapter and scorecard contract

**Files:**
- Modify: `engine/risk_radar_intl_audit.py`
- Modify: `tests/test_risk_radar_intl_audit_evidence.py`

**Interfaces:**
- Consumes: `derive_evidence()` metrics and unchanged shared `grant_authority()`.
- Produces: `_evaluate_authority_contract(metrics, now=None) -> dict` and additive scorecard fields; existing keys remain compatible.

- [ ] **Step 1: Write authority RED tests**

Add tests for: explicit legacy fence, tiny episode N refusal, stale episode evidence, no alerts, all hits with inadequate independent N, zero-base upper-bound behavior, incomplete rows, and final `can_force == row_gate_granted and episode_gate_granted`.

- [ ] **Step 2: Write the no-grant-more mutation test**

Generate adversarial count/rate combinations around all floors and Wilson boundaries. Assert that every new grant also has `row_gate_granted=True`; include a case that the old gate grants but the episode gate revokes.

- [ ] **Step 3: Verify RED**

Run: `python3 -m pytest -q tests/test_risk_radar_intl_audit_evidence.py -k 'authority or force or stale or zero_base or no_alerts'`

Expected: failures because the local adapter/additive fields are absent.

- [ ] **Step 4: Implement the exact legacy result**

Preserve the current precheck and shared call semantics as `row_gate_*`. Do not relabel its effective 30-loud/8-hit behavior as the documented total/loud contract.

- [ ] **Step 5: Implement the episode gate**

Require 30 total graded rows, 8 loud rows, 30 independent windows, 8 matured loud episodes, 8 episode hits, non-null evidence date, conservative Wilson lift above 1.25, and freshness. Invoke shared constitution only after named local floors pass.

- [ ] **Step 6: Conjoin grants and add scorecard fields**

Set `can_force = row_gate_granted and episode_gate_granted`. Preserve row meanings for existing fields; add explicit episode fields, reasons, contract version, and row/episode evidence dates.

- [ ] **Step 7: Extend governance transition evidence additively**

Keep the same governance ledger and transition behavior. Add row/episode counts and reasons to new events without rewriting history.

- [ ] **Step 8: Verify GREEN**

Run: `python3 -m pytest -q tests/test_risk_radar_intl_audit_evidence.py tests/test_risk_radar_intl_profiles.py tests/test_constitution.py`

Expected: all tests pass; shared constitution tests remain unchanged.

### Task 4: Replay the canonical CN/HK/CA ledgers and document the contract

**Files:**
- Modify: `docs/superpowers/specs/2026-09-23-cn-risk-evidence-authority-design.md` only if implementation naming differs under a recorded ruling.
- Create: `research/grey_deer/CN_RISK_RADAR_EPISODE_AUTHORITY_REPLAY_2026-09-23.md`
- Modify: `tests/test_risk_radar_intl_audit_evidence.py`

**Interfaces:**
- Consumes: checked-in canonical `data/risk_radar_intl/{cn,hk,ca}_forward_log.jsonl`.
- Produces: deterministic read-only replay metrics and regression assertions.

- [ ] **Step 1: Add July and September-like replay tests**

Pin July's five matured CN loud rows to one episode and a synthetic current-September persistent streak to one unmatured episode. Assert no historical file content changes.

- [ ] **Step 2: Add live-ledger replay assertions**

Assert current CN/HK/CA remain `can_force=False`; record row counts, episode counts, hit counts, precision/bounds, and evidence dates without asserting unstable presentation data.

- [ ] **Step 3: Run replay twice**

Run the same read-only replay command twice and compare canonical JSON output byte-for-byte to prove deterministic derivation.

- [ ] **Step 4: Write the replay note**

Document old row metrics, new effective N, current grant result, HK/CA regression result, exact episode law, and shared-caller audit. State explicitly that no ledger rows changed.

- [ ] **Step 5: Run focused regression**

Run: `python3 -m pytest -q tests/test_risk_radar_intl_audit_evidence.py tests/test_risk_radar_intl_profiles.py tests/test_constitution.py tests/test_gd4a_cnhk_ledger_repair.py tests/test_nightly_liveness.py`

Expected: all selected tests pass.

### Task 5: Whole-branch verification and Draft/HOLD publication

**Files:**
- No new implementation files beyond Tasks 1–4.

**Interfaces:**
- Consumes: exact tested branch head.
- Produces: one clean commit series, pushed branch, one Draft/HOLD PR, and exact-head CI status.

- [ ] **Step 1: Audit the diff against protected paths and invariants**

Confirm no signal/UI/weights/historical ledger files changed and shared constitution remains byte-identical.

- [ ] **Step 2: Run repository verification**

Run focused tests, formatting/static checks required by the touched Python paths, then the repository's full feasible pytest suite. Report every unrelated baseline failure by exact name; do not omit red output.

- [ ] **Step 3: Perform a fresh whole-branch review**

Review the merge-base-to-head package for statistical correctness, compatibility, mutation monotonicity, stale evidence, and accidental authority expansion. Fix Critical/Important findings with RED→GREEN tests in one pass.

- [ ] **Step 4: Commit and push exact head**

Commit only the owned source/tests/docs/replay note. Push without force to `sol/cn-risk-p2-evidence-authority-20260923`.

- [ ] **Step 5: Create one Draft/HOLD PR**

Title it `Draft/HOLD: make international Risk Radar authority episode-aware`. Include the bug reproduction, contract before/after, replay metrics, no-grant-more proof, tests, base/head SHAs, and explicit no-merge instruction.

- [ ] **Step 6: Observe exact-head CI**

Bind CI/check results to the pushed exact head. Do not merge. Return any pending or failing check truthfully with its exact status.
