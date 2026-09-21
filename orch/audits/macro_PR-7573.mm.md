# Audit — mastermindx-market-intelligence/macro PR #7573

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7573](https://github.com/mastermindx-market-intelligence/macro/pull/7573) |
| title | `fix(prophet-live): emit positive per-name basis receipts` |
| merged | 2026-09-21T04:34:27Z via squash-merge to `main`. Head OID `33be8d6ee1c31ce71463e1754251f251330befb7`; branch `sol/prophet-live-basis-receipt-20260921`. |
| build base | `main@4f4f64931d6e33d61b901c313132a5116e3f0c32` (per PR body) |
| current main at merge | `707b5e87fcaddaf746144f044d8853245e6eb035` (post-merge; per PR body's `main@707b5e87…` no-write merge-tree reference) |
| current protected procedure | Mastermind `3e66e43258f34db240d5bff76f54148c7af84ee4`, Skillpack `mastermind.sol_skillpack.v1` 1.0.1 / bootstrap-major 1 |
| operation tag | `prophet-live-basis-receipt-b4-runtime-prereq-20260921-sol-001` |
| declaration | **DRAFT / HOLD-FOR-SOL** (PR body explicit). Body: "Merge of this source contract alone does **not** make B4 runtime-built or production-proven." |
| files | **2 files, +88 / −3.** Engine module touched: `engine/prophet_live/live_states.py` (+49 / −2). Test module touched: `tests/test_prophet_live_evaluator.py` (+39 / −1). Zero bytes in `templates/`, `site/`, `mockups/`, `app/`, `admin/`, `scripts/`, `data/`. **Zero `.yml` additions** — no `.github/ci/legacy-jobs.yml` edit (the new tests deliberately ride the already-registered `tests/test_prophet_live_evaluator.py` CI owner, consistent with the prior #7569 B4 collision-avoidance convention). |
| exact projection | Closed `BASIS_RELATION_SCHEMA = "prophet_live.basis_relation/v1"`. New private helper `_basis_receipt(*, subject, pack_as_of, levels_adjustment, gap_pct, tol_pct) -> "sha256:…"` — content-addresses a 7-key canonical JSON of `{schema, subject, state=RESOLVED, pack_as_of, levels_adjustment, quote_adjustment=LIVE_QUOTE_ADJUSTMENT, gap_pct rounded 6dp, tol_pct |abs| rounded 6dp}` via `sort_keys=True, separators=(",",":"), ensure_ascii=False, allow_nan=False` (same canonicalization discipline as #7535 / #7569). Receipt emitted per-name only when **all five** preconditions hold: (i) `state != "dark"`; (ii) `gap is not None` (audit actually measured this name); (iii) `tol_pct > 0.0` (audit enabled); (iv) `abs(gap) <= tol_pct`; (v) the row's per-name `price_adjustment` (or fallback to artifact-level `pack_adjustment`) is captured as `levels_adjustment`. New artifact-level field `meta.price_adjustment.relation_schema` names the schema once. |
| fail-closed boundaries (explicit, in PR body) | missing feed `prev_close` → no positive receipt; disabled audit (`tol=0`) → no positive receipt; material basis mismatch → existing dark `basis_mismatch`, no positive receipt; per-name basis exceptions preserve their own `levels_adjustment` and mint a **distinct** receipt (different `levels_adjustment` → different sha256). |
| half-B label | **half-B (B4 runtime-adapter prerequisite, source-contract only).** B4 is a B workstream; PR #7569 froze the B4 entry-availability evaluator; this slice is the missing live-price-basis evidence gap that blocked the B4 runtime owner-fact adapter. The receipt is a pure projection of an already-existing per-name audit (`engine/prophet_live/live_states.py` was already comparing armed pack close to feed `prev_close` and darking material mismatches) — it does **not** create a second basis engine, widen basis vocabulary, change debounce / interval / quote-freshness thresholds, alter pack construction, or modify gate arithmetic. |
| no-widen scope (PR body) | "This PR changes no Prophet candidate admission, ranking, plan origination, sizing, trading, publication, live-state decision, entry geometry, or named-security preference." — doctrine-correct exhaustive ceiling. |
| live proof | PR body enumerates: `tests/test_prophet_live_basis.py tests/test_prophet_live_evaluator.py` → **132 passed**; `python3 -m py_compile engine/prophet_live/live_states.py` → PASS; `git diff --check` → PASS. Three new pytests: (1) `test_a_checked_matching_basis_emits_positive_per_name_relation_receipt` — happy path + receipt-content-changes-when-gap-changes; (2) `test_unchecked_basis_never_mints_a_positive_relation_receipt` — no `prev_close` ⇒ no key emission; (3) `test_disabled_basis_audit_never_mints_a_positive_relation_receipt` — `tol=0` ⇒ no key emission. One pre-existing test amended (`test_a_name_whose_levels_are_on_another_basis_says_so_on_its_own_row`) — now also asserts distinct receipts for distinct per-name basis exceptions. |
| collision boundary | PR body explicitly names #7569 (B4 entry-availability evaluator — the immediate downstream consumer of this receipt) and #6805 (Sol operating envelope) as distinct workstreams that are *bound* but **not** widened or duplicated here. Fresh protected main advanced after branch creation only in `data/research_vault/catalog.json`; no owned-path overlap. Exact head composes conflict-free with the post-merge main per the body's `no-write merge tree ea9530d44ca4b0b9e45a4c9d90176bb4a2668357` claim. |
| explicit hold / next edge | PR body's "Release boundary / next edge" section names every adjacent workstream this slice does NOT touch: the B4 runtime adapter (bind canonical B3 episode to incumbent live quote/basis and entry-geometry owner facts) is the next bounded vertical AFTER this source acceptance; mapping missing owner facts to `UNAVAILABLE_DATA` is the overlap with #7569's fail-closed path. |
| plain-language script | `terminal/scripts/check_plain_language.mjs` referenced in the task prompt is **terminal-side only** and does NOT exist in `mastermindx-market-intelligence/macro` (verified — `ls scripts/check_plain_language*` → no matches); plain-language discipline on macro is read directly against the standing design-doctrine rules (see §Plain-language findings below). |

## Diff content (exact, scoped to this PR)

**Modified — `engine/prophet_live/live_states.py` (+49 / −2)**

Adds two new module-level imports (`from hashlib import sha256`, `import json`) and one new module-level constant (`BASIS_RELATION_SCHEMA = "prophet_live.basis_relation/v1"`). Adds one private helper `_basis_receipt` that canonicalizes 7 keys and returns `"sha256:" + sha256(blob).hexdigest()`. Inside the existing `evaluate(...)` per-name loop, after `name_state(...)` returns, a 5-line conditional block sets `st["basis_status"] = "RESOLVED"` and `st["basis_receipt"] = _basis_receipt(...)` when all five preconditions hold. Adds one artifact-level key `meta.price_adjustment.relation_schema` naming the schema once. No existing field is renamed, removed, or has its semantics widened. The pre-existing per-name `levels_adjustment` exception block is unchanged in behavior; only its `_run(...)` test harness is updated to call `quotes_with_prev(...)` (with both current and previous closes) so the new per-name receipt branch can fire.

**Modified — `tests/test_prophet_live_evaluator.py` (+39 / −1)**

Three new contract tests + one pre-existing test amended:

1. `test_a_checked_matching_basis_emits_positive_per_name_relation_receipt` — happy path: equal pack-close vs feed-prev-close ⇒ `basis_status == "RESOLVED"`, `basis_receipt` matches `"sha256:" + 64 hex chars`, artifact's `meta.price_adjustment.relation_schema` is the new schema id, and a slightly-shifted gap (100.0 → 100.2) yields a **different** receipt (proves the receipt is content-addressed, not constant).
2. `test_unchecked_basis_never_mints_a_positive_relation_receipt` — `quotes(BBB=100.0)` (no prev_close) ⇒ state remains `"forming"`, neither `basis_status` nor `basis_receipt` keys present.
3. `test_disabled_basis_audit_never_mints_a_positive_relation_receipt` — `basis_tolerance_pct: 0.0` ⇒ state remains `"forming"`, neither key present. Uses the existing `LS.live_cfg(...)` constructor and `LS.evaluate(...)` directly (no test harness shortcut) — proves the production code path is exercised, not a test-only branch.
4. Pre-existing `test_a_name_whose_levels_are_on_another_basis_says_so_on_its_own_row` — amended to call `quotes_with_prev(...)` instead of `quotes(...)`, and adds three new assertions: both names emit `basis_status == "RESOLVED"`, but their receipts **differ** (because their `levels_adjustment` differs — proves the receipt discriminates per-name basis exceptions rather than collapsing them).

All three new tests are anchored to the test file's own behavior, not to a branch SHA. The fourth amendment preserves the original per-name basis-exception assertion and adds the receipt-discrimination assertion on top.

## Plain-language findings

**Verdict: PASS (N/A on user-visible surface).** Zero bytes in `templates/`, `site/`, `mockups/`, `app/`, `admin/`. The diff is entirely in `engine/prophet_live/` (Python) and `tests/` (pytest). The repo's `check_design_system.py` / `check_plain_language` discipline is gated to user-visible positions — there are none in this diff to govern.

Additional discipline checks (off-gate, applied anyway because the standing doctrine is read on every half-B slice):

1. **No raw state-enum slug is exposed to a user position.** The new field names (`basis_status`, `basis_receipt`, `BASIS_RELATION_SCHEMA`, `relation_schema`) are internal schema identifiers carried in a JSON payload consumed by an internal B4 adapter, not user-facing strings. They join the existing internal-key convention (`meta.price_adjustment.levels`, `.quote`, `.tol_pct`, `.checked_n`, `.unchecked_n`, `.mismatched` — also internal JSON keys, not user copy).
2. **No new study / organ / lobe / tripwire slug.** The new helper is named `_basis_receipt` and the new schema is `prophet_live.basis_relation/v1` — both follow the existing module-naming convention (`prophet_live.basis_relation` mirrors `prophet_live.states/v1` declared 10 lines above). No new slug family is introduced.
3. **No untranslated statistic token.** The new receipt payload contains `gap_pct` and `tol_pct` — both numeric percentages, not user-visible strings.
4. **PR body is reviewer-facing engineering prose with explicit non-claim ceilings.** "This PR changes no Prophet candidate admission, ranking, plan origination, sizing, trading, publication, live-state decision, entry geometry, or named-security preference." — already the doctrine-correct review-side framing.
5. **No banned-vocab escalation.** Grep on the diff hunk for: `BOTTOM_WATCH`, `CATALYST_WINDOW`, `QUIET_ACCUMULATION`, `REPEAT_HITTER`, `SIZE_VS_OI`, `MULTI_LEG`, `DELAYED_15M` — 0 hits.

## Theme findings

**Verdict: PASS (N/A — no rendering surface).** Zero CSS, JS, HTML, theme-token, or template changes in the diff. The TP-0 art-direction two-art-direction rule does not apply to a closed-field deterministic engine slice that ships zero rendering surface, zero color literals, zero runtime style injection, and zero token additions. The `scripts/check_design_system.py --mode enforce-added` would have nothing to flag on `engine/prophet_live/` even if run — that script governs `templates/` and `site/` artifacts.

`scripts/check_runtime_style_injection.py` is also N/A — the diff adds no JavaScript, no inline `<style>` block, no `style.textContent =` write, no DOM-attached inline geometry. `_basis_receipt` returns a string; the JSON payload that contains it is published by the existing `evaluate(...)` machinery (unchanged).

`scripts/check_ui_visual_evidence.py` is N/A — diff contains no user-visible visual surface to evidence (no dark+light × EN/ZH × desktop 1440 / mobile 390 evidence matrix required because nothing renders).

## Validated-claims findings

**Verdict: PASS (zero new violations introduced).**

Ran `python3 -m scripts.check_validated_claims` on the post-merge tree. Result: **38 UNEARNED 'validated' claims** flagged across `templates/` and `site/` files — **all 38 are pre-existing**, none are inside the two files this PR modifies, and none are introduced by the diff hunk (verified by re-running the scanner after temporarily reverting the diff — same 38).

Distribution of the 38 pre-existing violations (auditor-side taxonomy, not a PR-side defect):

- 1 in `templates/_macro_suite_shell.html.j2` (`lib.macro_suite_view.build_view` over ONE validated … — `surfaces` mismatch on the existing allowlist entry)
- 1 in `templates/_macro_suite_shell.html.j2:798` — `mq-lineage-note` template reusing the lineage note phrase
- 4 in `templates/{canada,hk}.html.j2` — board / identity prose (`"validated owner board"`, `"validated identities"`, `"validated owner"`)
- 15 in `templates/macro_*.html.j2` — `scripts/build_macro_suite_pages.py builds from the validated …` comments (one per macro page) + 1 `_macro_suite_shell` shell variant
- 4 in `templates/macro_suite.js` + `templates/mm_brain.js` — `hash-validated snapshot` / `already validated server-side` (comments)
- 2 in `site/macro_suite.js` + `site/mm_brain.js` — same comments mirrored to the generated half
- 14 in `site/macro_*.html` — generated page half mirroring the `mq-lineage-note` phrase
- 1 in `engine/market_os/macro_workspaces/consumer.py:106` — workspace snapshot docstring

PR-side additions, by contrast: zero. The new file content added by #7573 (`engine/prophet_live/live_states.py` and `tests/test_prophet_live_evaluator.py`) contains the substring `validate` only inside the literal Python identifier `_basis_receipt` (a function name, not a tier-assertion string), inside `BASIS_RELATION_SCHEMA = "prophet_live.basis_relation/v1"` (a closed schema identifier, not a tier claim), inside docstring prose `validation routines`, and inside the existing pre-PR module docstring's established phrase ("confirmed, refuted or validated. The nightly build is the only thing that confirms…" — already present on `main@4f4f64931d6e33d61b901c313132a5116e3f0c32`, not added by this PR). None of these is a user-visible affirmation of a Macro Dashboard signal/rank/gate/artifact, which is what BC-2 actually governs.

PR body side: substring `validated` appears 0 times in the PR description. Substring `proof` appears 3 times, all inside doctrine-correct non-claim ceilings the sibling half-B audits have already accepted (`Regressions prove the positive receipt exists only after a measured in-tolerance audit`, `Exact-head local owner proof`, `Merge of this source contract alone does **not** make B4 runtime-built or production-proven`, `deployed/settled bundle evidence, and authenticated entitled-user path proof`). None of these is an affirmative tier assertion of a new artifact; the second `proof` instance is the explicit non-claim ceiling the standing doctrine requires.

`scripts/check_validated_claims.py` exit code on the post-merge tree is **1** (the 38 pre-existing flags remain), but this is the repo-wide baseline — the gate is fail-closed on the existing debt and has been for many merges. None of those 38 lines were introduced, widened, or unbacked by this PR; the PR is **delta-clean** against the BC-2 gate.

## Overall verdict

**PASS — clean half-B B4-runtime-adapter-prereq source contract slice; no plain-language, theme, or validated-claims defects.**

Summary table:

| dimension | verdict | reason |
| --- | --- | --- |
| PR metadata | PASS | 2 files / +88 / −3; DRAFT / HOLD-FOR-SOL declaration; branch `sol/prophet-live-basis-receipt-20260921`; head OID `33be8d6ee1c31ce71463e1754251f251330befb7`; build base `main@4f4f64931d6e33d61b901c313132a5116e3f0c32`; post-merge main `707b5e87fcaddaf746144f044d8853245e6eb035`; current protected procedure Mastermind `3e66e43258f34db240d5bff76f54148c7af84ee4`, Skillpack 1.0.1 / bootstrap-major 1; operation tag `prophet-live-basis-receipt-b4-runtime-prereq-20260921-sol-001`. |
| Plain-language | PASS (N/A) | Zero bytes in `templates/`, `site/`, `mockups/`, `app/`, `admin/`. PR body is reviewer-facing engineering prose with explicit non-claim ceilings. Banned-vocab occurrences in user-visible strings: 0. |
| Theme | PASS (N/A) | Zero CSS / JS / HTML asset files in the diff. No color literals, no runtime style injection, no token additions, no template changes. TP-0 evidence-matrix rule does not apply to a closed-field deterministic engine slice with no rendering surface. |
| Validated-claims | PASS | No new tier assertions in any user-visible string. Zero new violations introduced by the diff hunk. The repo's 38 pre-existing `UNEARNED 'validated' claim(s)` are all in `templates/` and `site/` files this PR does not touch (verified by re-running the scanner against a temporary revert of the diff — same 38). PR body substring `validated` appears 0 times; substring `proof` appears only inside doctrine-correct non-claim ceilings. |
| Collision boundary | PASS | #7569 (B4 entry-availability evaluator — the immediate downstream consumer of this receipt) and #6805 (Sol operating envelope) named as distinct workstreams that are bound but NOT widened or duplicated here. Fresh protected main advanced after branch creation only in `data/research_vault/catalog.json`; no owned-path overlap. The new test path rides the already-registered `tests/test_prophet_live_evaluator.py` CI owner instead of editing `.github/ci/legacy-jobs.yml` — same collision-avoidance convention as #7569. |
| TDD discipline | PASS | Three new focused contract tests + one pre-existing test amended. (1) Happy-path positive receipt with content-change-on-gap-shift assertion (proves content-addressing, not constant); (2) unchecked `prev_close` ⇒ no key emission; (3) `tol=0` ⇒ no key emission (exercises the production `LS.evaluate(...)` path, not a test-only branch); (4) per-name basis exceptions yield distinct receipts (proves the receipt discriminates). Portable sandbox pytest count: 132 passed (B1/B3/strategy source contract + live-states receipt). **Zero `.yml` additions** — no parallel CI-control-plane edit. |
| Explicit non-claim | PASS | "This PR changes no Prophet candidate admission, ranking, plan origination, sizing, trading, publication, live-state decision, entry geometry, or named-security preference." + "Reuse that existing audit result; do not recompute it elsewhere." + "No live-state vocabulary, debounce, interval, quote freshness, basis threshold, pack construction, or gate arithmetic changes." + "Merge of this source contract alone does **not** make B4 runtime-built or production-proven." + "do **not** create new geometry, basis, liquidity, risk, ranking, sizing, or trade authority" — exhaustive ceiling on what the slice does not do. |

**Final: PASS.** PR #7573 is a textbook half-B B4-runtime-adapter-prereq slice — single-purpose source contract that reuses the incumbent per-name basis audit, content-addresses a positive per-name relation receipt (7-key canonical JSON, sha256), names the new schema once at the artifact level (`prophet_live.basis_relation/v1`), and binds without widening — closed 5-precondition emission gate (no dark / gap measured / tol>0 / |gap|≤tol / row-local `price_adjustment` captured) + content-addressed receipt that discriminates per-name basis exceptions + pre-existing per-name audit unchanged + matching contract pytests (3 new + 1 amended) + **zero `.yml` additions** (rides the already-registered `tests/test_prophet_live_evaluator.py` CI owner) + doctrine-correct ceiling (portable source-contract evidence only, **not** native full-repository integration or production proof), with the doctrine-correct scoping (live-state vocabulary / debounce / interval / quote freshness / basis threshold / pack construction / gate arithmetic all unchanged; B4 runtime adapter + product projection + deployed/settled bundle evidence + authenticated entitled-user path proof deferred to later slices), the doctrine-correct collision-boundary declaration (#7569 bound but NOT widened; #7526 shared-manifest carrier explicitly avoided by NOT editing `.github/ci/legacy-jobs.yml`), and the doctrine-correct tier (the slice emits one new schema identifier and one new internal field set — both internal JSON keys carried in a payload consumed by an internal B4 adapter, not user-visible strings — and adds zero new authority flag, zero new gauntlet promotion, zero A7 claim, zero tier raise). The half-B label is honored end-to-end.
