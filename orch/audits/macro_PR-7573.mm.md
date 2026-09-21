# Plain-language / theme / validated-claims audit — macro PR #7573

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-21.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7573 |
| title | `fix(prophet-live): emit positive per-name basis receipts` |
| merge head | `33be8d6ee1c31ce71463e1754251f251330befb7` |
| merged | 2026-09-21T04:34:27Z via squash-merge to `main`. Most recent non-audit-record half-B PR in the 24-h window that has not already been audited (`#7565 / #7566 / #7568 / #7569 / #7570 / #7571 / #7572 / #7573` — the audit list at row 1 / `ls orch/audits/macro_PR-*.mm.md` confirms each earlier PR already carries an audit record; `#7580 / #7582 / #7587` are later `orch(audit)` record PRs themselves, not target PRs). |
| author / carrier | `sol-integration-proof` operating as `sol/prophet-live-basis-receipt-20260921`. PR body declares "Protected procedure: `Mastermind@3e66e43258f34db240d5bff76f54148c7af84ee4`, `mastermind.sol_skillpack.v1` 1.0.1 / bootstrap-major 1" — i.e. this carrier matches Sol master `3e66e43258f34db240d5bff76f54148c7af84ee4`, so the carrier is positively bound to Sol as the named authority, not impersonating Sol from inside an unbounded Claude/Codex session. |
| base | `4f4f64931d6e33d61b901c313132a5116e3f0c32` (origin/main at PR-body merge base). |
| files | **2 paths, +88 / −3** — `engine/prophet_live/live_states.py` (+49 / −2), `tests/test_prophet_live_evaluator.py` (+39 / −1). |
| half-B label | **half-B (engine-only basis-receipt emission for Prophet B4 runtime owner-fact adapter; no candidate / plan / rank / gate / trading / sizing / publication / live-state decision / entry-geometry authority).** PR body is explicit: "This PR changes no Prophet candidate admission, ranking, plan origination, sizing, trading, publication, live-state decision, entry geometry, or named-security preference." It is a content-addressed receipt emitted by an already-existing per-name audit; the audit itself was not changed. |
| scope | (a) emit a positive `basis_status="RESOLVED"` + content-addressed `basis_receipt="sha256:..."` pair on each probed-name row when the incumbent per-name audit actually measured the name, the configured tolerance is enabled, the measured gap is inside tolerance, and the live state did not fail dark; (b) register the relation schema once at the artifact level (`meta.price_adjustment.relation_schema = "prophet_live.basis_relation/v1"`); (c) preserve per-name basis exceptions (their own `levels_adjustment` still gets a distinct receipt); (d) ship regression tests proving the positive receipt exists only after a measured in-tolerance audit, changes when the measured relationship changes, is absent when unchecked / disabled, and preserves per-name basis exceptions. |
| durable owner | `WS:PROPHET-LIVE-BASIS-RECEIPT-B4-RUNTIME-PREREQ` (the operation ID carried in the PR body — `prophet-live-basis-receipt-b4-runtime-prereq-20260921-sol-001`). The receipt is a knowledge-plane content-address for the existing audit's per-name outcome; no new gate, no new owner, no new owner surface. |
| collision / scope note | PR body explicitly lists what it does NOT change: "no live-state vocabulary, debounce, interval, quote freshness, basis threshold, pack construction, or gate arithmetic changes." It also names its dependency on B4 core PR #7569 (which preserves the two honest bases — raw vendor tape vs adjusted armed geometry — and requires a positive per-name owner fact before promoting to `corporate_action_basis=RESOLVED`) and its upstream `corporate-actions` carry from #6805. |
| known unrelated main-branch issue | PR body flags: "Fresh protected main advanced after branch creation only in `data/research_vault/catalog.json`; no owned-path overlap." No third-party owned-path collision. (Maintenance note, not a finding — recorded for transparency.) |
| checks | PR body reports green-first proof on the exact head: `tests/test_prophet_live_basis.py tests/test_prophet_live_evaluator.py` => **132 passed**; `python3 -m py_compile engine/prophet_live/live_states.py` => PASS; `git diff --check` => PASS. Exact head composes conflict-free with `main@707b5e87fcaddaf746144f044d8853245e6eb035` at no-write merge tree `ea9530d44ca4b0b9e45a4c9d90176bb4a2668357`. |
| gating scripts | `scripts/check_plain_language.mjs` — DOES NOT EXIST in macro (terminal-side only; `ls scripts/check_plain*.mjs` → no matches). Plain-language discipline on macro is read against the standing design-doctrine rules. `scripts/check_validated_claims.py` (1472 lines) exists but is **scoped to user-facing templates** (its CLI signature accepts no path arguments and reports `OK / MISS` rows against `templates/*.j2` / `site/*.html`). It does not scan engine Python — and is correctly not invoked on this PR's `engine/prophet_live/` files. `scripts/check_design_system.py`, `scripts/check_runtime_style_injection.py`, `scripts/check_ui_visual_evidence.py` exist but are scoped to design-system surfaces and are correctly not invoked on this engine-only PR. |

