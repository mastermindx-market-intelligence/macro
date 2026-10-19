# Plain-language / theme / validated-claims audit — macro PR #7600

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-21.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7600 |
| title | `fix(alt-data): make related-news access and recovery truthful` |
| merged | 2026-09-21T14:01:46Z via squash-merge to `main`. Selected as the most-recent non-audit half-B PR in the 24-h window that has not already been audited: cross-referencing `gh pr list --state merged --merged recent` against `git ls-tree origin/main -- orch/audits/` shows the prior 24-h merges #7607, #7608, #7603, #7602, #7599, #7589, #7585, #7573, #7571, #7568, #7539, #7535, #7534 already carry an audit on `origin/main` (`macro_PR-7607.mm.md` → `53732c31`, `macro_PR-7608.mm.md` → `c342bb71`, etc.). The post-#7600 merges #7619/#7613/#7612/#7621/#7627 are all either `orch(audit)` records, CI heals, or a CI fingerprint bind (none carry a user-facing template/theme/lens surface to audit). #7600 is the most-recent unaudited half-B PR in the 24-h window with a real user-facing template + theme-lens surface. |
| files | **5 source-code paths + 73 evidence/research files.** Source files: `templates/alt_data.html.j2` (+14 / −20 lines in the newsh-wrapper + JS rewrite, mostly +111 JS body and −41 JS body, plus +14 CSS rules and 1 line of section-note copy), `site/alt_data.html` (rendered twin of the template edit + CSS link swap `7d4fc68b.css` → `41a985eb.css`), `site/assets/css/41a985eb.css` (NEW, +127 lines, a new shared stylesheet for the alt-data chrome), `tests/test_altdata_price_truth.py` (+135 / −3 lines, 13 added test cases), `agentos/discoveries/DSC-ALTDATA-NEWS-ACCESS-STATES-20260921.md` (NEW, 30-line landmine discovery). Evidence/research files (73 paths in `mockups/evidence/uiux-altdata-news-20260921/` and `research/evidence/uiux-altdata-news-20260921/`) are PNG screenshots, JSON manifests, and gate receipts — content-addressed, not source. |
| half-B label | **half-B user-facing UIUX repair (Alt Data related-news panel).** Body is explicit: "Fix the Alternative Data related-news panel so inaccessible or failed requests are not described as an unbuilt feature or an absence of news. This is one grouped Web Chat UIUX repair." Real browser proof: "8 native browser cases: desktop/mobile × EN/ZH × dark/light, actual Settings, keyboard/touch retry and deliberately delayed success"; "24 canonical visual states across desktop/tablet/mobile, both languages/themes and rest/retry focus; every image digest verified." |
| scope | (a) Separate 401 sign-in, 403 restricted, unavailable/malformed response, successful-empty snapshot, related-headline, and market-fallback states on the alt-data page's `#sid-news` panel; (b) never claim "no related news" when its data request failed or requires access; (c) provide a native **Try again** button for failures and **Open News** link for navigation; (d) keep keyboard focus through delayed retry; repeated activation cannot duplicate the request batch (single-flight); when Retry disappears while it owns focus, focus moves to Open News rather than the page body; (e) use available Chinese titles and localized state messages on the existing document `langchange` event without refetching; (f) escape source text and render only HTTP(S) source links as links (reject `javascript:` URLs); (g) remove redundant raw signal scores and unsupported overlap interpretation from this secondary panel; (h) add static page-scoped styling using existing tokens and pair the generated HTML with the canonical inherited stylesheet `41a985eb.css`. |
| durable owner | None new. The alt-data page's existing conviction board and price-truth panels are unchanged. The repaired news panel lives on `templates/alt_data.html.j2`/`site/alt_data.html` + the new shared stylesheet `site/assets/css/41a985eb.css`. |
| checks | Body reports: **83 passed** in the existing Alt Data price-truth/intelligence/hygiene + product-chrome suites (13 of those are added cases in `tests/test_altdata_price_truth.py`); 12 executable page-script cases that fail on the original source (negative tests for 401/403/404/503/network/JSON/schema failures, genuine empty data, truthful fallback, escaping, language-without-fetching, duplicate-retry prevention); **8 native browser cases** desktop/mobile × EN/ZH × dark/light with real Settings, keyboard/touch retry, and deliberately delayed success; **24 canonical visual states** across desktop/tablet/mobile × EN/ZH × dark/light × rest/retry focus, every image digest verified; Visual/design/runtime-style gates pass; Agent OS validation reports zero errors. Body explicitly notes "Fixtures are explicitly simulated responses and illustrative headlines — not authenticated production proof." |
| evidence matrix | Body cites the 24-cell dark/light × EN/ZH × desktop/tablet/mobile × rest/retry-focus matrix as evidence shipped WITH the PR (in `mockups/evidence/uiux-altdata-news-20260921/`). The TP-0 dark/light × EN/ZH × 1440/390 matrix is satisfied by the body's claim, with extra dimensions (tablet and focus state) added. |
| gating scripts | `scripts/check_plain_language.mjs` — **DOES NOT EXIST** in macro (terminal-side only); macroside discipline is read against the design-doctrine banned-glance vocabulary + the standing `l-en`/`l-zh` bilingual-pair discipline enforced by `tests/test_bilingual_ui.py` and `scripts/check_bilingual.py`. `scripts/check_validated_claims.py` — exists; the new template content uses `aria-busy`/`aria-atomic`/`role="status"` (CSS-state hooks) and bilingual-paired state messages — no new affirmative `validated` vocabulary in PR-introduced copy; the PR actually REMOVES the false "News surface not built yet — runs on the next daily build." claim. `scripts/check_design_system.py` — out of scope (no design-system surface touched; the new CSS file lives under `site/assets/css/`, not `templates/`). `scripts/check_runtime_style_injection.py` — read against the inline `style="..."` attributes in the rendered page. |

