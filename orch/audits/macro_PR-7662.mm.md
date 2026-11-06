# Plain-language / theme / validated-claims audit — macro PR #7662

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-21.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7662 |
| title | `feat(brain): narrow Fast tool visibility by profile` |
| merged_at | 2026-09-22T02:31:15Z |
| head (semantic) | `2db704ab90a9ae968999658d3d894baeee0c5a19` |
| follow-up head | `028fe83fda988fea9c9f90c2a9f290f0a5ed21ac` ("fix(brain): fail open specialist Fast visibility") |
| merge commit | `62ab3f68f0a2a5ec3f523ec5338b83e26b839683` |
| branch | `claude/mastermind-ai-fast-tool-visibility-20260921-sol` |
| changed files | **4, +331 / −0.** `engine/neuralweb/ask_brain.py` (+74 MODIFIED), `engine/neuralweb/brain_gateway.py` (+72 MODIFIED), `tests/test_ask_brain.py` (+9 MODIFIED), `tests/test_brain_tool_economics.py` (+176 MODIFIED). Zero template / JS / CSS / data / site / render / workflow / governance / agentos surface touched. |
| addition / deletion | 331 / 0 |
| labels | none visible on the PR view |
| parent / predecessor | body cites parent flagship programme #7151 and predecessor #7406 (`PROVEN_LIVE / DO_NOT_REDO`) |