## Diff content (scoped to this PR)

The PR is a single bounded Python change. The two touched files are summarized below at the level of detail the three audits need.

**`engine/prophet_live/live_states.py` (+49 / −2, MODIFIED) — the engine-side emission**

Imports + module-level constant:
- Adds `from hashlib import sha256` and `import json` to the standard-library import block (lines 161-162 of the new file).
- Adds one module-level identifier: `BASIS_RELATION_SCHEMA = "prophet_live.basis_relation/v1"` (line 180). This is the relation-schema name the artifact's `meta.price_adjustment.relation_schema` field will quote.

Receipt builder:
- New private helper `_basis_receipt(...)` (lines 449-471 of the new file). Takes the probed-name subject, the pack session, the levels-adjustment string, the measured gap, and the configured tolerance. Materializes a content-addressed JSON blob with seven stable keys (`schema`, `subject`, `state`, `pack_as_of`, `levels_adjustment`, `quote_adjustment`, `gap_pct`, `tol_pct`), SHA-256-hashes it, and returns the `"sha256:<64-hex>"` form. `gap_pct` and `tol_pct` are rounded to 6 decimal places before the digest so float-representation drift does not change the receipt for a substantively identical measurement.

Per-row emission (inside the existing `evaluate(...)` per-name loop):
- The existing `name_state(...)` call is unchanged in argument list and behavior.
- After `name_state(...)` returns, the new code reads `gap = gaps.get(tkr)` (local variable for the `basis_gap_pct` that was already passed into `name_state`).
- The emission gates are explicit and fail-closed:
  - `st.get("state") != "dark"` — dark names keep no positive receipt.
  - `gap is not None` — missing `prev_close` keeps no positive receipt (no inferred pass).
  - `tol > 0.0` from `abs(float(audit["tol_pct"]))` — disabled audit (`tol=0`) keeps no positive receipt.
  - `abs(float(gap)) <= tol` — material mismatch (the existing darking path) keeps no positive receipt.
- When all four gates pass, the code sets `st["basis_status"] = "RESOLVED"` and `st["basis_receipt"] = _basis_receipt(...)`.
- The block comment at lines 943-947 explicitly states the design intent: "A positive row-local basis receipt is emitted only after the incumbent audit actually measured this name and the live state did not fail dark. Missing prev_close therefore remains absence of evidence, never an inferred pass." This is the same G0.6-style "absence of evidence is not an inferred pass" stance the design doctrine requires.
- The `levels_adjustment` field on the row is reused (it was already computed two lines earlier in the per-name loop), so no recomputation.

Artifact-level relation schema:
- `meta.price_adjustment` (the artifact-level price-adjustment block) gains one new key: `"relation_schema": BASIS_RELATION_SCHEMA`. The PR's module docstring comment above the block says the artifact-level block names the schema once — i.e. the row-local receipt names the relation schema implicitly via the `BASIS_RELATION_SCHEMA` constant inside `_basis_receipt`'s material, and the artifact block now spells that schema name out once for a reader who is looking at the block rather than at a row.

