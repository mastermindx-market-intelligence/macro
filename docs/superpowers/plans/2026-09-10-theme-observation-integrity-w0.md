# Theme Observation Integrity W0 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: execute this plan test-first in the already bound operation carrier. Do not create a replacement branch or second price/theme state plane.

**Goal:** Prevent theme and basket aggregates from speaking on phantom dates or silently survivor-reduced populations.

**Architecture:** Extend the existing `lib/closes_panel.py` owner with terminal-observation and population-receipt semantics. Route the existing Group Flow, Baskets, and Theme Scoring consumers through that contract while preserving every score, label, recommendation, and risk-transition rule.

**Tech Stack:** Python 3.12, pandas, pytest, existing Macro engine modules and GitHub Actions packs.

**Spec:** `docs/superpowers/specs/2026-09-10-theme-observation-integrity-w0-design.md`

**Operation:** `theme-observation-integrity-w0-20260910-sol-001`

## Global Constraints

- Preserve the canonical price, Group Reads, TIL, Theme Scoring, and publication planes; create no duplicate store or authority.
- Trim only terminal all-null calendar suffixes; preserve interior outages and never-populated columns.
- Require at least three observed members and at least 60% configured-live coverage before aggregate scoring.
- Preserve existing `n_members` consumer semantics; configured/present/observed counts live in the additive `observation` receipt.
- Do not edit Theme Tracker builder/template paths owned by PR #7010.
- No score, threshold, lifecycle, recommendation, rank, sizing, alert, Prophet, or risk-transition change.
- Real-data proof is read-only, source-SHA pinned, and must leave `data/` and `site/` unchanged.
- Keep W0 regressions in the already-wired `tests/test_group_flow.py` owner lane. Do not create a new standalone suite or edit global CI manifests merely to make the tests reachable.

## Task 1 — Pin the defect with RED tests

**Files:**
- Modify: `tests/test_group_flow.py`
- Modify: `tests/test_group_flow_regional.py`

1. Add a close-cache regression where every tier carries a final all-null session.
2. Assert the returned panel ends on the last actually observed session, columns remain intact, and metadata distinguishes raw/effective tips.
3. Add a common-session regression where the benchmark is missing at the panel tip; assert the helper retreats to the latest exact shared observation and never terminal-forward-fills.
4. Add population receipt tests for complete, partial-admissible and insufficient cases with dated membership.
5. Add a group-flow setup regression reproducing the nuclear shape: six broad names plus three extras-only names, all nine observed on the selected coherent date.
6. Add a theme-scoring refusal regression proving label/recommendation functions are not called below the floor.
7. Run only the new tests and capture the expected failures.
8. Keep these regressions inside the already-collected Group Flow suite; verify the existing pull-request path closure reaches every imported producer without editing global CI manifests.

## Task 2 — Repair the canonical close-panel observation contract

**Files:**
- Modify: `lib/closes_panel.py`

1. Trim only the terminal all-null row suffix from the merged output while preserving interior all-null outages and never-populated columns.
2. Emit additive raw/effective-tip and dropped-row metadata.
3. Add `align_latest_common_observation()`.
4. Add `population_observation()` using dated `[added, removed)` membership and the 3-member/60% floor.
5. Run Task 1 unit tests.

## Task 3 — Route US Group Flow through the common observation contract

**Files:**
- Modify: `engine/group_flow.py`
- Modify: `tests/test_group_flow.py`

1. Preserve the existing extras-only union; do not overwrite overlapping breadth columns.
2. Align the primary panel and benchmark to the latest exact common observation before extras are joined, so supplemental data can widen the population but never advance the desk clock.
3. Return additive `observation` metadata from `_setup()`.
4. Prove the nuclear-shaped fixture produces nine observations on the coherent date.
5. Prove a complete pre-existing fixture is unchanged apart from additive metadata.

## Task 4 — Attach per-theme receipts and refuse insufficient aggregates

**Files:**
- Modify: `engine/theme_scoring.py`
- Modify: `tests/test_group_flow.py`
- Modify: `tests/test_theme_scoring.py` only if an existing contract assertion needs an additive-key update

1. Compute each basket's population receipt before `_ew_level`, fingerprinting or scoring.
2. Append insufficient reads to top-level `observation_refusals`; do not call score, label or recommendation logic.
3. Attach `observation` to every admitted theme.
4. Preserve the existing `n_members` scored/observed denominator for current consumers; carry configured-live, in-panel, observed, missing-column, and missing-at-session counts only in the additive `observation` receipt.
5. Prove complete-data label/recommendation parity and BVI-R1 invariance through existing tests.

## Task 5 — Bring Baskets onto the same date/population receipt

**Files:**
- Modify: `engine/baskets.py`
- Modify: `tests/test_group_flow.py`

1. Align Baskets and SPY before computing returns or chart dates.
2. Attach the shared population receipt to every admitted basket row.
3. Add top-level observation metadata/refusals.
4. Emit a line-start warning for insufficient baskets without changing complete-basket math.
5. Prove Baskets and Group Flow report the same effective session on the same fixture.

## Task 6 — Targeted verification and real committed-data replay

**Files:**
- Create: `scripts/theme_observation_integrity_replay.py` only if a reusable read-only harness is justified; otherwise keep the replay in the external receipt directory.

1. Run targeted suites:
   - `tests/test_group_flow.py`
   - `tests/test_group_flow_regional.py`
   - `tests/test_theme_scoring.py`
   - `tests/test_theme_scoring_leadership_split.py`
   - `tests/test_theme_scoring_conflicted.py`
   - `tests/test_basket_member_context.py`
   - `tests/test_baskets.py`
   - `tests/test_baskets_calibration.py`
2. Run relevant CI job commands from `.github/ci/legacy-jobs.yml` or the selected pack.
3. Use either a detached full worktree pinned to the exact current `origin/main` SHA or extract the required cache blobs into an external receipt directory; never substitute an unpinned mutable checkout.
4. Execute the repaired code read-only against that exact data epoch.
5. Assert nuclear 9/9, memory 4/4, semicap 16/16 and grid 24/24 on the effective common session, or capture exact typed refusals.
6. Confirm `git status --short -- data site` is empty.

## Task 7 — Adversarial review, durable record, and delivery

**Files:**
- Create a narrowly scoped `DSC-*` only if the all-null-session mechanism is not already durably recorded.
- Create/update a handoff only if material continuation remains after this PR.

1. Review for duplicate systems, basis splicing, false freshness, silent omission, score/risk changes and incomplete consumer compatibility.
2. Run `python3 scripts/agentos.py validate` if Agent OS records are added.
3. Run contract/design/validated-claims guards required by the touched paths.
4. Commit explicit paths, push `claude/theme-observation-integrity-w0-20260910-sol-001`, open the PR, and add `merge-on-green` after checking for any hold barrier.
5. Wait for all binding checks to conclude. Repair real reds; never merge pending checks.
6. Squash-merge after green, verify the exact merge is on `origin/main`, and rerun the read-only real-data proof against merged bytes.
7. Record exact next action: W1 semantic projection repair, still avoiding PR #7010 path collision until reconciled.
