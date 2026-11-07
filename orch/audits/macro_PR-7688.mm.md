# Historical audit editions for Macro PR #7688

## Reconciliation recorded 2026-11-05 UTC

Two different September22 audits were proposed at this path. The protected #7745 edition and the original #7718 edition are preserved separately below, with all payload bytes retained. Neither is silently replaced or treated as an identical duplicate. Their PASS verdicts, worker-style labels, check output, dated source/hold descriptions and future-work instructions are historical statements by those reports; this reconciliation does not reissue those verdicts or establish current runtime, strategy, trading or release authority.

### Verified immutable source facts

Audited [Macro #7688](https://github.com/mastermindx-market-intelligence/macro/pull/7688) has final source head `02e3b9173f3d04b4711f23afca3333040c0ad466` and protected **one-parent squash merge** [`f47ccdcf717149199c1540742141a08592cf4f22`](https://github.com/mastermindx-market-intelligence/macro/commit/f47ccdcf717149199c1540742141a08592cf4f22), merged **2026-09-22 07:34:06 UTC**. Its sole parent is `3647902e1f4f1ee50e7be8677ec3f603b809496b`. The final source head, historical audit-base claims and protected merge are different identities.

Root read the complete actual-parent merge delta and parsed the immutable source without executing it:

| Source fact | Verified result | Qualification of the historical reports |
|---|---|---|
| Complete protected merge | Two files, **+310/-0** | The incoming report's +321/-11 is not the protected net delta. |
| New engine module | `engine/prophet_entry_policy.py`, **+211/-0**, blob `1340395cfef7a81e0ce2b69abd548e4fcdd54095` | The incoming +247 and intermediate-commit arithmetic are not this final file's size/delta. |
| Test module delta | `tests/test_prophet_strategy_definition.py`, **+99/-0**, blob `18bbbc8d38ee5f9892b6669e97c9424239aad41d` | The complete merge adds **five** top-level test functions: **19 before / 24 after**. The protected report's three-function description and the incoming 33-to-38 claim do not describe these immutable endpoints. Definition counts are not executed test-case counts or RED-to-GREEN proof. |
| Session phases | **Five** source values: NON_SESSION, WRONG_SESSION, PREMARKET, AFTER_HOURS, RTH | The incoming report says four while enumerating five. Unsupported years raise `EntryPolicyContractError`; they do not produce a normal FAIL fact. |
| Final fact payload keys | **31 distinct keys**: 19 policy-material keys, 11 distinct payload additions, then fact_receipt | The protected report's 28-key count is incorrect for this source. This static count does not validate field values, source schedules or downstream consumers. |

The engine has six module-level function definitions, including five underscored helpers and `evaluate_session_eligibility`; the protected report's wording about four exported symbols is not a verified public-API inventory. The five new test functions cover the named RTH, before/after-hours, early-close, non-session/wrong-clock, aware-clock/strategy/era boundaries in source. No original test, validator, calendar lookup or runtime operation was rerun for this archive.

### Provenance and exact preservation

- **Protected edition:** [#7745](https://github.com/mastermindx-market-intelligence/macro/pull/7745), report commit `a9199a70d4e98aa3653754264935cfe801149ad1`, introduced by protected merge `348f669e14f1cd4591e10b96df51f9c022594d13` at 2026-09-22 22:28:46 UTC. Its payload at current integration base `172893fab8b162a0297ecd3778f9f4b54d152985` is byte-identical to that merge: blob `32bd4fb8fe9405739effa203e2a208696b745937`, **30,414 bytes**, SHA256 `e5825197c16b4cf93bc84cf52c479a66690f51dcfd2682694fd121db3ece283e`, with its original terminal LF retained. The report commit is attributed by GitHub to `claude`, raw author Claude Code; no actual qwen worker execution is established by the report's style label.
- **Original proposed edition:** [#7718](https://github.com/mastermindx-market-intelligence/macro/pull/7718), authored in commit `d743d4d89638ffbac3fd566023ba0076f23a2688` and retained through source head `d7faa93fccc1bf069dafa422c25b0852e7af1314`: blob `bd8ba6165a7f8f41978f03e17ef6ed2a05c12893`, **28,801 bytes**, SHA256 `f49f3069676ddf66ecd48e50605d47480c2b90c5e4eb499e8ee853ff801ed5f7`. Its original payload has **no terminal LF**; one outside framing LF separates it from the closing fence. The original commit is linked to Karim13014 with raw author Claude Code; two later Chris-authored web-flow commits merge main. None has a coauthor trailer.

Both payloads appear once inside separate four-tilde historical fences. Added headings, corrections, separators and the explicitly identified framing LF are outside those payloads.

### Limits and continuing authority

The reports' historical DRAFT/hold wording does not reverse #7688's source merge and does not establish today's program-release state. Their future wiring and era-extension suggestions are non-operative historical proposals. This archival PR does not extend `NYSE_RTH_2026`, alter the policy owner, wire a consumer, select a security, or lift any actual original-carrier hold. Future work belongs to the currently assigned receiver under current protected source law and the actual original-carrier effect/custody constraints; old actor names are not new approval gates.

A content hash proves an identity relationship, not schedule accuracy, empirical validity, source rights or live acceptance. An absent validator finding or a disclaimer does not by itself prove correctness or waive required evidence. All claimed historical validation output, estate totals, execution counts, calendar verification and runtime ownership remain attributed unless separately established by their own canonical receipts. This change preserves research/audit evidence only; no product source, workflow, validator, ledger status, provider action, production state or trade authority is changed.

## Edition A — protected #7745 report, verbatim historical payload

~~~~markdown
# Plain-language / theme / validated-claims audit — macro PR #7688

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-22.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7688 |
| title | `feat(prophet): own B4 session eligibility policy` |
| merged_at | 2026-09-22T07:34:06Z |
| head (semantic) | `02e3b9173f3d04b4711f23afca3333040c0ad466` |
| base | `main` (PR body: "This is the existing #7688 carrier, still based directly on protected `main`", with "Fresh protected Macro observed during repair: `main@1e767a2f5b43f302b0e1068c9a7e60b12aeb98ee`") |
| branch | `claude/*` per standing fleet law; protected Mastermind re-pin `1358f9d9ab7b612e03c441982d442118116f837d` recorded at execution start (`mastermind.sol_skillpack.v1` 1.0.1 / bootstrap-major 1) |
| changed files | **2 files, +310 / −0.** `engine/prophet_entry_policy.py` (NEW, +211 — a v1 + v2 commit pair, totalling 167 lines in the initial commit and 66 lines / 11-line replace in the v2 commit; net +211); `tests/test_prophet_strategy_definition.py` (MODIFIED, +99 — three new test functions / three new assertions inside an existing test). |
| additions / deletions | 310 / 0 |
| labels | none visible at fetch time; merges from the macro sweeper signature on the listed timestamp. |
| scope collision | none — PR body explicitly bounds scope to a B4-session-eligibility policy owner ("This module owns only strategy policy facts that no incumbent data/geometry owner can truthfully answer"), explicitly disclaims any ranking/admission/sizing/execution/trade authority, and explicitly distinguishes itself from #7687 (separate structural-overlay owner) and from #7581 (existing runtime adapter, must not be duplicated). PR body closes `DRAFT / HOLD-FOR-SOL`. |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --json number,title,mergedAt --jq '.[] | select(.mergedAt > (now - 86400 | strftime("%Y-%m-%dT%H:%M:%SZ")))'` against `git ls-tree origin/main -- orch/audits/` (per the standing workflow memo `orch_audit_filename_convention.md`): the most recent macro merge at audit time is `fix(market-memory)` #7741 (4-file restore of a `data/seal_receipts` write-then-delete shape — small infra correction, not a half-B feature). The merges immediately before it are (a) `feat(prophet): own B4 structural risk ceiling` #7726 (already audited at `orch/audits/macro_PR-7726.mm.md`); (b) `orch(audit)` filing-only PRs #7736, #7730, #7714, #7707, #7703, #7732, #7730, #7699, #7689, #7686, #7682, #7679, #7673, #7671, #7670, #7659, #7651, #7643 — record-keeping); (c) `docs` PRs #7735 (`UNIFIED_DASHBOARD_DISPOSITION` doc update) and #7698 (`docs(ric): RIC F3 production proof`) — docs-only; (d) `noop` #7733 — idempotent re-stamp; (e) `feat(prophet)` sister PRs #7726 (B4 structural risk ceiling, already audited) and #7687 (B4 structural-overlay semantic repair, already audited); (f) `research(risk)` evidence-only deliverables #7683 and #7666 — user-facing surface untouched; (g) `agentos:` release-frontier sweeps #7679 — knowledge-plane only; (h) `fix(ci)` infra-only PRs #7693, #7678, #7614 — `check_design_system.py --mode enforce-added` reports zero template/JS/CSS surface added; (i) UI-facing half-B PRs #7712 (markets.html risk-regime strip), #7701 (`[MO F07] event -> AssumptionChange`), #7667 (compact China regime driver rail), #7634 (`fix(reports)`), #7629 (China public live client) — already audited at `orch/audits/macro_PR-<n>.mm.md`. **PR #7688** — a Prophet B4 strategy-policy owner that adds one new engine module + one paired test, with no new template/component/CSS/JS surface, no claim authorship, no theme-token or layout change, but a real new engine policy contract (B4 session eligibility) that the design system + bilingual + retrospective-evidence chain must still read for user-impact language drift — is the appropriate half-B scope: **2 files**, +310/−0, fully self-contained inside `engine/prophet_entry_policy.py` (NEW) + its test module.

**Nature of change (new bounded engine module + one paired test):**

1. *New file — `engine/prophet_entry_policy.py` (NEW, +211 across two commits).* The module deterministically owns **only** Early Leadership / Sector Rotation (`2_15_SESSIONS`, new-entry role) session eligibility — i.e. one B4 gate (`session_eligibility`) with one bounded vertical (RTH window for the exact market session). It composes the existing `lib.nyse_calendar.is_session` (whether a U.S. cash-equity session exists) with a B4-owned, era-stamped `NYSE_RTH_2026` execution-window law for the clock boundary (`_RTH_OPEN_ET=09:30`, `_RTH_REGULAR_CLOSE_ET=16:00`, `_RTH_EARLY_CLOSE_ET=13:00`, `_EARLY_CLOSE_DATES={2026-11-27, 2026-12-24}`). It does not create a second calendar, quote source, entry-geometry engine, ranking signal, plan, or trade authority. The v1 commit lays down the wire (`evaluate_session_eligibility(...)` returns one deterministic fact dict with `verdict` ∈ {`PASS`,`FAIL`}, `session_phase` ∈ {`NON_SESSION`,`WRONG_SESSION`,`PREMARKET`,`AFTER_HOURS`,`RTH`}, `extended_hours_eligible: False`, three SHA-256 fact receipts). The v2 commit replaces the originally-imported `engine.session_digest.session_window_et` (a descriptive/coverage-tier helper that explicitly has no gate authority) with a B4-owned `_execution_session_window_et(session)` that raises `EntryPolicyContractError` for sessions outside the frozen `NYSE_RTH_2026` era — fail-closed on unsupported policy years — and freezes the 2026-07-03 observed Independence Day full closure as a `NON_SESSION_DATE` rather than an early close (a subtle but important calendar fact that the descriptive helper did not encode). The PR body explicitly names the verified calendar fact: "the official NYSE 2026 schedule, verified 2026-09-22, with 13:00 ET closes frozen for 2026-11-27 and 2026-12-24; 2026-07-03 remains a full closure, not an early close."

2. *Where the impact lives.* No live probability / band / score / weight / gate / policy / sizing / ranking / ledger / capital authority is changed (PR body explicitly disclaims via the closing anti-promotion bullet "It does not rank, admit candidates, compute geometry, size, originate plans, execute or trade."). What changes is the *fact-contract surface* for one B4 gate: a new module publishes one deterministic JSON-shape (`SCHEMA = "prophet.entry_policy_fact/v1"`, `SESSION_POLICY_VERSION = "early-leadership-sector-rotation-session-rth-v2"`, `SESSION_POLICY_ERA = "NYSE_RTH_2026"`, `GATE = "session_eligibility"`) that future B4 stages (`#7581` runtime adapter, `#7584` acceptance) can compose against. PR body explicitly names the unresolved separate owners: "Positive risk-ceiling, liquidity/fillability and gap/velocity owners remain unresolved; #7584/#7581 acceptance and #7180 fresh-source release remain separate."

3. *Evidence preservation.* The PR adds three new test functions / three new assertions inside the existing `tests/test_prophet_strategy_definition.py` module (verified by reading the diff): `test_b4_session_policy_passes_only_inside_actual_rth_window` gets seven new assertions for `session_policy_era`, `calendar_owner`, `execution_window_owner`, `execution_schedule_source`, `execution_schedule_verified_on`, `supported_session_years`, `early_close_dates`; `test_b4_session_policy_uses_actual_early_close_not_a_hardcoded_1600` gets a Christmas-eve-at-18:00-UTC scenario asserting `verdict=FAIL` and `session_close=13:00:00-05:00`; `test_b4_session_policy_rejects_non_session_and_wrong_session_clocks` gets a July-3rd-observed-Independence-Day scenario asserting `verdict=FAIL`, `session_phase=NON_SESSION`, `session_close is None`; and a new `pytest.raises(EntryPolicyContractError, match="outside NYSE_RTH_2026")` for a 2027-01-04 session. Tests cover normal RTH, premarket, exact close, both official 2026 early-close dates, Thanksgiving holiday, the 2026-07-03 observed Independence Day full closure, wrong-session clocks, unsupported policy era, accepted-strategy integrity, stable receipts, and `extended_hours_eligible=false`.

## Diff content (scoped to this audit)

2 files, no new template/component/CSS/JS surface. Both files are engine Python + a paired test module. The visible-to-product surface is zero.

### `engine/prophet_entry_policy.py` (NEW, +211 across two commits)

The module opens with a module-level docstring that explicitly bounds the owner's scope:

```
This module owns only strategy policy facts that no incumbent data/geometry owner
can truthfully answer.  The first bounded vertical is session eligibility for
Early Leadership / Sector Rotation.  It composes the existing NYSE full-day
session calendar with an era-stamped RTH execution-window law frozen here; it does
not promote a descriptive/coverage helper into gate authority, create a second
session-existence calendar, quote source, entry-geometry engine, ranking signal,
plan, or trade authority.

Extended-hours eligibility intentionally fails closed in v2.  The repository's
extended-quote plane is not yet an accepted execution/fillability source for this
strategy, so premarket/after-hours opportunity research cannot be laundered into
B4 entry permission.
```

The module exports four public symbols: `SCHEMA`, `SESSION_POLICY_VERSION`, `SESSION_POLICY_ERA`, `GATE`, `EntryPolicyContractError`, `_policy_material`, `_parse_decision_at`, `_parse_session`, `_execution_session_window_et`, `evaluate_session_eligibility`. The single public entry point is `evaluate_session_eligibility(strategy_definition, decision_at, market_session)` which returns a deterministic fact dict. The dict shape is exhaustively enumerated in the source (28 keys) — every key is a snake_case identifier, a constant string from a closed enum, or an ISO timestamp; none of these strings is a user-facing display string, and none reaches `templates/` or `site/` directly without an intermediate producer that would re-shape the verdict/phase/reason constants into plain-language copy. The public constant strings used as verdict / phase / reason identifiers (`"PASS"`, `"FAIL"`, `"NON_SESSION"`, `"WRONG_SESSION"`, `"PREMARKET"`, `"AFTER_HOURS"`, `"RTH"`, `"INSIDE_ACTUAL_RTH_WINDOW"`, `"POST_RTH_NOT_ELIGIBLE_V1"`, `"PREMARKET_NOT_ELIGIBLE_V1"`, `"NON_SESSION_DATE"`, `"DECISION_NOT_IN_MARKET_SESSION_DATE"`, `"FAIL_CLOSED_PENDING_ACCEPTED_SOURCE_AND_FILLABILITY"`) are stable internal identifiers designed to be translated by a downstream producer; none is gloss-tier prose.

The two internal helpers (`_parse_decision_at`, `_parse_session`) are contract validators that raise `EntryPolicyContractError` on malformed inputs. The added `_execution_session_window_et(session)` raises `EntryPolicyContractError` for sessions outside the frozen era — fail-closed on policy-year mismatch. The added `_policy_material(strategy_definition_id)` exposes the policy receipt's stable material (including `execution_schedule_source = "NYSE_HOLIDAYS_AND_TRADING_HOURS_2026"` and `execution_schedule_verified_on = "2026-09-22"`) — these receipts are how a future reviewer proves the source schedule against a published NYSE reference, exactly matching the receipt discipline used elsewhere in the engine. The three SHA-256 receipts (`policy_receipt`, `session_receipt`, `fact_receipt`) are computed over canonical-JSON serializations of the deterministic material — same receipt pattern as other engine modules.

### `tests/test_prophet_strategy_definition.py` (+99 / 0, MODIFIED)

Four targeted edits in the test module:

1. *Import update (+3 lines).* Add `EntryPolicyContractError` and `SESSION_POLICY_VERSION` to the existing `from engine.prophet_entry_policy import ...` block, plus the new `SESSION_POLICY_ERA` constant.

2. *Existing test extension in `test_b4_session_policy_passes_only_inside_actual_rth_window` (+7 lines).* Seven new assertions on the policy-receipt material: `session_policy_era`, `calendar_owner`, `execution_window_owner`, `execution_schedule_source`, `execution_schedule_verified_on`, `supported_session_years`, `early_close_dates`. These pin the receipt's stable material so a future regression that changes the published material without bumping the version is caught at the test boundary.

3. *Christmas-eve scenario in `test_b4_session_policy_uses_actual_early_close_not_a_hardcoded_1600` (+4 lines).* `_session_policy("2026-12-24T18:00:00Z", "2026-12-24")` asserts `verdict == "FAIL"` and `session_close.endswith("13:00:00-05:00")` — pins the exact early-close clock for the 2026-12-24 entry in the frozen `_EARLY_CLOSE_DATES` set.

4. *July-3rd scenario in `test_b4_session_policy_rejects_non_session_and_wrong_session_clocks` (+4 lines).* `_session_policy("2026-07-03T15:00:00Z", "2026-07-03")` asserts `(verdict, session_phase) == ("FAIL", "NON_SESSION")` and `session_close is None` — pins the calendar fact that 2026-07-03 is a full closure, not an early close. This is the falsifier test for the subtle calendar shape documented in the PR body.

5. *Era-mismatch escalation in `test_b4_session_policy_requires_aware_clock_and_accepted_strategy_definition` (+3 lines).* `with pytest.raises(EntryPolicyContractError, match="outside NYSE_RTH_2026")` for a 2027-01-04 session — pins the fail-closed behaviour for unsupported policy years.

All five edits use the existing `_session_policy(...)` / `_b4_facts()` / `_b4_evaluate()` helpers — no new test infrastructure, no new fixtures, no new import beyond the three new public symbols.

## Plain-language findings

### 1.1 Pass — there is no user-facing copy in this PR; the macro-side plain-language discipline is structurally inapplicable on this diff

The diff contains zero template (`templates/`), zero product HTML (no `site/`), zero CSS, zero JS, zero chat surface, zero bilingual receipt text. Both changed files are Python: `engine/prophet_entry_policy.py` (new engine module) and `tests/test_prophet_strategy_definition.py` (test module). `tests/test_bilingual_ui.py` and `scripts/check_bilingual.py` cannot produce a finding against this diff by construction — there is no template surface to scan.

For the project-side plain-language read, the only prose that lands in this PR is the module-level docstring at the top of `engine/prophet_entry_policy.py` and the seven new comment lines that document the v2 replace of `engine.session_digest.session_window_et` with the B4-owned `_execution_session_window_et`. Both blocks are internal documentation for engineers reading the engine, not user-facing copy. The docstring uses bounded architectural-rationale vocabulary ("owns only strategy policy facts", "bounded vertical", "descriptive/coverage helper", "gate authority", "fail-closed"), names the contracts it does not duplicate ("session-existence calendar, quote source, entry-geometry engine, ranking signal, plan, or trade authority"), and explicitly disclaims any extended-hours laundering. The v2-replace comment names the rationale ("`lib.nyse_calendar` remains the owner of whether a cash-equity session exists. The clock window is intentionally owned here because the repository's other early-close helper is descriptive/coverage-tier and explicitly has no gate authority. An unsupported year is unavailable policy, never a guessed PASS.") — bounded, negative-space, falsifier-aware. Neither block is user-visible; both are documentation that future maintainers of `engine/prophet_entry_policy.py` need to recognise why the B4 owner owns the execution window and why the era is frozen. The PR body itself is a capability description with the canonical anti-promotion closer ("It does not rank, admit candidates, compute geometry, size, originate plans, execute or trade.") and the canonical `DRAFT / HOLD-FOR-SOL` closer — matching the same shape used by other recent macro engine-only feature PRs.

### 1.2 Pass — the docstring preserves the prose discipline

The new module docstring in `engine/prophet_entry_policy.py` names the standing architectural decision (B4 owns the clock window because `engine.session_digest.session_window_et` is descriptive/coverage-tier with no gate authority; the era is frozen at `NYSE_RTH_2026`), the non-waivable cases (`FAIL` for `NON_SESSION` / `WRONG_SESSION` / `PREMARKET` / `AFTER_HOURS` / unsupported year), the accepted case (`PASS` only inside `[09:30 ET, actual close)`), and the bounded behaviour for extended hours (fail-closed pending an accepted extended-quote/source-rights/fillability lane). None of these strings is user-visible; they are documentation that future maintainers of `engine/prophet_entry_policy.py` need in order to recognise why the policy owner exists, why the era is frozen, and why extended hours are explicitly fail-closed. The docstring does not oversell, does not use banned-glance vocabulary (`validated` / `proved` / `guaranteed` / `certified` / "ships"), and explicitly references the contracts it does not duplicate ("session-existence calendar, quote source, entry-geometry engine, ranking signal, plan, or trade authority") — so the falsifier (the policy owner is bounded to one vertical, not the broader strategy authority) is documented, not implied.

### 1.3 Pass — the PR body uses bounded, anti-promotion language

PR body opening (Capability section): "First owner-native positive B4 policy fact after the runtime adapter identified `session_eligibility` as permanently UNKNOWN without a strategy execution policy." — bounded to "owner-native positive B4 policy fact", naming the upstream contract (`session_eligibility` gate, identified UNKNOWN by the existing runtime adapter) and the gap this PR fills (strategy execution policy). No ranking, admission, sizing, execution, or trade authority is asserted.

PR body mid-section names the explicit anti-promotion bullet: "It does not rank, admit candidates, compute geometry, size, originate plans, execute or trade." — the canonical anti-promotion enumeration used across recent macro engine-only feature PRs (matching the canonical anti-weakening line in #7687).

PR body closing: "**DRAFT / HOLD-FOR-SOL.** The prior REQUEST_CHANGES was against the predecessor semantics; this source repair requires genuine fresh independent review and hosted exact-head qualification. It is not yet wired into #7581, does not clear B4, and is not merge/deploy/production/user-path acceptance. Positive risk-ceiling, liquidity/fillability and gap/velocity owners remain unresolved; #7584/#7581 acceptance and #7180 fresh-source release remain separate. No named security is selected or forced into a recommendation." — matches the standing `DEC:SOL-HOLD-IS-A-MERGE-BARRIER` hold protocol: the body names the authority (Sol), the release condition (none stated — the body does not promise a release), the scope (source capability only), explicitly disclaims six promotion-bearing states (review acceptance, wired into #7581, B4 cleared, merge, deploy, production/user-path acceptance), and explicitly names the unresolved separate owners (risk-ceiling, liquidity/fillability, gap/velocity). No banned vocabulary, no user-facing capability claim.

## Theme findings

### 2.1 Pass — `python3 scripts/check_design_system.py --mode enforce-added` reports **0 blocking findings** on this diff

The diff contains zero template/component/CSS/JS lines, so the design-system check has zero lines to assert against. The `enforce-added` mode reads the PR's own diff lines only and does not assert against pre-existing estate debt; the PR adds nothing the check could read as a design-system addition. **Consistent with `enforce-added` ratchet** — the design-system ratchet pins NEW surface; this PR contributes no surface.

### 2.2 Pass — TP-0 dark/light × EN/ZH × 1440/390 evidence matrix is structurally inapplicable; the change does not touch any visual surface

The TP-0 dark-and-light-are-two-art-directions rule (`scripts/check_design_system.py` + the standing design-doctrine §Theme art direction) requires every material UI packet to name DARK TREATMENT, LIGHT TREATMENT, which mechanisms intentionally differ, the reference/baseline, theme-specific degraded states, and the evidence matrix (dark/light × EN/ZH × desktop 1440 / mobile 390).

This PR adds zero user-visible surface. Every changed line is in `engine/` or `tests/` Python — no template, no inline style, no `<style>` block, no CSS rule, no JS payload. The "Token substitution alone is never proof of a light design" rule, the "Substantive product styling may not be authored as an opaque runtime stylesheet system inside page/composer JavaScript" rule, and the "every material UI packet must name DARK TREATMENT / LIGHT TREATMENT" rule are all structurally inapplicable. **Consistent with TP-0**.

### 2.3 Pass — `check_runtime_style_injection.py` is out-of-scope by construction

The diff contains no `style="..."` injection, no `style.textContent =`, no parallel palette, no duplicated light/dark branches inside JS, no inline `<style>` block, no `data-theme` override, no `class` attribute containing theme tokens. There is no JS payload change anywhere in the diff — both files are Python.

### 2.4 Pass — no theme-art-direction assertion is made or implied

The PR body does not claim a dark/light, EN/ZH, mobile/responsive, palette, type, motion, or material-design effect. It closes with the anti-promotion bullet plus the explicit "no ranked candidate, no sized plan, no selected security" line and the `DRAFT / HOLD-FOR-SOL` hold protocol. No evidence matrix is owed because no design surface is touched.

## Validated-claims findings

### 3.1 Pass — `python3 scripts/check_validated_claims.py --list` produces no MISS row for this PR's diff

`scripts/check_validated_claims.py --list` filtered for any `7688` / `prophet_entry_policy` / `session_eligibility` / `NYSE_RTH_2026` / `prophet.entry_policy_fact` key produces no MISS row — confirming the validator has no registered claim against this PR and nothing in the diff creates one. The PR's only user-facing-shaped text is the canonical anti-promotion closer ("It does not rank, admit candidates, compute geometry, size, originate plans, execute or trade."), which is the standing disclaimer that exempts the change from the promotion-bearing claim regime entirely. The PR body's source-schedule claim ("the official NYSE 2026 schedule, verified 2026-09-22, with 13:00 ET closes frozen for 2026-11-27 and 2026-12-24; 2026-07-03 remains a full closure, not an early close") is a third-party-published-schedule fact referenced from a named external authority (NYSE official schedule), not a platform-asserted "validated" claim — and the receipt is content-addressed in the policy material (`execution_schedule_source = "NYSE_HOLIDAYS_AND_TRADING_HOURS_2026"`, `execution_schedule_verified_on = "2026-09-22"`), which is the structured way the engine encodes external references without making a promotion-bearing user-facing claim.

### 3.2 Pass — the PR body does not introduce any promotion-bearing claim

PR body opening: "First owner-native positive B4 policy fact after the runtime adapter identified `session_eligibility` as permanently UNKNOWN without a strategy execution policy." — bounded to "owner-native positive B4 policy fact", naming the upstream contract (the existing runtime adapter's identification of `session_eligibility` as UNKNOWN) and the gap this PR fills (strategy execution policy). No release/upgrade/score/rank promotion.

PR body mid-section: "It composes the official NYSE 2026 schedule, verified 2026-09-22, with 13:00 ET closes frozen for 2026-11-27 and 2026-12-24; 2026-07-03 remains a full closure, not an early close. The v2 session policy emits `PASS` only inside `[09:30 ET, actual close)` for the exact market session. Non-session dates, wrong-session clocks, premarket, after-hours and the early-close tail emit `FAIL`. A session outside the frozen 2026 policy era is unavailable policy and raises `EntryPolicyContractError` rather than guessing a PASS/FAIL. Extended hours remain explicitly fail-closed pending an accepted extended-quote/source-rights/fillability lane." — bounded to a deterministic-policy contract: explicit PASS/FAIL surface, explicit fail-closed on unsupported years, explicit fail-closed on extended hours. No release/upgrade/score/rank promotion.

PR body closing: "**DRAFT / HOLD-FOR-SOL.** The prior REQUEST_CHANGES was against the predecessor semantics; this source repair requires genuine fresh independent review and hosted exact-head qualification. It is not yet wired into #7581, does not clear B4, and is not merge/deploy/production/user-path acceptance. Positive risk-ceiling, liquidity/fillability and gap/velocity owners remain unresolved; #7584/#7581 acceptance and #7180 fresh-source release remain separate. No named security is selected or forced into a recommendation." — explicitly disclaims six promotion-bearing outcomes (review acceptance, wired into #7581, B4 cleared, merge, deploy, production/user-path acceptance) and explicitly names the unresolved separate owners (risk-ceiling, liquidity/fillability, gap/velocity, fresh-source release). This is the canonical anti-promotion line for an engine-only feature PR under a Sol hold.

### 3.3 Pass — no `data/regime/validated_claims_allowlist.json` or template surface is touched

`tests/test_validated_claims_engine.py`, `tests/test_validated_claims_registry_source.py`, `tests/test_validated_claims_structural_scope.py`, and `tests/test_validated_claims_thirdparty.py` are the surface that enforces the user-facing claim discipline. None of them read or assert against engine code or test modules — they read `templates/` and the structural scope of `data/regime/validated_claims_allowlist.json`. This PR modifies neither surface. The validator's behaviour is unchanged on this PR. **Consistent with the structural-scope contract.**

### 3.4 Pass — no new `validated`/`proved`/`guaranteed`/`certified` vocabulary in any user-facing path

The PR diff and body contain zero uses of the promotion-bearing vocabulary (`validated` / `proved` / `guaranteed` / `certified` / "ships"). The module docstring uses "owns only strategy policy facts" (architectural scope framing), "fail-closed" (negative-space framing), "extended-quote plane" (technical scope framing), and "unavailable policy, never a guessed PASS" (anti-falsifier framing) — none of which is on the banned-glance list. The PR body's title and description use "policy fact" (architectural scope framing), "B4-owned" (owner-boundary framing), "fail-closed" (negative-space framing), and "DRAFT / HOLD-FOR-SOL" (hold protocol framing). No overselling language.

## Diff-line evidence (line-anchored, for the running cross-reference)

| claim | file:line anchor (semantic head `02e3b9173f3d04b4711f23afca3333040c0ad466`) |
|---|---|
| Module docstring bounds scope to one B4 vertical | `engine/prophet_entry_policy.py:1-13` (module docstring) |
| Era frozen at `NYSE_RTH_2026` | `engine/prophet_entry_policy.py:25` (`SESSION_POLICY_ERA = "NYSE_RTH_2026"`) |
| Exact 2026 early-close dates | `engine/prophet_entry_policy.py:32` (`_EARLY_CLOSE_DATES = frozenset({date(2026, 11, 27), date(2026, 12, 24)})`) |
| Era-mismatch fails closed via `EntryPolicyContractError` | `engine/prophet_entry_policy.py:97-100` (`raise EntryPolicyContractError(f"market_session outside {SESSION_POLICY_ERA} session policy era")`) |
| Receipt exposes `execution_schedule_source` and `execution_schedule_verified_on` | `engine/prophet_entry_policy.py:117-118` (in `_policy_material`) |
| Receipt exposes `supported_session_years`, `rth_open_et`, `regular_close_et`, `early_close_et`, `early_close_dates` | `engine/prophet_entry_policy.py:119-123` (in `_policy_material`) |
| Authority field set: `can_rank`, `can_admit_candidate`, `can_size`, `can_execute`, `can_trade` all `False` | `engine/prophet_entry_policy.py:124-130` (`authority` dict in `_policy_material`) |
| Verdict emit: `PASS` only inside `[09:30 ET, actual close)`; non-session, wrong-session, premarket, after-hours emit `FAIL` | `engine/prophet_entry_policy.py:171-181` (verdict assignment block) |
| Christmas-eve scenario asserts early-close clock | `tests/test_prophet_strategy_definition.py:456-458` |
| July-3rd-observed Independence Day scenario asserts full closure | `tests/test_prophet_strategy_definition.py:469-471` |
| Era-mismatch escalation test | `tests/test_prophet_strategy_definition.py:491-492` |
| Anti-promotion bullet in PR body | PR body §Capability, closing sentence: "It does not rank, admit candidates, compute geometry, size, originate plans, execute or trade." |
| `DRAFT / HOLD-FOR-SOL` hold protocol in PR body | PR body §Release boundary, opening line |

## Overall verdict

**PASS on all three dimensions.** This PR adds a new engine module (`engine/prophet_entry_policy.py`, +211 across two commits) and three new tests inside `tests/test_prophet_strategy_definition.py` (+99 across four targeted edits). No template/component/CSS/JS surface is added, no template/file is touched in `templates/` or `site/`, no `data/regime/validated_claims_allowlist.json` row is added or modified, no user-facing copy is introduced, and no promotion-bearing vocabulary (`validated` / `proved` / `guaranteed` / `certified`) is used in any user-facing path. The plain-language discipline is structurally inapplicable (no user-facing surface); the TP-0 dark/light × EN/ZH × 1440/390 evidence matrix is structurally inapplicable (no visual surface); the validated-claims allowlist registry is not touched; the third-party-schedule fact (NYSE 2026 official holiday-and-trading-hours) is encoded as content-addressed receipt material rather than a platform-asserted "validated" claim. The PR body explicitly disclaims six promotion-bearing outcomes (review acceptance, wired into #7581, B4 cleared, merge, deploy, production/user-path acceptance) and explicitly closes `DRAFT / HOLD-FOR-SOL`. The PR is a tightly bounded engine capability, consistent with the standing `DEC:SOL-HOLD-IS-A-MERGE-BARRIER` hold protocol for source-repair carriers under Sol.

**PASS** (plain-language: PASS — structurally inapplicable; theme: PASS — structurally inapplicable; validated-claims: PASS — no surface touched, no promotion-bearing vocabulary used).
~~~~

## Edition B — proposed #7718 report, verbatim historical payload

~~~~markdown
# Plain-language / theme / validated-claims audit — macro PR #7688

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-22.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7688 |
| title | `feat(prophet): own B4 session eligibility policy` |
| merged_at | 2026-09-22T07:34:06Z |
| head (semantic) | `02e3b9173f3d04b4711f23afca3333040c0ad466` (v2 final head after the dashboard-bot follow-up on top of the Sol-authored v1 commit) |
| merge_commit | `f47ccdcf717149199c1540742141a08592cf4f22` |
| base | `main` at `410ba8bf21a5f3d50dd47289ac85447df34b5b96` |
| branch | `sol/prophet-b4-session-policy-v1-20260922` (Sol-authored patch 1; `dashboard-bot` follow-up patch 2 added the era-stamped `_execution_session_window_et` helper, the `NYSE_RTH_2026` execution-window law, the `2026-11-27` and `2026-12-24` early-close dates, and the `2026-07-03` full-closure distinction) |
| author | Sol CEO (commit 1) + dashboard-bot (commit 2) — squash-merged by the macro sweeper |
| changed files | **2 files, +321 / −11.** `engine/prophet_entry_policy.py` (NEW, +247) — single-canonical owner `evaluate_session_eligibility` + the era-stamped `_execution_session_window_et` helper; `tests/test_prophet_strategy_definition.py` (+99 / −0) — five red-first regression tests covering normal RTH, premarket/after-hours boundary, the exact 2026-11-27 early close, the 2026-07-03 full closure, wrong-session clocks, the unsupported-era guard (`2027-01-04`), and the offset-aware-clock guard. |
| additions / deletions | 321 / 11 |
| labels | none visible at fetch time; merges from the macro sweeper signature on the listed timestamp. |
| scope collision | none — PR body explicitly bounds scope to "first owner-native positive B4 policy fact after the runtime adapter identified `session_eligibility` as permanently UNKNOWN", and the related-PR boundary block names #7687 (separate structural-overlay owner), #7581 (existing runtime adapter, must not be duplicated), and the test-owner collision with #7687 that must be reconciled only on the later lawful wiring edge. |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --limit 30` (24-h window) against `ls orch/audits/macro_PR-*.mm.md`: every recent macro merge in the prior idle-audit window was either (a) `orch(audit)` record-keeping PRs (#7707, #7703, #7699, #7689, #7686, #7682, #7673, #7671, #7659, #7651, #7644, #7636, #7627 — filing-only); (b) `fix(ci)` infra-only PRs (#7678, #7628 — `check_design_system.py --mode enforce-added` reports zero template/JS/CSS surface added by them); (c) research/governance/evidence-only deliverables (#7698, #7683, #7679, #7666 — research/agentos/doc-only surfaces); (d) already-audited PRs (#7701 → `orch/audits/macro_PR-7701.mm.md`, #7687 → `orch/audits/macro_PR-7687.mm.md`, #7667 → `orch/audits/macro_PR-7667.mm.md`, #7634 → `orch/audits/mastermindx-market-intelligence_pr7634.mm.md`, #7632 → `orch/audits/macro_PR-7632.mm.md`). The remaining recent merge with a substantive engine surface, without a committed audit, and with material semantic ownership content (a new single-canonical owner for B4 `session_eligibility` that the design system + bilingual + retrospective-evidence chain all need to read) is **#7688** — a half-B scope: 2 files, +321/−11, no new user-facing copy or template surface, no claim authorship, no theme-token or layout change, but a real single-canonical-owner repair that explicitly fails-closed on premarket/after-hours and the unsupported-era boundary.

**Nature of change (single-canonical B4 session-eligibility owner, half-B engine surface-touch):**

1. *Defect — B4 `session_eligibility` was permanently UNKNOWN.* The Prophet runtime adapter (`engine/prophet_strategy_definition.py` B4 path) reads the strategy-identity/availability gates, but no policy owner existed for `session_eligibility`. PR #7688 introduces `engine/prophet_entry_policy.py` as the single deterministic owner. It composes two existing modules — `lib.nyse_calendar.is_session` (calendar existence) and the new era-stamped `_execution_session_window_et` helper (RTH window clock) — and emits a fact payload whose `authority` block sets every flag false (`can_rank / can_admit_candidate / can_size / can_execute / can_trade`). The patch is the first positive B4 policy fact the lane has authored, deliberately fail-closed on extended hours ("the repository's extended-quote plane is not yet an accepted execution/fillability source for this strategy, so premarket/after-hours opportunity research cannot be laundered into B4 entry permission"), and fail-closed on any session outside the frozen `NYSE_RTH_2026` era (raises `EntryPolicyContractError` rather than guessing PASS/FAIL).

2. *Where the impact lives.* No live probability / band / score / weight / gate / policy / sizing / ranking / ledger / capital authority is changed at user surface (PR body explicitly disclaims; `can_size / can_trade / can_execute` are all false in the emitted `authority` block). What changes is the internal availability evidence: B4 now has a receipt-bearing deterministic owner for session eligibility where before it had an `UNKNOWN` placeholder. The downstream `#7581` runtime adapter is not yet wired to this fact, and the PR body explicitly states "It is not yet wired into #7581, does not clear B4, and is not merge/deploy/production/user-path acceptance." The PR body's closing release boundary is **DRAFT / HOLD-FOR-SOL** even after merge — i.e. the PR landed the source repair, the lane's full release remains a separate decision.

3. *Era/freeze discipline.* The v2 patch (the `dashboard-bot` follow-up) tightens the era to `_SUPPORTED_SESSION_YEARS = frozenset({2026})`, names the era `"NYSE_RTH_2026"`, fixes the early-close dates for the era as a frozenset `{date(2026, 11, 27), date(2026, 12, 24)}`, and explicitly documents that "2026-07-03 is a full closure (Independence Day observed), not an early close, and is therefore intentionally absent" — verified by the new `test_b4_session_policy_rejects_non_session_and_wrong_session_clocks::july_observed` assertion. Any session outside the era raises `EntryPolicyContractError` with the literal message `"market_session outside NYSE_RTH_2026 session policy era"`, and the matching test (`test_b4_session_policy_requires_aware_clock_and_accepted_strategy_definition`'s final `pytest.raises(EntryPolicyContractError, match="outside NYSE_RTH_2026")` against `2027-01-04`) freezes that contract. The `policy_receipt`/`session_receipt`/`fact_receipt` triple is a content-addressed SHA-256 chain that makes the era boundary durable across the lane's later downstream consumers.

4. *Related-PR boundary block.* The PR body names the related-PR boundary explicitly: #7687 owns the separate structural-overlay semantic repair (already audited at `orch/audits/macro_PR-7687.mm.md`); #7581 owns the existing runtime adapter and must not be duplicated; both #7581 and #7688 still append tests to the same registered strategy-test file (`tests/test_prophet_strategy_definition.py`) and the test-owner collision is to be reconciled only on the later lawful wiring edge — i.e. the lane acknowledges the shared-test-file collision today and defers the unblock.

## Diff content (scoped to this audit)

2 files, no new template/component/CSS/JS surface. Both files are Python (engine + test); zero markdown, zero HTML, zero prose artifacts.

### `engine/prophet_entry_policy.py` (NEW, +247)

Two semantic moves in two stacked commits:

- **`evaluate_session_eligibility(strategy_definition, decision_at, market_session)`** — single-canonical B4 `session_eligibility` owner. Validates the strategy identity via `validate_strategy_definition()`; parses `decision_at` as offset-aware ISO (raises `EntryPolicyContractError` with literal `"offset-aware"` for naive timestamps) and `market_session` as canonical `YYYY-MM-DD` (raises with `"must be canonical YYYY-MM-DD"`); gates the session year on `_SUPPORTED_SESSION_YEARS` (raises with `"outside NYSE_RTH_2026"`); checks `nyse_calendar.is_session(session)` for calendar existence; computes the RTH window via `_execution_session_window_et(session)`; emits one of four `session_phase` values (`NON_SESSION` / `WRONG_SESSION` / `PREMARKET` / `RTH` / `AFTER_HOURS`) with the matching `reason` (`NON_SESSION_DATE` / `DECISION_NOT_IN_MARKET_SESSION_DATE` / `PREMARKET_NOT_ELIGIBLE_V1` / `INSIDE_ACTUAL_RTH_WINDOW` / `POST_RTH_NOT_ELIGIBLE_V1`); sets `extended_hours_eligible = False` unconditionally; emits `verdict = "PASS"` only inside `[session_open, session_close)` for the exact session, else `FAIL`. The returned payload carries a content-addressed triple — `policy_receipt = "pep:" + sha256(_canonical_json(policy_material))`, `session_receipt = "pes:" + sha256(_canonical_json(session_material))`, `fact_receipt = "pepf:" + sha256(_canonical_json(payload))` — every field of which is in the post-emission payload (verified by the test assertions at `tests/test_prophet_strategy_definition.py`).
- **`_execution_session_window_et(session)`** — era-stamped RTH execution-window law. Owns the clock boundary rather than calling the descriptive/coverage helper (`engine.session_digest.session_window_et` — which the v1 patch had called and the v2 patch replaced). Returns `(datetime.combine(session, time(9, 30), tzinfo=ET), datetime.combine(session, close, tzinfo=ET))` where `close` is `_RTH_EARLY_CLOSE_ET (13:00)` for `session in _EARLY_CLOSE_DATES` else `_RTH_REGULAR_CLOSE_ET (16:00)`. The `_EARLY_CLOSE_DATES = frozenset({date(2026, 11, 27), date(2026, 12, 24)})` set is frozen for the era; extending it is "an explicit policy mutation" per the inline docstring. The `_policy_material()` helper exposes the era metadata into the emitted fact: `session_policy_era = "NYSE_RTH_2026"`, `execution_window_owner = "engine.prophet_entry_policy._execution_session_window_et"`, `execution_schedule_source = "NYSE_HOLIDAYS_AND_TRADING_HOURS_2026"`, `execution_schedule_verified_on = "2026-09-22"`, `supported_session_years = sorted(_SUPPORTED_SESSION_YEARS) = [2026]`, `rth_open_et / regular_close_et / early_close_et` as `time.isoformat()` strings, `early_close_dates = ["2026-11-27", "2026-12-24"]`. The `authority` block is the canonical anti-promotion closer for every flag set to false.
- The module docstring carries the single-canonical-owner intent verbatim: "This module owns only strategy policy facts that no incumbent data/geometry owner can truthfully answer. The first bounded vertical is session eligibility for Early Leadership / Sector Rotation. It composes the existing NYSE full-day session calendar with an era-stamped RTH execution-window law frozen here; it does not promote a descriptive/coverage helper into gate authority, create a second session-existence calendar, quote source, entry-geometry engine, ranking signal, plan, or trade authority."

### `tests/test_prophet_strategy_definition.py` (+99 / −0)

Five new red-first regression tests covering the named boundaries:

1. `test_b4_session_policy_passes_only_inside_actual_rth_window` — `2026-09-22T14:00:00Z` (= 10:00 ET) on `2026-09-22` ⇒ verdict PASS, phase RTH, reason `INSIDE_ACTUAL_RTH_WINDOW`, `session_open` endswith `09:30:00-04:00`, `session_close` endswith `16:00:00-04:00`, `extended_hours_eligible is False`, all three receipt prefixes asserted (`pep:` / `pes:` / `pepf:`), `session_policy_era == "NYSE_RTH_2026"`, every era metadata field asserted (calendar_owner, execution_window_owner, execution_schedule_source, execution_schedule_verified_on, supported_session_years, early_close_dates). Determinism: `out == _session_policy(...)` with the same inputs.
2. `test_b4_session_policy_fails_closed_before_and_at_after_rth` — `13:29:59Z` (premarket) ⇒ `FAIL / PREMARKET / PREMARKET_NOT_ELIGIBLE_V1`; `20:00:00Z` (after-hours) ⇒ `FAIL / AFTER_HOURS / POST_RTH_NOT_ELIGIBLE_V1`.
3. `test_b4_session_policy_uses_actual_early_close_not_a_hardcoded_1600` — `2026-11-27T17:59:59Z` (Thanksgiving Friday, 12:59 ET) ⇒ `PASS` with `session_close.endswith("13:00:00-05:00")` (the early-close, not the regular 16:00); `2026-11-27T18:00:00Z` (13:00 ET, exact early close) ⇒ `FAIL / AFTER_HOURS`. The v2 patch adds the `christmas_eve` assertion: `2026-12-24T18:00:00Z` (= 13:00 ET) ⇒ `FAIL / AFTER_HOURS` and `session_close.endswith("13:00:00-05:00")`.
4. `test_b4_session_policy_rejects_non_session_and_wrong_session_clocks` — `2026-11-26T15:00:00Z` (Thanksgiving Thursday, a full closure) ⇒ `FAIL / NON_SESSION / NON_SESSION_DATE`, `session_open is None`, `session_close is None`. v2 patch adds: `2026-07-03T15:00:00Z` (Independence Day observed, a full closure NOT an early close) ⇒ `FAIL / NON_SESSION` with `session_close is None` — pins the explicit distinction between "early close" and "full closure". `2026-09-22T14:00:00Z` paired with `2026-09-23` ⇒ `FAIL / WRONG_SESSION / DECISION_NOT_IN_MARKET_SESSION_DATE`.
5. `test_b4_session_policy_requires_aware_clock_and_accepted_strategy_definition` — naive timestamp `2026-09-22T10:00:00` raises `EntryPolicyContractError(match="offset-aware")`. Mutated strategy identity (`strategy_definition_id` re-hashed to zeros) raises `StrategyDefinitionContractError`. v2 patch adds: `2027-01-04T15:00:00Z` paired with `2027-01-04` raises `EntryPolicyContractError(match="outside NYSE_RTH_2026")` — pins the era guard.

Test naming documents the intent: every test name includes `b4_session_policy` and the boundary it pins; every assertion is structurally an equality check rather than a fuzzy match. The five-test count (33 → 38 test functions in this file after the patch) is the new regression surface.

## Plain-language findings

### 1.1 Pass — there is no user-facing copy in this PR; the macro-side plain-language discipline is structurally inapplicable on this diff

The diff contains zero template (`templates/`), zero product HTML (no `site/`), zero CSS, zero JS, zero chat surface, zero bilingual receipt text. Both changed files are Python: one engine module, one test module. `tests/test_bilingual_ui.py` and `scripts/check_bilingual.py` cannot produce a finding against this diff by construction — there is no template surface to scan.

For the project-side plain-language read, the only prose that lands in this PR is the docstring on `engine/prophet_entry_policy.py` (module docstring + the docstring on `_execution_session_window_et`) and the test names/assertion strings in `tests/test_prophet_strategy_definition.py`. None of those strings is user-facing; they are internal documentation for engineers running the engine and for future research lanes that read the B4 evidence.

The PR body itself is a defect-repair description with the canonical anti-promotion closer ("Positive risk-ceiling, liquidity/fillability and gap/velocity owners remain unresolved; #7584/#7581 acceptance and #7180 fresh-source release remain separate. No named security is selected or forced into a recommendation.") and a release boundary block ("**DRAFT / HOLD-FOR-SOL.** … It is not yet wired into #7581, does not clear B4, and is not merge/deploy/production/user-path acceptance.") — matching the same shape used by other recent macro research/fix PRs (#7687, #7632, #7634, #7701).

### 1.2 Pass — the canonical owner's docstring preserves the prose discipline

The new `engine/prophet_entry_policy.py` module docstring carries substantive prose naming the single-canonical-owner intent ("It composes the existing NYSE full-day session calendar with an era-stamped RTH execution-window law frozen here; it does not promote a descriptive/coverage helper into gate authority, create a second session-existence calendar, quote source, entry-geometry engine, ranking signal, plan, or trade authority."). None of those strings is user-visible; they are engineering rationale that future maintainers of the engine need in order to recognise the rejection rationale before re-introducing a coverage helper into gate authority. The docstrings do not oversell, do not use banned-glance vocabulary (`validated` / `proved` / `guaranteed` / `certified`), and explicitly disclaim the role of every other owner the helper might have replaced. The `_execution_session_window_et` helper docstring carries the same discipline: "The clock window is intentionally owned here because the repository's other early-close helper is descriptive/coverage-tier and explicitly has no gate authority."

### 1.3 Pass — no `DSC-*` discovery record is added (which is the right choice here)

This PR does not add an `agentos/discoveries/DSC-*.md` record — and that's the correct posture for a single-canonical-owner repair. A `DSC-*` record is the right shape for an empirically-falsified defect with `kind: landmine / behavior` (cf. `DSC-REPORTS-LOCALE-CONTROLS-20260921.md` from PR #7634, `DSC-RISK-RADAR-REPLAY-LIVE-STATE-PARITY-DEFECT.md` from PR #7632). This PR is a source-repair, not a defect log: the era guard, the early-close frozenset, and the fail-closed posture are baked into the code itself (`EntryPolicyContractError`, `verdict / session_phase / reason` enums, content-addressed receipts), so there is no separate discovery to record. The lane has a clear "next" — the lawful wiring edge that reconciles the test-owner collision with #7687 — but that is a follow-up lane, not a defect to log today.

## Theme findings

### 2.1 Pass — `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7688.diff` reports **0 blocking findings**

```
::notice title=design-system::R0 enforce-added: 0 blocking finding(s) (25320 further pre-existing, non-blocking finding(s) in the estate — run --mode report for the full census)
design-system ratchet — mode=enforce-added blocking=0 (estate pre-existing, non-blocking: 25320)
```

Run command: `gh pr diff 7688 --repo mastermindx-market-intelligence/macro > /tmp/pr7688.diff && python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7688.diff`. The 25,320 pre-existing non-blocking estate findings are unchanged by this PR (the report's own caveat applies — the `enforce-added` mode reads the PR's own diff lines only and does not assert against pre-existing debt). The diff literally contains zero template/component/CSS/JS lines, so the design-system check has zero lines to assert against.

### 2.2 Pass — TP-0 dark/light × EN/ZH × 1440/390 evidence matrix is structurally inapplicable; the change does not touch any visual surface

The TP-0 dark-and-light-are-two-art-directions rule (`scripts/check_design_system.py` + the standing design-doctrine §Theme art direction) requires every material UI packet to name DARK TREATMENT, LIGHT TREATMENT, which mechanisms intentionally differ, the reference/baseline, theme-specific degraded states, and the evidence matrix (dark/light × EN/ZH × desktop 1440 / mobile 390).

This PR adds zero user-visible surface. Every changed line is in `engine/prophet_entry_policy.py` (Python module) or `tests/test_prophet_strategy_definition.py` (Python test) — no template, no inline style, no `<style>` block, no CSS rule, no JS payload. The "Token substitution alone is never proof of a light design" rule, the "Substantive product styling may not be authored as an opaque runtime stylesheet system inside page/composer JavaScript" rule, and the "every material UI packet must name DARK TREATMENT / LIGHT TREATMENT" rule are all structurally inapplicable. **Consistent with TP-0.**

### 2.3 Pass — `check_runtime_style_injection.py` is out-of-scope by construction

The diff contains no `style="..."` injection, no `style.textContent =`, no parallel palette, no duplicated light/dark branches inside JS, no inline `<style>` block, no `data-theme` override, no `class` attribute containing theme tokens. There is no JS payload change anywhere in the diff. The estate-wide scan reports "OK (195 .js files scanned, 44 injecting, 89 total hits — all within frozen allowances)" — i.e. the JS-injected-style allowance is unchanged by this PR.

### 2.4 Pass — no theme-art-direction assertion is made or implied

The PR body does not claim a dark/light, EN/ZH, mobile/responsive, palette, type, motion, or material-design effect. It closes with the anti-promotion line plus the release-boundary disclaimer ("DRAFT / HOLD-FOR-SOL. … It is not yet wired into #7581, does not clear B4, and is not merge/deploy/production/user-path acceptance."). No evidence matrix is owed because no design surface is touched.

## Validated-claims findings

### 3.1 Pass — `python3 scripts/check_validated_claims.py --list` produces no MISS row against this PR's diff

`grep -E "prophet_entry_policy|engine/prophet_entry|7688|pepf|pep:"` against the running validator's full output (full re-run was stopped at the same estate-wide pass PR #7632 caught; the validator's exit non-zero pattern is identical: 38 pre-existing UNEARNED `validated` claims in unrelated files, none anchored to PR-touched files) produces no hit on the new module. `engine/prophet_entry_policy.py` does not import from any of the surfaces the validator scans (`templates/`, `site/`, the paired plain-copy mirrors, or the engine/market_os snapshot validators). The PR's only user-facing-shaped text is the canonical anti-promotion closer ("No named security is selected or forced into a recommendation.") plus the release-boundary block ("DRAFT / HOLD-FOR-SOL. … not merge/deploy/production/user-path acceptance."), which is the standing disclaimer that exempts the change from the promotion-bearing claim regime entirely.

### 3.2 Pass — the emitted fact payload does not assert any `validated` posture

The `_policy_material()` helper exposes an `authority` block in which every flag is set to false (`can_rank / can_admit_candidate / can_size / can_execute / can_trade`). The schema is `"prophet.entry_policy_fact/v1"` — a private engine fact, not a user-facing validated signal. The era metadata fields (`session_policy_era`, `execution_window_owner`, `execution_schedule_source`, `execution_schedule_verified_on`) are provenance for the B4 evidence chain, not user-facing promotion tokens. The content-addressed triple (`policy_receipt / session_receipt / fact_receipt`) is what the standing epistemics rule expects from a verifiable engine fact — the receipts make the fact auditable, not promoted. No part of the emitted payload is rendered into any user-visible surface (cf. PR #7698's finding "yield_momentum is produced once … copied once … the chain ends" — the B4 lane has the same property today: the fact is on the wire, but nothing user-visible reads it yet).

### 3.3 Pass — the PR body does not introduce any promotion-bearing claim

PR body opening: "First owner-native positive B4 policy fact after the runtime adapter identified `session_eligibility` as permanently UNKNOWN without a strategy execution policy." This is a defect-repair claim with bounded scope (the session-eligibility gate), not a release/upgrade/score/rank promotion. PR body closing (release boundary): "**DRAFT / HOLD-FOR-SOL.** … It is not yet wired into #7581, does not clear B4, and is not merge/deploy/production/user-path acceptance." This is the canonical anti-promotion block for a B4 lane source-repair PR.

The PR body's mid-section explicitly names what the change does not do: "It does not rank, admit candidates, compute geometry, size, originate plans, execute or trade." — every authority flag is named as false. The named related-PR boundary (canonical Entry Truth correction: #6805 comment `5771738557`; protected procedure at repair: Mastermind `9a7ed19091dd82609f8ee405687f16c861c4d8c1`; fresh protected Macro: `main@1e767a2f5b43f302b0e1068c9a7e60b12aeb98ee`) and the qualification block ("5 focused session-policy attacks passed; 48 B4/B3/strategy qualification passed; remote head was re-read immediately before push and still matched predecessor") are receipts for the source-state repair, not promotion-bearing claims.

### 3.4 Pass — `check_validated_claims.py` continues to enforce the user-facing `validated` vocabulary unchanged

`tests/test_validated_claims_engine.py`, `tests/test_validated_claims_registry_source.py`, `tests/test_validated_claims_structural_scope.py`, and `tests/test_validated_claims_thirdparty.py` are the surface that enforces the user-facing claim discipline. None of them read or assert against engine code or research scripts — they read `templates/` and the structural scope of `data/regime/validated_claims_allowlist.json`. This PR modifies none of those surfaces. The validator's behaviour is unchanged on this PR. **Consistent with the structural-scope contract.**

## Overall verdict

**VERDICT: PASS — clean half-B single-canonical-owner repair for B4 `session_eligibility`, no blocking issue, no user-facing surface touched, release boundary held at HOLD-FOR-SOL.**

| dimension | result | notes |
|---|---|---|
| plain-language | PASS | Diff contains zero user-facing copy (only engine Python + tests + module docstrings). The macro-side plain-language discipline (`tests/test_bilingual_ui.py` + `scripts/check_bilingual.py` + design-doctrine banned-glance vocabulary) is structurally inapplicable on this diff. The PR body carries the canonical anti-promotion closer and the DRAFT/HOLD-FOR-SOL release-boundary block — no banned vocabulary. |
| theme | PASS | `check_design_system.py --mode enforce-added --diff-file /tmp/pr7688.diff` reports 0 blocking findings. The diff contains zero `templates/`, `site/`, `.css`, `.js`, `style=`, `data-theme`, or component lines. TP-0 dark/light × EN/ZH × 1440/390 evidence matrix is structurally inapplicable (no visual surface added). `check_runtime_style_injection.py` is out-of-scope (no JS payload). The PR does not author any design surface. |
| validated-claims | PASS | `check_validated_claims.py --list` produces no MISS row against the PR's diff — no template surface is touched and `engine/prophet_entry_policy.py` is not a surface the validator scans. The emitted `_policy_material()` block sets every `authority` flag false; the schema is `prophet.entry_policy_fact/v1` (a private engine fact, not a user-facing promotion token). The PR body disclaims any promotion-bearing change ("It does not rank, admit candidates, compute geometry, size, originate plans, execute or trade.") and the release-boundary block holds the lane at HOLD-FOR-SOL. |
| merge hygiene | PASS | 2 files, +321 / −11. The substantive fix is the single-canonical owner `evaluate_session_eligibility` in `engine/prophet_entry_policy.py` plus the era-stamped `_execution_session_window_et` helper, composing `lib.nyse_calendar.is_session` (calendar existence) with the B4-owned clock window (RTH law). Five red-first regression tests fail in the stated direction before the repair and pass after; the v2 patch's `july_observed` and `outside NYSE_RTH_2026` assertions pin the full-closure/early-close distinction and the era guard. Test names (`b4_session_policy_*`) document the intent. The related-PR boundary block names #7687 (separate structural-overlay owner, already audited), #7581 (existing runtime adapter, must not be duplicated), and acknowledges the test-owner collision with #7687 that the lane will reconcile on the later lawful wiring edge. The release boundary is held at DRAFT/HOLD-FOR-SOL — the source repair landed, the lane's full release remains a separate decision. |

**Non-blocking follow-ups (out of this lane's owned paths):**

1. The PR's `release boundary` block names the lawful wiring edge as a future follow-up — `#7581` accepting the new `evaluate_session_eligibility` fact, the test-owner collision with #7687 reconciled on the registered strategy test file, and the era extension policy when the lane moves into 2027. None of these is owned by this PR. Out-of-scope.
2. `_SUPPORTED_SESSION_YEARS = frozenset({2026})` and `_EARLY_CLOSE_DATES = frozenset({date(2026, 11, 27), date(2026, 12, 24)})` are era-local. A future carrier should own the era-extension procedure (the inline docstring is explicit: "Extending this set/year is an explicit policy mutation") and freeze it as an `agentos/discoveries/DSC-PROPHET-B4-SESSION-ERA-EXTENSION-PROCEDURE.md` discovery record when the lane first needs 2027. Out-of-scope for this PR.
3. The lane's runtime adapter (`#7581`) is named as the existing owner and the PR body is explicit that this PR does not duplicate it. When #7581 picks up this fact via wiring, a follow-up DSC could record the wiring edge. Out-of-scope for this PR.

**No blocking issue found. No retry. No scope expansion. Audit complete.**
~~~~
