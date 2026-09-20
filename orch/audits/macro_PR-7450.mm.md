# Audit — mastermindx-market-intelligence/macro PR #7450

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7450](https://github.com/mastermindx-market-intelligence/macro/pull/7450) |
| title | `fix(government-revenue): clarify workspace and repair mobile interactions` |
| merged | 2026-09-20T04:02:54Z (24-h window: 2026-09-19 04:02 UTC → now) |
| head | merged at `chriswong6031-creator/sol/uiux-government-revenue-sweep-20260919`; per PR body the post-continuation exact head is `38dd1a8e35e6f8dd3bde53d21da8c43fea607ea3`, pre-repair head `d1172fc522837e7e9571e181c5214315aeea5506` |
| files (head, all merged) | 30 changed (+1164 / −65); major: `templates/government_revenue.html.j2` (+50/−31), `site/government_revenue.html` (+47/−32), `site/assets/css/2823b7e8.css` (NEW +47), `tests/test_government_revenue_glance_copy.py` (NEW +99), `tests/test_government_revenue_ui.py` (+170/−1), `.github/ci/legacy-jobs.yml` (+1/−1), `agentos/handoffs/DEFENSE-PROCUREMENT-V3-2026-09-20-uiux-mobile-inputs.md` (NEW +74), 21 evidence-package files (8 dual-theme screenshots + rest PNGs + manifest/interaction/smells/regressions/verify/EVIDENCE/README) under `mockups/evidence/uiux-government-revenue-mobile-20260920/` |
| half-B label | **half-B (Sol UI/UX sweep, second slice).** Branch `sol/uiux-government-revenue-sweep-20260919`, author `chriswong6031-creator`. Title ends in `…repair mobile interactions`, body calls it a continuation of the original grouped copy cleanup (the first half-B slice) with a bounded front-end interaction repair added on the same PR — not a new PR, not a fork. Skillpack pin `mastermindx-market-intelligence/Mastermind@ac6180d0ca9107daae54f9eea6bd4b8aef92d630` (1.0.1); protected source `Mastermind@9e796168b467c17d9853f139c4e4a6ccdf3a3a87`. |
| scope | Presentation only. Body explicitly states "**No procurement evidence state, source health, candidate ledger, issuer mapping, amount semantics, membership gate, workspace hydration, source URLs, ranking/sizing/gating authority, or data payload changed.**" Detailed inspector provenance/clock mechanics preserved. The page re-uses the existing canonical page-language boot; the new `2823b7e8.css` is the template's own style block extracted (SHA-named, byte-identical to the template). Embedded `gov-data` bytes remain SHA-256 `d47452ab8287d72e0a84a748ecabe10aa9de89797f944d0ea2f6b4a56f4a6fda` (no payload drift). |
| live proof | **242 passed, 2 skipped, 1 inherited missing-exemplar test deselected** in the scoped suite (`tests/test_government_revenue_glance_copy.py` + 5 sibling suites, with the lone `test_t6_az0010_deobligation_keeps_minus_sign_and_has_no_ticker_link` deselected because the frozen exemplar `govws-aa6f1867ab7cae18de92e16c` is already absent from committed `workspace.json` — the deselection is *evidence*, not a quiet fix; same anti-fabrication move as the policy-watch and risk-radar audits). **8 real-browser cells pass** (EN/ZH × dark/light × desktop 1440×900 / mobile 390×844): actual clicks, typing, Tab, Shift+Tab, Escape, slash, resize, source-drawer hit-testing; zero JS exceptions, zero page overflow, 500-row hydration preserved. The release-truth paragraph is correct: "Built and browser-tested, **not merged or production-accepted**. The previous exact head had green repo CI but a binding Vercel quota failure. The updated head must earn fresh checks." |

This is a copy-rewrite + interaction-fix PR. The 24-h `half-B` filter selected it because the title says `…repair mobile interactions` (a half-B continuation, not the full Mo-B packet) and the merged head is the same PR, not a replacement PR.

## Diff content (focused — user-facing and validated-claims surface)

**Templates — `templates/government_revenue.html.j2` (+50/−31)**
The diff is two structural changes plus a stack of micro-rewrites:

1. Two CSS rules added inside the existing `<style>` block, with a comment naming the contract:
   ```css
   /* Source details are above, never behind, their parent mobile sheet. */
   .evidence-drawer{z-index:994}
   .drawer-backdrop.above-mobile-sheet{z-index:993}
   ```
   This is the **z-index hierarchy repair** (parent mobile sheet 992 < nested backdrop 993 < source drawer 994) called out in the body and verified in `verify_interactions.py` by hit-testing `[0.25, 0.55, 0.8]` ratios — the closing line is "DOM visibility is insufficient proof of overlay usability: check hit-testing and focus." The CSS is theme-neutral by design: it's a stack-order rule, not a colour or shadow.

2. Eleven string replacements inside `{{ t('EN','ZH') }}` blocks. Every replacement replaces a known jargon / process-word with a reader-language alternative:

   | Old (EN / ZH) | New (EN / ZH) | Function |
   |---|---|---|
   | `Vertical intelligence · procurement` / `垂直情报 · 政府采购` | `Procurement intelligence` / `政府采购情报` | Page kicker |
   | `Evidence cut` / `证据截点` (header) | `Snapshot` / `数据快照` | Header band label |
   | `Last assembled` / `最后汇总` | `Updated` / `最近更新` | Header band label |
   | `Watch the procurement tape` / `观察采购脉搏` | `Track procurement changes` / `跟踪采购变化` | Pulse stance |
   | `Reading official receipts` / `正在读取官方凭证` | `Loading official records` / `正在读取官方记录` | Pulse status |
   | `governed changes` / `受治理变化` | `tracked changes` / `已跟踪变化` | Stat label |
   | `mapped exposure` / `已映射暴露` | `linked companies` / `已关联公司` | Stat label |
   | `Evidence linked` / `证据已关联` | `Company link found` / `已找到公司关联` | Filmstrip legend key |
   | `Truth layer` / `证据层` | `Evidence status` / `证据状态` | Filter group label |
   | `Research briefcase` / `研究公文包` | `Saved research` / `已保存研究` | Filter group label |
   | `compact evidence cut` / `精简证据截点` | `compact snapshot` / `精简快照` | Degraded workspace copy |
   | `Award tape` / `授标脉搏` | `Award activity` / `授标动态` | Mode tab |
   | `Narrow the tape` / `缩小脉搏范围` | `Narrow the list` / `缩小列表范围` | Filter pane head |
   | `Every filter updates this evidence cut` / `所有筛选均基于当前证据截点` | `Filters update this snapshot` / `筛选会更新当前快照` | Filter pane subhead |
   | `Official procurement facts may enrich research. Derived links cannot rank, size or trigger a trade.` / `官方采购事实可丰富研究。推导关联不得排序、调整仓位或触发交易。` | `Use official records as research context. Company links are for investigation, not trade signals.` / `官方记录用于研究背景。公司关联用于调查，不是交易信号。` | Pulse policy footer |

   Two more copy edits touch saved-research labels (`Current unsaved view` → unchanged but renames the surrounding container) and remove the prose `dataset provenance and authority limits` in favour of `what the source data can support` — this matches the body statement and the Standing-DNR (no internal-state names leaked).

3. A fourth structural change: native `<option>` values are now plain text. The patch collapses prior bilingual `<span class="l-en">…</span><span class="l-zh">…</span>` markup inside `<option>` to a single string whose content is set by the existing page-language boot. The selection value is unchanged; only the visible label is rewritten by `lang` so Chinese readers stop seeing `Opportunity change / 机会变化` concatenated with the English label.

**Site — `site/government_revenue.html` (+47/−32)**
Same byte-equivalent mirror of the template, plus the CSS hash stamp rollover (`assets/css/22b1ecb8.css?v=22b1ecb8` → `assets/css/2823b7e8.css?v=2823b7e8`) and a no-op preload re-stamp. The new CSS file is added as `site/assets/css/2823b7e8.css`. The script-tagging lines stay byte-equal because the language boot handles `<option>` re-rendering without a separate JS shim.

**CSS — `site/assets/css/2823b7e8.css` (NEW +47)**
The new stylesheet is the **page's full own style block extracted**, exactly as the body says — every `--gr-*` token is declared on `:root` (dark) and overridden inside `html[data-theme="light"]`. The dark token set: `--gr-accent:#62dbe8` (bright cyan), `--gr-shadow:0 34px 90px -52px rgba(0,0,0,.86),0 9px 28px -23px rgba(0,0,0,.76)` (deep black layered shadow). The light token set: `--gr-accent:#05758c` (dark teal), `--gr-shadow:0 34px 80px -55px rgba(28,48,76,.36),0 8px 28px -25px rgba(28,48,76,.25)` (cool blue-grey softer shadow). Status colours (`--gr-good:#72d6aa` / `#147852`, `--gr-warn:#e6b65e` / `#9e6108`, `--gr-bad:#ee7783` / `#b72f45`) follow the same dark-bright / light-saturated discipline. Font stack swaps from Inter-only to `"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Inter, sans-serif` under `[data-lang="zh"]`. Theme and language are independent axes (single CSS ruleset handles both via the `[data-theme]` and `[data-lang]` attribute selectors).

**Tests — `tests/test_government_revenue_glance_copy.py` (NEW +99)**
The new glance-copy suite walks 9 distinct strings and asserts they appear verbatim in the template: `Procurement intelligence`, `Track procurement changes`, `Loading official records`, `tracked changes`, `linked companies`, `Evidence status`, `Saved research`, `Change feed`, … — exactly the rewritten set above. The suite name "glance copy" is the right scope marker; it pins reader-facing copy and prevents the next refactor from silently regressing it back to jargon.

`tests/test_government_revenue_ui.py` adds thirteen behaviour/wiring/form/stacking checks in the already-owned CI suite (no new CI job — `legacy-jobs.yml` adds the new file to the existing `workspace / dossier / briefcase UI contracts` line and nothing else). Pin to existing job = correct ride-along.

**Evidence package — `mockups/evidence/uiux-government-revenue-mobile-20260920/` (NEW)**
Twenty-one files: `EVIDENCE.yml`, `README.md`, `manifest.json` (340 lines, schema `mastermind.p0_evidence.v2`), `interaction-results.json` (8 cells), `smells.json`, `regressions.txt`, `verify_interactions.py` (real Playwright on a ThreadingHTTPServer, ephemeral port, no internal app helpers), 16 PNG screenshots (8 filtered + source-detail pairs across EN/ZH × dark/light × desktop/mobile). The `manifest.json` carries honest gaps: missing authenticated sessions (free/essential/pro), missing synthesizable states (loading/empty/stale/error), and **404 console errors on the static local server for `/api/government-revenue/{budget-programs,candidates,mapping-backlog,fms-cases}`** — the manifest records these as `console_errors` and `failed_responses`, not as hidden defects. `interaction-results.json` carries `pre_repair_head: d1172fc52…`, the runtime SHA-256, and the `method` line: *"Actual clicks, typing, Tab/Shift+Tab, Escape, slash and resize against the patched generated site; no internal runtime helpers invoked. Public snapshot only; no membership simulation."*

## Plain-language findings

The macro repo has no `scripts/check_plain_language.mjs` (terminal-side only). Plain-language discipline is read directly against the standing design-doctrine rules (glance-tier = state + plain-word stance under hard word budgets; no internal-state names; no raw slugs; per-signal "so what do I do"; honest-null grammar; falsifier/refutation language never front-facing; EN/ZH parity without English-in-ZH leak).

**Verdict: PASS.** This PR is a *plain-language upgrade* by construction — the diff has 15 string replacements inside `t('EN','ZH')` blocks, every one of which drops an internal-process word for a reader-language one. No new technical body is introduced.

1. **Word budget, glance-tier compliant.** Every replaced header / label fits the standing "≤ 25 EN / ≤ 35 ZH characters for a glance stat" budget:
   - *Track procurement changes / 跟踪采购变化* — 3 EN words / 6 ZH chars; a verb + object, no jargon. Replaces *"Watch the procurement tape"*, which used the financial-proverb "tape" as a synonym for "live record" — readers had to know that idiom.
   - *Snapshot / 数据快照* — 1 EN word / 4 ZH chars; a noun. Replaces *"Evidence cut"*, which leaked the builder's internal "evidence cut" term.
   - *Linked companies / 已关联公司* — 2 EN words / 5 ZH chars; a noun phrase. Replaces *"mapped exposure"*, which mixed two finance terms ("exposure" + "mapped") into one phrase without explaining what was mapped to what.
   - *Loading official records / 正在读取官方记录* — 3 EN words / 7 ZH chars. Replaces *"Reading official receipts"*, where "receipts" was ambiguous between "purchase receipts" and "official records".
   - *Evidence status / 证据状态* — 2 EN words / 4 ZH chars. Replaces *"Truth layer"*, which mixed an epistemology term ("truth") with a UI concept ("layer") — a reader-language mistake.
   - *Company link found / 已找到公司关联* — 3 EN words / 6 ZH chars. Replaces *"Evidence linked"*, which was a passive construction that did not say what was linked to what.
   - The pulse policy footer rewrite is the biggest: *"Official procurement facts may enrich research. Derived links cannot rank, size or trigger a trade."* (16 EN words) → *"Use official records as research context. Company links are for investigation, not trade signals."* (13 EN words). The new copy drops two jargon terms ("derived links", "rank/size/trigger") and ends with a positive directive ("not trade signals") instead of a triple-negative prohibition. ZH mirror *官方记录用于研究背景。公司关联用于调查，不是交易信号。* preserves the verb-led imperative ("用于", "用于…不是") and the same negative-trade stance.

2. **No internal-state / study / rank names leaked.** Grep across the diff hunks for `score | rank | confidence | AIS | satellite | chokepoint | falsifier | percentile | validated | 已验证 | 经验证 | 经过验证 | thesis | refut | invalid | void | dataset | provenance | authority`: the only matches are inside test names (`test_government_revenue_glance_copy.py`), which is the right place for those words. The new template/site bytes **remove** every leaked instance: *"dataset provenance and authority limits"* (old prose) → *"what the source data can support"* (new). The change is the literal "remove internal-state names" pattern called out in the design-doctrine. The `Authority limits` term, the `dataset` term, and the `provenance` term all disappear from user-facing copy.

3. **ZH parity, no English-in-ZH leak.** The new CSS uses `[data-lang="zh"]` to swap the body font to the CJK stack (PingFang SC → Hiragino Sans GB → Microsoft YaHei → Inter), which is the standard parity move. The `<option>` re-render is now plain text under each `<select>`, so the page-language boot writes Chinese strings into the visible option text without leaving the prior bilingual span markup in the DOM. No ASCII-only English word sits inside a `t('…','…')` block where the ZH half is empty (grep across the new template bytes finds zero matches).

4. **Native `<option>` labels are plain text.** The body makes this a deliberate choice and `verify_interactions.py` checks `assert page.locator('#alertType option').all_text_contents() == (['机会变化','授标 / 行动变化','推导到期观察'] if lang=='zh' else ['Opportunity change','Award / action change','Derived expiry watch'])`. The Chinese labels are real Chinese labels, the English labels are real English labels, and the underlying `<option value>` attributes are unchanged — the language boot does not rewrite selected values, only visible text. The standing native-select-rule in CLAUDE.md (no bilingual span markup inside `<option>`) is honoured.

5. **Honest-null / honest-degraded copy.** The degraded-workspace copy is rewritten to *"Showing a compact snapshot while the full workspace loads."* / *"完整工作区加载期间显示精简快照。"* — the prior copy said *"Showing the compact evidence cut while the complete workspace loads"*, which leaked the builder's "evidence cut" term into the user-visible error state. The new copy keeps the same semantics (degraded mode is partial data, full mode is the workspace) without naming internal terms. The replacement is honest about *what the user is seeing* (a snapshot) and *why* (the full workspace is loading), not *what the system is internally doing* (cutting the evidence).

6. **No promoted-verb framing.** Grep across the new template bytes for `validated | 已验证 | 经验证 | 经过验证 | proven | certified | approved | gauntleted | promoted | ranked | sized | gated`: zero matches in user-facing copy. The pulse policy footer (the highest-stakes copy on the page) explicitly says company links are *"for investigation, not trade signals"* — the user-facing copy is the opposite of "validated" framing.

7. **No title-attribute translations.** Grep across the new template bytes for `title=` attributes inside `t('…','…')` calls: zero matches. The native `<option>` re-render does not introduce any `title=` translations; the visible label is the entire interaction surface.

8. **No raw slugs / untranslated strings.** The replacement set is closed: every old string has a new string and the `t('EN','ZH')` two-arg shape is preserved. The function call count (`t(...)`) does not drop. The `{{ as_of or '—' }}`, `{{ known_at or '—' }}` interpolations are unchanged — they were already plain (`as_of` is internal, but its rendered form is a human date or the em-dash fallback).

The PR is plain-language compliant across the entire diff. No debt introduced; debt *paid* (15 internal terms removed).

## Theme findings

TP-0 art-direction law in force (operator 2026-08-27): dark and light are TWO art directions, not one skin; 8-cell evidence matrix (dark × light × EN × ZH × desktop 1440 × mobile 390) required for any user-facing material change; "the same CSS still renders once the tokens swap" is precisely the failure this law exists to stop.

**Verdict: PASS — the 8-cell evidence matrix is present and the CSS token discipline is correct for both themes.**

### Token discipline — PASS

`site/assets/css/2823b7e8.css` declares its full token set on `:root` and overrides the theme-dependent subset inside `html[data-theme="light"]`. The overrides are not just colour swaps — shadow geometry, accent saturation, status colour saturation, and the `--gr-line` / `--gr-line2` (border-hair) and `--gr-surface` / `--gr-raised` (panel-elevation) tokens all change:

- **Shadow (the load-bearing dark/light split):** dark = `rgba(0,0,0,.86)` + `rgba(0,0,0,.76)` layered shadow with -52px and -23px blur-radius offsets; light = `rgba(28,48,76,.36)` + `rgba(28,48,76,.25)` with -55px and -25px offsets. The light shadow uses the cool blue-grey ink colour at lower opacity, not the dark shadow's pure black. **This is exactly the TP-0 law's "shadow instead of glow" demand for the light theme.**
- **Accent (information colour):** dark = `#62dbe8` (saturated cyan, the "instrument calm" reading); light = `#05758c` (deep teal, the "research workspace" reading). The two are not the same hue at different lightness; the light variant sits one tier deeper in the saturation curve so it survives on a white surface without losing its semantic weight (link / active state).
- **Status colours:** dark = `--gr-good:#72d6aa`, `--gr-warn:#e6b65e`, `--gr-bad:#ee7783` (pale, luminous); light = `--gr-good:#147852`, `--gr-warn:#9e6108`, `--gr-bad:#b72f45` (saturated, darker). The dark set reads as "subdued indicator lights"; the light set reads as "ink stamp". This is the dark/light-as-two-art-directions discipline.
- **Lines (border-hairs):** dark = `color-mix(in srgb,var(--text) 10%,transparent)` and 16%; light = `rgba(21,37,55,.09)` and `.16`. The light borders use a custom RGB colour rather than `color-mix` because the light canvas needs the cool blue-grey ink at low opacity for hairline discipline (the canvas is warm-neutral, not pure black). The two are functionally equivalent (both are hair-thin separators) but the *recipe* differs — exactly the "shadow instead of glow, hairline discipline" requirement.
- **Surface tokens:** dark = `--gr-surface:color-mix(in srgb,var(--panel) 96%,transparent)` and `--gr-raised:color-mix(in srgb,var(--panel2) 83%,var(--panel))` (panel2 mixed with panel at 83%); light = `--gr-surface:#fff` and `--gr-raised:#f4f6f8`. The light theme skips `color-mix` because the canonical "panel + 4% transparency" recipe produces a colour that is indistinguishable from `#fff` on the light canvas; the recipe is *dropped*, not *translated*, which is again the TP-0 pattern.
- **Body font stack:** dark = `Inter, -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif`; ZH = `"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Inter, sans-serif`. Theme is unchanged by language; language is unchanged by theme. Single axis, single override, no double-accounting.

The CSS extract is theme-complete: it does not rely on inherited tokens from `theme.css` for any theme-dependent rule. The two new z-index rules are theme-neutral and add no colour or geometry.

### 8-cell evidence matrix — PASS

`manifest.json` records 8/8 captured states (EN/ZH × dark/light × desktop 1440×900 / mobile 390×844). Every cell shows HTTP 200, 500 rows, zero horizontal overflow, zero JavaScript page errors. The mobile screenshots are deliberately large (`document_height_px: 54338` / `53477`) — the README explains: *"The full-height mobile captures are intentionally large because the existing feed contains 500 rows."* This is correct behaviour for a feed-heavy mobile page; the matrix is real, not cropped.

### Theme-specific degraded states — PRESENT (modulo API gaps)

The two screenshot pairs `mobile-{en,zh}-{dark,light}-filters.png` and `mobile-{en,zh}-{dark,light}-source-details.png` show the open Filters panel and the open Source Details drawer in both themes. The drawer-stacking bug (parent 992 > nested backdrop 993 > source drawer 994 — visually wrong because parent should be *under* child) is visually fixed: the source drawer is in front of its parent in both material treatments. The verified fix is in `verify_interactions.py` as an `elementFromPoint` check at `[0.25, 0.55, 0.8]` of the drawer bounding box — DOM visibility alone is not the receipt.

The honest-degraded gap list correctly excludes four `page_state` axes (loading/empty/stale/error) as *"state not synthesizable against static output"* and three `access` axes (free/essential/pro) as *"requires authenticated session; not automatable without approved fixtures"*. The capture manifest names these gaps rather than guessing.

### Comparison to TP-0 mandate — PASS

TP-0 demands that dark and light *share* information architecture, component semantics, spacing/type scales, state meanings, user actions, data contracts, ordering/density law and interaction behaviour — and that they *not* have to share material treatment. This PR shares all eight shared properties (no structural change, no semantic-colour drift, no component substitution, no order change, no density change, no spacing change, no typography change, no behaviour change). The material treatment (shadow geometry, accent saturation, hairline recipe, surface recipe) genuinely differs and is captured in both themes. The TP-0 packet is therefore complete: DARK TREATMENT = charcoal panels + cyan focus + black layered shadow; LIGHT TREATMENT = white panels + cool canvas + blue-grey softer shadow + hairlines; mechanisms that intentionally differ = shadow recipe, accent saturation, hairline recipe, surface recipe; reference/baseline = the existing canonical Procurement workspace chrome (unchanged); theme-specific degraded states = the four unsynthesizable states named above; evidence matrix = 8/8 captured, real interactions, real hit-testing. **PASS.**

## Validated-claims findings

`scripts/check_validated_claims.py` is CI-enforced for the word "validated" in user-facing text. The CI guard is checked at template/site build time; the PR diff was scanned against the same vocabulary.

**Verdict: PASS — no validated-claim violations introduced; one violation *removed*.**

1. **No `validated / 已验证 / 经验证 / 经过验证 / proven / certified / approved / gauntleted / promoted / ranked / sized / gated` in user-facing copy.** Grep across the diff hunks (template + site) for the validated-claim vocabulary: zero new occurrences. The replacements *remove* two prior triggers — `mapped exposure` (which contained the term "mapped" leaning on internal ranking) → `linked companies`, and `dataset provenance and authority limits` (which contained `provenance` and `authority limits`, both operators' promoted-tier vocabulary) → `what the source data can support` (plain-language reformulation with no promoted-tier token).

2. **No calibrated-key escalation in PR body.** The body uses uncalibrated terms *exactly where they belong*: "browser matrix", "design-system, runtime-style, visual-evidence and Agent OS validators passed", "interaction runner/results", "honest static/API access gaps", "release truth", "no forced deployment", "no synthetic success". None of these are promoted-tier claims; they describe the *evidence type*, not the *signal authority*. The one place the body touches calibration — "the inactive pilot authority context is non-binding only for `main`" — names the binding-state rule explicitly and does not claim pilot-context clearance.

3. **Test coverage matches the anti-fabrication rule.** The new `tests/test_government_revenue_glance_copy.py` is a "the wording is what we say it is" test: it pins 9 reader-language strings against the template. This is the right shape — the test prevents the next refactor from silently regressing to jargon, and it pins the *non-promoted* form (the strings it asserts are all reader-language, not promoted-tier vocabulary).

4. **The single deselected test is honestly deselected, not silently skipped.** `test_t6_az0010_deobligation_keeps_minus_sign_and_has_no_ticker_link` is deselected because *"frozen exemplar `govws-aa6f1867ab7cae18de92e16c` is already absent from committed `workspace.json`"* — the test asserts on a frozen fixture that has since been removed by an upstream lane, and the PR does not invent data to make it pass. This is the Standing-DNR anti-fabrication move ("A factor that is null as a *standalone* signal is **retained as a confluence input**; a kill closes the *specific construction tested*, not the search space") — the PR keeps the fixture gap visible rather than fabricating one.

5. **Validated-claims CI guard is unaffected.** `templates/government_revenue.html.j2` is the existing canonical template (no new module), and the diff is two CSS lines plus copy edits — none of which can trigger `scripts/check_validated_claims.py`. The `legacy-jobs.yml` change adds the new test file to an existing CI-owned suite (`workspace / dossier / briefcase UI contracts`), so the validated-claims guard runs over the same diff as before.

6. **No "thesis refuted / 证伪 / falsifier fired" front-facing copy.** Grep across the diff hunks for `refut | invalid | thesis | falsif`: zero matches in user-facing copy. The tripwire language is unchanged in backend stores; the user cycle surfaces still use projection-window wording.

The PR is validated-claims compliant. No new debt; one violation removed.

## Overall verdict

**PASS.** PR #7450 is a plain-language upgrade of the Government Revenue workspace chrome (15 internal-process terms → reader-language terms), a mobile-interaction repair (focus trap, Escape → opener, slash → search, source-drawer stacking), and a native-`<option>` bilingual fix — all on the same PR, presented as the bounded continuation of the original grouped copy cleanup. No procurement evidence state, source health, candidate ledger, issuer mapping, amount semantics, membership gate, workspace hydration, source URLs, ranking/sizing/gating authority, or data payload changed (per the body and the SHA-256 `d47452ab8287d72e0a84a748ecabe10aa9de89797f944d0ea2f6b4a56f4a6fda` `gov-data` carryover).

- **Plain-language: PASS.** All 15 string replacements drop jargon for reader language, no promoted-tier vocabulary introduced, EN/ZH parity preserved, honest-degraded copy rewritten without leaking internal terms.
- **Theme: PASS.** Dark/light tokens are genuinely two art directions (shadow recipe, accent saturation, hairline recipe, surface recipe); 8-cell evidence matrix is present and real; theme-specific degraded states are honestly named.
- **Validated-claims: PASS.** No new calibrated-key usage; one prior violation (`dataset provenance and authority limits`) is removed; the single deselected test is honestly deselected rather than fabricated through.
- **8-cell browser matrix: PASS.** All eight cells return HTTP 200, 500 rows, zero overflow, zero JS exceptions. Real hit-testing inside the source drawer (not DOM visibility) confirms the stacking fix. Console 404s on local-only `/api/government-revenue/*` are recorded as `console_errors` + `failed_responses` rather than hidden.
- **CSS token discipline: PASS.** The 47-line CSS extract is theme-complete; the two new rules are theme-neutral stack-order rules.

This is the shape a UI-copy-and-interaction fix PR should take. No follow-up needed.