The total of +49 / −2 lines is consistent with: +2 imports, +1 module constant, +24 receipt helper, +12 emission block, +1 artifact-level relation-schema line, −1 dedup of the `ent_adj = entry.get("price_adjustment")` line (moved earlier so it is computed once and used by both the new receipt emission and the existing `levels_adjustment` exception path).

**`tests/test_prophet_live_evaluator.py` (+39 / −1, MODIFIED) — the regression coverage**

Three new tests + one modified existing test:

1. **`test_a_checked_matching_basis_emits_positive_per_name_relation_receipt`** (NEW, 30 lines):
   - Runs `_run(...)` with `pack({"BBB": buyable()})` + `quotes_with_prev({"BBB": 100.0}, {"BBB": 100.0})`.
   - Asserts `state["basis_status"] == "RESOLVED"`.
   - Asserts `state["basis_receipt"].startswith("sha256:")` and has length `len("sha256:") + 64` (i.e. SHA-256 hex digest length).
   - Asserts `art["meta"]["price_adjustment"]["relation_schema"] == "prophet_live.basis_relation/v1"`.
   - Asserts a SHIFTED quote (`prev_close=100.2`) produces a DIFFERENT receipt — i.e. the receipt content-addresses the actual measurement, not just the existence of a pass.

2. **`test_unchecked_basis_never_mints_a_positive_relation_receipt`** (NEW, 5 lines):
   - Runs `_run(...)` with no `prev_close`.
   - Asserts the state is `"forming"` and `"basis_status"` / `"basis_receipt"` are NOT present on the row (i.e. unchecked remains absence of evidence, not inferred pass).

3. **`test_disabled_basis_audit_never_mints_a_positive_relation_receipt`** (NEW, 7 lines):
   - Constructs a config with `basis_tolerance_pct=0.0` (audit disabled).
   - Runs `LS.evaluate(...)` and asserts the state is `"forming"` and `"basis_status"` / `"basis_receipt"` are NOT present.

4. **`test_a_name_whose_levels_are_on_another_basis_says_so_on_its_own_row`** (MODIFIED, +5 / −1):
   - The existing test now also passes matching `prev_close` values for both `AAA` and `BBB`, so both rows qualify for the positive receipt.
   - Asserts BOTH `AAA["basis_status"] == "RESOLVED"` and `BBB["basis_status"] == "RESOLVED"` (the per-name exception path is compatible with the positive receipt — i.e. an exception row with its own `levels_adjustment` still gets a distinct receipt, exactly the scope rule the PR body states).
   - Asserts `AAA["basis_receipt"] != BBB["basis_receipt"]` — i.e. the receipt content-addresses the row's measured relationship, not a global per-pack constant.

The four tests together prove the four claim kinds the PR body makes: (i) positive receipt exists only after a measured in-tolerance audit; (ii) receipt changes when the measured relationship changes; (iii) receipt is absent when unchecked; (iv) receipt is absent when audit disabled; (v) per-name basis exceptions preserve their own receipt.

## Plain-language findings

The standing plain-language discipline is scoped to user-facing surfaces (per `docs/DESIGN_DOCTRINE.md` "Glance tier = state + plain-word stance under hard word budgets; technicals demoted to hover/popover/detail pages"). PR #7573 is a backend engine change. No user-facing copy, no glance tier, no CTA, no card label, no SEO description, no hero eyebrow. The `evaluate(...)` function returns a JSON-shaped payload that is consumed by the dashboard's glance tier downstream — but the strings this PR adds (`basis_status`, `basis_receipt`) are content-addressed identifiers, not human copy. The artifact's `meta.price_adjustment.relation_schema` field is an internal-schema name (`prophet_live.basis_relation/v1`), not a user-facing string.

**Summary: N/A by surface (no user-facing copy changed).** Standing plain-language laws are scoped to the user-facing tier, and this PR is engine-only. The `prophet_live.basis_relation/v1` schema name is an internal content-addressing convention — it lives in the payload for `B4 runtime adapter` consumers to verify the receipt schema, not for end-users to read. The PR body's prose is operator-facing (it names the operation, the carrier, the exact head, the bounded scope, and the verification proof); the prose is concrete and falsifiable throughout (see Validated-claims findings, §7).