## Diff content (scoped to this audit)

The PR's five source-code diffs are summarised below at the level the three audits need.

### `templates/alt_data.html.j2` (+CSS +14, JS +111 / −41, markup +14)

**Markup change.** The `News on these names` section heading on the alt-data page (lines 514–518 in the template) gets a new bilingual heading-note replacing the old demand/supply framing:
```diff
- <span class="h-note"><span class="l-en">the demand-side tape beside the supply-side signal — context only, never blended</span>
-   <span class="l-zh">需求侧舆情与供给侧信号并列——仅供参考，绝不混合</span></span></h2>
- <div id="sid-news" class="sid-card"><p class="mut" style="font-size:12px">
-   <span class="l-en">Loading…</span><span class="l-zh">加载中…</span></p></div>
+ <span class="h-note"><span class="l-en">Related headlines · research context</span>
+   <span class="l-zh">相关标题 · 研究背景</span></span></h2>
+ <div id="sid-news" class="sid-card" aria-busy="true">
+   <p id="sid-news-status" role="status" aria-atomic="true" class="sid-news-status">
+     <span class="l-en">Loading related news…</span><span class="l-zh">正在加载相关新闻…</span></p>
+   <div id="sid-news-results" hidden></div>
+   <div class="sid-news-actions">
+     <button id="sid-news-retry" type="button" aria-disabled="false" hidden>
+       <span class="l-en">Try again</span><span class="l-zh">重试</span></button>
+     <a id="sid-news-open" href="news.html">
+       <span class="l-en">Open News</span><span class="l-zh">打开新闻页</span></a>
+   </div>
+ </div>
```
The old markup was a single `<p>` whose contents were wholesale-overwritten by JS (`mount.innerHTML = ...`). The new markup is a structured DOM: a status paragraph (`#sid-news-status`, `role="status"`, `aria-atomic="true"`), a results container (`#sid-news-results`), and a persistent actions row (Retry + Open News). The new structure separates state from content — JS swaps `textContent` on `#sid-news-status` rather than rewriting the whole card. `aria-busy="true"` is the initial state; JS flips it to `"false"` after settle. The heading-note swap is a plain-language improvement: "the demand-side tape beside the supply-side signal — context only, never blended" (jargon) → "Related headlines · research context" (plain noun phrase).

**CSS change.** A new block of page-scoped styles appended to the existing `{% block base_css %}` (lines 119–132 in the new template):
```css
.sid-news-row{padding:8px 0;border-top:1px solid var(--line)}
.sid-news-headlines{font-size:12px;margin-top:3px;line-height:1.5;overflow-wrap:anywhere}
.sid-news-title{color:var(--ink-link,var(--link));text-decoration:none}
.sid-news-title:hover{text-decoration:underline}
.sid-news-meta{color:var(--muted);font-size:11px}
.sid-news-status{font-size:12px;color:var(--muted);margin:0 0 10px}
.sid-news-actions{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:10px}
.sid-news-actions button,.sid-news-actions a{min-height:40px;display:inline-flex;align-items:center;touch-action:manipulation}
.sid-news-actions button{font:inherit;color:var(--text);background:var(--panel2);border:1px solid var(--line);border-radius:var(--r-sm);padding:5px 12px;cursor:pointer}
.sid-news-actions button[aria-disabled="true"]{opacity:.6;cursor:wait}
.sid-news-actions :focus-visible,.sid-news-title:focus-visible{outline:2px solid var(--ink-link,var(--link));outline-offset:2px}
#sid-news [hidden]{display:none!important}
```
All values are `var(--token)` references (`var(--line)`, `var(--muted)`, `var(--text)`, `var(--link)`, `var(--ink-link, var(--link))`, `var(--panel2)`, `var(--r-sm)`). The 40px min-height and `touch-action:manipulation` on the action row are mobile-tap-target discipline. `:focus-visible` outlines are token-routed. `aria-disabled="true"` styling is the design-doctrine-permitted busy state (semantic state, not disabled-bool — the body notes "native disabled was proven to blur the button"; `aria-disabled` keeps focus and a single-flight guard without blurring).

**JS change.** The 60-line old block (a single `Promise.all` + `hl()` helper + per-row `mount.innerHTML = '<div style="..." class="...">...'` composition with raw rgba-bordered rows, raw `signal_score` exposure, and three unhandled error branches) is replaced with a 100-line stateful controller. Key elements:
- **State table** — a 9-key `messages` dictionary, each key carrying an `[en, zh]` pair:
  - `loading` → `'Loading related news…'` / `'正在加载相关新闻…'`
  - `related` → `'Recent headlines for these names.'` / `'这些标的的近期新闻。'`
  - `market` → `'No related headlines in this snapshot. Showing market news.'` / `'当前快照中没有相关标题，以下为市场新闻。'`
  - `market_gate` → `'Sign in for related headlines. Showing market news.'` / `'登录后可查看相关标题，以下为市场新闻。'`
  - `market_unavailable` → `'Related headlines are unavailable. Showing market news.'` / `'相关新闻暂时不可用，以下为市场新闻。'`
  - `gated` → `'Sign in to read news for these names.'` / `'登录后可查看这些标的的新闻。'`
  - `restricted` → `'Access to this news is restricted.'` / `'这些新闻的访问受到限制。'`
  - `market_restricted` → `'Related news access is restricted. Showing market news.'` / `'相关新闻的访问受到限制，以下为市场新闻。'`
  - `unavailable` → `'News is unavailable right now. Try again.'` / `'新闻暂时无法加载，请重试。'`
  - `empty` → `'No headlines in this snapshot.'` / `'当前快照中没有新闻标题。'`
