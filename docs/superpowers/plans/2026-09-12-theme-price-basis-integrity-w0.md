# Theme Price-Basis Integrity W0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Baskets, Group Flow thematic baskets, and Theme Scoring one safe frozen-calendar price-resolution contract without changing sector-PIT or decision authority.

**Architecture:** Extend `lib/closes_panel.py` with a pure whole-column thematic resolver. Group Flow keeps its incumbent primary sector matrix and adds a separate thematic matrix; Baskets and Theme Scoring consume the same resolution semantics. Divergent sources never row-splice unless the incumbent `_stitch_ok` measurement gate proves the donor safe.

**Tech Stack:** Python 3.12, pandas, pytest, existing Macro close-panel and basket engines.

**Spec:** `docs/superpowers/specs/2026-09-12-theme-price-basis-integrity-w0-design.md`

## Global Constraints

- Source base: `acb0d75e49596a62230542cf297a84391694f765`; re-fetch current main before push/merge.
- No new store, queue, registry, lifecycle, publication, price service, or authority plane.
- Supplemental data never extends the primary/common-session calendar.
- Whole-source selection only; donor backfill requires incumbent `_stitch_ok` success.
- Ties prefer `baskets_extras`; fresher observed source otherwise wins.
- Preserve sector-PIT `closes/rets`, formulas, labels, recommendations, risk transitions, and authority.
- No production `data/` or `site/` write in verification.
- PR #7064 remains a separate Draft/HOLD research carrier.

---

### Task 1: Pin the whole-column resolver contract RED

**Files:** Modify `tests/test_closes_panel_freshness.py`; later modify `lib/closes_panel.py`.

**Interfaces:** Produce `resolve_thematic_close_panel(primary: DataFrame, supplemental: DataFrame | None, tickers) -> tuple[DataFrame, dict]`.
- [ ] Add failing tests for supplemental-fresher, primary-fresher, tie→supplemental, supplemental-only, unresolved, and safe identical-series donor stitching.
- [ ] Assert a divergent losing source never fills winner-null history.
- [ ] Assert output index equals primary index and supplemental tail cannot advance it.
- [ ] Assert receipt source counts, per-ticker source/reason, stitch diagnostics, unresolved list, basis disclosure, and `measurement_only` authority.
- [ ] Run only the new tests and confirm they fail because the helper is absent.
- [ ] Implement the minimal pure helper in `lib/closes_panel.py` using existing `_stitch_ok` and index normalization.
- [ ] Re-run the new tests to GREEN, then `tests/test_closes_panel_freshness.py` in full.

### Task 2: Route Group Flow thematic baskets without repricing sectors

**Files:** Modify `tests/test_group_flow.py`, `engine/group_flow.py`, and `engine/baskets.py` only for shared membership-ticker extraction if needed.

**Interfaces:** `group_flow._setup('us')` adds `theme_closes`, `theme_rets`, `theme_price_resolution`; legacy `closes/rets/idx/bench` remain.

- [ ] Extend the existing extras/common-session fixture so RED asserts `closes['A']` remains primary while `theme_closes['A']` follows the resolver and extras cannot advance `idx`.
- [ ] Add a RED fixture proving a stale divergent supplemental series cannot replace a fresher primary theme series.
- [ ] Implement basket-member union extraction and call the shared resolver before the legacy extras-only union.
- [ ] Compute `theme_rets` on the resolved thematic matrix.
- [ ] Change only Group Flow's thematic-basket branch to use thematic matrices; leave PIT sector frames on legacy matrices.
- [ ] Run the new tests and the full Group Flow + regional Group Flow suites.

### Task 3: Make Baskets consume the shared resolver

**Files:** Modify `tests/test_group_flow.py`, `engine/baskets.py`.

**Interfaces:** `compute_baskets()` carries additive `price_resolution` and uses the resolver result for returns/member output.

- [ ] Add a RED test that Baskets and Group Flow produce identical thematic price-source choice on the same synthetic overlap.
- [ ] Add a RED test that a basis-divergent deep series is selected whole rather than backfilled from primary.
- [ ] Replace Baskets' local `extras[overlap].combine_first(closes[overlap])` block with `resolve_thematic_close_panel`.
- [ ] Preserve SPY/common-session alignment before resolution and all existing observation/refusal math afterward.
- [ ] Run Baskets/Group Flow focused tests and existing basket suites.
### Task 4: Route Theme Scoring through thematic matrices

**Files:** Modify `tests/test_group_flow.py` and `engine/theme_scoring.py`.

**Interfaces:** `compute_theme_intel()` reads `theme_closes/theme_rets` when supplied and falls back to legacy `closes/rets` for old fixtures.

- [ ] Add a RED test where legacy closes and thematic closes disagree and assert population/scoring preparation reads the thematic matrix.
- [ ] Implement the minimal matrix selection at the start of `compute_theme_intel()`.
- [ ] Carry additive `price_resolution` from `_setup()` into the returned payload.
- [ ] Preserve all formula, threshold, sort, conflict, risk-transition, label, and recommendation code.
- [ ] Run Theme Scoring, leadership split, conflicted, and observation-integrity suites.

### Task 5: Real-input read-only proof and integration

**Files:** No production artifact writes. Create a reusable script only if existing builders cannot expose the receipt without writing; otherwise execute a temporary external proof harness.

- [ ] Point candidate code at a pinned committed data checkout without modifying that checkout.
- [ ] Run the real resolver over the current US basket membership and committed primary/extras inputs.
- [ ] Print effective session, requested/resolved/unresolved, source counts, stitch count, and basket admission/refusal parity.
- [ ] Run real Group Flow/Theme Scoring compute in-memory and compare admitted/refused basket IDs with Baskets' in-memory result.
- [ ] Assert `git status --short -- data site` remains empty in the candidate checkout.
- [ ] Run relevant focused pytest suites and CI-local guards for changed paths.

### Task 6: Review and delivery

**Files:** The spec/plan plus implementation/test paths only; add Agent OS records only if a durable fact is not already captured by this spec.

- [ ] Re-fetch `origin/main`; compare current-main movement against every changed path and material dependency.
- [ ] Review for duplicate price planes, hidden row splices, calendar advancement, sector repricing, authority leakage, and false provenance claims.
- [ ] Run `git diff --check`, targeted suites, and required contract/CI registration guards.
- [ ] Commit explicit paths and push `claude/theme-price-basis-integrity-w0-20260912-sol-001`.
- [ ] Open one PR, wait for concluded checks, repair genuine candidate reds, and preserve any real hold barrier.
- [ ] After merge, verify exact merged bytes and repeat the read-only real-input proof before claiming source delivery complete.
- [ ] Resume the original program at the next dependency: the separately governed 4H/1D/2D/3D temporal-grain/MACD research wave downstream of leadership persistence.