**Specific plain-language deltas worth recording (engine-internal, not user-facing):**

1. **`basis_status="RESOLVED"` is a content-addressing state name, not a user-facing claim word**: NEUTRAL — the string `"RESOLVED"` is a state enum value already in the module's vocabulary (`prophet_live.states/v1` ships states like `"unknown"`, `"forming"`, `"stress"`, `"dark"`; `"RESOLVED"` follows the same uppercase-named-state convention). It is content-addressed via the receipt's SHA-256 digest, not published as a user copy. The design-doctrine rule about not asserting "validated" / "confirmed" / "fired" in user-facing copy is preserved at the user-facing layer; the engine's internal enum vocabulary is not the user copy.
2. **`meta.price_adjustment.relation_schema = "prophet_live.basis_relation/v1"` is a schema identifier, not a copy line**: NEUTRAL — this is the same shape as the module's existing `SCHEMA = "prophet_live.states/v1"` constant. It identifies the relation schema for downstream consumers (B4 runtime adapter, calibration pages), it does not appear on a user-facing surface.
3. **`_basis_receipt(...)` docstring + inline comment**: NEUTRAL — the comment "A positive row-local basis receipt is emitted only after the incumbent audit actually measured this name and the live state did not fail dark. Missing prev_close therefore remains absence of evidence, never an inferred pass." is operator-facing documentation. It is concise, falsifiable, and is the same stance the design doctrine requires at the user-facing tier ("nulls printed, not hidden"; "plain-word null disclosure + Tier-2 receipt"). The comment is the right altitude for an engine-emission gate.

**Plain-language residual issues: none.** No user-facing surface was touched. No new copy was introduced. No existing copy was changed. The PR does not change the dashboard's glance tier, glance labels, hero eyebrow, card CTAs, segment toggle, or SEO description.

**Plain-language verdict: N/A by surface.** The PR is engine-only and touches no user-facing copy. Standing plain-language laws are correctly preserved at the user-facing layer and are not relevant at the engine layer.

## Theme findings

The TP-0 standing rule ("dark and light share information architecture, component semantics, spacing/type scales, state meanings, user actions, data contracts, ordering/density law and interaction behavior — they do **not** have to share material treatment. … Every material UI packet must name DARK TREATMENT, LIGHT TREATMENT, which mechanisms intentionally differ, the reference/baseline, theme-specific degraded states, and the evidence matrix (dark/light × EN/ZH × desktop 1440 / mobile 390)") binds UI packets, not engine emission. PR #7573 is a backend engine change — it adds a per-row content-addressed field to the `evaluate(...)` payload, names one schema identifier, and writes nothing to CSS, JS, or templates.

**Summary: N/A by surface.** The PR does not touch `templates/`, `site/`, `site/assets/css/`, `theme.css`, `theme.js`, or any design-system token file. The standing TP-0 evidence matrix (`dark × light × EN × ZH × desktop 1440 / mobile 390`) is correctly NOT invoked for an engine-only PR.

**Specific theme deltas worth recording: none.** The added payload fields (`basis_status`, `basis_receipt`, `meta.price_adjustment.relation_schema`) are content-addressed identifiers consumed by downstream dashboard rendering code — but they do not pre-commit to a specific dashboard treatment. The downstream rendering code, when it draws a row's `basis_status="RESOLVED"`, is free to render that as a small green check, a checkmark glyph, or as a hover-only receipt popup. That decision is downstream of this PR and is correctly NOT made here.

**Theme residual issues: none.** No CSS, JS, or template was touched. No design-system token was introduced or modified. The `var(--info)` token family and the existing snapshot-dot / live-dot patterns are untouched.

**Theme verdict: N/A by surface.** The PR is engine-only and binds no UI surface. The TP-0 evidence matrix is correctly not invoked. The downstream rendering of the new `basis_status` / `basis_receipt` fields will be a separate half-B UI packet if/when the dashboard surfaces them; that packet will be the one that owes the TP-0 evidence matrix.