- **`read(url, valid)`** — a fetch wrapper that classifies responses: `r.status === 401` → `{kind:'gated'}`; `r.status === 403` → `{kind:'restricted'}`; `!r.ok` (404, 503, etc.) → `{kind:'unavailable'}`; valid JSON passing `valid(data)` → `{kind:'ready', data}`; invalid JSON or schema-violating JSON → `{kind:'unavailable'}`; network errors → `{kind:'unavailable'}`. The classifier is the heart of the fix: 401 and 403 never reach the "no headlines" path.
- **`localize()`** — reads `document.documentElement.getAttribute('data-lang')` and writes the matching string into `#sid-news-status`'s `textContent`. Wired to a `document.addEventListener('langchange', localize)` so a language toggle updates the status without refetching.
- **`headline(h)`** — escape full-coverage (`&<>"'`), URL safety check via `new URL(url, window.location.href)` + `^https?:$` protocol test (rejects `javascript:` and other non-HTTP(S) schemes), and emits an `<a class="sid-news-title">` only when the URL is safe (otherwise emits a `<span>` so the title still renders).
- **`setView(kind, html, canRetry)`** — sets state, mounts the HTML, hides/shows Retry. **Captures `document.activeElement === retry` BEFORE mounting; if retry then vanishes, focus moves to Open News, not the page body.** This is the keyboard-focus invariant the body promises.
- **Single-flight retry** — `busy` flag prevents duplicate request batches from rapid repeated activations; `aria-disabled="false"` is the standing state (visible-style focus retention) with the busy check internally guarding new requests.

The new JS body does **not** use `mount.innerHTML = '<div style="...">...'` patterns. The old code rendered each row with inline `style="padding:8px 0;border-top:1px solid rgba(128,128,128,.15); ..."` (3-4 inline-style declarations per row, hardcoded gray rgba border); the new code composes rows via class-driven `.sid-news-row` + `.sid-news-headlines` + `.sid-news-title` + `.sid-news-meta` CSS. **This is a runtime-style-injection improvement**: the JS no longer authors hardcoded color literals in inline style attributes.

### `site/alt_data.html` (rendered twin + CSS link swap)

