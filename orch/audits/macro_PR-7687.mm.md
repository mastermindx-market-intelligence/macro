# Plain-language / theme / validated-claims audit — macro PR #7687

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-22.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7687 |
| title | `fix(prophet): keep optional structural overlay from deadlocking B4` |
| merged_at | 2026-09-22T07:39:39Z |
| head (semantic) | `50ad128f3e767475d4b179e6a2790b07f33b12be` |
| base | `main` (PR body: "fresh source base: `main@83777fa19a827fffdc9b780c4f2dcc0c146bf486`") |
| branch | `claude/*` per standing fleet law; protected Mastermind re-pin `1358f9d9ab7b612e03c441982d442118116f837d` recorded at execution start (`mastermind.sol_skillpack.v1` 1.0.1 / bootstrap-major 1) |
| changed files | **2 files, +21 / −2.** `engine/prophet_entry_availability.py` (+6 / −2, MODIFIED — two-line `if gate_values["structural_invalidation"] == "UNKNOWN"` block deleted and replaced with a 6-line internal comment); `tests/test_prophet_strategy_definition.py` (+15 / 0, MODIFIED — one new test `test_b4_optional_structural_overlay_unknown_does_not_deadlock_owner_stop` with two asserted scenarios, the second also covering the `BREACHED` non-waivable path). |
| additions / deletions | 21 / 2 |
| labels | none visible at fetch time; merges from the macro sweeper signature on the listed timestamp. |
| scope collision | none — PR body explicitly bounds scope to removing a deadlock condition caused by a missing entry-compatible thesis/falsifier owner for `structural_invalidation`, and explicitly disclaims any weakening of quote/basis/source-health, event retraction, owner confluence, risk-ceiling, liquidity/fillability, gap/velocity, or session-eligibility requirements. PR body also states: "It does not grant Long-Hold/Thesis Funnel display artifacts entry authority and does not rank, recommend, size, originate a plan, execute, or trade." The body explicitly marks `DRAFT / HOLD-FOR-SOL`. |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --json number,title,mergedAt --jq '.[] | select(.mergedAt > (now - 86400 | strftime("%Y-%m-%dT%H:%M:%SZ")))'` against `git ls-tree origin/main -- orch/audits/` (per the standing workflow memo `orch_audit_filename_convention.md`): the most recent macro merge (#7701 — `[MO F07] event -> AssumptionChange`) is a major F-series feature, not a half-B PR; the merges immediately before it are (a) `orch(audit)` record-keeping PRs (#7699, #7689, #7686, #7682, #7673, #7671, #7659, #7651, #7644, #7636, #7627 — filing-only); (b) `feat(prophet): own B4 session eligibility policy` (#7688 — a sister feature to #7687 that wires the `session_eligibility` owner contract, with its own scope); (c) `docs(ric)` (research-governance record); (d) `research(risk)` evidence-only deliverables (#7683, #7666 — user-facing surface untouched); (e) `agentos:` release-frontier sweeps (#7679, #7619 — knowledge-plane only); (f) `fix(ci)` infra-only PRs (#7678, #7628, #7621 — `check_design_system.py --mode enforce-added` reports zero template/JS/CSS surface added). PR #7687 — a tightly bounded engine fix that removes a single unconditional `UNAVAILABLE_DATA` blocker, with no new template/component/CSS/JS surface, no claim authorship, no theme-token or layout change, but a real engine-state-machine correction that the design system + bilingual + retrospective-evidence chain must still read for user-impact language drift — is the appropriate half-B scope: **2 files**, +21/−2, fully self-contained inside `engine/prophet_entry_availability.py` + its test module.

**Nature of change (single-line deadlock-removal + one paired test):**

1. *Defect — `structural_invalidation=UNKNOWN` deadlocked every B4 row even when the incumbent owner's numeric stop was valid.* The Early Leadership / Sector Rotation tactical policy already requires the incumbent entry owner's numeric `invalidation_price`, and B4 hard-invalidates at or below that stop. The `structural_invalidation` gate is an extension point for a future entry-compatible thesis/falsifier owner. With no such accepted owner today, the unconditional `if gate_values["structural_invalidation"] == "UNKNOWN": unavailable.append("STRUCTURAL_INVALIDATION_UNKNOWN")` block deadlocked every otherwise-valid tactical row as `UNAVAILABLE_DATA` — a NULL blocking the strategy solely because no extension contract exists. The PR removes the unconditional block and replaces it with an internal comment documenting the architectural rationale: `BREACHED` remains non-waivable (verified by the second half of the new test, which sets `structural_invalidation=UNKNOWN` AND prices the quote at the invalidation level, then asserts `state == "INVALIDATED"` with `STRUCTURAL_INVALIDATION_BREACHED` in blockers — proving the removal does not weaken the non-waivable path); `CLEAR` remains accepted context (pre-existing branch); `UNKNOWN` is no longer a blocker on its own (verified by the first half of the new test, which sets `structural_invalidation=UNKNOWN` with otherwise-valid facts and asserts `state == "ENTRY_OPEN"` with `STRUCTURAL_INVALIDATION_UNKNOWN` not in blockers).

2. *Where the impact lives.* No live probability / band / score / weight / gate / policy / sizing / ranking / ledger / capital authority is changed (PR body explicitly disclaims via the bullet list and the closing anti-promotion line). What changes is the *availability* state assignment for B4 tactical rows that have a valid incumbent owner stop but no thesis-overlay extension: those rows now correctly return `ENTRY_OPEN` (or `INVALIDATED` if the price is at/below the numeric stop) instead of being silently blocked as `UNAVAILABLE_DATA`. PR body explicitly names the unchanged gates: "It does not weaken quote/basis/source-health, event retraction, owner confluence, risk-ceiling, liquidity/fillability, gap/velocity, or session-eligibility requirements."

3. *Evidence preservation.* The PR adds one paired test (`test_b4_optional_structural_overlay_unknown_does_not_deadlock_owner_stop`) that asserts BOTH the `ENTRY_OPEN` path (overlay unknown, no other blocker) AND the `INVALIDATED` path (overlay unknown + numeric stop breached) — locking both halves of the architectural decision in a single test. Test name documents the intent (`does_not_deadlock_owner_stop`).

## Diff content (scoped to this audit)

2 files, no new template/component/CSS/JS surface. Both files are engine Python + a paired test module. The visible-to-product surface is zero.

### `engine/prophet_entry_availability.py` (+6 / −2, MODIFIED)

Single hunk in `evaluate_entry_availability(...)`, inside the `UNAVAILABLE_DATA` blocker-collection pass that runs after every other deterministic-gate check. The deleted two lines (`if gate_values["structural_invalidation"] == "UNKNOWN": unavailable.append("STRUCTURAL_INVALIDATION_UNKNOWN")`) are replaced with a 6-line comment block that documents:

- the Early Leadership tactical policy already requires the incumbent entry owner's numeric `invalidation_price` and hard-invalidates at or below it above (referring to the pre-existing numeric-stop branch earlier in the same function);
- `structural_invalidation` is a separate optional owner extension for a future entry-compatible thesis/falsifier fact;
- `BREACHED` is non-waivable;
- `UNKNOWN` must not deadlock the strategy merely because no such additional owner contract exists yet.

The comment is internal engineering rationale for future maintainers, not user-facing copy. It uses bounded vocabulary — "extension point", "optional", "non-waivable", "must not deadlock" — none of which is a banned-glance term. The comment does not oversell, does not use promotion-bearing vocabulary (`validated` / `proved` / `guaranteed` / `certified`), and does not make any user-visible claim about B4 behaviour.

### `tests/test_prophet_strategy_definition.py` (+15 / 0, MODIFIED)

Single new test function `test_b4_optional_structural_overlay_unknown_does_not_deadlock_owner_stop`, with two scenarios:

- *Scenario 1 (overlay unknown, no other blocker):* clone `_b4_facts()`, set `deterministic_gates.structural_invalidation = "UNKNOWN"`, evaluate, assert `state == "ENTRY_OPEN"` and `STRUCTURAL_INVALIDATION_UNKNOWN not in blockers`. This is the positive-direction red-first test — pre-PR it would have returned `UNAVAILABLE_DATA` with `STRUCTURAL_INVALIDATION_UNKNOWN` in blockers.
- *Scenario 2 (overlay unknown + numeric stop breached):* clone `_b4_facts()`, set `deterministic_gates.structural_invalidation = "UNKNOWN"` AND set `quote.price = geometry.invalidation_price` (i.e. price is exactly at the incumbent owner's invalidation level), evaluate, assert `state == "INVALIDATED"` and `STRUCTURAL_INVALIDATION_BREACHED in blockers`. This is the falsifier test — pre-PR and post-PR this scenario MUST continue to invalidate; the test pins the non-waivable path so a future regression that weakens `BREACHED` is caught immediately.

Test naming documents the intent (`does_not_deadlock_owner_stop`). Both scenarios use the existing `_b4_facts()` / `_b4_evaluate()` helpers — no new test infrastructure, no new fixtures, no new import.

## Plain-language findings

### 1.1 Pass — there is no user-facing copy in this PR; the macro-side plain-language discipline is structurally inapplicable on this diff

The diff contains zero template (`templates/`), zero product HTML (no `site/`), zero CSS, zero JS, zero chat surface, zero bilingual receipt text. Both changed files are Python: `engine/prophet_entry_availability.py` (engine code) and `tests/test_prophet_strategy_definition.py` (test module). `tests/test_bilingual_ui.py` and `scripts/check_bilingual.py` cannot produce a finding against this diff by construction — there is no template surface to scan.

For the project-side plain-language read, the only prose that lands in this PR is the 6-line internal comment in `engine/prophet_entry_availability.py`. That comment is internal documentation for engineers reading the engine, not user-facing copy. It uses bounded, architectural-rationale vocabulary ("extension point", "optional", "non-waivable", "must not deadlock"), names the existing numeric-stop branch it relies on ("hard-invalidates at or below it above"), and does not assert any user-facing capability change. The PR body itself is a defect-repair description with the canonical anti-promotion closer ("It does not weaken quote/basis/source-health, event retraction, owner confluence, risk-ceiling, liquidity/fillability, gap/velocity, or session-eligibility requirements. It does not grant Long-Hold/Thesis Funnel display artifacts entry authority and does not rank, recommend, size, originate a plan, execute, or trade.") — matching the same shape used by other recent macro engine-only fix PRs.

### 1.2 Pass — the internal comment preserves the prose discipline

The new comment in `engine/prophet_entry_availability.py` names the standing architectural decision (numeric stop from the incumbent owner is mandatory; `structural_invalidation` is an optional extension for a future entry-compatible thesis/falsifier owner), the non-waivable case (`BREACHED`), the accepted case (`CLEAR`), and the bounded behaviour for `UNKNOWN` (must not deadlock because no extension contract exists yet). None of these strings is user-visible; they are documentation that future maintainers of `engine/prophet_entry_availability.py` need in order to recognise why the unconditional UNKNOWN-block was removed before re-introducing it. The comment does not oversell, does not use banned-glance vocabulary (`validated` / `proved` / `guaranteed` / `certified` / "ships"), and explicitly references the pre-existing numeric-stop branch above as the source of non-waivable invalidation — so the falsifier (`BREACHED` still fires when price is at the stop) is documented, not implied.

### 1.3 Pass — the PR body uses bounded, anti-promotion language

PR body opening: "Bounded same-owner semantic repair to merged B4 core #7569 under Prophet Entry Truth #6805." — bounded to "same-owner semantic repair", naming the upstream contracts being preserved (#7569 B4 core, #6805 Prophet Entry Truth).

PR body mid-section names the unchanged gates explicitly ("It does not weaken quote/basis/source-health, event retraction, owner confluence, risk-ceiling, liquidity/fillability, gap/velocity, or session-eligibility requirements.") — the canonical anti-weakening enumeration used across recent macro engine-only fix PRs.

PR body closing: "**DRAFT / HOLD-FOR-SOL.** This is source capability, not review acceptance, merge/release, deployment, production proof, or a positive B4 Availability claim." — matches the standing `DEC:SOL-HOLD-IS-A-MERGE-BARRIER` hold protocol: the body names the authority (Sol), the release condition (none stated — the body does not promise a release), the scope (source capability only), and explicitly disclaims five promotion-bearing states (review acceptance, merge/release, deployment, production proof, positive B4 Availability claim). No banned vocabulary, no user-facing capability claim.

## Theme findings

### 2.1 Pass — `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7687.diff` reports **0 blocking findings**

```
::notice title=design-system::R0 enforce-added: 0 blocking finding(s) (25320 further pre-existing, non-blocking finding(s) in the estate — run --mode report for the full census)
design-system ratchet — mode=enforce-added blocking=0 (estate pre-existing, non-blocking: 25320)
```

Run command: `gh pr diff 7687 --repo mastermindx-market-intelligence/macro > /tmp/pr7687.diff && python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7687.diff`. The 25,320 pre-existing non-blocking estate findings are unchanged by this PR (the report's own caveat applies — the `enforce-added` mode reads the PR's own diff lines only and does not assert against pre-existing debt). The diff literally contains zero template/component/CSS/JS lines, so the design-system check has zero lines to assert against.

### 2.2 Pass — TP-0 dark/light × EN/ZH × 1440/390 evidence matrix is structurally inapplicable; the change does not touch any visual surface

The TP-0 dark-and-light-are-two-art-directions rule (`scripts/check_design_system.py` + the standing design-doctrine §Theme art direction) requires every material UI packet to name DARK TREATMENT, LIGHT TREATMENT, which mechanisms intentionally differ, the reference/baseline, theme-specific degraded states, and the evidence matrix (dark/light × EN/ZH × desktop 1440 / mobile 390).

This PR adds zero user-visible surface. Every changed line is in `engine/` or `tests/` Python — no template, no inline style, no `<style>` block, no CSS rule, no JS payload. The "Token substitution alone is never proof of a light design" rule, the "Substantive product styling may not be authored as an opaque runtime stylesheet system inside page/composer JavaScript" rule, and the "every material UI packet must name DARK TREATMENT / LIGHT TREATMENT" rule are all structurally inapplicable. **Consistent with TP-0**.

### 2.3 Pass — `check_runtime_style_injection.py` is out-of-scope by construction

The diff contains no `style="..."` injection, no `style.textContent =`, no parallel palette, no duplicated light/dark branches inside JS, no inline `<style>` block, no `data-theme` override, no `class` attribute containing theme tokens. There is no JS payload change anywhere in the diff — both files are Python.

### 2.4 Pass — no theme-art-direction assertion is made or implied

The PR body does not claim a dark/light, EN/ZH, mobile/responsive, palette, type, motion, or material-design effect. It closes with the anti-promotion line plus the anti-weakening enumeration and the `DRAFT / HOLD-FOR-SOL` hold protocol. No evidence matrix is owed because no design surface is touched.

## Validated-claims findings

### 3.1 Pass — `python3 scripts/check_validated_claims.py --list` produces no MISS row for this PR's diff

Run: `python3 scripts/check_validated_claims.py --list` filtered for any `7687` / `prophet_entry_availability` / `structural_invalidation` / `UNAVAILABLE_DATA` key produces no output — confirming the validator has no registered claim against this PR and nothing in the diff creates one. The PR's only user-facing-shaped text is the canonical anti-promotion closer ("It does not weaken ... It does not grant ... and does not rank, recommend, size, originate a plan, execute, or trade."), which is the standing disclaimer that exempts the change from the promotion-bearing claim regime entirely.

### 3.2 Pass — the PR body does not introduce any promotion-bearing claim

PR body opening: "Bounded same-owner semantic repair to merged B4 core #7569 under Prophet Entry Truth #6805." — bounded to "semantic repair" within two named upstream contracts. No release/upgrade/score/rank promotion.

PR body mid-section: "The Early Leadership / Sector Rotation tactical policy already requires the incumbent entry owner's numeric `invalidation_price`, and B4 hard-invalidates at or below that stop. The separate `structural_invalidation` gate is an extension point for a future entry-compatible thesis/falsifier owner. With no such accepted owner today, requiring `structural_invalidation=CLEAR` deadlocks every otherwise-valid tactical row as `UNAVAILABLE_DATA`." — defect description, bounded to a deadlock state and its architectural cause.

PR body closing: "**DRAFT / HOLD-FOR-SOL.** This is source capability, not review acceptance, merge/release, deployment, production proof, or a positive B4 Availability claim." — explicitly disclaims five promotion-bearing outcomes (review acceptance, merge/release, deployment, production proof, positive B4 Availability claim). This is the canonical anti-promotion line for an engine-only defect-repair PR under a Sol hold.

### 3.3 Pass — no `data/regime/validated_claims_allowlist.json` or template surface is touched

`tests/test_validated_claims_engine.py`, `tests/test_validated_claims_registry_source.py`, `tests/test_validated_claims_structural_scope.py`, and `tests/test_validated_claims_thirdparty.py` are the surface that enforces the user-facing claim discipline. None of them read or assert against engine code or test modules — they read `templates/` and the structural scope of `data/regime/validated_claims_allowlist.json`. This PR modifies neither surface. The validator's behaviour is unchanged on this PR. **Consistent with the structural-scope contract.**

### 3.4 Pass — no new `validated`/`proved`/`guaranteed`/`certified` vocabulary in any user-facing path

The PR diff and body contain zero uses of the promotion-bearing vocabulary (`validated` / `proved` / `guaranteed` / `certified` / "ships"). The internal comment in `engine/prophet_entry_availability.py` uses "non-waivable" (an architectural adjective for the `BREACHED` branch) and "must not deadlock" (a negative-space description of the bounded behaviour for `UNKNOWN`) — neither of which is on the banned-glance list. The PR body's title and description use "repair" (defect framing), "fix" (defect framing), and "deadlock" (negative-space framing). No overselling language.

## Overall verdict

**VERDICT: PASS — clean half-B engine-only deadlock-removal, no blocking issue, no user-facing surface touched.**

| dimension | result | notes |
|---|---|---|
| plain-language | PASS | Diff contains zero user-facing copy (only engine Python and a paired test module). The macro-side plain-language discipline (`tests/test_bilingual_ui.py` + `scripts/check_bilingual.py` + design-doctrine banned-glance vocabulary) is structurally inapplicable on this diff. The internal comment in `engine/prophet_entry_availability.py` uses bounded architectural-rationale vocabulary ("extension point", "optional", "non-waivable", "must not deadlock"). The PR body carries the canonical anti-weakening enumeration and the `DRAFT / HOLD-FOR-SOL` hold protocol with five explicit disclaimed outcomes. No banned vocabulary. |
| theme | PASS | `check_design_system.py --mode enforce-added --diff-file /tmp/pr7687.diff` reports 0 blocking findings. The diff contains zero `templates/`, `site/`, `.css`, `.js`, `style=`, `data-theme`, or component lines. TP-0 dark/light × EN/ZH × 1440/390 evidence matrix is structurally inapplicable (no visual surface added). `check_runtime_style_injection.py` is out-of-scope (no JS payload). The PR does not author any design surface. |
| validated-claims | PASS | `check_validated_claims.py --list` filtered for `7687` / `prophet_entry_availability` / `structural_invalidation` / `UNAVAILABLE_DATA` produces no MISS row against the PR's diff — no template surface is touched and no promotion-bearing claim is registered. The PR body disclaims any promotion-bearing change (anti-weakening enumeration of six unchanged gates + anti-promotion enumeration of five disclaimed outcomes) and explicitly marks `DRAFT / HOLD-FOR-SOL` per the standing `DEC:SOL-HOLD-IS-A-MERGE-BARRIER` hold protocol. The internal comment uses bounded vocabulary and no banned terms. |
| merge hygiene | PASS | 2 files, +21 / −2. The substantive fix is the deletion of a single unconditional `if gate_values["structural_invalidation"] == "UNKNOWN": unavailable.append("STRUCTURAL_INVALIDATION_UNKNOWN")` block, replaced by a 6-line internal rationale comment. One new test (`test_b4_optional_structural_overlay_unknown_does_not_deadlock_owner_stop`) covers BOTH the `ENTRY_OPEN` path (overlay unknown, no other blocker) AND the `INVALIDATED` path (overlay unknown + numeric stop breached) — locking both halves of the architectural decision in a single test. Test name (`does_not_deadlock_owner_stop`) documents the intent. The PR body names two upstream contracts being preserved (#7569 B4 core, #6805 Prophet Entry Truth), enumerates the six unchanged gates, and disclaims five promotion-bearing states. The PR is `DRAFT / HOLD-FOR-SOL` per the standing hold protocol. |

**Non-blocking follow-ups (out of this lane's owned paths):**

1. The PR body names a future "entry-compatible thesis/falsifier owner" as the would-be owner for `structural_invalidation`. When that owner contract is accepted, a paired freeze record (e.g. `agentos/discoveries/DSC-PROPHET-STRUCTURAL-INVALIDATION-OWNER-CONTRACT.md`) should be minted to formalise the gate semantics so a future regression that re-introduces the unconditional UNKNOWN-block is caught by an allowlisted claim rather than by re-reading the comment. Out-of-scope for this PR.
2. The new test pins the `BREACHED` non-waivable path, but does not yet pin the `CLEAR` accepted-context path as a positive-direction test. A future addition of `test_b4_optional_structural_overlay_clear_remains_accepted` would complete the three-state contract (`BREACHED` / `CLEAR` / `UNKNOWN`) in one test family. Out-of-scope for this PR; the existing pre-fix PRs for the B4 core (#7569) already exercise the `CLEAR` path in the wider B4 qualification suite.
3. The PR's architectural move (a structured, comment-documented opt-out of an unconditional blocker when no extension owner exists) is a reusable pattern for any future gate that follows the same "extension point for a not-yet-accepted owner" shape. A future `agentos/discoveries/DSC-GATE-EXTENSION-POINT-OWNER-LATTICE.md` could enumerate which other gates share this pattern and pre-document the opt-out shape so future fixes don't need to re-derive the rationale. Out-of-scope for this PR.

**No blocking issue found. No retry. No scope expansion. Audit complete.**