## Validated-claims findings

The standing rule "The word 'validated' in user-facing text is CI-enforced (`scripts/check_validated_claims.py`)" binds every claim that uses the word. PR #7573 introduces a new user-facing vocabulary piece — the `basis_status="RESOLVED"` state on the row — that is published into the `evaluate(...)` JSON payload. The word chosen (`RESOLVED`) is the same uppercase-named-state vocabulary the module already uses for `prophet_live.states/v1`, NOT the banned "validated" / "proven" / "confirmed" word family. The standing `tests/test_prophet_live_evaluator.py:13` "G0.6 VOCABULARY" rule (and the `FORBIDDEN_WORDS = ("fired", "confirmed", "refuted", "validated", "thesis")` constant at `tests/test_prophet_live_evaluator.py:1333`) is the engine-side analog of the design-doctrine user-facing rule; the PR preserves both.

**Summary: PASS.** The PR introduces no new user-facing claim using the banned "validated" / "proven" / "confirmed" / "fired" / "refuted" word family. The new engine-state value `"RESOLVED"` follows the module's existing uppercase-named-state convention. The new content-addressed `basis_receipt` is a SHA-256 of the measured relationship — it is exactly what the G0.6 "absence of evidence is not an inferred pass" rule requires: the receipt only exists when the audit actually measured the name, the tolerance is enabled, the measured gap is inside tolerance, and the live state did not fail dark. The PR's failure modes (missing `prev_close`, disabled audit, material mismatch, dark state) all keep no positive receipt — the four emit-but-fail-closed paths are test-enforced.

**Specific validated-claims deltas worth recording:**

1. **`basis_status="RESOLVED"` is a state-name enum, not the banned "validated" word**: PASS — `RESOLVED` is the module's existing uppercase-named-state convention (sibling to `unknown`, `forming`, `stress`, `dark` at `engine/prophet_live/live_states.py:182-183`). It does NOT match the design-doctrine banned set. The PR body's own prose never uses "validated" / "proven" / "confirmed" / "fired" / "refuted" either.
2. **`basis_receipt="sha256:<hex>"` is content-addressing, not a claim word**: PASS — the receipt is a SHA-256 digest of the measured relationship. The digest is what the design-doctrine calls a "Tier-2 receipt": falsifiable, reproducible, schema-bound. It binds the subject, pack session, levels adjustment, quote adjustment, measured gap, tolerance, and relation schema. No new claim word is introduced.
3. **`meta.price_adjustment.relation_schema = "prophet_live.basis_relation/v1"`**: PASS — schema identifier, matches the module's existing `SCHEMA = "prophet_live.states/v1"` naming convention. Not a claim.
4. **The four emission gates preserve "absence of evidence is not an inferred pass"**: PASS — the inline comment at the emission block is explicit: "Missing prev_close therefore remains absence of evidence, never an inferred pass." The three regression tests (`test_unchecked_basis_never_mints_a_positive_relation_receipt`, `test_disabled_basis_audit_never_mints_a_positive_relation_receipt`, `test_a_dividend_sized_pack_vs_feed_gap_darks_that_name`) pin each fail-closed path. The G0.6 vocabulary rule (`FORBIDDEN_WORDS` at `tests/test_prophet_live_evaluator.py:1333`) is the engine-side analog of the user-facing `scripts/check_validated_claims.py` rule, and the PR preserves both.
5. **The receipt content-addresses the measured relationship**: PASS — the SHIFTED-quote assertion in `test_a_checked_matching_basis_emits_positive_per_name_relation_receipt` proves the receipt changes when the measured relationship changes. The AAA-vs-BBB assertion in `test_a_name_whose_levels_are_on_another_basis_says_so_on_its_own_row` proves the receipt differs per row (different subject, different `levels_adjustment`).
6. **Per-name basis exceptions preserve their own receipt**: PASS — the existing `levels_adjustment` exception path is unchanged; the exception row's `levels_adjustment` is passed into `_basis_receipt` as the `levels_adjustment` parameter, so the receipt's digest reflects the row-local exception. The AAA/BBB test asserts the two receipts differ. The PR body explicitly states "per-name basis exceptions preserve their own `levels_adjustment` and receive a distinct receipt."
7. **PR-body self-claims are concrete and falsifiable**:
     - "132 passed" — concrete test count, matches the two touched test files in the regression sweep (`test_prophet_live_basis.py` + `test_prophet_live_evaluator.py`). Falsifiable.
     - "`python3 -m py_compile engine/prophet_live/live_states.py` => PASS" — concrete compile check. Falsifiable.
     - "`git diff --check` => PASS" — concrete whitespace check. Falsifiable.
     - "Exact head composes conflict-free with `main@707b5e87fcaddaf746144f044d8853245e6eb035` at no-write merge tree `ea9530d44ca4b0b9e45a4c9d90176bb4a2668357`" — concrete merge-tree hash. Falsifiable.
     - "Fresh protected main advanced after branch creation only in `data/research_vault/catalog.json`; no owned-path overlap" — concrete git diff. Falsifiable.
     - "Operation: `prophet-live-basis-receipt-b4-runtime-prereq-20260921-sol-001`" — a binding operation ID, not a `validated`-tag claim.
     - "Protected procedure: `Mastermind@3e66e43258f34db240d5bff76f54148c7af84ee4`, `mastermind.sol_skillpack.v1` 1.0.1 / bootstrap-major 1" — a binding skillpack anchor; the carrier is positively bound to Sol as the named authority.
     - All PR-body claims are concrete and falsifiable. No "validated" word in the PR body. PASS.