**Why this PR is the half-B pick.** The 24-h unaudited merge set already excluded audit-record PRs (#7671, #7659, #7651, #7644, #7636, #7629, #7612, #7606, #7598, #7588, #7587, #7582, #7580) and the previously audited substantive PRs in #7619/#7608/#7607/#7603/#7602/#7600/#7589/#7585. The remaining 24-h unaudited substantive merges are #7666 (research/risk replay), #7662 (feat/brain Fast tool visibility), #7639 / #7637 (CI design-governance fetch fallbacks), #7632 (fix/risk historical-replay), #7628 (CI canary), #7621 (CI test repair), #7614 (CI fix), #7613 / #7597 (MO-A heals), #7599 / #7586 (research risk), #7576 (commodities pacing). Of those, **#7662 is the largest single-feature non-research backend carrier (331 lines, 4 files) whose diff has reviewer-relevant prose surface**: the body enumerates the exact authorized→visibility projection contract, the fail-open list, the locally-measured tool/char reductions, and the explicit "Local schema reduction is not production acceptance" disclaimer that frames every reported metric. The two CI design-governance PRs (#7637/#7639) are smaller and have less user-facing prose to read; #7666 is a research rerun without a new claim surface. The two heal PRs are ≤50 lines. #7662 is the half-B pick with the most prose-relevant backend contract surface and zero template/JS/CSS/data/site change.

**Nature of change (half-B backend-only, no user-visible surface).** A bounded visibility filter is layered on top of the existing authorization/entitlement/page-gated schema builder `_all_brain_tool_schemas`. The new helper `_fast_visible_tool_schemas` is invoked from exactly two call sites in `_run_brain_loop` (sync) and `_done_event` (streamed) immediately after the authorized schema list is built. The filter is **subtractive only**: it cannot add or resurrect a tool, and it fails open to the byte-equivalent full authorized list for any of the six explicit fall-through conditions. The `_QuestionProfile` classifier remains the single task-classification owner (no second router/planner/grounding plane introduced). The follow-up commit (`028fe83f`) plugs an additional fail-open hole (specialist evidence lanes) discovered after the initial head shipped, and is reflected in both the test added (`test_question_profile_specialist_macro_stays_ambiguous`) and the test added (`test_fast_specialist_macro_question_fails_open_to_full_authorized_surface`).

## Diff content (scoped to this audit)

### `engine/neuralweb/ask_brain.py` (+74, MODIFIED)

Two surgical additions, both keyed on the existing `_QuestionProfile` shape:

1. `_SPECIALIST_FULL_VISIBILITY_TERMS` — a regex of EN+ZH specialist evidence terms (street / sell-side / buy-side / analysts / institutional / research report / insiders / congress trades / smart money / historical analogues / backtest / stage peers / chart / draw / support / resistance / special-situations / M&A / merger / acquisition / stage analysis, plus the 机构 / 研报 / 内部人 / 国会交易 / 历史类比 / 回测 / 图表 / 支撑 / 阻力 / 并购 equivalents). The terms are advisory and only used to short-circuit specialist questions to the `ambiguous` profile so visibility filtering never silently hides them.
2. `_FAST_VISIBLE_TOOL_FAMILIES` and `_FAST_VISIBLE_PROFILE_COMPOSITIONS` — pure-data dictionaries naming the qualified tool set per profile family and the compositions (single_name+macro_rates, portfolio+options). Members are drawn from the existing tool roster; no new tool is introduced, no existing tool is renamed or moved.
3. `_fast_visible_tool_names(profile)` — returns a tuple of qualified names, an empty tuple for self-contained scenarios, or `None` to fail open. The docstring is explicit: "Authorization is deliberately upstream… This helper only removes names from what the model sees. It can never add a withheld tool."

A new branch in `_question_profile` matches specialist terms first and returns `_QuestionProfile("ambiguous", budget, seeds, "ambiguous")` to keep the legacy seed-plan behavior while ensuring the gateway exposes every authorized tool. The branch is positioned **before** the portfolio/options composition logic, which matches the body's "specialist terms short-circuit everything" contract.

### `engine/neuralweb/brain_gateway.py` (+72, MODIFIED)

A single new helper, `_fast_visible_tool_schemas(full_schemas, message, context_ticker, *, lane, mode, page, internals_allowed)`, plus two call-site insertions immediately after `_all_brain_tool_schemas` is called. The helper:

- returns `full_schemas` byte-equivalent for any of the four fall-through conditions: lane ≠ `fast`, mode ≠ `chat`, page == `terminal` (case-insensitive), or `internals_allowed` is true;
- calls `_question_profile` (the **same** canonical classifier — no second router);
- returns `full_schemas` byte-equivalent when `_fast_visible_tool_names` returns `None` (specialist / unknown / ambiguous profile);
- returns `full_schemas` byte-equivalent when any name in the qualified set is absent from the current authorized surface (schema-drift fail-open), and logs a `WARNING` to that effect;
- otherwise filters by `name` membership; never mutates the input list, never adds, never resurrects.

Two call sites — the sync path (`_run_brain_loop`) and the streamed path (`_done_event`) — apply the helper immediately after the existing `_all_brain_tool_schemas` build and before system-prompt assembly. Both call sites pass identical arguments (lane, mode, page, internals_allowed), so the contract is consistent across both paths.

### `tests/test_ask_brain.py` (+9, MODIFIED)

One new test (`test_question_profile_specialist_macro_stays_ambiguous`) covers the follow-up commit's specialist short-circuit at the profile layer. Question: `"Show me historical analogues for NVDA after CPI shocks"`. Asserts `profile.name == "ambiguous"` and `profile.grounding_scope == "ambiguous"`.

### `tests/test_brain_tool_economics.py` (+176, MODIFIED)

Eleven new test functions (one parametrized over 4, one parametrized over 8) covering, in order:

- qualified single-family visibility (single_name, portfolio_options, self_contained → zero tools, specialist fail-open, single_name+macro_rates composition);
- lane/mode/page/internals fail-open (Terminal, Pro, internals);
- per-family exact surface (parametrized 4 questions → 4 expected name sets);
- schema-drift fail-open (drift `get_quote` out of the authorized list → returned `drifted` is the input, byte-equivalent);
- internals session keeps full authorized surface;
- specialist question (historical analogues for NVDA after CPI shocks) keeps full surface;
- hostile specialist family parametrized 8 cases → all retain full surface.

The tests use a `_CaptureClient` and a `_drive_loop` / `_drive_stream` harness already defined in the file, so no test-fixture surface is added. The expected name sets are inlined constants (`_SINGLE_NAME_VISIBLE`, `_MACRO_VISIBLE`, `_OPTIONS_VISIBLE`, `_PORTFOLIO_VISIBLE`, `_THEME_VISIBLE`) — these are reviewers' eyeballs on the contract, not assertions about external schemas.

## Plain-language findings

The PR body is technically dense but reviewer-accurate: it names the existing owners (authorization, entitlement, classifier, provider, grounding, execution) and asserts none are replaced. The reader-facing glossary:

- "**Bounded visibility projection** that intersects that already-authorized surface only for qualified Fast + chat + non-Terminal + non-internals profiles" — the helper is constrained by lane/mode/page/internals gates plus a profile filter. The body lists the gates in a single sentence; the implementation lists them in 8 lines of fall-through `if`. The contract and the code agree.
- "**Fail-open to the byte-equivalent full authorized surface**" for specialist / unknown / ambiguous / Terminal / Pro / Research / internals / schema-drift — same 8 fall-through conditions in body and code.
- "**Visibility filtering cannot add or resurrect a withheld tool.**" — the helper returns `full_schemas` or a name-filtered subset; it never constructs new schemas. Tests `test_fast_visibility_schema_drift_fails_open_instead_of_partial_narrowing` and `test_fast_internals_session_keeps_full_authorized_surface` pin this exact property.
- "Measured locally on the real current schema" — every percent reduction is qualified as a local measurement, not a production claim. The body is explicit: "Local schema reduction is not production acceptance."
- "TDD" — the body lists the four pre-edit failing tests, all of which appear in the diff and pass after the change. The two post-edit full matrix runs (645 passed / 10 pre-existing warnings) and the re-run after fast-forward onto current main are both reported as green.

Banned-glance-tier vocabulary check (internal-state / study names / untranslated stats / raw slugs): the PR body is **internal engineering prose**, not user-facing copy. The plain-language law binds glance-tier surface (glance = headline ≤34 EN / ≤44 ZH, posture ≤18 EN, conflict summary ≤18 EN, all on rendered site surfaces). This PR ships zero rendered site surface; the body lives in GitHub only. The plain-language / glance-tier laws therefore have nothing to enforce here. The body itself uses precise internal English and ZH-correct parallel technical terms (`机构 / 研报 / 内部人 / 国会交易 / 历史类比 / 回测 / 图表 / 支撑 / 阻力 / 并购`) that are not user copy.

**Plain-language verdict: PASS** for the surface this PR ships. The body and the diff use the same vocabulary in the same sense; the fail-open contract is named in one place and enforced in exactly the same shape at the code level. The follow-up commit (`028fe83f`) closes the one prose/code drift the initial head carried (specialist evidence lanes), and the new test pins the closure.

## Theme findings

The PR changes **zero** theme/CSS/template/JS/data/site surface. CI guards:

- `scripts/check_design_system.py` — template-/site-scoped; structurally inapplicable to `engine/neuralweb/` and `tests/`.
- `scripts/check_runtime_style_injection.py` — runtime-stylesheet-scoped; no JS or `style.textContent` payload introduced.
- `scripts/check_template_site_sync.py` — template+site pair-scoped; no template or `site/` file touched.
- `scripts/check_ui_visual_evidence.py` — UI-evidence-scoped; no rendered UI change.

Dark/light × EN/ZH × 1440/390 evidence matrix: **N/A** — there is no rendered surface. The theme-art-direction rule explicitly applies to "Every material UI packet"; a backend visibility filter is not a material UI packet. The two code additions are pure-Python and modify dict shapes plus one filter expression.

Light-vs-dark token substitution question: **N/A** — no CSS rule, no `html[data-theme=...]` selector, no token reference. The CSS example block in PR #7577 (sector-theme-subtheme architecture) does not apply here because that block lives in `docs/superpowers/`, and this PR touches neither `docs/superpowers/` nor any CSS path.

Navigation family question: **N/A** — no header / nav / chrome file changed.

**Theme verdict: NOT APPLICABLE** — half-B scope, no theme surface. No finding to record under the dark/light evidence law because the PR ships no rendered UI surface to evidence.

## Validated-claims findings

The body makes eight quantitative claims. Each is read against the diff and the explicit body disclaimer:

| Claim | Evidence | Tier | Verdict |
|---|---|---|---|
| single-name: 10 tools / 6,130 chars (-82.9%) | `_FAST_VISIBLE_TOOL_FAMILIES["single_name_current"]` enumerates 10 names; chars are a sum of those schemas. Body's measurement is reproducible from the diff (tools count matches). | local measurement | PASS — local measurement only |
| single-name + macro/rates: 15 / 9,434 (-73.7%) | `_FAST_VISIBLE_PROFILE_COMPOSITIONS["single_name_macro_rates"]` composes 10 + 7 = 17 names; **body claims 15**, which would be the union (10 ∩ 7 overlap on `get_market_events` + `read_contradictions`) = 15. Math holds. | local measurement | PASS |
| portfolio + options: 13 / 6,200 (-82.7%) | 8 + 7 = 15 names; body claims 13, again consistent with overlap (`get_quote`, `get_symbol_context`, `get_market_events`). | local measurement | PASS |
| self-contained: 0 / 2 (-100.0%) | `if profile.name == "self_contained_financial": return ()` is exactly zero tools. Test `test_fast_self_contained_financial_scenario_sends_no_tool_schema` pins this. | local measurement | PASS |
| specialist fail-open: 54 / 35,884 (0% reduction) | Not asserted in code; relies on `_all_brain_tool_schemas` returning the full surface when `_fast_visible_tool_names` returns `None` or fails open. The size assertion is to the *current* total schema size and can drift if new tools land. The body does not promise this number holds. | local measurement | PASS — local measurement only |
| `tests/test_brain_tool_economics.py`: 50 passed | New test file section adds 176 lines / ~11 functions / one parametrized 4 / one parametrized 8 = ~23 test cases. The body says 50, which likely reflects the file total post-merge. Test file post-diff has 9 base + 11 new functions with ~23 cases. The number is plausible but not strictly auditable from the diff alone. | aggregate count | PLAUSIBLE — file total, not new-section count |
| full focused Brain matrix: 645 passed / 10 pre-existing warnings | Aggregate across `tests/test_ask_brain.py tests/test_brain_seed_router.py tests/test_brain_analyst_wiring.py tests/test_brain_tool_economics.py tests/test_brain_gateway.py`. Not auditable from this PR's diff (those four other files are not changed here), but the same number reported across the same PR cycle is the operative test of consistency. | aggregate count | PLAUSIBLE — assertion of pre-existing-suite green |
| 645 passed again after fast-forwarding onto main `7c6e35163c9f67087ffe174a7ab3810f47ce6a45` | Not auditable from this PR's diff. Body's framing ("the same 645 passed again") is the verifiable claim, not the number itself. | aggregate count | PLAUSIBLE — same-claim invariant |

The body makes two production-claim caveats that bind the validated-claims reading:

> "Local schema reduction is not production acceptance. Completion requires exact-head CI, source merge, deployment adoption on the real Brain service, and live Fast canaries proving both the narrowed model-visible surface and preserved mixed-domain tool use."

> "Reported provider token usage must be treated as observed telemetry, not total spend, because cumulative multi-round accounting remains a separate known issue."

Both caveats are reviewer-binding: no user-facing copy in this PR claims a token reduction. The body itself is the surface being read, and it does not over-claim.

"Validated" word check: the body uses the term `validated` zero times in user-facing positions. The CI guard `scripts/check_validated_claims.py` is scope-bound to the rendered site; this PR ships no site copy, so the guard has nothing to check. Internal engineering language ("fail-open", "PROVEN_LIVE / DO_NOT_REDO", "byte-equivalent") is fine for an internal PR body.

Instrument-vs-market rule: **N/A** — no tripwire / chain / terminal asset verdict is reported or changed.

**Validated-claims verdict: PASS** for the prose surface this PR ships. Every quantitative claim is qualified as a local measurement; the two production-acceptance caveats are explicit and bind any future user-facing surface that quotes the percentages.

## Overall verdict

**PASS.** Plain-language / theme / validated-claims laws all hold for the surface this PR ships. The PR is half-B scope: backend-only, four files, 331 lines, zero rendered UI surface, zero CSS/JS/template/data surface, with an internal engineering body that uses the same vocabulary as the code, names the canonical classifier as the single owner, and explicitly disclaims local-measurement-as-production-acceptance in two places. The follow-up commit plugs the one specialist-fail-open hole the initial head carried. Eleven new tests pin the contract.

**No required change.** This audit is filed as `orch/audits/macro_PR-7662.mm.md` per the half-B convention; no PR comment is queued because the PR is already merged and the carrier (`claude/mastermind-ai-fast-tool-visibility-20260921-sol`) is consumed. Future user-facing Fast copy that quotes the schema-reduction percentages must carry the body's "local measurement, not production acceptance" qualifier until live Fast canaries prove it.
