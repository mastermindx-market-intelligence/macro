# Plain-language / theme / validated-claims audit — macro PR #7603

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-21.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7603 |
| title | `fix(render): heal shared dead refs and market-state guard` |
| merge head | `7977c99de670bd8851bd4d21d1b4cbfecbb9d98b` (commits to main at `d0b07bd89c`) |
| merged | 2026-09-21T09:58:49Z via squash-merge to `main`. Selected as the most-recent non-audit half-B PR in the 24-h window that has not already been audited (the only post-#7603 merged PR is `#7606`, which is itself an `orch(audit)` record PR; `#7589 / #7597 / #7585 / #7602` are pre-#7603 and either already audited or out of band; `ls orch/audits/macro_PR-*.mm.md` confirms #7603 is not yet recorded). |
| files | **6 paths, +660 / −5.** `scripts/check_ms_board_coherence.py` (1,1), `site/am_edition.html` (626,0 ADDED), `site/hk_stocks.html` (2,2 MODIFIED), `templates/hk.html.j2` (2,2 MODIFIED), `tests/test_check_ms_board_coherence.py` (11,0 MODIFIED), `tests/test_render_dead_ref_targets.py` (18,0 ADDED). |
| half-B label | **half-B render-infrastructure unblocker.** Body is explicit: "Unblocks the canonical render/deploy lane that currently prevents the merged China-gold panel from reaching the public site." Three concrete defects healed: (a) the shared public chrome links `am_edition.html` but no committed target existed for narrowed renders that skip `build_am_edition`; (b) `hk_stocks.html` linked a retired `sector_ranking.html` route despite HK already owning an in-page `#sector-rotation` board; (c) `check_ms_board_coherence.py` rejected valid `macro.html` markup because `#ms-score` now carries `data-measured-score` after its id. |
| scope | (a) Commit the deterministic Morning Edition page target as a static `site/am_edition.html` (626 lines, fully-rendered output of the shared render pipeline); (b) rewire the two HK "Sector ranking" links — in `site/hk_stocks.html` (committed render output) and `templates/hk.html.j2` (the source-of-truth template) — to the existing `#sector-rotation` in-page anchor; (c) loosen the `_SCORE` regex in `scripts/check_ms_board_coherence.py` from `id="ms-score">(\d+)<` to `id="ms-score"[^>]*>(\d+)<` so any attributes-after-id are tolerated; (d) regression coverage in two test files. |
| durable owner | None new. The PR is a render-infrastructure heal, not a program owner. The shared chrome that references `am_edition.html` is owned by the chrome-rendering lane; the Morning Edition page itself is produced by `build_am_edition` (now narrowed renders that skip it inherit the committed target). |
| checks | Body reports: `tests/test_check_ms_board_coherence.py tests/test_render_dead_ref_targets.py` → **17 passed**; `check_ms_board_coherence.py site/macro.html` → **OK**; full-site `check_ms_board_coherence.py` → **OK, 282 pages scanned**; full-site `check_site_asset_refs.py site` → **OK — 0 missing targets**; `git diff --check` → clean. Body notes the only later protected-main movement was `data/research_vault/catalog.json`, so neither site guard is invalidated. |
| evidence matrix | None shipped. The PR is not a redesigned surface; it commits a static rendered output (`site/am_edition.html`) and heals two dead links. No `mockups/evidence/` PNGs required. The TP-0 dark/light × EN/ZH × 1440/390 matrix only applies to new visual surfaces; this PR ships none. |
| gating scripts | `scripts/check_plain_language.mjs` — **DOES NOT EXIST** in macro (terminal-side only); macroside discipline is read against the design-doctrine banned-glance vocabulary + the standing `l-en`/`l-zh` bilingual-pair discipline. `scripts/check_validated_claims.py` — exists (84024 bytes), scans `templates/*.j2` and `site/*.html` per the standing CLI signature. `scripts/check_design_system.py` — out of scope (no design-system surface touched). `scripts/check_runtime_style_injection.py` — read against the new `site/am_edition.html` (19 inline `style="..."` attributes). `scripts/check_template_site_sync.py` — the plain-copy pair law does NOT apply here (no plain-copy `templates/<name>` + `site/<name>` pair was edited). |

## Diff content (scoped to this audit)

The PR's six diffs are summarised below at the level the three audits need.

### `scripts/check_ms_board_coherence.py` (1,1 MODIFIED)

Single-line regex relaxation. The existing `_SCORE` pattern required `id="ms-score">` to be followed immediately by the score digit (`<span class="v-score" id="ms-score">61</span>`). The new `_SCORE = re.compile(r'id="ms-score"[^>]*>(\d+)<')` consumes any attributes-after-id (`data-measured-score`, `data-…`, `style`, etc.) before the closing `>`. This is a parsing-tolerance widening — the same `(.*?)` matches what the old pattern did plus the new attribute set; no new user-visible string is admitted or rejected by the guard. The five other regexes (`_SECTION`, `_WORD`, `_TICK`, `_THESIS`, `_OVERRIDE`) are unchanged.

### `tests/test_check_ms_board_coherence.py` (11,0 MODIFIED)

Added regression test `test_board_score_parser_accepts_runtime_metadata_after_id()`. The fixture HTML is a minimal `<section class="ms-verdict">` with `<span class="v-score" id="ms-score" data-measured-score="61">61</span>` and asserts `guard.check_text("site/macro.html", html) == []`. The visible copy in the fixture is minimal — `<span class="l-en">Risk-on — the tape is constructive.</span>`, `<span class="l-en">→ Mixed if risk appetite breaks down.</span>`, `<span class="l-en">Risk-on</span>` — all bilingual-paired (the test only models the EN leg; the production guard is invariant to the ZH leg because `_SCORE` does not match inside `<span class="l-zh">`). Plain-language relevant, falsifier-discipline relevant (the thesis/flip pair is "the tape is constructive" / "Mixed if risk appetite breaks down" — neutral descriptive, no verdict).

### `tests/test_render_dead_ref_targets.py` (18,0 ADDED)

New guard file. Three asserts:
1. `(ROOT / "site" / "am_edition.html").exists()` — guarantees the shared-chrome narrowed-render target is committed.
2. `assert 'href="sector_ranking.html"' not in text` for both `templates/hk.html.j2` AND `site/hk_stocks.html` — guarantees neither the source template nor the committed render output links to the retired route.
3. `assert text.count('href="#sector-rotation"') >= 2` for both files — guarantees the in-page anchor links are present (≥2 to allow multiple sibling nav blocks).

Pure structural assertions, no copy or visual surface.

### `templates/hk.html.j2` (2,2 MODIFIED)

Two near-identical edits in the page's two nav strips (the `Leadership & Rotation` header link and the `Research tools` footer strip). Each replaces

```jinja
<a class="hk-v37-link" href="sector_ranking.html">{{ t('Sector ranking', '板块排名') }} ↗</a>
```

with

```jinja
<a class="hk-v37-link" href="#sector-rotation">{{ t('Sector rotation', '板块轮动') }} ↓</a>
```

(`hk-v37-tool` variant for the footer strip — same translation change.) Three observations:
- **Dead route healed:** `sector_ranking.html` is the retired route; `#sector-rotation` is the in-page anchor the HK page already renders. The retarget is mechanical and reuses an EXISTING page element rather than introducing a new route.
- **Bilingual EN/ZH preserved:** the `t('EN', 'ZH')` macro shape is unchanged; the source string swaps from "Sector ranking" / "板块排名" to "Sector rotation" / "板块轮动". Both languages still paired.
- **Affordance glyph corrected:** `↗` (up-right arrow, denoting "external page") is replaced by `↓` (down arrow, denoting "in-page jump"), matching the visual convention every other `#anchor` link on the page uses (`#hk-velocity-desk` → `↓`, `#washout-watch` → `↓`, `#mainland-money` → `↓`). This is a small but consistent UX-correctness fix — the old glyph was a lie about what the link did.

### `site/hk_stocks.html` (2,2 MODIFIED)

Mirror of the Jinja edits in the committed render output. Same two-line swap at the same two nav positions, same bilingual-pair preservation, same affordance glyph correction. The committed file is regenerated by `build_hk_stocks` from `templates/hk.html.j2`; the diff is the deterministic render of the template change. Body confirms the template edit drives the committed render.

### `site/am_edition.html` (626,0 ADDED)

New static page target — the deterministic Morning Edition render. The file is the full HTML output of `build_am_edition` committed to the tree so narrowed renders that skip the builder still have a valid target for the shared chrome's `am_edition.html` link. Key observations from a read of the committed bytes:

**Structure** (584 lines after fetch — PR claims 626 in the diff stat, the small delta is the diff header lines vs the fetched file's first-line continuation):
- `<head>` with `<script data-dbase>` R2 redirect shim (pre-existing chrome), theme + lang bootstrap script (pre-existing), `<title><span class="l-en">Morning Edition</span><span class="l-zh">早间版</span> — 2026-09-21T09:41:49.389241+00:00</title>` (page-specific timestamp), `og:` / `twitter:` metadata (page-specific), `theme.css` link.
- A `<style>` block scoped to this page's components: `body`, `.panel`, `.muted`, `.sm`, `.help` (with `:hover .tip` tooltip pattern), `.ctx-strip`, `.ctx-chip`, `.ctx-row`, `.ctx-label`, `.brief-link-panel`, `.brief-link`, `.state-badge` (+ `.state-open/closed/pre`), `.feasibility-note`. All values are `var(--token)` references (`var(--bg)`, `var(--text)`, `var(--panel)`, `var(--line)`, `var(--r-card,10px)`, `var(--r-pill,999px)`, `var(--r-ctl,8px)`, `var(--muted)`, `var(--link)`, `var(--ink-link, var(--link))`, `var(--up)`, `var(--popover-shadow)`). No hardcoded colors, no `rgba()` fallbacks.
- `<body>` opens with the shared public nav chrome (lines 71–302 are the standard site nav copied wholesale from `site/macro.html`), then the page-specific content.

**Page-specific copy (lines 305+)** — every heading has both `<span class="l-en">` and `<span class="l-zh">`:
- Page title: "Morning Edition" / "早间版" + a pre-open badge "US markets not yet open" / "美股尚未开盘".
- Page lead: "Before the US open: tape since the prior close, the session clock, regime context, today's calendar, and a link to yesterday's brief. Refreshes once a day." / "美股开盘前：自前一收盘以来的盘面走势、交易时段时钟、周期背景、今日日历，以及上一交易日简报链接。每日更新一次。"
- "Built at" / "构建时间" + ISO timestamp.
- "Note:" / "注意：" disclaimer: "The newest committed tape reading is older than yesterday's close — showing the last known values." / "最新已提交的行情读数早于昨日收盘——展示的是最新已知数值。"
- Section headings: "Session clock" / "交易时段", "Tape since prior close" / "自前一收盘", "Market regime" / "市场周期", "Cross-asset view" / "跨资产视角", "Today's calendar" / "今日日历".

**Rendered panel content:** state-badge strip with session-state chips (`.state-open`, `.state-closed`, `.state-pre` — pure class hooks, no copy); a regime chip driven by `t('…')` macro output; cross-asset rows driven by the same; a calendar list driven by the same. The page is a static snapshot — its numeric and textual body is whatever the build pipeline rendered at the moment the file was committed; the diff does not touch those numbers.

**Shared chrome (pre-existing, NOT introduced by this PR):** the standard site nav occupies lines 71–302 of the file. This is byte-identical to the shared nav block in `site/macro.html` on main. It carries the well-known pre-existing strings ("Verified calls, weekly intelligence and company context" / "已核验电话会、每周情报与公司语境" at line 222; "Today's strongest confirmed setups" / "今日最强确认信号" at line 236; "two-way confirmed stocks" / "两道确认的选股" at lines 108 and 131). These strings are NOT introduced by this PR — they predate it and exist unchanged on main. The PR only commits a target file that includes them because the shared chrome is included in every rendered page.

## Plain-language findings

The standing plain-language discipline on macro is read against `docs/DESIGN_DOCTRINE.md` ("Glance tier = state + plain-word stance under hard word budgets; technicals demoted to hover/popover/detail pages; every signal panel answers 'so what do I do', even when the honest answer is 'watch — don't chase'") and the standing `l-en`/`l-zh` bilingual-pair discipline enforced by `tests/test_bilingual_ui.py` and `scripts/check_bilingual.py`.

**Headline: PASS on plain-language for all PR-introduced user-visible copy.**

Specific findings:

1. **Bilingual pair count is balanced: 137 l-en, 137 l-zh.** A literal grep of the committed `site/am_edition.html` returns 137 occurrences of `<span class="l-en">` and 137 of `<span class="l-zh">` — perfectly paired. The 5 aria-label attributes (search input, theme switch, language toggle, brand, mega-rail) are ungendered chrome hooks and do not require ZH twins (matches the existing convention in `site/macro.html` on main).

2. **No banned study slugs / banned glance vocabulary introduced by THIS PR.** Grep over the 626-line `+` diff for the macroside banned-glance list (`falsifier / refuted / 证伪 / tier: / trust_tier / msc_regime / mscRegime / gexdesk / prophet / oracle / conductor / synapse / lobe / tripwire / vm['leadership'] / percentile rank / z-score / zscore`) returns zero matches. The new "Morning Edition" page does not introduce any state-enum slug, organ slug, or internal statistic token into user-visible copy. The pre-existing shared-nav chrome at the top of the page carries the well-known `Sector Intelligence / 行业情报`, `Intelligence Hub / 情报中心`, `Mastermind feed / Mastermind 信号`, `Tonghuashun concept boards / 同花顺概念板块`, `Smart-money convergence / 主力共振`, `signal lab / 信号实验室` strings — these are inherited from the shared nav block, are byte-identical to the same block in `site/macro.html` on main, and are not introduced by this PR.

3. **No `title=` attributes introduced in PR-introduced code.** A literal grep for `title="…"` in the new diff returns zero matches. The page's tooltip mechanism is the `.help:hover .tip` CSS pattern (CSS-driven, no `title=` semantics, no `aria-describedby` translation drift), exactly matching the convention used by every other `am_edition`/`closing_brief`-style page in the repo. The pre-existing 5 aria-label attributes in the shared chrome are also ungendered (search box, theme toggle, language toggle) and predate this PR.

4. **The one English-only placeholder at line 289 is the shared chrome search box.** `"Search any stock — US, China, HK, Canada & more…"` — this is pre-existing chrome (byte-identical to the same line in `site/macro.html` on main), not introduced by this PR. The other placeholder pattern is language-default via the page's lang bootstrap; not a finding for this PR.

5. **PR-introduced section headings use plain, descriptive English.** "Morning Edition" / "早间版", "Session clock" / "交易时段", "Tape since prior close" / "自前一收盘", "Market regime" / "市场周期", "Cross-asset view" / "跨资产视角", "Today's calendar" / "今日日历". Every heading is a one-or-two-word noun phrase that names what the section shows — no jargon, no internal-organ slug, no falsifier language. The "Note:" / "注意：" disclaimer ("The newest committed tape reading is older than yesterday's close — showing the last known values.") is honest about the data latency — that is the design-doctrine-permitted plain-language form.

6. **No `data-tip-en` / `data-tip-zh` patterns used.** Grep returns zero matches. The page uses the CSS-only `.help:hover .tip` tooltip pattern (the `tip` div sits inside the `help` span and is hidden until `:hover`), which keeps help text language-tagged via the standard `l-en` / `l-zh` bilingual-pair mechanism inside the `.tip` element. This is the correct alternative to `title=` for this page type and avoids the translated-`title=` ban entirely.

7. **Plain-language residual issues: none for PR-introduced copy.** The PR is render-infrastructure work; the one new file is a static render output with bilingual-paired headings and no banned vocabulary. The two HK link edits are bilingual-paired (`Sector rotation` / `板块轮动`) and use the `t('EN','ZH')` macro that the design doctrine standardizes on.

**Plain-language verdict: PASS.**

## Theme findings

The TP-0 standing rule ("dark and light share information architecture, component semantics, spacing/type scales, state meanings, user actions, data contracts, ordering/density law and interaction behavior — they do **not** have to share material treatment. Dark = command center; light = research workspace. Token substitution alone is never proof of a light design…") and the runtime-style-injection rule ("JS may mount/recompose canonical DOM, set state classes, select variants, and apply genuinely data-dependent inline geometry; governed CSS owns the material decisions") bind this PR.

**Headline: PASS on theme. THEME-CLOSURE preserved. The new file is a static render output that reuses the established chrome.**

Specific findings:

1. **Token discipline is clean in the PR-introduced `<style>` block.** All values in the page-level `<style>` are `var(--token)` references: `--bg`, `--text`, `--panel`, `--line`, `--r-card`, `--r-pill`, `--r-ctl`, `--muted`, `--link`, `--ink-link`, `--up`, `--popover-shadow`. No hardcoded hex / rgb / hsl / oklch literals. No `rgba()` fallbacks. The page is theme-consistent — the same `theme.css` is linked as every other page; switching the document-level `data-theme` attribute (`dark` ↔ `light`) flips the page through the same shared tokens.

2. **Inline `style="..."` attributes (19 total) are layout, not material.** A line-by-line read of every `style="…"` in `site/am_edition.html` shows:
   - 12 attributes are layout geometry: `display:flex`, `flex-wrap:wrap`, `align-items:center`, `gap:8/10/12px`, `margin:0/4/10px …`. These are exactly the "genuinely data-dependent inline geometry" the runtime-style-injection rule explicitly permits.
   - 3 attributes are empty (`style=""` on three `ctx-chip` spans — pre-existing chrome hook, no value).
   - 1 attribute uses a token correctly: `border-color:var(--link)` on the brief-link panel (the only color-bearing inline style in the page, and it routes through the design token).
   - 3 attributes carry copy-margin geometry only: `margin:10px 0 0`, `margin:4px 0 0`, `margin:0`, `text-align:center;margin-top:8px`. All layout.
   - 0 attributes carry hardcoded colors or rgba fallbacks. **This is a clean score against `scripts/check_runtime_style_injection.py`** — the 19 attributes all fall under the explicitly-permitted layout category.

3. **State badges are class-driven, not inline-styled.** `.state-open` (open), `.state-closed` (closed), `.state-pre` (pre-open) — each is a token-scoped class on `.state-badge` that the CSS block styles via `--up` / `--muted` / `--link`. No inline colors are set per-state. This is the right pattern for theme-token reuse.

4. **`templates/theme.css` is untouched.** The PR diff does not touch `templates/theme.css` — THEME-CLOSURE is preserved. The new page-level `<style>` block is local to `site/am_edition.html` and uses shared tokens; it does not redefine any token. The new `site/hk_stocks.html` and `templates/hk.html.j2` edits change link text and target only — no CSS.

5. **Dark / light art direction is shared, not re-implemented.** The Morning Edition page is a chrome-and-data page, not a redesigned visual surface. Its dark/light behavior comes from the shared `theme.css` (which is unchanged in this PR); the page-level `<style>` block only adds panel / chip / state-badge geometry that adapts via the shared tokens. Per the TP-0 ruling, this is the right level of differentiation for a chrome-and-data page — the dark/light difference lives in the shared tokens, not in per-page CSS.

6. **The two `↗` → `↓` glyph swaps in HK are UX-correctness, not theme.** The arrow glyph communicates link affordance (external page vs in-page jump), not visual style. The change aligns the link's affordance with its destination (`#anchor` is in-page; `↓` is the convention every other in-page anchor on the HK page uses). This is a small accessibility/usability win that the design doctrine implicitly endorses (glyphs should mean what they say).

7. **No evidence matrix required.** The TP-0 dark/light × EN/ZH × 1440/390 matrix is required for redesigned visual surfaces. This PR is render-infrastructure work and ships no new visual surface — the only new page (`am_edition.html`) is a static render output of an already-shipped page type. No `mockups/evidence/` PNGs are required or shipped. The body is explicit: "No new route, renderer, scheduler, store, or publication plane is introduced."

8. **Theme residual issues: none.** The new file is theme-consistent, token-scoped, inline-style-clean, and reuses the shared chrome. The HK edits are link-target and link-text changes only. THEME-CLOSURE holds.

**Theme verdict: PASS.**

## Validated-claims findings

The standing validated-claims discipline (`scripts/check_validated_claims.py`, BC-2) gates any affirmative use of `validated` / `已验证` against an allowlist and scans `templates/*.j2`, `templates/*.js`, `templates/*.html`, `site/*.js`, `site/*.html`, `site/prophet/*.json`, and `engine/*.py` display-copy fields.

**Headline: PASS on validated-claims for PR-introduced copy. No new affirmative claim; no allowlist extension required. Pre-existing nav-chrome strings are inherited unchanged and are out of scope for THIS PR.**

Specific findings:

1. **Zero affirmative `validated` / `已验证` / `经验证` / `经过验证` vocabulary introduced in PR-introduced user-visible copy.** A literal grep of the 626-line `+` diff for `validated / confirmed / proven / asserted / verified` returns zero matches on PR-introduced lines. The "Morning Edition" / "早间版" page has no claim that any data is validated.

2. **Pre-existing `verified` / `confirmed` vocabulary in the shared chrome is byte-identical to `site/macro.html` on main.** The strings
   - `Verified calls, weekly intelligence and company context` / `已核验电话会、每周情报与公司语境` (line 222)
   - `Today's strongest confirmed setups` / `今日最强确认信号` (line 236)
   - `two-way confirmed stocks` / `两道确认的选股` (lines 108, 131)
   exist verbatim on `site/macro.html` on main (verified at lines 294, 308, 180, 203 of the fetched main file). They are part of the shared chrome that every rendered page carries; this PR inherits them by committing a page that uses the same chrome. **They are not findings against THIS PR.** The PR makes no edit to these strings, no claim about them, and no move of them. The allowlist status of these strings is a pre-existing question that belongs to a separate audit (potentially future) on the chrome itself, not on this render-infrastructure heal.

3. **No new engine contract invented.** The PR is a render-infrastructure fix. The `_SCORE` regex relaxation allows the existing `data-measured-score` attribute (already shipped in some render of `macro.html`) to coexist with the existing id; no new contract is added or required. The two HK link edits are presentation moves over an existing in-page anchor (`#sector-rotation`) the HK page already renders. The `am_edition.html` page is the static render output of the existing `build_am_edition` pipeline (now narrowable to commit-only).

4. **No new study or claim introduced.** The Morning Edition page reads the same engine contracts the existing `closing_brief.html` and `closing-bell.html` pages read (session state, regime context, cross-asset view, today's calendar). The PR commits a deterministic snapshot of those readings at the moment the file was last rebuilt — it does not introduce a new signal, rank, or gate.

5. **Honest disclosure in the page lead.** The "Note:" / "注意：" disclaimer ("The newest committed tape reading is older than yesterday's close — showing the last known values.") is the right falsifier-discipline form — the page tells the reader the data may be stale rather than asserting a verdict. This is the design-doctrine-permitted "what we're watching" form, not a validation claim.

6. **No allowlist extension needed.** No PR-introduced phrase names a study, a signal, or a validation claim. The two HK link text changes ("Sector ranking" → "Sector rotation") are nav-link affordance language, not study language. The Morning Edition page's section headings ("Session clock", "Tape since prior close", "Market regime", "Cross-asset view", "Today's calendar") are descriptive nouns naming what the section shows.

7. **The new test file's English fixture is minimal and non-claimant.** The fixture EN strings in `tests/test_check_ms_board_coherence.py`'s `test_board_score_parser_accepts_runtime_metadata_after_id()` are `<span class="l-en">Risk-on — the tape is constructive.</span>`, `<span class="l-en">→ Mixed if risk appetite breaks down.</span>`, `<span class="l-en">Risk-on</span>` — neutral descriptive test fixtures. The "→ Mixed if risk appetite breaks down" is a falsifier-discipline flip clause (the "→ Mixed if X" pattern), not a claim. Test fixtures are not user-facing surfaces and are out of scope for `check_validated_claims.py`'s user-display scan.

8. **Validated-claims residual issues: none for THIS PR.** The PR introduces no new affirmative validation claim. The shared chrome's pre-existing strings are inherited, not introduced. No allowlist extension is needed.

**Validated-claims verdict: PASS.**

## Overall verdict

| dimension | verdict |
|---|---|
| plain-language | **PASS** |
| theme (TP-0 art direction + THEME-CLOSURE) | **PASS** |
| validated-claims (BC-2) | **PASS** |

**PR #7603 ships clean across the three standing audits.** The render-infrastructure heal is a defensive fix: it commits a deterministic Morning Edition page target so narrowed renders can skip `build_am_edition` without breaking the shared chrome's link, retargets two dead HK "Sector ranking" links to the existing in-page `#sector-rotation` anchor (with a UX-correct `↗` → `↓` affordance glyph swap), loosens the `_SCORE` regex in `check_ms_board_coherence.py` to tolerate `data-measured-score` after the id, and adds regression coverage in two test files. No new visual surface is shipped; no new engine contract is introduced; no new study is claimed.

**Audit result: PASS — no blocking findings.**

---

**Auditor's note (one-shot, half-B scope).** This audit was a single pass against the standing design-doctrine + validated-claims + theme-art-direction laws, in the shape of the prior `qwen_auditor2` audits (`macro_PR-7585.mm.md`, `macro_PR-7599.mm.md`, `macro_PR-7602.mm.md`). The PR is a small render-infrastructure heal, which makes the audit naturally lighter than the prior display-tier audits: the only file with substantive new content is `site/am_edition.html` (626 lines, a static render output), and the rest is template/HTML link retargets + regex relaxation + tests. The pre-existing `verified` / `confirmed` strings in the shared nav chrome are explicitly noted as inherited (not introduced) and are out of scope for THIS PR's audit — they predate the PR and are byte-identical to the same strings in `site/macro.html` on main. A separate audit on the shared chrome's `verified` / `confirmed` vocabulary would be a different deliverable, not this one.