**Validated-claims residual issues (none material):**

- The PR body uses the word "pass" / "passed" for test outcomes (e.g. "132 passed", "`git diff --check` => PASS") — neither is the design-doctrine "validated" claim, and `scripts/check_validated_claims.py` does not scan PR-body prose. The "PASS" word here is operator-facing test-result language, consistent with prior audited PRs.
- The inline comment in `live_states.py` uses the phrase "absence of evidence, never an inferred pass" — the word "pass" here means "false-positive pass", i.e. the absence-of-evidence is not an inferred positive verdict. This is the correct engine-side analog of the user-facing null-disclosure rule. Not a finding.
- The new `BASIS_RELATION_SCHEMA = "prophet_live.basis_relation/v1"` constant uses the word "Relation" — not in the banned set. The schema identifier is content-addressing, not a claim word.
- The `basis_status="RESOLVED"` value is structurally similar to the design-doctrine-banned "validated" / "confirmed" words (they all describe a positive verdict on a measurement) — but the module's existing vocabulary uses `"RESOLVED"` for the same semantic (e.g. the existing `"unknown" / "forming" / "stress" / "dark"` state machine), and the design-doctrine `scripts/check_validated_claims.py` does not scan engine Python. A future half-B UI packet that surfaces `basis_status="RESOLVED"` to a user will need to render it as a state glyph / chip (e.g. `✓ Resolved`) and not as the banned `validated` / `confirmed` / `proven` copy word. That is correctly a downstream concern, not a finding on this PR.

**Validated-claims verdict: PASS.** The PR introduces no new user-facing claim using the banned "validated" / "proven" / "confirmed" / "fired" / "refuted" word family. The new engine-state value `"RESOLVED"` follows the module's existing uppercase-named-state convention. The new content-addressed `basis_receipt` is a SHA-256 digest of the measured relationship — falsifiable, reproducible, schema-bound. The four emit-but-fail-closed paths are test-enforced. The PR body is concrete and falsifiable throughout. The downstream rendering of `basis_status="RESOLVED"` on a user-facing surface is correctly deferred to a future half-B UI packet.

## Overall verdict

**PASS — half-B plain-language / theme / validated-claims audit on macro PR #7573.**

