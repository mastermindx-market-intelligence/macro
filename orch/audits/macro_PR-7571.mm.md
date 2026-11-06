# Audit — mastermindx-market-intelligence/macro PR #7571

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7571](https://github.com/mastermindx-market-intelligence/macro/pull/7571) |
| title | `design ratchet: FUNC_COLOR_RE covers CSS Color 4/5 functions (color-mix, oklch, lab/lch, hwb, color())` |
| merged | 2026-09-21T04:05:57Z via squash-merge to `main`. Head OID `2042b2f4ca5bcd84da47f0937f3b6a1e3d488b77`; branch `claude/design-ratchet-css-color4-funcs`. |
| half-B label | **half-B (linter-only design-ratchet widening).** Forward-only enforcement arm of `scripts/check_design_system.py` (R0 `enforce-added`). Pure regex extension + parametrized tests — no template/CSS/JS bytes, no rendered surface. The PR closes a measured gap from PR #7554's review (2026-09-20): a token-composed `color-mix(in srgb, …)` on a changed line reported `blocking=0` because `FUNC_COLOR_RE` only matched `rgba?|hsla?`. Rule 1 (color-literal) now fires on every CSS Color 4/5 function shape so the colour decision has to land in `theme.css` as a token. |
| files | **3 files, +96 / −3.** `scripts/check_design_system.py` (+22 / −1), `tests/test_check_design_system.py` (+56 / −0), `tests/test_stock_dashboard_css.py` (+18 / −2). Zero bytes in `templates/`, `site/`, `mockups/`, `engine/`, `data/`. |
| owner | `chriswong6031-creator` (branch carrier `claude/design-ratchet-css-color4-funcs`). |
| live proof | PR body enumerates: `python3 -m pytest tests/test_check_design_system.py tests/test_stock_dashboard_css.py -q` — pass (97 + file suite); `python3 scripts/check_design_system.py --self-check` — OK; design-governance bundle (`test_check_runtime_style_injection`, `test_check_ui_visual_evidence`, `test_freshness_chips_language_invariant`) — pass. PR body caveats 17 `test_unified_dashboard_b1.py` failures as `data/`-omission artifacts in a sparse worktree — unrelated, correctly diagnosed. |
| explicit hold | None. The change IS the ratchet widening; no follow-on hold. The body flags downstream impact: open PRs adding inline `color-mix` template lines (cited #7554) will now block on those lines at next CI run, and the R-W2-16 test in that program already asserts changed lines drop `color-mix`. |
| plain-language script | `scripts/check_plain_language.mjs` referenced in the task prompt is **terminal-side only** and does NOT exist in `mastermindx-market-intelligence/macro` (verified — `ls scripts/check_plain_language*` → no matches). Plain-language discipline on macro is read directly against the standing design-doctrine rules and a regex scan for the documented banned vocab on the PR's three changed files (see §Plain-language findings below). |

## Diff content (exact, scoped to this PR)

**`scripts/check_design_system.py` (+22 / −1)** — `FUNC_COLOR_RE` widened from `\b(?:rgba?|hsla?)\s*\(` to a four-alternative pattern covering CSS Color 4/5 function shapes. Three named categories with false-positive guards measured on the live estate:

- **Unambiguous names** (`color-mix`, `hwb`, `oklab`, `oklch`, `light-dark`, `device-cmyk`) match on the name + immediate `(` — so prose like `light-dark (two art directions)` cannot fire.
- **`lab(` / `lch(`** require an additional CSS-colour first argument (`from`, `none`, `var(`, `calc(`, or `[+-]?\.?\d`) because the names are real identifiers elsewhere (a JS label helper `lab(lo, …)` in `options.html.j2`, prose `factor/index lab (factors …` in `theme.css`).
- **Bare `color(`** requires a predefined colourspace ident (`srgb`, `srgb-linear`, `display-p3`, `a98-rgb`, `prophoto-rgb`, `rec2020`, `xyz`, `xyz-d50`, `xyz-d65`) or relative-colour `from` because `color(` is everyday prose (`verdict color (--ms-c …)`).
- The rgb/hsl alternative keeps its historical `\s*` verbatim so the legacy census is byte-stable.

**`tests/test_check_design_system.py` (+56 / −0)** — fourteen new parametrized `color-literal` fixtures (a4–a14), each pinning a distinct CSS Color 4/5 shape including the motivating exemplar (`color-mix(in srgb, var(--up) 40%, var(--line))`) and the relative-colour forms (`oklch(from var(--accent) …)`, `color(from var(--x) srgb …)`). Two new end-to-end tests:

- `test_ambiguous_colour_function_names_do_not_fire_on_prose_or_js` — pins the six measured estate shapes (JS label helper, prose comments, chart-library method call). All must return zero `color-literal` findings. The whole point: a false positive on an added line blocks a PR.
- `test_enforce_added_blocks_a_newly_added_color_mix` — pins the PR #7554 gap end-to-end. A token-composed `color-mix` on an ADDED line now exits 1 with an error annotation naming `color-mix(`. Diff fixture is hand-rolled unified-diff text.

**`tests/test_stock_dashboard_css.py` (+18 / −2)** — `test_stylesheet_is_token_clean` carves a frozen-shrink-only debt ceiling for the 75 pre-existing token-mix `color-mix(...)` uses in `stock-dashboard.css`: those are debt, not endorsement, but the ceiling lets the test stay useful while retiring mixes lowers the count for good. Any other new colour function still fails at zero. The error message was upgraded to separate `hard` from `color_mix_debt`.

## Plain-language findings

- **No template/UI copy is touched** by this PR — only `scripts/check_design_system.py` and its two test files. The standing plain-language discipline (no banned marketing-style vocab, plain prose for user-facing surfaces) therefore has nothing to gate on the change itself.
- **Banned-vocab regex scan** over the merged diff (delve / navigate the / in the realm of / plethora / robust / seamless(ly) / leverage / utilize / demystify / embark / dive into / comprehensive / holistic / crucial / pivotal / meticulous) — **0 hits**.
- **Docstring / comment quality**: the new `FUNC_COLOR_RE` docstring reads like the doctrine-correct form — names the WHY (the colour-mix gap surfaced in PR #7554's review, 2026-09-20), names the three false-positive categories with concrete estate measurements, names the byte-stability guarantee for the legacy rgb/hsl alternative. No adverbs. The test docstrings repeat the same shape: each new test names the measured estate exemplar it's pinning (PR #7554 gap, six measured prose/JS shapes for the ambiguous-name guard). This is the model for design-ratchet PRs — the rationale lives in the linter, not in the PR body.
- **No Chinese / bilingual copy** introduced or changed. Nothing for the language-invariants test to gate.
- **Verdict: PASS.** Nothing in the PR needs plain-language correction.

## Theme findings

This is a **theme-ratchet** change, not a theme change — the theme system itself (tokens, palette, art direction, dark/light split) is untouched. What changed is the **linter** that gates the forward-only flow onto theme.css.

- **Two art directions preserved.** Both dark and light still own their token sets in `theme.css`; nothing in `scripts/check_design_system.py` or its tests darkens one theme or lightens the other. The ratchet widens the same rule to both.
- **`scripts/check_design_system.py --self-check`** — `self-check OK: 8 rule fixtures + clean fixture + traversal`. Rule 1 still distinguishes dark/light tokens correctly (none of the new fixtures collapse them).
- **`scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7571_diff.txt`** against the actual PR diff — `::notice title=design-system::R0 enforce-added: 0 blocking finding(s) (18961 further pre-existing, non-blocking finding(s) in the estate — run --mode report for the full census)`. The PR's own diff is clean under the new rule. The 18,961 pre-existing findings are unchanged estate debt — the PR adds no new debt.
- **Estate census** (PR body, re-verifiable): **6,410 pre-existing `color-mix` findings** under the widened regex (warn-tier census debt; forward-only mode leaves them non-blocking) and **zero hits from the guarded ambiguous names** — no prose/JS false positives in today's estate. That ratio (6,410 real colour-mix violations vs zero false positives across six measured ambiguous-name shapes) is the falsifier that the guards are tight enough to ship.
- **Debt ceiling is shrink-only** (`tests/test_stock_dashboard_css.py::test_stylesheet_is_token_clean`). Retiring one of the 75 `stock-dashboard.css` mixes lowers the ceiling; adding a new one fails. This is the right shape — it lets the ratchet stay useful while honest migration proceeds, and a future heal PR that actually moves those 75 mixes into `theme.css` shrinks the ceiling rather than working around it.
- **No new templates, no new tokens, no new colour values**. Pure forward-only enforcement widening.
- **Verdict: PASS.** The ratchet widens correctly, the false-positive guards are measured, and the new rule will start catching real PRs (the cited PR #7554 shape) without breaking the existing estate.

## Validated-claims findings

- **PR does NOT touch any user-facing surface**. Verified across all three changed files via `grep -inE "(validated|已验证|经验证|经过验证)"` — **0 hits**. The standing `check_validated_claims.py` gate (`BC-2`, pre-registration §4 / D2 §4.3) has nothing new to gate; no new affirmative claim ships.
- **No "validated" / 中文-verified phrase** appears in the regex docstring, the test docstrings, the test data, the parametrized fixtures, or the error annotation. The change is pure tooling.
- **No phrase that maps to a stored artifact** (`backtest`, `signal`, `edge`, `validated cohort`, `validated ladder`) is introduced anywhere in the diff.
- **Repo-wide gate** (`python3 scripts/check_validated_claims.py`) is unchanged by this PR — it is gated by file content, not by linter behaviour.
- **Verdict: PASS.** Zero validated-claims surface area; gate stays clean.

## Overall verdict

**PASS — design-ratchet widening with no plain-language, theme, or validated-claims concerns.**

PR #7571 widens the `FUNC_COLOR_RE` rule in `scripts/check_design_system.py` so that CSS Color 4/5 function shapes (`color-mix`, `oklch`/`oklab`, `lab`/`lch`, `hwb`, `color(…)`) trip rule 1 (color-literal) the same way `rgba()` already did, with three named false-positive guards that are each pinned by a measured estate exemplar and a parametrized test. The estate census (`6,410 real color-mix violations, 0 false positives across six ambiguous-name shapes`) and the reproducing test (`test_enforce_added_blocks_a_newly_added_color_mix`) both falsify the worry that the new regex would either miss real violations or block on prose. The `stock-dashboard.css` debt is acknowledged honestly with a shrink-only ceiling so the ratchet stays useful while migration proceeds.

No user-facing copy changes, no theme bytes, no "validated" claims, no banned plain-language vocab. Self-check OK, enforce-added against the PR diff = 0 blocking findings, design-governance bundle passes per the PR body. Heads-up in the PR body — open PRs adding inline `color-mix` template lines (cited #7554) will now block — is the correct downstream effect: the next time someone hand-rolls a colour decision instead of minting a token, the ratchet catches it.

No follow-on actions required from this audit.
