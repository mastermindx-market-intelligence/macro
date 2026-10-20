# Plain-language / theme / validated-claims audit — macro PR #7632

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-21.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7632 |
| title | `fix(risk): make historical replay match live state transitions` |
| merged_at | 2026-09-22T01:01:07Z |
| head (semantic) | `f8b2bb5d3fad22b5d62eea2991fa507a3cd22517` |
| merge_commit | `7c6e35163c9f67087ffe174a7ab3810f47ce6a45` |
| base | `main` at `3776ad133c748a177b9db9f7867575721f41ad86` |
| branch | `claude/*` (per PR body "Source base: `4eafb563cecb5747c9b5414a70a7281a33bdb6e2`") |
| changed files | **7 files, +286 / −131.** `agentos/discoveries/DSC-RISK-RADAR-REPLAY-LIVE-STATE-PARITY-DEFECT.md` (+35 / 0, ADDED — frontmatter-only `DSC-*` record); `engine/risk_radar.py` (+112 / −64, MODIFIED — single-canonical state-transition owner `_resolve_state_row` extracted, live `compute()` now delegates to it); `engine/risk_radar_backtest.py` (+37 / −32, MODIFIED — replay `state_series` threads `sigs` and calls the same canonical owner); `scripts/research/risk_radar_caution_persistence.py` (+1 / −1, MODIFIED); `scripts/research/risk_radar_episode_atlas.py` (+1 / −1, MODIFIED); `scripts/research/risk_radar_gate_latency.py` (+16 / −24, MODIFIED — passes `sigs` through to the canonical transition); `tests/test_risk_radar.py` (+84 / −9, MODIFIED — red-first parity cases for the three divergent scenarios). |
| additions / deletions | 286 / 131 |
| labels | none visible at fetch time; merges from the macro sweeper signature on the listed timestamp. |
| scope collision | none — PR body explicitly bounds scope to repair of the historical replay-vs-live state machine parity and explicitly disclaims any live probability/band/score/weight/gate/policy/sizing/ranking/ledger/capital-authority change. |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --limit 30` against `git ls-tree origin/main -- orch/audits/` (per the standing workflow memo `orch_audit_filename_convention.md`): every recent macro merge in the prior idle-audit window (last ~24 h) was either (a) `orch(audit)` record-keeping PRs (#7686, #7682, #7673, #7671, #7659, #7651, #7644, #7636, #7627 — filing-only); (b) `fix(ci)` infra-only PRs (#7678, #7628, #7621 — `check_design_system.py --mode enforce-added` reports zero template/JS/CSS surface added by them, so they are out-of-scope for a half-B plain-language/theme/validated-claims audit); (c) `[MO-A heal]` governance repairs (#7639, #7637 — research/governance lane); (d) `research(risk)` evidence-only deliverables (#7683, #7666 — research-output files plus a research-only Python script and a test, user-facing surface untouched); (e) PR #7629 (already produced an audit file at `orch/audits/macro_PR-7629.mm.md`, currently untracked — no new audit owed). The remaining 24-h merge with a real audit-relevant engine surface, without a committed audit, and with a substantive user-impact claim (research-grade parity repair that materially changes state-bucket composition for replay-derived studies) is **#7632** — a half-B scope: 7 files, +286/−131, no new user-facing copy or template surface, no claim authorship, no theme-token or layout change, but a real parity repair to the canonical Risk Radar state machine that the design system + bilingual + retrospective-evidence chain all need to read.

**Nature of change (single-defect parity repair, half-B engine surface-touch):**

1. *Defect — historical replay did not reproduce the shipped live state machine.* The Risk Radar replay previously used two rules production had explicitly replaced: (i) naive `>=2 Tier-A caution` conjunction (rejected in `RISK_RADAR_TUNING.md` in favour of validated armed leg + second Tier-A at watch); (ii) permissive Tier-B escalation that did not exclude measured-zero lift_2020 firing legs. Three red-first parity tests captured the regression in opposite directions (two hot Tier-A with no validated armed leg; validated armed + second at watch; hot Tier-B whose only firing leg has measured lift_2020==0.0). The replay chose the wrong state in each case. The PR extracts a single canonical row-level state transition owner `_resolve_state_row` in `engine/risk_radar.py` and has both `compute()` (live) and `state_series()` (replay) call it with the same causal signal row — eliminating the architectural surface that let research drift silently back to the rejected rules.

2. *Where the impact lives.* No live probability / band / score / weight / gate / policy / sizing / ranking / ledger / capital authority is changed (PR body explicitly disclaims). What changes is the historical **state bucket composition** for research re-runs: 152 of 8,216 known historical state days (1.85%) migrate, 46/1,687 since 2020 (2.73%). The composition shift is concentrated in the caution→watch / elevated↔caution / risk-off↔elevated movements — exactly the buckets any state-ladder calibration study uses as its object. Four replay-derived studies are now invalidated and explicitly named in the PR body (#7586 fixed-episode warning persistence, #7599 gate selectivity/latency, #7608 five-session caution persistence, #7611 state-ladder calibration; the last returned to Draft). The forward-probability audit (#7603 family) is a separate evidence class and is **not** invalidated — the PR names this distinction.

3. *Evidence preservation.* The PR adds a `DSC-*` discovery record (`DSC-RISK-RADAR-REPLAY-LIVE-STATE-PARITY-DEFECT.md`) with the standard frontmatter contract — `claim`, `falsifier`, `so_what`, `kind: data`, `verified_at`, `verified_by`, `scope`, `confidence: verified` — so the invalidator is durable and discoverable for future research lanes that might otherwise re-run invalidated replay.

## Diff content (scoped to this audit)

7 files, no new template/component/CSS/JS surface. Five of the seven files are engine / research / test Python; one is the new `DSC-*` discovery frontmatter-only markdown; one is a test module. The visible-to-product surface is zero.

### `agentos/discoveries/DSC-RISK-RADAR-REPLAY-LIVE-STATE-PARITY-DEFECT.md` (+35 / 0, ADDED)

Standard `DSC-*` frontmatter shape (35 lines, all frontmatter; no body prose). Required `claim` / `falsifier` / `so_what` / `kind` / `verified_at` / `verified_by` / `scope` / `confidence` keys are all populated per the `agentos/README.md` schema. The `verified_by` cites the exact test command (`python3 -m pytest tests/test_risk_radar.py -k replay_matches_live -q`); the `scope` enumerates six owned paths (`engine/risk_radar.py`, `engine/risk_radar_backtest.py`, three research scripts) and two program/scope markers (`macro`, `grey-deer-risk-intelligence`); `confidence: verified` matches the standing posture for empirically-falsified defects.

### `engine/risk_radar.py` (+112 / −64, MODIFIED)

Two semantic moves:

- **New canonical helper `_resolve_state_row`** (lines 877–967 in the post-merge file). Takes `(subrow, sigrow, calib, gate_met)` and returns `{state, state_ungated, conjunction, hot_a_count}`. Owns Tier-A origin (max band across Tier-A scares), armed-and-confirm conjunction (validated armed leg + second Tier-A at watch, replacing the rejected naive-count rule), Tier-B escalation eligibility (display-only exclusion + measured-zero lift_2020 exclusion), and the broad-tape loud-state cap. Single source of truth.
- **Live `compute()`** now delegates to `_resolve_state_row(row, sigrow, calib, gate_met=bool(gate.get("met")))` instead of inlining the rule. The docstring/comment block immediately above the new helper explains the parity intent verbatim: "Replay code must call this helper with the same causal signal row rather than reconstructing a simplified state machine from sub-scores."
- **`trajectory()`** signature gains an optional `sigs` parameter so the replay can pass the original causal frame through (default behaviour preserved — when `sigs is None` it still calls `leading_signals()` as before).
- The docstring on `subscore_series` updates a stale reference (`"enforced only in _tierb_can_escalate"` → `"enforced only in _resolve_state_row"`); the same string change appears in `display_only_legs`' docstring. Pure docstring hygiene.

### `engine/risk_radar_backtest.py` (+37 / −32, MODIFIED)

The replay's `state_series()` signature gains the same optional `sigs` parameter, and the body delegates to the new canonical owner. The net diff is a refactor + delegation; no semantic change to the replay output values other than the now-parity-correct state assignment.

### `scripts/research/risk_radar_caution_persistence.py` (+1 / −1, MODIFIED)
### `scripts/research/risk_radar_episode_atlas.py` (+1 / −1, MODIFIED)
### `scripts/research/risk_radar_gate_latency.py` (+16 / −24, MODIFIED)

Research scripts that touched the inlined helper now either thread `sigs` through to `state_series`/`trajectory` or call the canonical owner. The PR's body also names the research-ladder-study scripts that must be re-run before any state/probability/gate change (#7586, #7599, #7608, #7611); none of those scripts is itself changed by this PR — only the call sites they depend on are.

### `tests/test_risk_radar.py` (+84 / −9, MODIFIED)

Three new red-first parity tests covering exactly the three divergent scenarios named in the defect description (two hot Tier-A with no validated armed leg; validated armed + second at watch; hot Tier-B whose only firing leg has measured lift_2020==0.0). Each test failed in the stated direction on the pre-fix branch and passes after the canonical owner is in place. Test naming documents the intent: `replay_matches_live` / `state_transitions_match_live`.

## Plain-language findings

### 1.1 Pass — there is no user-facing copy in this PR; the macro-side plain-language discipline is structurally inapplicable on this diff

The diff contains zero template (`templates/`), zero product HTML (no `site/`), zero CSS, zero JS, zero chat surface, zero bilingual receipt text. Every changed file is either (a) Python engine (`engine/risk_radar.py`, `engine/risk_radar_backtest.py`), (b) research Python (`scripts/research/risk_radar_*.py`), (c) Python tests (`tests/test_risk_radar.py`), or (d) the `DSC-*` discovery markdown (frontmatter-only). `tests/test_bilingual_ui.py` and `scripts/check_bilingual.py` cannot produce a finding against this diff by construction — there is no template surface to scan.

For the project-side plain-language read, the only prose that lands in this PR is the `DSC-*` frontmatter (`claim`, `falsifier`, `so_what`) plus the docstring/comment updates in `engine/risk_radar.py`. None of those strings is user-facing; they are internal documentation for engineers running the engine and for future research lanes that read the discovery. The PR body itself is a defect-repair description with the canonical anti-promotion closer ("No live probability, band, score, weight, gate, policy, sizing, ranking, ledger, or capital authority is changed here."), matching the same shape used by other recent macro research/fix PRs (#7619, #7586, #7610, #7599).

### 1.2 Pass — the canonical owner's internal comments preserve the prose discipline

The new `_resolve_state_row` helper carries substantive prose comments naming the standing rejection (the naive-count conjunction), the VSB W6 doctrine on `display_only` legs, and the measured-zero lift_2020 exclusion rule. None of those strings is user-visible; they are engineering rationale that future maintainers of `engine/risk_radar.py` need in order to recognise the rejection rationale before re-introducing the rejected rule. The comments do not oversell, do not use banned-glance vocabulary (`validated` / `proved` / `guaranteed` / `certified`), and explicitly disclaim the role of every other rule the helper replaces.

### 1.3 Pass — the `DSC-*` discovery frontmatter reads "discovery", not promotion

The `claim:` field is bounded to "the historical US Risk Radar state replay did not reproduce the shipped live escalation rules", the `so_what:` field is bounded to "replay-based studies produced before the parity repair must be rerun before they can support state/probability/gate changes", and the `confidence:` field is `verified` rather than `validated` — the standard DSC posture for an empirically-falsified defect rather than a promotion-bearing fact. `kind: data` is honest (the discovery is an empirical false-rejection, not a behavioural promotion). No DSC content makes any new affirmative claim about live Risk Radar behaviour.

## Theme findings

### 2.1 Pass — `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7632.diff` reports **0 blocking findings**

```
::notice title=design-system::R0 enforce-added: 0 blocking finding(s) (25334 further pre-existing, non-blocking finding(s) in the estate — run --mode report for the full census)
design-system ratchet — mode=enforce-added blocking=0 (estate pre-existing, non-blocking: 25334)
```

Run command: `gh pr diff 7632 --repo mastermindx-market-intelligence/macro > /tmp/pr7632.diff && python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7632.diff`. The 25,334 pre-existing non-blocking estate findings are unchanged by this PR (the report's own caveat applies — the `enforce-added` mode reads the PR's own diff lines only and does not assert against pre-existing debt). The diff literally contains zero template/component/CSS/JS lines, so the design-system check has zero lines to assert against.

### 2.2 Pass — TP-0 dark/light × EN/ZH × 1440/390 evidence matrix is structurally inapplicable; the change does not touch any visual surface

The TP-0 dark-and-light-are-two-art-directions rule (`scripts/check_design_system.py` + the standing design-doctrine §Theme art direction) requires every material UI packet to name DARK TREATMENT, LIGHT TREATMENT, which mechanisms intentionally differ, the reference/baseline, theme-specific degraded states, and the evidence matrix (dark/light × EN/ZH × desktop 1440 / mobile 390).

This PR adds zero user-visible surface. Every changed line is in `engine/`, `scripts/research/`, `tests/`, or the new `agentos/discoveries/` markdown — no template, no inline style, no `<style>` block, no CSS rule, no JS payload. The "Token substitution alone is never proof of a light design" rule, the "Substantive product styling may not be authored as an opaque runtime stylesheet system inside page/composer JavaScript" rule, and the "every material UI packet must name DARK TREATMENT / LIGHT TREATMENT" rule are all structurally inapplicable. **Consistent with TP-0**.

### 2.3 Pass — `check_runtime_style_injection.py` is out-of-scope by construction

The diff contains no `style="..."` injection, no `style.textContent =`, no parallel palette, no duplicated light/dark branches inside JS, no inline `<style>` block, no `data-theme` override, no `class` attribute containing theme tokens. There is no JS payload change anywhere in the diff.

### 2.4 Pass — no theme-art-direction assertion is made or implied

The PR body does not claim a dark/light, EN/ZH, mobile/responsive, palette, type, motion, or material-design effect. It closes with the anti-promotion line plus the invalidation disclosure ("Replay-derived studies created before this repair must be rerun before they can support state/probability/gate changes"). No evidence matrix is owed because no design surface is touched.

## Validated-claims findings

### 3.1 Pass — `python3 scripts/check_validated_claims.py --list` produces no MISS row for this PR's diff

Run: `python3 scripts/check_validated_claims.py --list` filtered for any `7632` / `RISK-RADAR-REPLAY` key produces no output — confirming the validator has no registered claim against this PR and nothing in the diff creates one. The PR's only user-facing-shaped text is the canonical anti-promotion closer ("No live probability, band, score, weight, gate, policy, sizing, ranking, ledger, or capital authority is changed here."), which is the standing disclaimer that exempts the change from the promotion-bearing claim regime entirely.

### 3.2 Pass — the `DSC-*` frontmatter says `confidence: verified`, not `validated`

The DSC posture is the calibrated empirical-falsification class (`verified`) rather than the gauntlet-promotion class (`validated`). This is the appropriate choice for an internal-engine defect: the discovery records an empirically-falsified parity failure rather than authoring a new affirmative user-facing claim. The DSC frontmatter is not surfaced to users by any rendering pipeline (the `agentos/` knowledge plane is a worker knowledge plane; `docs/AGENT_OS_STATE.md` is nightly-regenerated, never hand-edited, and does not appear on the user-facing site per `DEC:AGENTOS-NIGHTLY-IS-THE-ONLY-REGENERATOR`). The DSC's `validated` field is not the user-facing promotion token — that token is governed by `scripts/check_validated_claims.py` against `data/regime/validated_claims_allowlist.json` and templates, neither of which is touched here.

### 3.3 Pass — the PR body does not introduce any promotion-bearing claim

PR body opening: "Make the historical US Risk Radar evaluator reproduce the shipped live state machine instead of a stale simplified replica." This is a defect-repair claim with bounded scope (the state machine), not a release/upgrade/score/rank promotion. PR body closing: "No live probability, band, score, weight, gate, policy, sizing, ranking, ledger, or capital authority is changed here." This is the canonical anti-promotion line for an engine-only defect-repair PR.

The PR body's mid-section does not claim any user-facing capability change. The body explicitly names which prior replay-derived studies are invalidated (#7586 / #7599 / #7608 / #7611) and explicitly distinguishes them from the recorded forward-probability audit (which is a separate evidence class, not invalidated). The named invalidation is itself a **defect**, not a promotion: the studies are flagged as needing re-runs before they can support any future change, with no language that implies the re-runs are already done.

### 3.4 Pass — `check_validated_claims.py --mode list` continues to enforce the user-facing `validated` vocabulary unchanged

`tests/test_validated_claims_engine.py`, `tests/test_validated_claims_registry_source.py`, `tests/test_validated_claims_structural_scope.py`, and `tests/test_validated_claims_thirdparty.py` are the surface that enforces the user-facing claim discipline. None of them read or assert against engine code or research scripts — they read `templates/` and the structural scope of `data/regime/validated_claims_allowlist.json`. This PR modifies none of those surfaces. The validator's behaviour is unchanged on this PR. **Consistent with the structural-scope contract.**

## Overall verdict

**VERDICT: PASS — clean half-B engine-parity repair, no blocking issue, no user-facing surface touched.**

| dimension | result | notes |
|---|---|---|
| plain-language | PASS | Diff contains zero user-facing copy (only engine Python, research Python, tests, and `DSC-*` frontmatter). The macro-side plain-language discipline (`tests/test_bilingual_ui.py` + `scripts/check_bilingual.py` + design-doctrine banned-glance vocabulary) is structurally inapplicable on this diff. The `DSC-*` discovery uses `confidence: verified` (calibrated empirical-falsification) not `validated` (gauntlet-promotion). The PR body carries the canonical anti-promotion line and a defect-repair framing, no banned vocabulary. |
| theme | PASS | `check_design_system.py --mode enforce-added --diff-file /tmp/pr7632.diff` reports 0 blocking findings. The diff contains zero `templates/`, `site/`, `.css`, `.js`, `style=`, `data-theme`, or component lines. TP-0 dark/light × EN/ZH × 1440/390 evidence matrix is structurally inapplicable (no visual surface added). `check_runtime_style_injection.py` is out-of-scope (no JS payload). The PR does not author any design surface. |
| validated-claims | PASS | `check_validated_claims.py --list` produces no MISS row against the PR's diff — no template surface is touched. The `DSC-*` discovery records an empirically-falsified defect (`confidence: verified`, `kind: data`) not a promotion-bearing claim, and lives in the worker knowledge plane (no user-facing render path). The PR body disclaims any promotion-bearing change ("No live probability, band, score, weight, gate, policy, sizing, ranking, ledger, or capital authority is changed here.") and explicitly names which downstream studies must be re-run before they can support future state/probability/gate changes. |
| merge hygiene | PASS | 7 files, +286 / −131. The substantive fix is the single canonical state-transition owner `_resolve_state_row` extracted in `engine/risk_radar.py` and called by both `compute()` (live) and `state_series()` (replay) — eliminating the architectural surface that allowed research drift. Three red-first parity tests fail in opposite directions before the repair and pass after. Test names (`replay_matches_live` / `state_transitions_match_live`) document the intent. The four named invalidated studies (#7586, #7599, #7608, #7611) are explicitly flagged in the PR body as needing re-runs before they can support state/probability/gate changes; the forward-probability audit (#7603 family) is explicitly excluded from the invalidation as a separate evidence class. The `DSC-*` discovery carries the standard frontmatter contract (`claim`, `falsifier`, `so_what`, `kind`, `verified_at`, `verified_by`, `scope`, `confidence`). |

**Non-blocking follow-ups (out of this lane's owned paths):**

1. The PR adds one new public export to `engine/risk_radar.py` (`_resolve_state_row`) that downstream research will eventually call directly. The docstring already names the contract; a future `agentos/discoveries/DSC-RISK-RADAR-RESOLVE-STATE-ROW-CONTRACT-FREEZE.md` freeze-record could formalise the helper's contract once it's been battle-tested by the four named invalidated studies re-running. Out-of-scope for this PR.
2. `trajectory()`'s signature change adds an optional `sigs` parameter; callers that did not previously thread `sigs` continue to call `leading_signals()` internally (the default branch preserves prior behaviour). The research-script call sites that DO need `sigs` were updated in this PR. If a future research script adds another `trajectory()` call site, the same threading change will be needed there. Out-of-scope for this PR; the pattern is now established by the three updated research scripts.
3. The PR's architectural move (single-canonical owner, eliminating the surface that allowed drift) is exactly the shape that should be retro-applied to any future research script whose current state model can drift from the live engine. A future `agentos/DSC-RESEARCH-SCRIPT-CANONICAL-OWNER-ENFORCEMENT.md` could enumerate which research scripts should adopt the same delegation pattern. Out-of-scope for this PR.

**No blocking issue found. No retry. No scope expansion. Audit complete.**