The PR is a bounded engine-only change that adds a positive per-name basis-receipt emission to the existing `evaluate(...)` payload. It introduces two row-level fields (`basis_status="RESOLVED"`, `basis_receipt="sha256:<hex>"`) and one artifact-level field (`meta.price_adjustment.relation_schema = "prophet_live.basis_relation/v1"`). The emission is fail-closed across four gates: not dark, has `prev_close`, audit tolerance enabled, measured gap inside tolerance. The receipt content-addresses the actual measured relationship, so it changes when the measurement changes and differs per row. Per-name basis exceptions preserve their own receipt. Three new regression tests + one modified existing test pin each emit-but-fail-closed path. PR body validation is green-first on the exact head `33be8d6ee1c31ce71463e1754251f251330befb7` (132 tests passed, `py_compile` PASS, `git diff --check` PASS, conflict-free compose with protected main).

Plain-language: **N/A by surface** — no user-facing copy was touched. The PR is engine-only. Standing plain-language laws are correctly preserved at the user-facing layer and are not relevant at the engine layer.

Theme: **N/A by surface** — no CSS, JS, or template was touched. No design-system token was introduced or modified. The TP-0 evidence matrix is correctly not invoked for an engine-only PR. The downstream rendering of the new `basis_status` / `basis_receipt` fields (if/when surfaced to a user) will be a separate half-B UI packet that owes the TP-0 evidence matrix.

Validated-claims: **PASS** — the PR introduces no new user-facing claim using the banned "validated" / "proven" / "confirmed" / "fired" / "refuted" word family. The new engine-state value `"RESOLVED"` follows the module's existing uppercase-named-state convention. The new content-addressed `basis_receipt` is a SHA-256 digest of the measured relationship (a Tier-2 receipt per the design doctrine). The four emit-but-fail-closed paths are test-enforced. The engine-side `FORBIDDEN_WORDS` rule (`tests/test_prophet_live_evaluator.py:1333`) is preserved. The PR body is concrete and falsifiable throughout.

**Residual notes (none blocking):**

- The new `basis_status="RESOLVED"` row state is structurally similar to the design-doctrine-banned "validated" / "confirmed" copy words at the conceptual level — they all describe a positive verdict on a measurement. The PR correctly defers the user-facing rendering of this state to a future half-B UI packet; when that packet lands, it must render `basis_status="RESOLVED"` as a state glyph / chip (e.g. `✓ Resolved`) and not as the banned `validated` / `confirmed` / `proven` copy word. This is a downstream concern, not a finding on this PR.
- The new `BASIS_RELATION_SCHEMA = "prophet_live.basis_relation/v1"` constant uses the word "Relation" — not in the banned set. The schema identifier is content-addressing, not a claim word. The downstream B4 runtime adapter consumer will need to read this schema identifier when it verifies receipts; that consumer is the next bounded vertical per the PR body's "Release boundary / next edge" section.
- The PR body's "Known unrelated main-branch issue" paragraph is the maintenance note about `data/research_vault/catalog.json` advancing on protected main while this branch was open — a normal cadence, no owned-path collision. Not an audit finding.

**No release-boundary or authority concern flagged.** The PR is a half-B engine-only change, does not touch candidate / plan / rank / gate / trading / sizing / publication / live-state decision / entry-geometry authority, does not widen or narrow the gate, and the carrier (`sol/prophet-live-basis-receipt-20260921`) is positively bound to Sol master `3e66e43258f34db240d5bff76f54148c7af84ee4`. The PR was squash-merged cleanly to `main` at 2026-09-21T04:34:27Z.

**This audit does not hold the merge, does not request repair, and does not block the worktree or any further PR.** The PR has already merged and is live. The audit is a record-of-pass for `orch(audit)` archival, consistent with the standing audit-record pattern (`orch(audit)` record PRs for each merged half-B PR from the last 24 h).

## Audit-record hook

The next `orch(audit)` record PR for macro #7573 follows the standing pattern: `orch(audit): record macro PR #7573 plain-language/theme/validated-claims audit (2026-09-21)`. The record PR body carries the exact audit head (`33be8d6ee1c31ce71463e1754251f251330befb7`), the verdict (PASS), and a pointer to this file (`orch/audits/macro_PR-7573.mm.md`). No durable change other than the audit record itself.
