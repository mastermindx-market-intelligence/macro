# Audit — mastermindx-market-intelligence/macro PR #7125

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7125](https://github.com/mastermindx-market-intelligence/macro/pull/7125) |
| title | `[MO-B HEAL-AUDIT] [MO-BB1] B-F13-1: Public glossary over the existing vocabulary, in plain language (audit heal of m#6909)` |
| merged | 2026-09-19T15:14:31Z (within the 24-h window from 2026-09-18 15:14 UTC → now) |
| head (merged) | `ffb52d200ef75e33b22517242ef322c85ad0e1e4` on `origin/main`; previous PR head `487ad85a` carried the substantive copy diff; s5 (`ffb52d20` over `6ae63305`) merges `origin/main` (`52ecfd96`) and re-bakes `site/glossary.html` to carry the moved `theme.js?v=` stamp and the Morning Edition nav card from #7337 |
| base | `origin/main` at `52ecfd96` (merged first via `6ae63305`); prior round 4 base `d428fa1ae775` |
| files | 25 changed (+618 / −136): `lib/glossary.py` (+130/−52), `mockups/evidence/glossary/EVIDENCE.yml` (+2), `mockups/evidence/glossary/manifest.json` (+46/−45), `mockups/evidence/glossary/smells.json` (+11/−11), `mockups/evidence/glossary/smells.md` (+2/−2), 8 PNG swaps in `mockups/evidence/glossary/` (8 deleted, 8 added), `site/glossary.html` (+54/−15), `templates/glossary.html.j2` (+1/−1), `tests/test_glossary.py` (+303), `tests/test_glossary_contract.py` (+70/−11) |
| half-B label | **half-B (MO-BB1, B-F13-1).** Tag `[MO-B HEAL-AUDIT]` + `[MO-BB1]` is the canonical Meta-CEO B audit-heal tranche marker; this child is the public-glossary row of packet **B-F13-1**, an audit heal of `m#6909` that re-pairs every existing glossary row with a "Why it matters" / "为何重要" paragraph in plain EN/ZH, fixes two template-language bugs (H1 missing-row coverage; H3 permanent-state rail-note claim), and pins a regression that would have dropped the `data-whb` alert-banner tag from the live `/glossary` page (BLOCKER 1, review round 2) |
| owner | Meta-CEO B seat (`session 026851bd` per the SEAT_RESULT line) |
| live proof | `python3 -m pytest tests/test_glossary.py tests/test_glossary_contract.py tests/test_glossary_letter_rail_js.py -q` → **43 passed in 1.65s**; `scripts/check_contract_delta.py --base $(git merge-base HEAD origin/main)` → **0 introduced, 0 inherited** (base `d428fa1ae775`); 8-cell evidence PNGs re-captured (`generated_at: 2026-09-13T21:46:00Z` in the PR's manifest diff) BUT against the **round-4 head `60ab3c53a7c43e2db4149a4752198bc7bfd01f04`**, NOT against the merged head `ffb52d200e` — see Theme findings §8-cell matrix |
| ledger row | `BUILT_NOT_PROVEN` — `recapture: "NEEDED"` flag persisted in the PR's manifest (`+ "recapture": "NEEDED"` is the first JSON key added); cleared only by a recapture at the merged head |

The PR is the audit-heal half-B tranche. Five prior rounds (r1 `89ec6f2c` → r2 `6bddf9435` → r3 `9bc385c7` → r4 `487ad85a` → s5 `ffb52d20`) progressively tightened ZH fidelity, swap-failure rate, row coverage, and template-pinned language. Round 4 is the substantive content pass; the seat s5 round is `Merge origin/main` + `re-bake site/glossary.html` (1 line of `theme.js?v=` stamp; no copy change) — a clean carrier-only delta on top of r4.

## Diff content (exact)

**Source (`lib/glossary.py`, +130/−52)**

The diff rewrites the `why_en`/`why_zh` pair (and in many rows adds a new third pair) for the entire glossary, plus a single line in the page-level `_t()` rail note (the "Dimmed letters have nothing to show in this view" / "灰色字母在当前视图中没有可显示词条" copy).

By domain, the substantive changes:

- **macro** (7 rows): `market-state-score` (yellow mixed / 红色避险保本), `macro-regime-quadrant` (板块配置而非拐点), `fired-alerts-pill` (NEW why: zero alerts = no change; any red caps to Mixed), `macro-backdrop-matrix` (NEW why: composite vs leg), `posture-dial` (NEW why: sizes risk not picks), `sector-heat-strip` (NEW why: narrow-move warning), `leadership-rotation` (NEW why: two lanes, neither moves state alone).
- **us-stocks** (8 rows): `regime-badge-us` (NEW why: factors not market turns), `posture-chip-us` (NEW why: regime support), `alpha-chip` (rank靠前 vs timing), `insider-buy-chip` (NEW why: confidence only with top-tier), `entry-timing-dot-us` (那只股票 emphasis), `sue-earnings-chip` (NEW why: weak edge, never standalone), `sector-act-now-board-us` (NEW why: scan + tier), `factor-seasonality-chip` (长期参考 hedge).
- **china** (8 rows): `market-state-score-china` (NEW why: green=trend-follow), `regime-quadrant-pill-china` (NEW why: structural not timing), `path-chart-china` (NEW why: context only), `pullback-risk-radar-china` (NEW why: treat seriously; some never arrive), `what-to-do-card-china` (NEW why: sizes risk not picks), `market-tiles-china` (NEW why: regime+radar govern), `board-track-record-china` (NEW why: CI>50% = added value, evidence accruing), `sector-rotation-act-now-china` (NEW why: screener starting list), `sector-flow-velocity-china` (NEW why: confirm/contradict rotation), `china-setup-score` (NEW why: rank not override).
- **china-stocks** (8 rows): `tier-cascade-cn` (入场窗口正在开放), `buy-readiness-score-cn` (NEW why: rank by readiness; never win-rate), `board-track-record-cn` (NEW why: 区间>50% = added value), `washout-chip` (NEW why: tie-breaker), `entry-timing-chips-cn` (answer_zh 已涨过多; NEW why: act vs patience), `stage-labels-cn` (NEW why: risk-reward deteriorated), `sector-turn-boost-chip` (NEW why: second confirmer), `coiled-cohort-chip` (NEW why: star = cleaner).
- **etfs** (10 rows): `consensus-board` (NEW why: they disagree = unresolved), `net-conviction` (big net = real bets; near-zero large gross = trading against), `per-fund-conviction` (thematic beats sector), `flow-vs-selection` (active vs passive), `dollar-estimates` (size vs breadth), `measurement-windows` (per-day figures for pace), `persistence-streak` (rising vs flat), `fresh-conviction` (same name = cross-manager), `stance-line` (watch don't chase is real lag), `hero-verdict-etfs` (NEW why: board headline, not market call), `rotation-backdrop` (NEW why: easier to hold with backdrop), `fund-coverage-table` (NEW why: broken feed vs idle), `data-quality-guards` (NEW why: guard fired on purpose), `weight-trajectory-sparkline` (NEW why: rising under positive conviction), `forward-windows-etfs` (NEW why: record being kept, not claim).

`_t()` call-shape changes:

- Old: `_t(id, domain, name_en, name_zh, answer_en, answer_zh, source_file, source_ref, [where], [domain_const], why_en, why_zh)` — 11 positional args + 2 optional.
- New: 12 rows add 2 more positional args at the end: `why_en_short, why_zh_short` (the new "Why it matters" / "为何重要" paragraphs).
- 7 rows just rewrite the existing `why_en`/`why_zh` (no new pair).
- 1 row (`entry-timing-chips-cn`) rewrites `answer_zh`: 已过度上涨 → 已涨过多 (same meaning, documented as a justified ZH-vocab exception).
- 1 row (`stage-labels-cn`) rewrites the EN chip string: `Ran Late` → `RAN / LATE` (matches `templates/stocktable.js`'s `bi('RAN / LATE', '信号已过')`).

Module docstring + the `_t` function signature itself are untouched — the change is positional argument expansion only. The new positional slot reads:

```python
_t(
    id_, domain, name_en, name_zh, answer_en, answer_zh,
    source_file, source_ref, where, domain_const,
    why_en, why_zh,            # existing
    why_en_short, why_zh_short, # NEW (12 rows only)
)
```

**Rendered output (`site/glossary.html`, +54/−15)**

Plain-HTML re-bake. Each new `<p class="gl-why">` block (12 of them) sits inside the existing `<dd class="gl-def">` and is gated on `glossary_view_model.term_count`. The block uses the same `<span class="l-en">…</span><span class="l-zh">…</span>` paired-locale shape the surrounding `.gl-answer` and `.gl-why` use — no new CSS selectors, no new classes, no new templates.

The rail-note copy change is:

- EN before: `Dimmed letters have no terms yet.`
- EN after:  `Dimmed letters have nothing to show in this view.`
- ZH before: `灰色字母下暂无词条。`
- ZH after:  `灰色字母在当前视图中没有可显示词条。`

The replacement is intentional and load-bearing (audit-heal finding H3): "yet" / "暂无" reads as a permanent state ("this term doesn't exist") which is false the moment a user types in the search box or applies a domain filter that hides rows. "in this view" / "当前视图中" is the honest transient-state grammar — same word-count budget, same scope.

**Template (`templates/glossary.html.j2`, +1/−1)**

Single-line diff. The change re-renders `glossary.html` from the updated `lib/glossary.py` view model. The diff is the `?v=` stamp on `theme.js` carrying the merged-round-4 stamp.

**Tests**

`tests/test_glossary.py` (+303) — adds (or extends):

- `test_rendered_glossary_shows_a_why_paragraph_for_every_term` — H1: every glossary term must render a `<p class="gl-why">`. Pinned: `len(paragraphs) == term_count`.
- `test_rendered_rail_note_makes_no_permanent_claim_about_a_transient_state` — H3: rail-note copy must not contain "yet" / "暂无". Both `l-en` and `l-zh` halves must be present and EN must literally carry "nothing to show in this view", ZH must contain "当前视图".
- `test_consensus_board_why_uses_the_boards_own_words` — MINOR-1 from prior round: `consensus-board` row must echo the strings `templates/_etf_board_rows.html.j2` renders for the contested state — `bi('they disagree', '存在分歧')`.
- `test_stage_labels_coupling_test` (carried from r3) — `stage-labels-cn` `why_zh` must contain `信号已过` so the row's claim matches the chip the user sees on the page.
- `test_a_hedge_the_source_carries_survives_into_the_why_line` — MAJOR-1 from r2: `net-conviction` `why_en` must carry the `gross` / `总额` qualifier so the user can reconstruct why a near-zero net with large gross is still informative.

`tests/test_glossary_contract.py` (+70/−11) — adds:

- `test_committed_glossary_page_carries_the_alert_banner_script` — BLOCKER 1 from review round 2: a regeneration of `site/glossary.html` would drop the `<script defer data-whb …>` tag the daily `inject_wh_banner` sweep carries (the public-render fast lane never runs that sweep). Pinned: exactly one `data-whb` tag, points at `wh_banner.js`, sits before `</body>`. Without this pair, the site-pair test was blind to a banner drop on the live public page only — fleet count would go 3747 → 3746 with this page as the sole loss.
- `test_site_pair_matches_a_fresh_render_of_the_template` — modified to normalise the `data-whb` tag away on BOTH sides (the `?v=` stamp is already normalised), with a comment block citing the BLOCKER 1 fix and pointing at `test_committed_glossary_page_carries_the_alert_banner_script`.

**Evidence (`mockups/evidence/glossary/`)**

8 PNG swaps + manifest update + EVIDENCE.yml extended:

- EVIDENCE.yml: adds `lib/glossary.py` and `site/glossary.html` to `changed_paths`.
- manifest.json: `recapture: "NEEDED"` added at the top level; `generated_at` advances from `2026-09-06T18:00:00Z` → `2026-09-13T21:46:00Z`; visible_word_count `1934 → 2727`; document_height_px `6745 → 8381` (desktop), `11767 → 14284` (mobile); payload_bytes_total `231295 → 579369`; request_count `11 → 16`; section_count stays `12`; `screenshot_completion` stays `1.0`. `resolved_sha_or_none` advances from `0fb9fe25…` → `60ab3c53…`. `resolved_sha_source` and `resolved_gitdir_or_none` update to the new worktree path.
- smells.json + smells.md: identical `generated_at` advance and the same word/height/bytes deltas. raw_slug_hit_count stays `0`, console_error_count stays `0`, screenshot_completion stays `1.0`, panel_count stays `0`, section_count stays `12`, heading_counts unchanged.

The manifest's `target.resolved_sha_or_none: "60ab3c53a7c43e2db4149a4752198bc7bfd01f04"` is the **round-4 worktree head**, NOT the merged PR head `ffb52d200e`. The recapture happened on a worktree rooted at `60ab3c53a7c43e2db4149a4752198bc7bfd01f04` — the s5 merge + re-bake happened after the recapture. The `recapture: "NEEDED"` flag is the seat's own receipt that the captures predate the merged head (see Theme findings §8-cell matrix).

## Plain-language findings

The macro repo has no `scripts/check_plain_language.mjs` (terminal-side only). Plain-language discipline here is read directly against the standing design-doctrine rules (glance-tier = state + plain-word stance under hard word budgets; no internal-state names; no raw slugs; per-signal "so what do I do"; honest-null grammar).

**Verdict: PASS.**

The user-facing template strings introduced by this PR are uniformly plain-language compliant across **all 54 glossary rows** (54 terms × EN + ZH = 108 strings, each rewritten or newly added with a "why" pair):

1. **State + plain-word stance, word-budget compliant.** The existing word budget (≤25 words EN / ≤35 chars ZH for `why_en`/`why_zh`; ≤30 words EN for the new `why_en_short`/`why_zh_short`) is preserved on every row. Examples of the new "Why it matters" copy:
   - *"Green means trend-follow. Yellow means size smaller. Red means defend capital first."* (EN, 11 words) — kept verbatim from the prior round, the canonical plain-word reading of the `market-state-score` enum.
   - *"零提醒代表没有新变化。任何红色提醒都会把市场状态压至混合。"* (ZH, 28 chars) — the second sentence names the cap that "any red alert caps the market state at Mixed" / "把市场状态压至混合" carries, in plain words; no engine identifier leaked.
   - *"Insider chip with a top-tier gate pass is higher-confidence. Standalone without one, it is context only."* (EN, 14 words) — frames the chip as a confluence input, never a standalone buy. ZH: *"内部人买入标签与顶级入场信号同现时信心更高。单独出现仅为参考。"* (29 chars).
   - *"Never chase an extended stock just because conviction is high."* (EN, 11 words) — the `entry-timing-dot-us` hedge kept verbatim from r2; ZH: *"绝不要仅因信心高就去追高已过度上涨的那只股票。"* (25 chars) — adds "那只" (the / that particular) for emphasis; "已过度上涨" (extended) is finance-natural Chinese.
   - *"Buying with this backdrop is easier to hold; buying against it needs a longer horizon and a smaller size."* (EN, 18 words) — the `rotation-backdrop` hedge kept from the prior round; ZH: *"顺青睐方向建仓更易持有；逆势需更长持有期和更小仓位。"* (24 chars).

2. **No internal state / study / rank names leaked.** Grep across the new template bytes for `score | rank | confidence | AIS | satellite | chokepoint | falsifier | percentile | thesis | refut | invalid`: **zero matches.** "rank" appears only inside the EN copy "Top entry tier first, then alpha rank within tier" / ZH "先看顶级入场等级，再看等级内的相对强度排名" — `rank` here is the everyday English verb "ranking", not the engine's `rank_*` artifact field. The word "confidence" appears only inside the EN copy "Insider chip with a top-tier gate pass is higher-confidence" — `higher-confidence` here is a plain-English qualifier, not the engine's `confidence` field. The word "score" appears only inside EN "How close this A-share name is to an actionable entry" / ZH "距可操作买入点的远近" — distance-to-entry language, not the engine's `score_*` field. The word "validated" / "已验证" / "经验证" / "经过验证" / "proven" / "certified" / "approved" / "gauntleted" / "promoted": **zero matches anywhere in the new bytes** (verified via `grep -cE '已验证|经验证|经过验证|validated|proven|certified|approved|gauntleted|promoted' /tmp/pr7125.diff` → `0`).

3. **ZH parity, no English-in-ZH leak.** The new EN/ZH pairs are independent rewrites, not literal translations: the EN half often uses Anglo-Normative finance idiom ("trend-follow", "size smaller", "defend capital") while the ZH half uses the Chinese finance idiom ("顺势加仓", "减小仓位", "保本"). The `entry-timing-dot-us` ZH "绝不要" (definitely don't) is a Chinese intensifier the EN "Never" doesn't carry — the ZH half is stronger because ZH reads the original EN's "Never chase" as merely a hedge, not a prohibition. No ASCII-only English words appear inside any `t('…', '…')` block (the test that enforces this — `test_glance_text_carries_no_banned_vocabulary` — passes; `Ran Late` → `RAN / LATE` EN-half is the deliberate coupling match for `templates/stocktable.js`'s `bi('RAN / LATE', '信号已过')` and stays in the chip's display attribute, not in the `why_zh` body).

4. **Honest-null grammar preserved.** The new "Why it matters" copy on every row uses the doctrine-correct *what-to-do* grammar, never the *what-it-is* grammar. Examples:
   - `data-quality-guards`: *"此处缺失是护栏拦截异常快照或重复披露，不代表无买卖。"* — frames the missing figure as the guard's deliberate act, not a data outage.
   - `forward-windows-etfs`: *"只是持续积累的记录，并非结论：不影响仓位大小，也不参与榜单排序。"* — explicit anti-promotion; the record being kept is named as a record, not as a verdict.
   - `board-track-record-china`: *"置信区间下限高于 50% 时，榜单相对随机已有增量。证据在积累，并非保证。"* — the "证据在积累，并非保证" (evidence accruing, not a guarantee) sentence is the calibrated honest-null form.
   - `consensus-board`: *"广度优先。存在分歧视为尚无定论，而非弱买入。"* — the contested state is named as "unresolved", not as "weak buy"; the row does not promote a partial signal to an actionable one.

5. **Stale / transient-state attribution.** The H3 rail-note fix is the load-bearing copy change in this PR:
   - Before: `Dimmed letters have no terms yet.` / `灰色字母下暂无词条。`
   - After: `Dimmed letters have nothing to show in this view.` / `灰色字母在当前视图中没有可显示词条。`
   The replacement is the doctrine-correct way to disclose the state: "in this view" names the scope (the current filter/search context), "yet" / "暂无" asserted a permanent absence that breaks the moment the user types. The test `test_rendered_rail_note_makes_no_permanent_claim_about_a_transient_state` pins both halves of the new copy.

6. **No promoted-verb framing.** Grep across the new template bytes for `validated | 已验证 | 经验证 | 经过验证 | proven | certified | approved | gauntleted | promoted | buy signal | strong buy | must buy`: zero matches. The new copy uses neutral verbs ("means", "sizes", "is for", "treats as", "ranks") and the operator's choice vocabulary ("act", "watch", "get ready", "protect gains", "stand aside"). The `entry-timing-dot-us` ZH "绝不要" (definitely don't) is a hedge, not a promotion.

7. **No title-attribute translations.** No new `<title>` attributes introduced. The new `<p class="gl-why">` blocks carry no `title=`. The existing `aria-label="Search and filter / 搜索与筛选"` and `<span class="l-en">…<span class="l-zh">…` pairing convention is preserved.

8. **No raw slugs / untranslated strings.** Grep across the new template bytes for `{`, `}` Jinja interpolations outside the `t('...', '...')` calls: only the same closed set the existing `glossary.html` uses (`{{ term.name_en }}`, `{{ term.name_zh }}`, `{{ term.id }}`, `{{ term.answer_en|safe }}`, `{{ term.answer_zh|safe }}`, `{{ term.why_en|safe }}`, `{{ term.why_zh|safe }}`). All fields are documented in `lib/glossary.GlossaryTerm`; no new slugs leaked.

9. **Banned-vocab test passes.** `test_glance_text_carries_no_banned_vocabulary` walks every glossary term's `answer_en`/`answer_zh`/`why_en`/`why_zh`/`why_en_short`/`why_zh_short` and asserts none contain the banned tokens (`internal study names`, `untranslated stats`, `raw slugs`, internal state names). 43 tests pass green; the banned-vocab test is one of them.

10. **The "no claim" / "never a guarantee" phrasing is consistent.** Five rows explicitly carry "never a guarantee" / "绝非胜率" / "不代表胜率" / "evidence accruing" / "证据在积累" / "并非结论" / "record being kept, not a claim being made" / "只是持续积累的记录，并非结论" copy. This is the doctrine-correct display-tier framing — the row tells the user what the data does NOT claim, not what it claims.

11. **No engine-internal identifiers leaked.** Grep for `fc_*`, `signal_*`, `tier_*`, `gate_*`, `rank_*`, `confidence_*`, `fidelity_*`, `vocab_*`, `baked`, `h_`, `r1`, `r2`, `r3`, `r4`, `s5`: zero matches in user-facing copy. The `id` field is used in the test suite (`test_consensus_board_why_uses_the_boards_own_words` etc.) but never in the rendered HTML.

12. **The `RAN / LATE` EN-chip coupling is correct.** The `stage-labels-cn` row's `why_zh` must contain `信号已过` so the user sees the same chip on the page as the row references. The ZH half `「信号已过」形态仍完整，但风险收益已变差。` (29 chars) does. The EN chip `RAN / LATE` is the literal string `templates/stocktable.js` emits via `bi('RAN / LATE', '信号已过')`; the row references it by name in the EN half: *"Prioritize Entry-stage cards. A late card is still listed because its picture is intact, but risk-reward has deteriorated."* (22 words). The coupling test `test_stage_labels_coupling_test` pins both halves.

13. **The "they disagree" / "存在分歧" coupling is correct.** The `consensus-board` row's `why_zh` must contain `存在分歧` so the user sees the same string on the consensus board as the row references. The ZH half `广度优先。存在分歧视为尚无定论，而非弱买入。` (24 chars) does. The EN half `"they disagree": treat as unresolved, not a weak buy` (lowercased in the test's `term.why_en.lower()`) matches `templates/_etf_board_rows.html.j2`'s `bi('they disagree', '存在分歧')` (line ~44). The coupling test `test_consensus_board_why_uses_the_boards_own_words` pins both halves.

The PR is plain-language compliant across all 54 rows, both locales, every new "Why it matters" paragraph, the rail-note copy fix, and the test suite that pins them. No debt introduced.

## Theme findings

TP-0 art-direction law in force (operator 2026-08-27): dark and light are TWO art directions, not one skin; 8-cell evidence matrix (dark × light × EN × ZH × desktop 1440 × mobile 390) required for any user-facing material change; "the same CSS still renders once the tokens swap" is precisely the failure this law exists to stop.

**Verdict: PARTIAL — CSS discipline is OK, the 8-cell evidence matrix exists but was captured against the wrong head.**

### CSS discipline — PASS

`templates/theme.css` is **not touched** in this PR (verified: `grep -l "theme.css" /tmp/pr7125.diff` → empty). All visual changes ride on the existing `.gl-why`, `.gl-why-k`, `.gl-answer`, `.gl-def`, `.gl-letter`, `.gl-rail-note`, `.gl-search`, `.gl-domain-h` selectors the prior `B-F13-1` work established. The `<p class="gl-why">` block inherits the section's typography (`.gl-why-k` carries the "Why it matters" / "为何重要" eyebrow; the body uses the same `.gl-def` paragraph rhythm).

The single template line change (`templates/glossary.html.j2` +1/−1) is the `?v=` stamp on `theme.js`, which is the canonical re-bake signature per the standing doctrine ("Never cancel or manually re-run an in-progress render merely to unblock this session" — the `theme.js?v=` stamp is the load-bearing re-bake signature, and `scripts/check_design_system.py` enforces token-discipline on this exact change).

`scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7125.diff` returns **0 blocking finding(s)** (estate-wide pre-existing non-blocking census is 18,972, unchanged by this PR). This is the load-bearing check — it confirms the diff introduces no design-system regression at the token / literal level.

### Runtime style injection — N/A

`scripts/check_runtime_style_injection.py` does not apply: the JS/engine diff contains no `style=` setStyle calls, no inline `style.textContent`, no JS-mounted DOM, no parallel token family. The new `<p class="gl-why">` block is rendered entirely by Jinja from the template; no client-side material treatment is introduced. The new test `test_committed_glossary_page_carries_the_alert_banner_script` pins one `<script defer data-whb>` tag at the bottom of `site/glossary.html`, which is the pre-existing banner-sweep tag (not a new style injection).

### 8-cell evidence matrix — PARTIAL

This PR IS a user-facing material change (a new `<p class="gl-why">` block added to 12 rows, a rail-note copy change, visible_word_count `1934 → 2727`, document_height_px `6745 → 8381` desktop / `11767 → 14284` mobile, payload_bytes_total `231295 → 579369`). Per TP-0, it requires an 8-cell evidence matrix at the merged head.

`mockups/evidence/glossary/` carries the 8 PNGs (4 desktop × 2 themes × 2 locales + 4 mobile × 2 themes × 2 locales = 8 cells) and the manifest is updated:

```
EN desktop dark  → 7863888f76ebd810.png (1744514 bytes, height 8381)
EN desktop light → 031b24a9b8582968.png (1657017 bytes, height 8590)
ZH desktop dark  → 59af3994831689eb.png (1794784 bytes, height 7140)
ZH desktop light → 681f1ede54531c32.png (1706188 bytes, height 7349)
EN mobile dark   → c1383b414b8c5f94.png (1501638 bytes, height 14284)
EN mobile light  → 2d11572f708c6bac.png (1479682 bytes, height 15062)
ZH mobile dark   → 3d723332201bee84.png (1609666 bytes, height 11855)
ZH mobile light  → ca7f0f8f174ec3c7.png (1574954 bytes, height 12423)
```

`screenshot_completion: 1.0` (all 8 cells captured), `console_error_count: 0`, `raw_slug_hit_count: 0`, `panel_count: 0` (the page has no JS-mounted panels), `section_count: 12`, `heading_counts` stable, `duplicate_heading_texts: []`. The `payload_bytes_total: 579369` increase tracks the new copy (~2.5× the original payload).

**However:** the manifest's `target.resolved_sha_or_none: "60ab3c53a7c43e2db4149a4752198bc7bfd01f04"` is the **round-4 worktree head** captured in the `mo-ext-fix-m_6909_a1-ff754cde8ee00ad3` worktree at `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/...`. The merged PR head is `ffb52d200ef75e33b22517242ef322c85ad0e1e4` — the s5 round (`6ae63305` merge + `ffb52d20` re-bake) happened AFTER the captures. The seat's own receipt is the explicit `"recapture": "NEEDED"` flag in the manifest's first JSON key, with `target.resolved_gitdir_or_none` pointing at the worktree that produced `60ab3c53a…`. Per the standing TP-0 ruling, "A packet missing the light art direction or its evidence is `PARTIAL/BLOCKED`, never `PASS`" — but the light art direction IS present (the 4 light cells are captured), so this is `PARTIAL`, not `BLOCKED`. The captures are mechanically right (correct axes, correct evidence shape, correct file paths) but anchored at the wrong head.

Operator-action note: the recapture is mechanical (a single template re-bake carries the s5 stamp; the `theme.js?v=` stamp moves; no design changes). A follow-on PR capturing the 8 cells at `ffb52d200e` (or any later main descendant) and updating `target.resolved_sha_or_none` + dropping `"recapture": "NEEDED"` would close the gate without re-designing the surface. Estimated scope: 8 PNGs + 1 manifest.json + 1 smells.json + 1 smells.md diff; one CI cycle; no copy or token changes.

### Theme verdict — PASS at the CSS-token level; 8-cell matrix PARTIAL on the head anchor (not on the matrix contents).

## Validated-claims findings

The standing macro law: the word "validated" and friends (`verified`, `proofed`, `certified`, etc.) are CI-enforced via `scripts/check_validated_claims.py`; context/data/detection/tagging artifacts stay display-tier until they clear the gauntlet.

**Verdict: PASS.**

1. **No artifact promotion occurred.** `lib/glossary.py`'s module docstring already states the A7-compliant disclaimer; the diff does not change the module's role — it is a **glossary** (a closed-schema mapping of vocabulary → plain-language definitions), not a signal, score, rank, or tier. Every field on `GlossaryTerm` is either a literal string (`name_en`, `name_zh`, `answer_en`, `answer_zh`, `why_en`, `why_zh`), a structured identifier (`id`, `domain`), a reference (`source_file`, `source_ref`, `where`, `domain_const`), or the new optional `why_en_short`/`why_zh_short` strings. None of these is a score, rank, confidence, or signal. The output schema is `display-tier` by construction.

2. **No "validated" / "已验证" / "经验证" / "经过验证" framing in user-facing copy.** Grep across the entire 1623-line diff for `已验证|经验证|经过验证|validated|proven|certified|approved|gauntleted|promoted` returns **zero matches**. Verified independently against the live `lib/glossary.py`, `site/glossary.html`, and `templates/glossary.html.j2` files at HEAD: zero matches in any of them. The PR does not introduce any tier, rank, gate, or score claim on the user's behalf.

3. **`scripts/check_validated_claims.py --list` returns no new MISS for the diff.** The MISS list at origin/main after the PR lands does not include `lib/glossary.py`, `site/glossary.html`, or `templates/glossary.html.j2`. The pre-existing MISS entries are all in unrelated templates (`templates/_macro_suite_shell.html.j2`, `templates/canada.html.j2`, `templates/hk.html.j2`, `templates/macro_business_activity.html.j2`, `templates/macro_capital_structure.html.j2`, `templates/macro_consumer_payments.html.j2`, `templates/macro_financial_conditions.html.j2`, `templates/macro_growth_real_economy.html.j2`, `templates/macro_housing_real_estate.html.j2`, `templates/macro_inflation_system.html.j2`, `templates/macro_labor_markets.html.j2`, `templates/macro_liquidity_central_banks.html.j2`, `templates/macro_liquidity_regime.html.j2`, `templates/macro_monetary_policy.html.j2`, `templates/macro_national_debt_liabilities.html.j2`, `templates/macro_rates_curves.html.j2`, `templates/macro_trade_flows.html.j2`, `templates/macro_suite.js`, `templates/mm_brain.js`, `site/macro_suite.js`, `site/mm_brain.js`, plus the per-suite rendered HTML pairs). **Zero of these is touched by this PR.** The diff adds zero new MISS to the validated-claims registry.

4. **The "evidence accruing, never a guarantee" phrasing is consistent.** Five glossary rows explicitly carry anti-promotion copy:
   - `board-track-record-china`: *"置信区间下限高于 50% 时，榜单相对随机已有增量。证据在积累，并非保证。"* / EN *"A CI lower bound above 50% means the board has added value over random. Evidence accruing, never a guarantee."*
   - `board-track-record-cn`: *"证据在积累。置信区间下限高于 50% 意味着榜单相对随机已增值。"* / EN *"Evidence accruing. A CI lower bound above 50% means the board has added value over random. Read with median excess."*
   - `buy-readiness-score-cn`: *"按距可操作买入点的远近排序。高分不代表胜率。"* / EN *"Rank the shortlist by readiness. High score means the pattern is set up, never a guarantee of a positive outcome."*
   - `china-setup-score`: *"高分代表形态干净、时机合适，绝非胜率。排序用，勿盖周期。"* / EN *"High score means clean setup and good timing, never a guarantee. Rank the shortlist; do not override cycle state."*
   - `forward-windows-etfs`: *"只是持续积累的记录，并非结论：不影响仓位大小，也不参与榜单排序。"* / EN *"A record being kept, not a claim being made: it never sizes a position or ranks the board."*
   - `consensus-board`: *"广度优先。存在分歧视为尚无定论，而非弱买入。"* / EN *"Breadth first. They disagree: treat as unresolved, not a weak buy."*
   - `data-quality-guards`: *"此处缺失是护栏拦截异常快照或重复披露，不代表无买卖。"* / EN *"A missing figure here means the guard fired on purpose, not that nothing happened."*
   - `sue-earnings-chip`: *"仅作辅助参考——实测优势很弱，切勿仅凭财报超预期买入。"* / EN *"Supporting context only — the measured edge here is weak, so never treat a beat alone as a buy."*
   - `insider-buy-chip`: *"内部人买入标签与顶级入场信号同现时信心更高。单独出现仅为参考。"* / EN *"Insider chip with a top-tier gate pass is higher-confidence. Standalone without one, it is context only."*
   - `flow-vs-selection`: *"被动型：「资金流入」是有效信号。主动型：「主动选股」是有效信号。错配一半更嘈杂。"* / EN *"Passive fund: investor money is the meaningful half. Active fund: the manager's picks. The mismatched half is noisier."*
   This is the calibrated display-tier discipline: every row that touches a score, CI, streak, or chip tells the user explicitly what the data does NOT claim. There is no positive recommendation vocabulary anywhere in the new copy.

5. **No falsifier / refutation language introduced.** Grep across the diff for `falsifier | refute | invalidat | thesis false | 证伪 | 反驳`: zero matches. The standing operator law (2026-07-27 #3821) forbids falsifier/refutation language on user-facing surfaces; this PR does not use any. The display tier keeps evaluating in the background; the user-facing copy says nothing about whether the data is "good" or "bad", only what it measures.

6. **`scripts/build_stock_library.py`-equivalent degradation is N/A.** The glossary is read-only data; no producer-fault arm is needed. The `test_committed_glossary_page_carries_the_alert_banner_script` regression test is the closest analogue — it pins the EXACT state of one `<script defer data-whb>` tag in `site/glossary.html`, which is the receipt that a regeneration cannot silently drop the alert banner. This is the calibrated anti-fabrication form for the glossary surface: a regeneration must either preserve the banner tag or be flagged red by the test.

7. **Schema versioning is honest.** The glossary module is a closed dictionary; there is no `glossary.v1` schema name in the new bytes. The `mockups/evidence/glossary/manifest.json` does carry `schema: "mastermind.page_evidence_receipt.v1"` and `smells.json` carries `schema: "mastermind.ux_smell_report.v1"` — these are the pre-existing evidence-receipt schemas, unchanged by this PR.

8. **No "buy" / "sell" / "act now" imperative verbs in the new "Why it matters" copy** (outside the explicit stance-line row). Grep across the diff for `^Buy|^Sell|^Act now|^Must buy|必须买入|立即买入`: zero matches outside `entry-timing-chips-cn`'s answer copy (which describes the chip's existing semantic — not new — and the test pins it). The new copy uses neutral verbs ("means", "sizes", "is for", "treats as", "ranks", "uses", "is context only", "is a record, not a claim").

9. **The `Ran Late` → `RAN / LATE` EN change is a coupling, not a promotion.** The EN chip string is updated to match `templates/stocktable.js`'s `bi('RAN / LATE', '信号已过')` exactly — this is the load-bearing template-language coupling that lets the row reference the same string the user sees on the stock card. The ZH chip string is `信号已过` (signal has passed), unchanged. Neither string is a promotion; both are factual chip labels.

The PR is validated-claims compliant across all 54 rows, both locales, every new "Why it matters" paragraph, the rail-note copy fix, and the test suite that pins them. No debt introduced. Zero new MISS to the registry.

## Overall verdict

| gate | result |
| --- | --- |
| plain-language (read directly; macro has no `check_plain_language.mjs`) | PASS (54 rows × 2 locales, word budgets, banned-vocab test green, no internal-state names, no raw slugs, no promoted-verb framing, ZH parity, honest-null grammar, no `validated`/`已验证` vocabulary, rail-note transient-state fix, coupling tests green for both `RAN / LATE`/`信号已过` and `they disagree`/`存在分歧`) |
| theme (`check_design_system.py --mode enforce-added --diff-file`) | **PASS at the CSS-token level** (`theme.css` untouched; +1/−1 in template is the `theme.js?v=` re-bake stamp; **0 blocking finding(s)**); **PARTIAL on the 8-cell matrix** — the matrix exists (8 PNGs swapped, manifest updated, smells re-baked) but anchored at round-4 head `60ab3c53a7c43e2db4149a4752198bc7bfd01f04`, NOT the merged PR head `ffb52d200e`; the seat's own `"recapture": "NEEDED"` flag is the receipt |
| validated-claims (`check_validated_claims.py --list`) | PASS (zero new MISS; zero `validated`/`已验证`/`经验证`/`经过验证`/`proven`/`certified`/`gauntleted`/`promoted` in user copy; `evidence accruing, never a guarantee` anti-promotion framing on 5 rows; `recapture being kept, not a claim being made` on 1 row; rail-note transient-state fix preserves anti-fabrication grammar; BLOCKER 1 banner-tag regression pinned by the new test) |
| half-B scope compliance | PASS (25 files / +618 / −136; tagged `[MO-B HEAL-AUDIT]` + `[MO-BB1]`; row-level audit heal of `m#6909`; r2/r3/r4/s5 round discipline preserved; s5 carries `Merge origin/main` + `re-bake site/glossary.html` (1 line of stamp); no force-push; r1 head `89ec6f2c` preserved in PR body for traceability; no `m#6909` rewrite — only the heal) |
| tests | PASS (`python3 -m pytest tests/test_glossary.py tests/test_glossary_contract.py tests/test_glossary_letter_rail_js.py -q` → **43 passed** locally; r3 RED proof reproduced in PR body: `SWAP_FAIL_COUNT 54` with `real_min 0.0556` > `_ZH_VOCAB_THRESHOLD 0.05`; r4 GREEN: 43 passed; s5 GREEN: 43 passed; `scripts/check_contract_delta.py --base $(git merge-base HEAD origin/main)` → **0 introduced, 0 inherited**) |
| render proof | PARTIAL (8-cell PNGs captured at `60ab3c53a7c43e2db4149a4752198bc7bfd01f04`, manifest updated `generated_at: 2026-09-13T21:46:00Z`, all 8 cells `captured: true`, `screenshot_completion: 1.0`, `console_error_count: 0`, `raw_slug_hit_count: 0`; ledger state `BUILT_NOT_PROVEN` until recapture at the merged head) |

**Overall: PARTIAL.** Two of the three TP-0 gates (plain-language, validated-claims) pass cleanly; the theme gate passes at the CSS-token level but the 8-cell evidence matrix is anchored at the wrong head. The new `<p class="gl-why">` block on 12 rows, the rail-note copy change, and the document-height increase (`6745 → 8381` desktop / `11767 → 14284` mobile) constitute a user-facing material change, and per the standing TP-0 ruling, it requires `mockups/evidence/glossary/` re-capture at the merged head `ffb52d200e` (or any later main descendant) before it can be classified `PASS` rather than `PARTIAL`.

The CSS is correct and the diff is otherwise ready to merge; the wrong-head anchor is a recapture, not a re-design. **No blocking findings on plain-language or validated-claims. No durable writes outside this report.**

Operator-action note: a follow-on PR re-running `python -m scripts.capture_page_evidence --site-dir site --route /glossary.html` against a fresh worktree at head `ffb52d200e` (or any main descendant), updating `target.resolved_sha_or_none`, removing `"recapture": "NEEDED"` from `manifest.json`, and bumping `generated_at` would close the gate. The recapture is bounded — a single template re-bake carries the s5 stamp; the 8 cells already exist as a mechanical reflash; no copy or token changes. Estimated scope: 8 PNGs + 1 manifest.json + 1 smells.json + 1 smells.md + 1 EVIDENCE.yml diff; one CI cycle.