The committed render output carries the same DOM + state table + CSS classes as the template. One CSS link swap:
```diff
-<link rel="stylesheet" href="assets/css/7d4fc68b.css?v=7d4fc68b">
+<link rel="stylesheet" href="assets/css/41a985eb.css?v=41a985eb">
```
The old fingerprint `7d4fc68b` is replaced by the new `41a985eb` — the body says "pair the generated HTML with canonical inherited stylesheet `41a985eb.css`". Both filenames are content-addressed (the `?v=` is the content hash) — the swap means the old stylesheet is no longer referenced and the new one is now in use. The old CSS file `7d4fc68b.css` is presumably still on disk (the render pipeline doesn't delete unreferenced assets in this PR) but is no longer served.

### `site/assets/css/41a985eb.css` (NEW, 127 lines)

A new shared stylesheet for the alt-data chrome. Header section declares the shared chrome for the Research-Reports-style alt-data page (body / `.wrap` / `.r-pos` / `.r-neg` / `.mut` / `.chip` / tag-chip variants / `.sid` / `.sid-eyebrow` / `.sid h1` / `.sid-sub` / `.sid-meta` / `.sid-stats` / `.sid-stat` / `.sid-regime` / `.sid-sec` / `.sid-card` / `.conv-list` / `.conv-row` / `.conv-score` / `.conv-main` / `.conv-chips` / `.pill` / `.conv-thesis` / `.conv-actors` / `.conv-so` / `table.sid-t` / `.num` / `.tkc` / `.sid-grid` / `.kind-row` / `.kind-grp` / `.repoint` / `details.sid-more` / `.feedlink` / `.sid-cov` / `.cov`).

Token discipline observations:
- **Token-scoped values dominate**: `var(--bg)`, `var(--text)`, `var(--muted)`, `var(--line)`, `var(--panel)`, `var(--panel2)`, `var(--info)`, `var(--ink-info, var(--info))`, `var(--warn)`, `var(--ink-warn, var(--warn))`, `var(--up)`, `var(--ink-up, var(--up))`, `var(--down)`, `var(--ink-down, var(--down))`, `var(--r-sm)`, `var(--r-pill, 999px)`, `var(--font-mono, ui-monospace, "SF Mono", ...)`.
- **One pair of unambiguous move colors** (`.r-neg`, `.r-pos`) — light/dark aware via `html[data-theme="dark"]` overrides:
  ```css
  .r-neg { color:#d23f3f; font-weight:600; }   /* light */
  .r-pos { color:#1f9a55; font-weight:600; }   /* light */
  html[data-theme="dark"] .r-neg { color:#ef6a6a; }
  html[data-theme="dark"] .r-pos { color:#3fc07e; }
  ```
  The body explicitly notes "unambiguous move colours (NOT tied to the zh red=up swap)". Per the standing rule that move/change indicators must be **unambiguous across cultures and themes**, the light/dark pair with explicit dark-overrides is the correct pattern. The CSS module gives both themes a distinct visual treatment (light = darker, deeper red/green for daylight readability; dark = softer, more luminous red/green on the dark command-center surface) — exactly the TP-0 art-direction standard.
- **Tag-chip colors** (`.chip.tag-macro` etc.) — each tag carries a hardcoded color literal (`#5b8def` for macro, `#c77dff` for fed, `#3fb6c0` for rates, `#46b87a` for equities, `#e0973a` for crypto, `#cf7b3a` for energy, `#e0607a` for event, `#b48ead` for AI, `#d0554f` for china, `#d08770` for credit) with a same-color 0x55-alpha border. **These are pre-existing in the alt-data page's tag vocabulary** — they are domain-specific brand colors, not theme tokens. They do not flip with `data-theme` because they are category identifiers, not state indicators. (The pill-action states — `.pill.act-ACCUMULATE`, `.pill.act-AVOID`, `.pill.act-WATCH` — DO use `var(--ink-up, var(--up))` / `var(--ink-down, var(--down))` / `var(--ink-info, var(--info))` tokens with `color-mix` transparency, because those are state indicators that must adapt to theme.)
- **`.pill.src-brain { color:#c77dff; border-color:#c77dff66; }`** — a single hardcoded purple for the Brain-source tag, mirroring the existing tag-chip pattern. Same justification as the other tag colors.

### `tests/test_altdata_price_truth.py` (+135, −3)

13 new test cases (12 page-script executable cases + 1 template-parity case). All are negative or behavior-coverage tests — they pin the post-fix behavior and confirm the original source fails them.

1. `_news_client_result(tmp_path, scenario, actions=None)` — extracts the page-script block from `templates/alt_data.html.j2`, runs it in `node:vm` against a fixture-driven mock fetch and DOM, and returns the resulting state (initial render + post-action state). The harness consumes both the old and the new script (the body notes "same harness consumes old and repaired scripts; before source is expected to fail").
2. `@pytest.mark.parametrize("code", [401, 403]) test_altdata_news_signin_is_not_missing_feature(tmp_path, code)` — 401 → state `gated`, status contains "Sign in"; 403 → state `restricted`, status contains "restricted"; in both cases "next daily build" is absent from the rendered HTML and Retry is hidden.
3. `@pytest.mark.parametrize("failure", [{...}]) test_altdata_news_failure_is_not_no_headlines(tmp_path, failure)` — 503/404/network-error/invalid-JSON/data-not-object all → state `unavailable`, Retry is visible, status contains "unavailable", and "not built" is absent from the rendered HTML.
4. `test_altdata_news_successfully_empty_snapshot(tmp_path)` — three successful empty responses → state `empty`, status "No headlines in this snapshot", Retry hidden. Distinguishes a successful empty snapshot from a network failure.
5. `test_altdata_market_fallback_does_not_claim_no_related_news_on_401(tmp_path)` — 401 + 401 + market-data-200 → state `market_gate`, status contains "登录" (the test toggles `lang=zh` via the harness's `actions: ["language"]`), HTML contains the market headline AND does NOT contain "No news yet", and the call count is exactly 3 (translation did NOT refetch).
6. `test_altdata_news_related_headlines_keep_chinese_order_and_escape_markup(tmp_path)` — fixture includes `<script>bad</script>` and `javascript:alert(1)` URLs. Asserts: state `related`; Chinese order preserved (BBB before AAA); `中文标题` is present; `&lt;script&gt;` is present (escaped); raw `<script>` is absent; `href="javascript:` is absent (rejected URL scheme); `"alt signal"` is absent (the raw-score leak the PR removes).
7. `test_altdata_news_retry_is_single_flight_and_restores_focus(tmp_path)` — first attempt 503×3 (triggers Retry), second attempt 200×3 (success). Asserts: initial state has Retry visible; total `fetch` calls = 6 (three per attempt, NOT six on a single click — proves single-flight); `aria-busy` flips back to `"false"` after settle; post-success focus is on `#sid-news-open` (not on the body — Retry vanished and focus moved); Retry is now hidden.

   The harness deliberately calls the click handler twice in the retry action to prove the second click is a no-op: the workflow is "rapid repeated activation cannot duplicate the request batch" (the body phrase). The handler's busy-guard makes the second click return without firing `fetch` again.
8. `test_altdata_news_template_preserves_native_loading_and_actions` — template-string assertions: `#sid-news-status role="status"` present; `#sid-news-retry type="button"` present; `document.addEventListener('langchange',localize)` present; the old "News surface not built yet" copy is **absent**.
9. `test_altdata_news_generated_source_parity` — the script block in `templates/alt_data.html.j2` is byte-identical to the corresponding script block in the rendered `site/alt_data.html`. Pins the plain-copy pair law (the body says "Template/generated client and inherited CSS bytes are checked for parity").

**Test discipline observations:**
- The tests run the actual template-authored script in `node:vm` — they do not mock the script. This means the tests break if the JS state machine is broken (regression-coverage strength).
- Negative fixtures cover the failure surface explicitly: 503, 404, network error, invalid JSON, data-not-object, success-but-empty. The pre-fix code conflated all of these into "no news" → false-claim.
- The dual-script harness ("same harness consumes old and repaired scripts; before source is expected to fail") is the design-doctrine-permitted falsifier discipline: the test pins the fix by failing on the prior state.

### `agentos/discoveries/DSC-ALTDATA-NEWS-ACCESS-STATES-20260921.md` (NEW, 30 lines)

A landmine discovery record. Frontmatter declares: `key: ALTDATA-NEWS-ACCESS-STATES-20260921`, `kind: landmine`, `confidence: verified`, `verified_by: 'python3 -m pytest tests/test_altdata_price_truth.py -q'`. The body of the record restates the claim, the falsifier (read anonymous and see the sign-in state), and the so-what (separate access/transport/successful-empty states; native retry focus with `aria-disabled` + in-flight guard). Scope is bound to `templates/alt_data.html.j2`, `site/alt_data.html`, `tests/test_altdata_price_truth.py`. Post-claim prose explicitly disclaims: "The bounded candidate does not widen access, change source data, rank names, or add polling/automatic retries. Its local fixture results are not authenticated production proof. Existing News PR #7591 remains a separate held writer; this discovery does not transfer its source custody." Honest disclosure on every dimension.

## Plain-language findings

The standing plain-language discipline on macro is read against `docs/DESIGN_DOCTRINE.md` ("Glance tier = state + plain-word stance under hard word budgets; technicals demoted to hover/popover/detail pages; every signal panel answers 'so what do I do', even when the honest answer is 'watch — don't chase'") and the standing `l-en`/`l-zh` bilingual-pair discipline enforced by `tests/test_bilingual_ui.py` and `scripts/check_bilingual.py`.

**Headline: PASS on plain-language. This is a plain-language IMPROVEMENT as well as a state-discipline fix.**

Specific findings:

1. **Bilingual pair count is balanced: 364 `l-en`, 364 `l-zh`.** A literal grep of the committed `site/alt_data.html` returns 364 `<span class="l-en">` and 364 `<span class="l-zh">` — perfectly paired. The 5 aria-label attributes in the shared chrome (search input, theme switch, language toggle, brand, mega-rail) are ungendered chrome hooks and do not require ZH twins. The new `#sid-news-status` and action row copy is fully bilingual-paired via the `messages` dictionary in JS, which selects the EN or ZH string on every state transition.

2. **No banned study slugs / banned glance vocabulary introduced by THIS PR.** Grep over the PR-introduced diff for the macroside banned-glance list (`falsifier / refuted / 证伪 / tier: / trust_tier / msc_regime / mscRegime / gexdesk / prophet / oracle / conductor / synapse / lobe / tripwire / vm['leadership'] / percentile rank / z-score / zscore`) returns **zero matches** in the PR-introduced lines. The new state messages use plain, descriptive English ("Sign in to read news", "News is unavailable right now", "No headlines in this snapshot") — no banned slugs.

3. **No `title=` attributes introduced in PR-introduced code. The new accessibility model uses `role="status"`, `aria-atomic`, `aria-busy`, and `aria-disabled`.** A literal grep for `title="…"` in the section/markup diff returns **zero matches**. The new `#sid-news-status` carries `role="status"` + `aria-atomic="true"` so screen-readers announce state transitions as a single coherent utterance (the existing convention used by every state-bearing region on the alt-data page). `#sid-news-retry` carries `aria-disabled="false"` initially; the JS flips it via `setAttribute('aria-disabled', 'true'|'false')` to keep semantic focus while the busy-guard prevents duplicate requests.

4. **The section heading note is plainly improved.** Old copy:
   - EN: "the demand-side tape beside the supply-side signal — context only, never blended"
   - ZH: "需求侧舆情与供给侧信号并列——仅供参考，绝不混合"

   This was jargon-heavy ("demand-side tape", "supply-side signal", "context only, never blended") and read as a domain-insider disclaimer rather than as a page description. New copy:
   - EN: "Related headlines · research context"
   - ZH: "相关标题 · 研究背景"

   Plain noun phrase naming what the section shows. **This is a plain-language WIN.** The section's relationship to the conviction board is established by the page-level structure (the conviction board is above, the news panel is below), not by an inline disclaimer that reads as apologetic.

5. **All 9 state messages are plain, honest, falsifier-discipline-respecting.** Sample:
   - `loading`: "Loading related news…" / "正在加载相关新闻…" — descriptive, no claim.
   - `related`: "Recent headlines for these names." / "这些标的的近期新闻。" — descriptive noun phrase.
   - `market`: "No related headlines in this snapshot. Showing market news." / "当前快照中没有相关标题，以下为市场新闻。" — honest about empty + explicit about fallback. **This is the design-doctrine-permitted "what we're watching" form** — it says what we have, not what we don't.
   - `market_gate`: "Sign in for related headlines. Showing market news." / "登录后可查看相关标题，以下为市场新闻。" — honest about access + explicit about fallback. **No false "no news" claim.**
   - `market_unavailable`: "Related headlines are unavailable. Showing market news." / "相关新闻暂时不可用，以下为市场新闻。" — honest about transport + explicit about fallback.
   - `gated`: "Sign in to read news for these names." / "登录后可查看这些标的的新闻。" — honest about gating, actionable.
   - `restricted`: "Access to this news is restricted." / "这些新闻的访问受到限制。" — honest about restriction.
   - `market_restricted`: "Related news access is restricted. Showing market news." / "相关新闻的访问受到限制，以下为市场新闻。" — honest about restriction + explicit about fallback.
   - `unavailable`: "News is unavailable right now. Try again." / "新闻暂时无法加载，请重试。" — honest about transport + actionable.
   - `empty`: "No headlines in this snapshot." / "当前快照中没有新闻标题。" — honest about empty.

   Every state message is a short imperative-or-declarative English sentence with a plain ZH translation. None use jargon. None over-claim. None use the `falsifier / refuted / 证伪` banned vocabulary.

6. **Action-row copy is plain and actionable.** `Try again` / `重试` is a standard retry-button idiom. `Open News` / `打开新闻页` is a plain navigation link. Neither uses jargon, neither embeds a hidden promise.

7. **The old false claim is removed.** The pre-fix page asserted "News surface not built yet — runs on the next daily build." (EN) / "新闻层尚未生成——将在下次每日构建后出现。" (ZH) when in fact all three news reads had returned 401. This was a **plain-language FAIL**: it lied about why the page was empty. The PR removes both strings (the template no longer contains them, and the new test `test_altdata_news_template_preserves_native_loading_and_actions` asserts `"News surface not built yet" not in source`). This is the central defect the body fixes.

8. **Plain-language residual issues: none.** The PR is a state-discipline fix; the meaningful plain-language changes are the section-note rewrite (jargon → plain) and the new state-message dictionary (false claim → honest disclosure). Both are improvements.

**Plain-language verdict: PASS.**

## Theme findings

The TP-0 standing rule ("dark and light share information architecture, component semantics, spacing/type scales, state meanings, user actions, data contracts, ordering/density law and interaction behavior — they do **not** have to share material treatment. Dark = command center; light = research workspace. Token substitution alone is never proof of a light design…") and the runtime-style-injection rule ("JS may mount/recompose canonical DOM, set state classes, select variants, and apply genuinely data-dependent inline geometry; governed CSS owns the material decisions") bind this PR.

**Headline: PASS on theme. THEME-CLOSURE preserved. The PR improves runtime-style-injection discipline (inline-style → class-driven CSS) and adds one new shared stylesheet with proper light/dark token discipline.**

Specific findings:

1. **Token discipline is clean in the PR-introduced CSS.** The new `.sid-news-*` block in `templates/alt_data.html.j2` is entirely token-scoped: `var(--line)`, `var(--muted)`, `var(--text)`, `var(--link)`, `var(--ink-link, var(--link))`, `var(--panel2)`, `var(--r-sm)`. No hardcoded colors, no rgba fallbacks. The new shared stylesheet `41a985eb.css` uses tokens for state-bearing surfaces (`--bg`, `--text`, `--muted`, `--line`, `--panel`, `--panel2`, `--info` + `--ink-info`, `--warn` + `--ink-warn`, `--up` + `--ink-up`, `--down` + `--ink-down`, `--r-sm`, `--r-pill,999px`, `--font-mono,ui-monospace,...`).

2. **Inline `style="..."` attributes DROP, not rise, after this PR.** A count of inline `style="..."` in the rendered `site/alt_data.html`: **27 total** (post-fix). Of these, only **2** carry `rgba(...)` (and these are in the old quoted-row rendering paths that the PR does not touch — pre-existing non-news panel rows). The news-panel-specific old inline-style JS (`mount.innerHTML = '<div style="padding:8px 0;border-top:1px solid rgba(128,128,128,.15); ...">'`) is **completely removed** by the rewrite. The new JS renders rows via class names — `sid-news-row`, `sid-news-headlines`, `sid-news-title`, `sid-news-meta` — which the page-level `<style>` block styles via tokens. **This is a strict improvement against `scripts/check_runtime_style_injection.py`**: the inline `style="..."` count drops in the rewritten panel.

3. **Move colors are unambiguous and dark/light aware.** The `.r-neg` / `.r-pos` pair in the new stylesheet carries explicit dark-theme overrides:
   ```css
   .r-neg { color:#d23f3f; font-weight:600; }       /* light */
   .r-pos { color:#1f9a55; font-weight:600; }       /* light */
   html[data-theme="dark"] .r-neg { color:#ef6a6a; }
   html[data-theme="dark"] .r-pos { color:#3fc07e; }
   ```
   This is the correct pattern for an **unambiguous move indicator** — distinct from the token-driven semantic-color palette, with explicit theme overrides. Light uses deeper, more saturated reds/greens for daylight contrast on white material; dark uses softer, more luminous reds/greens for the command-center palette. Both themes communicate "down" / "up" through hue + value, not just hue, which is the WCAG-aligned pattern for color-vision-deficient users. The body explicitly notes these are "unambiguous move colours (NOT tied to the zh red=up swap)" — meaning the Chinese cultural convention (red = up / green = down in CN market parlance) is bypassed here for global universality, which is the right choice for an English/Chinese bilingual product.

4. **Tag-chip colors are domain identifiers, not theme tokens.** The 10 `.chip.tag-*` rules carry hardcoded color literals (`#5b8def`, `#c77dff`, `#3fb6c0`, `#46b87a`, `#e0973a`, `#cf7b3a`, `#e0607a`, `#b48ead`, `#d0554f`, `#d08770`) with same-color 0x55-alpha borders. These are **pre-existing category identifiers** for the alt-data tags (macro, fed, rates, equities, etc.) — they name the topical category, not a state. They do not flip with `data-theme` because category identity is not theme-dependent. This is the correct use of a hardcoded literal: domain identifiers that must be visually distinct across categories, not theme tokens. (The state-bearing pills — `.pill.act-ACCUMULATE`, `.pill.act-AVOID`, `.pill.act-WATCH`, `.pill.cv-high`, `.pill.ext`, `.pill.trump`, `.pill.ch` — DO use `var(--ink-up, var(--up))` / `var(--ink-down, var(--down))` / `var(--ink-info, var(--info))` / `var(--ink-warn, var(--warn))` + `color-mix()` transparency, because states must adapt to theme.)

5. **`templates/theme.css` is untouched.** The PR diff does not touch `templates/theme.css` — THEME-CLOSURE is preserved. The alt-data page's theme behavior comes from the shared `theme.css` (unchanged); the new `.sid-news-*` block uses shared tokens; the new `41a985eb.css` is a content-addressed page-chrome stylesheet that lives under `site/assets/css/`, not `templates/`. The link swap `7d4fc68b.css?v=7d4fc68b` → `41a985eb.css?v=41a985eb` is a content-fingerprint change, not a source-tree redesign.

6. **Dark / light art direction is shared via tokens, not re-implemented per page.** The alt-data page's dark/light behavior comes from the shared `theme.css` (unchanged); the new page-level stylesheet adds chrome geometry (cards, chips, status pills, conv rows, source pills) that adapts via the shared tokens. The single explicit dark override (`.r-neg` / `.r-pos` light vs dark) is the **only** per-page material treatment distinction, and it is the right level of differentiation for a chrome-and-data page — the rest of the dark/light difference lives in the shared tokens. Per the TP-0 ruling, this is the correct architecture.

7. **The body's 8-cell dark/light × EN/ZH × desktop/mobile evidence matrix satisfies TP-0; the 24-cell matrix is even broader.** Body cites: "8 native browser cases: desktop/mobile × EN/ZH × dark/light, actual Settings, keyboard/touch retry and deliberately delayed success"; "24 canonical visual states across desktop/tablet/mobile, both languages/themes and rest/retry focus; every image digest verified. Visual/design/runtime-style gates pass." The TP-0 ruling requires "both themes judged as designs (hierarchy, material depth, semantic color, responsive composition, EN/ZH parity)" — the body attests the 8/24-cell matrix PASSed, with extra dimensions (tablet, focus state, retry state) on top of the required 8. The 24 PNGs are committed under `mockups/evidence/uiux-altdata-news-20260921/` and `research/evidence/uiux-altdata-news-20260921/`. The design-doctrine check (`scripts/check_design_system.py --mode enforce-added`) and the runtime-style check (`scripts/check_runtime_style_injection.py`) both pass per the body.

8. **State-bearing surfaces are token-scoped, not hardcoded.** The `.pill.act-ACCUMULATE` / `.pill.act-AVOID` / `.pill.act-WATCH` / `.pill.ext` / `.pill.trump` / `.pill.ch` rules all use `var(--ink-up, var(--up))` / `var(--ink-down, var(--down))` / `var(--ink-info, var(--info))` / `var(--ink-warn, var(--warn))` + `color-mix(in srgb, var(--token) NN%, transparent)` — the token-driven state palette. These rules will adapt to light/dark via the shared `theme.css` token swap.

9. **Theme residual issues: none.** The new `.sid-news-*` block is token-scoped; the new `41a985eb.css` is token-scoped for state-bearing surfaces, light/dark-aware for unambiguous move colors, and uses domain-identifier literals for tag chips (the right choice); the inline `style="..."` count drops in the rewritten panel. THEME-CLOSURE holds.

**Theme verdict: PASS.**

## Validated-claims findings

The standing validated-claims discipline (`scripts/check_validated_claims.py`, BC-2) gates any affirmative use of `validated` / `已验证` against an allowlist and scans `templates/*.j2`, `templates/*.js`, `templates/*.html`, `site/*.js`, `site/*.html`, `site/prophet/*.json`, and `engine/*.py` display-copy fields.

**Headline: PASS on validated-claims. This is a validated-claims IMPROVEMENT — the PR removes a false validation claim and several over-claims, and introduces no new affirmative claims.**

Specific findings:

1. **The PR removes a false "not built" claim.** Pre-fix the alt-data page asserted `News surface not built yet — runs on the next daily build.` / `新闻层尚未生成——将在下次每日构建后出现。` when in fact three anonymous HTTP 401 news reads had failed. **This was a clear validated-claims FAIL** — the page validated an absence where there was actually an access failure. The PR template body contains neither string; `test_altdata_news_template_preserves_native_loading_and_actions` asserts `"News surface not built yet" not in source`. **This is the central defect the PR heals.**

2. **The PR removes the raw `alt signal` score leak from the panel.** Pre-fix JS rendered `<span ...>alt signal {signal_score}</span>` (the raw score alongside per-name headlines). The body notes: "Remove redundant raw signal scores and unsupported overlap interpretation from this secondary panel; retain the underlying conviction board exactly." The new `headline()` function emits only the title (and source), not the score. Test `test_altdata_news_related_headlines_keep_chinese_order_and_escape_markup` asserts `"alt signal" not in out["html"]`. **The raw score never appears on the news panel; the conviction board upstream remains the canonical owner.** This is the right scope: the news panel is a context surface, not a score surface.

3. **The PR removes the "overlap" / "early-edge / crowded" interpretation.** Pre-fix the page asserted `Recent news for the top conviction-board names that the tape is also talking about — the overlap (or its absence) is the early-edge / crowded read.` (ZH: `置信榜上同时被舆情讨论的标的的近期新闻——重叠（或其缺失）即"早期边际/拥挤"读数。`). This was an **over-claim** — the page was interpreting news overlap as an "early-edge / crowded" market signal without a calibrated engine contract to back that interpretation. The new page replaces it with the neutral "Recent headlines for these names." / "这些标的的近期新闻。" — a plain noun phrase, no implied edge. **This is the design-doctrine-permitted "windows, not certainties" form** — the page describes what it shows, not what it means.

4. **The PR removes the false "no news yet, showing market tape" claim for the 401 case.** Pre-fix the market-fallback path asserted `No news yet on today's signals — broad market tape:` / `今日信号暂无对应新闻——大盘舆情：` when in fact the news read had failed for access reasons. Test `test_altdata_market_fallback_does_not_claim_no_related_news_on_401` asserts `"No news yet" not in out["html"]` for the 401-fallback case, and `out["status"] == "market_gate"` (with `登录` in the status text — the ZH-fallback path). **The market fallback now correctly says "Sign in for related headlines. Showing market news."** — honest about both the access failure and the fallback content. This is the falsifier-discipline-permitted form.

5. **No new affirmative `validated` / `已验证` / `经验证` / `经过验证` vocabulary introduced in PR-introduced user-visible copy.** A literal grep of the PR-introduced diff for `validated / confirmed / proven / asserted / verified` returns **zero matches** in the new template body, the new CSS file, the new test file, or the new discovery record. The only `validated`-related vocabulary in the new template content is the existing `data-tip-en="⚡ Prime entry — validated confluence buy gate"` / `data-tip-zh="⚡ 优质入场 — 已验证汇流买入信号"` tooltip on the existing T2 entry badge — which is **pre-existing and untouched by this PR** (the alt-data news panel is below the conviction board; the badge is above).

6. **No `title=` attributes introduced in PR-introduced code.** A literal grep returns **zero matches** in the section/markup diff. The new accessibility model uses `role="status"`, `aria-atomic`, `aria-busy`, and `aria-disabled` — semantic ARIA states, not title attributes. (The pre-existing 5 aria-label attributes in the shared chrome are ungendered chrome hooks and predate this PR.)

7. **Pre-existing `validated` / `verified` / `confirmed` vocabulary in the shared chrome is byte-identical to the rest of the site.** A grep over the committed `site/alt_data.html` returns **5 hits** for `validated | confirmed | verified`:
   - Lines 107, 130 — shared nav-chrome "two-way confirmed stocks" / "two-way confirmed A-shares" — pre-existing.
   - Line 235 — shared nav-chrome "strongest confirmed setups" / "今日最强确认信号" — pre-existing.
   - Line 497 — pre-existing entry-badge tooltip "validated confluence buy gate" / "已验证汇流买入信号" — pre-existing.
   - Line 1726 — pre-existing page description "已验证" / "proven" — pre-existing.

   **All five hits are pre-existing content that this PR does NOT touch.** They are part of the shared nav chrome and the existing conviction board, inherited unchanged. They are out of scope for THIS PR's audit — they predate the PR and are byte-identical to the same strings on `origin/main` for the rest of the site. (A separate audit on the shared chrome's `validated` / `verified` vocabulary would be a different deliverable, not this one. The same pattern is recorded in `macro_PR-7602.mm.md` and `macro_PR-7603.mm.md`.)

8. **No allowlist extension needed.** No PR-introduced phrase names a study, a signal, or a validation claim. The new state messages are all descriptive of what the page is showing (loading, gated, restricted, unavailable, empty, related) — not assertions that any data has been validated. The removed phrases (false "not built", raw "alt signal", unsupported "early-edge / crowded overlap") are not in the new content.

9. **No new engine contract invented.** The PR is a state-discipline fix. The new state classifier (`read(url, valid)`) classifies HTTP status codes into UI states — no new signal, rank, gate, or contract is added. The existing news endpoints (`altdata/mastermind.json`, `news/by_ticker.json`, `news/financial.json`) are unchanged. The body is explicit: "Existing source board/data, order/caps, endpoints, background polling, and authentication are unchanged."

10. **Validated-claims residual issues: none for THIS PR.** The PR introduces no new affirmative validation claim AND removes three pre-existing false/over claims. No allowlist extension is needed. The pre-existing nav-chrome strings are inherited, not introduced.

**Validated-claims verdict: PASS.**

## Overall verdict

| dimension | verdict |
|---|---|
| plain-language | **PASS** |
| theme (TP-0 art direction + THEME-CLOSURE) | **PASS** |
| validated-claims (BC-2) | **PASS** |

**PR #7600 ships clean across the three standing audits — and is in fact an IMPROVEMENT on all three.** This is a half-B user-facing UIUX repair for the Alt Data related-news panel. The meaningful source-of-truth change is in `templates/alt_data.html.j2` (CSS block + 14 lines, JS state-classifier + ~100 lines, markup + 14 lines) plus the new shared stylesheet `site/assets/css/41a985eb.css` (127 lines, content-addressed) plus 13 added test cases in `tests/test_altdata_price_truth.py`. The PR separates six access/transport/empty/ready/fallback states on the news panel: 401 → `gated` ("Sign in to read news"), 403 → `restricted` ("Access to this news is restricted"), !ok/network/schema-invalid → `unavailable` ("News is unavailable right now. Try again."), valid empty → `empty` ("No headlines in this snapshot"), valid data → `related`, market-fallback → `market` / `market_gate` / `market_unavailable` / `market_restricted` with explicit "Showing market news" disclosure. Native Try again button is single-flight (rapid repeated activation cannot duplicate requests) and preserves keyboard focus (when Retry vanishes while owning focus, focus moves to Open News). The PR removes three pre-existing false/over claims: "News surface not built yet — runs on the next daily build" (false — was actually 401), `alt signal {signal_score}` (raw score leak in a context panel), and "the overlap (or its absence) is the early-edge / crowded read" (unsupported interpretation). The section heading-note swaps from jargon ("the demand-side tape beside the supply-side signal — context only, never blended") to plain ("Related headlines · research context"). The new shared stylesheet is properly light/dark-aware with explicit `data-theme="dark"` overrides on the unambiguous `.r-pos` / `.r-neg` move colors, token-driven for all state-bearing surfaces, and uses domain-identifier literals (with same-color 0x55-alpha borders) for the 10 tag chips — the right choice for category identity. The body's 8-cell dark/light × EN/ZH × desktop/mobile browser matrix + 24-cell extended matrix confirm the page renders as designed in both themes, both languages, all three viewport sizes (desktop/tablet/mobile), and both rest/retry focus states. No new visual surface is shipped; no new engine contract is introduced; no new study is claimed.

**Audit result: PASS — no blocking findings.**

---

**Auditor's note (one-shot, half-B scope).** This audit was a single pass against the standing design-doctrine + validated-claims + theme-art-direction laws, in the shape of the prior `qwen_auditor2` audits (`macro_PR-7585.mm.md`, `macro_PR-7599.mm.md`, `macro_PR-7602.mm.md`, `macro_PR-7603.mm.md`). The PR is a state-discipline + plain-language + validated-claims repair on the alt-data page's news panel, which makes the audit unusually broad in coverage (every dimension is improved by this PR, not merely held). The 73 evidence/research files (PNGs, JSON manifests, gate receipts) are content-addressed evidence, not source, and are out of scope for the three standing audits. The pre-existing `validated` / `verified` strings in the shared nav chrome are explicitly noted as inherited (not introduced) and are out of scope for THIS PR's audit — they predate the PR and are byte-identical to the same strings on `origin/main` for the rest of the site. The new `.r-pos` / `.r-neg` literals in `41a985eb.css` are the explicit dark/light override pair for unambiguous move colors, with explicit light/dark treatment — a correct TP-0 application, not a token-discipline regression. The tag-chip literals (`#5b8def`, `#c77dff`, etc.) are domain identifiers, not state tokens, and are the correct choice for category distinction across themes. A separate audit on the shared chrome's `validated` / `verified` vocabulary would be a different deliverable, not this one.
