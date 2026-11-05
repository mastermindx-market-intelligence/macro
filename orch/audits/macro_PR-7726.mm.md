---
pr: 7726
repo: mastermindx-market-intelligence/macro
title: "feat(prophet): own B4 structural risk ceiling"
merged_at: "2026-09-22T12:36:15Z"
merge_commit: "2a5d60d0d3"
head_sha: "f43f55ebcf4ef6d22d914e9e1e0e48add6669f83"
branch: "claude/prophet-b4-risk-ceiling-policy-20260922-sol-001"
class: half-B (backend, 2 files, +180 lines, 0 deletions)
audited_at: "2026-09-22"
audited_by: "idle-audit (orchestrator-driven, ROUTE review via reviewer model policy)"
prior_art: "orch(audit): record macro PR #7629 plain-language/theme/validated-claims audit (2026-09-21)"
---

# macro PR #7726 — plain-language / theme / validated-claims audit

## PR metadata

| field | value |
|---|---|
| PR | [#7726](https://github.com/mastermindx-market-intelligence/macro/pull/7726) |
| Title | feat(prophet): own B4 structural risk ceiling |
| Merged | 2026-09-22T12:36:15Z |
| Merge commit | `2a5d60d0d3` (squash-merge into `main`) |
| Author/head SHA | `f43f55ebcf4ef6d22d914e9e1e0e48add6669f83` |
| Files | `engine/prophet_entry_policy.py` (+100/-0), `tests/test_prophet_strategy_definition.py` (+80/-0) |
| Lines | +180 / -0 |
| Type | Backend policy owner — pure Python policy module + tests |
| Scope | Extend `engine/prophet_entry_policy.py` with a single `risk_ceiling` fact for the already-accepted `EARLY_LEADERSHIP_SECTOR_ROTATION / 2_15_SESSIONS / new_entry` control sleeve |
| Cross-refs | Prophet Entry Truth `#6805` comment `5774665916`, operation `prophet-b4-risk-ceiling-policy-20260922-sol-001` |

## Pre-flight: is this audit a re-do?

`git ls-tree origin/main -- orch/audits/` confirms `macro_PR-7726.mm.md` does **not** exist on `origin/main`. No working-tree draft at `orch/audits/macro_PR-7726.mm.md` (verified via `git status --porcelain`). PR is the freshest merged half-B in the last 24 h whose verdict cannot have been recorded before — every macro PR in the 7629–7701 window already carries its own audit on `origin/main`; #7726 (12:36:15Z merge) is the next one past that sweep.

## Plain-language findings

**Verdict: PASS** — no user-facing copy is introduced, modified, or gated.

**Scope of textual surface.** The diff touches only:

- `engine/prophet_entry_policy.py` — module-level constants (`RISK_POLICY_VERSION`, `RISK_POLICY_ERA`, `RISK_GATE`, `RISK_ATR_CEILING = 2.0`), two private helpers (`_finite_positive_number`, `_risk_policy_material`), and one public function `evaluate_risk_ceiling(...)` whose docstring is a five-line policy disclosure.
- `tests/test_prophet_strategy_definition.py` — five new pytest functions, all `assert`/`pytest.raises` against dict shapes; no string fixtures.

**No glance-tier text is added.** No template (`.j2`), no static page (`.html`), no manifest, no JS payload, no command copy (`scripts/check_macro_command_copy.py` has no contract on this PR). The single docstring is internal documentation — it explicitly says "*The constant is not a calibrated optimum and cannot establish promotion, sizing, execution or trade authority.*" which is the **opposite** of the design-doctrine banned-glance vocabulary (`trading thesis`, `validated edge`, `we recommend`, `edge confirmed`, etc.).

**Bilingual parity (EN/ZH)**: N/A — no human-language strings enter the surface. No `t(...)` calls, no `data-i18n`, no `l-en`/`l-zh` blocks. `check_title_i18n.py` and the bilingual-UI test would have nothing to flag because nothing moved through their gates.

**Internal exception messages** (`f"{field} must be numeric"`, `f"{field} must be finite and > 0"`) are Python exceptions on the contract boundary — they surface through whatever upstream error path uses them, not directly to anonymous readers. Even at the worst case the language is short, declarative, and free of jargon. No action.

**Operator-visible docstring** correctly uses the standing `CONTROL_ONLY / SHADOW_ONLY` vocabulary rather than promotional prose — this is itself a plain-language positive signal: a half-B internal PR that **says plainly** "this is not calibrated" is exactly the discipline the law wants.

## Theme findings

**Verdict: PASS** — no design-system surface is touched.

**Mode**: `python3 scripts/check_design_system.py --mode enforce-added --diff-file <pr7726.diff>` returns:

```
::notice title=design-system::R0 enforce-added: 0 blocking finding(s) (25321 further pre-existing, non-blocking finding(s) in the estate — run --mode report for the full census)
design-system ratchet — mode=enforce-added blocking=0 (estate pre-existing, non-blocking: 25321)
```

**Scope.** The diff is two Python files. There is no template, no CSS, no JS, no asset. Theme law (dark/light art direction, palette, material, governed tokens, runtime stylesheet injection) has no purchase on a backend policy module.

**Light/dark art direction (TP-0, 2026-08-27)** — N/A; the PR does not touch any rendered surface.

**Runtime stylesheet injection** (`scripts/check_runtime_style_injection.py`) — N/A; no JS module added.

**Visual evidence** (`scripts/check_ui_visual_evidence.py`) — N/A; no UI asset, no screenshot, no fixture.

**Reuse of existing planes.** The PR deliberately composes the existing `evaluate_session_eligibility` plane (`validate_strategy_definition` is reused; the same `pep:` / `pepf:` content-addressed receipt scheme is reused; the same `strategy_definition_id` is the binding key). It does not carve a Prophet-specific UI plane — this is the structurally correct posture for a backend policy owner.

## Validated-claims findings

**Verdict: PASS** — no new validated claims; explicit anti-validated status markers throughout.

**Check**: `scripts/check_validated_claims.py --list` against the PR head (`engine/prophet_entry_policy.py`) — no MISS or new OK entry is introduced by the diff. The PR file does not contain the substring `validated` at all (verified by direct inspection: `grep -n validated <engine/prophet_entry_policy.py@7726>` → 0 hits). The new test file is symmetric (`grep` → 0 hits).

**Honest status markers** — the diff actually _encodes_ the un-calibrated posture into the payload itself, which is exactly the compliance posture:

| field in payload | value | purpose |
|---|---|---|
| `scientific_status` | `"CONTROL_ONLY"` | declares not a published finding |
| `authority_tier` | `"SHADOW_ONLY"` | declares not in production routing |
| `threshold_status` | `"INITIAL_OPERATION_CONSTANT_NOT_CALIBRATED"` | declares the 2.0 ATR constant is an operation placeholder, not an optimized parameter |
| `calibration_requirement` | `"PROSPECTIVE_OR_OOS_SAME_TAPE_WITH_COSTS"` | declares the future promotion gate, in plain terms |
| `authority.can_rank` / `can_admit_candidate` / `can_size` / `can_execute` / `can_trade` | all `False` | five explicit denials of promotion, ranking, sizing, execution, and trade authority |
| `universal_percent_ceiling` | `None` | deliberately denies the existence of a "universal stop" |
| `geometry_owner` | `"incumbent_entry_owner_invalidation"` | defers the entry/stop geometry to the existing owner |
| `volatility_input` | `"owner_supplied_atr"` | ATR comes from the upstream owner, not invented |

The PR body echoes the same discipline ("shadow control ceiling", "not a calibrated optimum", "explicitly published as INITIAL_OPERATION_CONSTANT_NOT_CALIBRATED", "deliberately no universal percent-of-price ceiling", "`DRAFT / HOLD-FOR-SOL`") and pre-locks the next gate ("Require exact-head hosted gates and one genuine non-author semantic review before Ready/merge"). The body also names non-goals the diff does not violate: no B1/B3 mutation, no entry-zone/chase/stop recomputation, no liquidity policy, no #7581 runtime wiring, no ranking/sizing/execution authority.

**Receipt completeness.** Each fact binds `strategy_definition_id`, `entry_policy_version`, `risk_policy_version`, `risk_policy_era`, `horizon`, `horizon_role`, `scientific_status`, `authority_tier`, `method`, `threshold`, `risk_to_invalidation_atr`, `risk_to_invalidation_pct`, `policy_receipt` (`pep:`), and `fact_receipt` (`pepf:`). That is the standard control-owner receipt shape — nothing is hidden, every fact is content-addressed.

**No aspirational language** appears anywhere: no "edge", "alpha", "validated", "we recommend", "optimal", "best", "expected to deliver". The half-B scope is correctly framed as **owning one fact**, not as **shipping a capability**.

## Overall verdict

**PASS on all three dimensions.**

- **Plain-language**: PASS — no user-facing copy is touched.
- **Theme**: PASS — design-system enforce-added reports 0 blocking findings; the PR adds no template/CSS/JS/asset.
- **Validated-claims**: PASS — no `validated` substring in either changed file; the payload itself encodes the un-calibrated, non-promotion, non-authoritative posture with explicit markers; the PR body declares `DRAFT / HOLD-FOR-SOL` and pre-locks the next gate.

This is a model half-B policy-owner PR for the B4 lane: small scope, content-addressed receipts, explicit anti-promotion markers, no user-facing surface change, no design surface change. The audit is filed so a future sweep (or the next half-B Prophet policy owner) has an attested reference for "what compliance looks like on a single-fact policy owner that is honest about not being calibrated".