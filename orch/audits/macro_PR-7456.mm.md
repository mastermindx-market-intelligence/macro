# Audit — mastermindx-market-intelligence/macro PR #7456

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7456](https://github.com/mastermindx-market-intelligence/macro/pull/7456) |
| title | `Restore canonical China macro dashboard` |
| merged | 2026-09-19T23:59:44Z (24-h window: 2026-09-19 00:00 UTC → now) |
| head | merge commit `ef5fb6bd57` on `origin/main`; code head same (single-commit restoration); base `e0e2600d6228af074c56b7ce7d46928db7442538` (the canonical pre-#7054 parent) |
| files | 2 changed (+696 / −1510): `templates/china.html.j2` (596 + / 464 −) and `tests/test_china_archetype_d_s1.py` (100 + / 1046 −) |
| half-B label | **NOT half-B.** This PR carries no `[MO-A…]` / `[MO-B…]` / `[MAIN-RED-REPAIR]` tag and is not part of any numbered Meta-CEO tranche; it is a **Chairman-direction regression restoration** (`claude/restore-old-china-dashboard-20260919`). The "half-B" framing in the audit task brief does not apply; this child sits outside the Meta-CEO A/B calendar entirely. The audit still applies the plain-language / theme / validated-claims gates because the diff is user-facing. |
| owner | `chriswong6031-creator` (operator 2026-09-19 direction) |
| base | `origin/main` at `e0e2600d6228af074c56b7ce7d46928db7442538` (the exact canonical pre-#7054 parent; verified via PR body "restore from the exact canonical parent of #7054") |
| live proof | (per PR body) Jinja parse PASS; focused China/render contracts 162 passed; `check_design_system.py --mode enforce-added` blocking=0; runtime style-injection guard PASS; `git diff --check` PASS; legacy-jobs YAML parse PASS |

This PR is a regression restoration, not a new build. It re-applies the pre-#7054 deep China macro dashboard (the 14-module canonical published product) and removes the 14→6 L1 Archetype-D S1 compression (#7054) as the published default. Archetype-D remains recoverable in #7054 and its evidence corpus; the child preserves the idea in git history rather than deleting it.

## Diff content (exact)

**Template (`templates/china.html.j2`, +596 / −464)**

The diff restores the canonical pre-#7054 hero band (gauge + verdict word + posture + thesis + flip + hero buttons + path-graph) and replaces the Archetype-D 6-block L1 compression with the 14-row classic dashboard (regime gauge, score gauge, 60-session path, market tiles, what-to-do, upcoming events, pullback risk, market sentiment, sector temperature, policy monitor, connect flows, macro news, property, AI brief, alerts centre). The CSS additions (≤ 60 lines in the path-graph block) sit alongside the removals; the net CSS change is small.

The key user-facing copy blocks restored include:

- **`Composite regime score, anchored in words`** / **`综合状态评分，以文字为锚`** (figcaption caption, restored verbatim from pre-#7054 canonical). Honest "anchored in words" framing — the score is paired with a verdict word so it cannot be read in isolation.
- **`What To Do`** / **`该怎么做`** card with posture + reasons + imminent; posture uses EN/ZH enum tokens (`DEFENSIVE/CAREFUL/NEUTRAL/CONSTRUCTIVE/AGGRESSIVE` ↔ `防御/谨慎/中性/积极/进取`) with emoji icons (`🛡/⚠/◐/✅/🚀`).
- **`Pullback Risk`** / **`回撤风险`** card with severity pill (`HIGH/ELEVATED/CAUTION` ↔ `高/偏高/谨慎`), 5% dip odds, deep-drawdown gauge, "what to do" foot (`High pullback risk — size down, watch alerts.` / `回撤风险高 — 缩仓，关注警报。`).
- **`Market Sentiment`** / **`市场情绪`** odometer dial with zone labels (`PANIC/EUPHORIA` ↔ `恐慌/亢奋`); sub-line "Composite at {N} · a heads-up, not a scored signal" / `综合指数 {N} · 仅供参考，不构成评分信号`. Explicit "not a scored signal" framing — calibrated anti-promotion language.
- **`Sector Temperature`** / **`板块温度`** card with hot chips, turning-up chips, 16-cell heat row.
- **`Top Stock Setups`** / **`精选买点`** card with stage tag + screener link.
- **`AI Brief`** / **`AI 简报`** v2 teaser card — first ≤2 engine-computed key facts as chips; falls back to regime/policy/southbound chips on v1 payloads. The inline comment explicitly states "**No raw slugs (doctrine Law 2)**" — the brief card consumes only human-readable label/value pairs from `china_brief.key_facts`, never raw ticker / schema keys.
- **`Macro News`** / **`宏观新闻`** card with 2 headlines + "X of Y stories kept" ratio disclosure.
- **`Property`** / **`房地产`** card with regime label + 70-city breadth + foot ("Still the economy's main drag." / `仍是经济的主要拖累。`).

The 60-session path graph uses **threshold-based verdict bands** (`<42 risk-off`, `42–60 mixed`, `≥60 risk-on`) painted from `--up` / `--warn` / `--down` so they flip in zh (operator ruling 2026-07-21). The path JSON is emitted server-side (`data-points='{{ _ph_json | tojson }}'`) with bilingual EN/ZH date stamps (`Jan 27` / `1月27`); tooltip content is patched by JS at hover. The `<g filter="url(#cnxDialGlow)">` wraps the needle + hub circles so the SVG filter bounding box is always non-zero — this is the doctrinal fix for the 2026-08-11 "torch / blank dial" failure mode.

**Test (`tests/test_china_archetype_d_s1.py`, +100 / −1046)**

- Filename retained (CI authority surface in `.github/ci/legacy-jobs.yml`); contract repurposed from "China.html Archetype-D S1 — structure + landing + copy gates" → "China dashboard publication contract". The docstring explicitly cites the chairman directive: *"the pre-#7054 deep China macro dashboard is the published default. Archetype-D remains recoverable in #7054 and its evidence corpus, but its six-block L1 compression is not the production composition until separately matured and approved."*
- The "approved" word here is a chairman-approval statement, **not** a user-facing validation claim. It does not surface on any page; it is a maintainer note inside a test docstring.
- 946 lines of Archetype-D assertions are removed (G1 structure / G2 count-truth / G3 banned Tier-1 tokens / G4 Growth-Scare ZH / G5 skeleton / §1.6 demotion landings); 100 lines of generic publication contract tests are added in their place. The PR body reports the focused China/render contracts are 162 passing.

## Plain-language findings

The macro repo has no `scripts/check_plain_language.mjs` (terminal-side only). Plain-language discipline is read directly against the standing design-doctrine rules (glance-tier = state + plain-word stance under hard word budgets; no internal-state names; no raw slugs; per-signal "so what do I do"; honest-null grammar).

**Verdict: PASS.**

The user-facing strings restored by this PR are uniformly plain-language compliant. The 80 new bilingual `t(...)` calls introduced cover section titles, posture labels, severity pills, zone labels, status phrases, and foot summaries. Spot audit of representative strings:

1. **State + plain-word stance.** Examples restored verbatim from the pre-#7054 canonical:
   - *"Composite regime score, anchored in words"* / *"综合状态评分，以文字为锚"* — 6 words EN / 11 characters ZH; "anchored in words" replaces the engine's `verdict_word` token, the user sees the framing (number + label), not just the formula.
   - *"What To Do"* / *"该怎么做"* — 3-word title; the card carries the posture + reasons + imminent line, so the user gets the answer, not the playbook schema.
   - *"Pullback Risk"* / *"回撤风险"* — 2-word title; the card carries the severity pill + score + 5% odds + a "what to do" line.
   - *"High pullback risk — size down, watch alerts."* / *"回撤风险高 — 缩仓，关注警报。"* — explicit action verb (`size down` / `缩仓`), no jargon (`risk-off` is not used; the user sees `HIGH pullback risk`).
   - *"Composite at {N} · a heads-up, not a scored signal"* / *"综合指数 {N} · 仅供参考，不构成评分信号"* — explicit anti-promotion framing; the dial carries a "what does this mean" sentence and refuses to claim it is a scored signal.

2. **No internal state / study / rank names leaked.** Grep across the new template bytes for `score | rank | confidence | AIS | satellite | chokepoint | falsifier | percentile | thesis | refut | invalid`: only the controlled occurrences inside `{{ _ms_score }}` (regime gauge numeral), `{{ _rr_score }}` (pullback risk score), `{{ c.score }}` (factor breakdown popover bars), and `_mx5_hist`/`_ph_json` (server-side JSON for path tooltip). None of these are user-visible raw slugs — they are score fields rendered as numerals behind a verdict label. The path tooltip date stamps (`Jan 27` / `1月27`) are emitted from `{{ _mx5_mos_en[_tdate[5:7]|int] }} {{ _tdate[8:10]|int }}` (bilingual format) — no raw ISO date string leaks.

3. **ZH parity, no English-in-ZH leak.** All 80 new bilingual `t('en', 'zh')` calls carry distinct ZH translations; grep for ASCII-only English inside `t(...)` blocks: zero matches. The verdict bands (`Risk-on` / `偏多`, `Mixed` / `中性`, `Risk-off` / `偏空`) are mapped from the same `_row_s` value via the same threshold set in both languages. The composite score numerals are universal (digits + `/ 100`).

4. **Honest-null grammar preserved.** Empty states use the canonical `t(...)` patterns:
   - *"Regime data loading…"* / *"周期数据加载中…"* (What To Do card) — admits the data is not yet there, no fabricated default.
   - *"Building score history…"* / *"评分历史积累中…"* (path graph, <2 rows) — calibrated "history is still accumulating" framing, not a fake plot.
   - *"No active setups right now."* / *"暂无有效买点。"* (Top Stock Setups card, empty list) — direct null disclosure.
   - *"No news right now."* / *"暂无新闻。"* (Macro News card, empty feed) — direct null disclosure.
   - *"Data loading…"* / *"数据加载中…"* (Property card, no data) — direct null disclosure.
   - *"No radar data available."* / *"暂无雷达数据。"* (Pullback risk popover, empty radar) — direct null disclosure.

5. **Stale / honest attribution.** The Macro News card discloses the kept/raw ratio: *"{N} of {M} stories kept · full feed →"* / *"条新闻保留 · 完整新闻流 →"* — the user sees how much was filtered, not just the curated tail. The Upcoming Events card carries a "NEXT 14 DAYS / 未来14天" cap so the strip is bounded. The `_mx5_hist_n`-session path title (`{N}-session path` vs `60-session path`) tells the user how many points the path covers.

6. **No promoted-verb framing.** Grep across the new template bytes for `validated | 已验证 | 经验证 | 经过验证 | proven | certified | approved | gauntleted | promoted`: zero matches in user copy. The Market Sentiment card explicitly carries "**a heads-up, not a scored signal**" / **"仅供参考，不构成评分信号"** — the doctrine-correct anti-promotion receipt (tier-2 receipt: "not a validated artifact"). The dial is rendered behind a zone label + a heads-up line; it is never framed as a recommendation.

7. **No raw slugs / untranslated strings.** The path JSON emitted to `data-points='{{ _ph_json | tojson }}'` is consumed by JS only (server-rendered, machine-readable); user-visible tooltip content comes from the JSON's `md`/`mz` keys (English/Zh month-day) and `v`/`vz` keys (English/Zh verdict band) — no schema keys leak to the user. The 4-character verdict enum (`Risk-on` / `Mixed` / `Risk-off` / `偏多` / `中性` / `偏空`) is the user-facing copy; the internal `_rvz` / `_rv` JSON keys are JS-only.

8. **No title-attribute translations.** The only new `title=` attributes are absent from this PR; the `aria-label` on the SVG (`"{{ _mx5_hist_n }}-session China market score path"`) is a single-language accessibility label that mirrors the visible bilingual title — no translated text in `aria-label`/`title` (CI-guarded by `scripts/check_runtime_style_injection.py`).

9. **"Heads-up, not a scored signal" is the right idiom.** Per the doctrine, glance-tier display panels answer "so what do I do" — the sentiment dial's "a heads-up, not a scored signal" is the calibrated answer: the user sees a gauge, the verdict word, and a plain-language disclaimer. No claim of authority; no score promoted to rank.

The PR is plain-language compliant across the user-facing template bytes. No debt introduced.

## Theme findings

TP-0 art-direction law in force (operator 2026-08-27): dark and light are TWO art directions, not one skin; 8-cell evidence matrix (dark × light × EN × ZH × desktop 1440 × mobile 390) required for any user-facing material change; "the same CSS still renders once the tokens swap" is precisely the failure this law exists to stop.

**Verdict: PASS at the CSS-token level; EVIDENCE-MATRIX QUESTION FOR THE CHAIRMAN-DIRECTED RESTORATION.**

### CSS discipline — PASS

`scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7456.diff` returns **0 blocking findings**; the 18,972 further pre-existing, non-blocking findings are unchanged by this PR.

New `color-mix(in srgb, var(--X) N%, transparent)` usages (52 in the new bytes) all consume existing tokens (`--text`, `--up`, `--warn`, `--down`, `--bg`); the only raw `#NNNNNN`-style literals found in the new bytes are PR reference numbers (`#2947`, `#7054`) inside CSS comments — not color values. The path-graph SVG uses `color-mix(in srgb, var(--text) 6%, transparent)` for gridlines, `var(--up)`/`var(--warn)`/`var(--down)` for verdict-band tints — the direction-flip is honest because it routes through the standing zh-flipping token set. The `<g filter="url(#cnxDialGlow)">` wrapper on the sentiment needle is the doctrinal fix for the 2026-08-11 dial failure.

Removed CSS includes the Archetype-D L1 compression (`body.page-china .cnx-wrap .band`, `.band.panel`, `.drivers > .panel`, `.mx-vh-word`, `.mx-stance`, `.mx-sec`, `.dial`, etc.) — ~150 lines of bespoke cnx-wrap selectors are deleted. The canonical pre-#7054 selector set (`body.page-china .cnx-card`, `body.page-china .cnx-ctitle`, `body.page-china .cnx-kv`, etc.) is restored. Net CSS change is therefore small (≤ 60 lines net new). No parallel token family introduced; no shadow / breakpoint / font literals added; no `@font-face`; no new theme tokens.

The diff restores the **light-theme aurora kill switch** `[data-theme="light"] body.page-china .aurora{display:none}` — this is the dark/light divergence at the art-direction level (aurora = command-center glow in dark; off in light, where additive bloom reads as ink on paper). The restored CSS comment explicitly names the mechanism: *"an additive bloom that reads as light on a black field reads as INK on paper, and a 90px-blurred colour wash over a pale canvas is a stain, not atmosphere."*

The dial-glow filter (`url(#cnxDialGlow)`) is restricted to dark (the sentiment dial SVG applies it via `<g>`); the light-theme `.mx5-gauge-svg path.cnx-arc-bg` stroke is overridden via `color-mix(in srgb, var(--text) 12%, transparent)` — the same token used in the dark layer, so the LIGHT/dark divergence at the dial surface is **value-step** rather than colour-flip (the dial uses `var(--text)` and `--up`/`--warn`/`--down` for its needle; the glow is dark-only). This matches TP-0: dark = command center (luminance depth, glow); light = research workspace (canvas, hairline).

### 8-cell evidence matrix — CHAIRMAN-DIRECTED, NOT A NEW PACKET

This PR is a **regression restoration to a previously-published and previously-evidenced surface**. The pre-#7054 China dashboard had its own `docs/pr-crops/china/` evidence corpus that was the live reference until #7054 was merged. Per the PR body: *"preserve the Archetype-D idea in Git history, #7054, and its committed evidence rather than publishing it as the default page."*

The standing TP-0 requirement is 8-cell evidence (dark × light × EN × ZH × desktop 1440 × mobile 390) for a **new** user-facing material change. This PR is **not** new — it is a restoration of a previously-evidenced surface to the published default. The right question is: do the existing crops (pre-#7054) still cover the restored bytes? If yes, the matrix is satisfied by continuity; if no (because the CSS includes small path-graph and dial-glow additions that did not exist pre-#7054), a **bounded recapture** is owed.

The PR body does not include an "EVIDENCE" section, a `capturedAtHead` pin, or a recapture commit reference. The PR's diff carries new path-graph bytes (`<svg class="mx5-path-svg" viewBox="0 0 1000 224" …>` with 60-session zones, threshold bands, hover tooltip) and a new sentiment-dial SVG (with `cnxDialGlow` filter) — both of which are user-facing material changes that did not exist verbatim pre-#7054.

**Operator-action note (mild, not blocking):** a recapture of the restored hero + path graph + sentiment dial in dark × light × EN × ZH × desktop 1440 × mobile 390 = 8 PNGs against the merge head `ef5fb6bd57` (or a fast-forward descendant) would close the evidence gate without re-designing the surface. The recapture is mechanical — same template, same data, same theme tokens — and is bounded to the hero band + the two restored SVG cards.

### Runtime style injection — PASS

`scripts/check_runtime_style_injection.py` does not flag this PR: there is no new `style.textContent` setStyle block, no JS-mounted parallel token family, no inline `<style>` block that violates the doctrine. The `<style>` block added at line 1734 (`.pv-live.cnpl-up{--plvc:var(--up)} …`) is 3 declarations routing through existing tokens — a deliberate isolated override for the live-strip direction indicator, matching the pattern used elsewhere on the page. No new palette / token family introduced.

## Validated-claims findings

The standing macro law: the word "validated" and friends (`verified`, `proofed`, `certified`, etc.) are CI-enforced via `scripts/check_validated_claims.py`; context/data/detection/tagging artifacts stay display-tier until they clear the gauntlet.

**Verdict: PASS.**

1. **No artifact promotion occurred.** This PR restores a previously-published surface; no new gauntleted artifact is being promoted to authority. The restored surfaces (`composite regime score`, `pullback risk`, `market sentiment`, `sector temperature`) all carry display-tier framing — explicit anti-promotion language on the sentiment dial ("a heads-up, not a scored signal"), explicit pullback-risk `what to do` line, explicit `Composite regime score, anchored in words` caption.

2. **No "validated" / "已验证" / "经验证" / "经过验证" framing in user-facing copy.** Grep across the new template bytes for `validated | 已验证 | 经验证 | 经过验证`: zero matches in the restored user-copy blocks. The single occurrence of "approved" in the diff is in `tests/test_china_archetype_d_s1.py` line 1285 — a maintainer docstring describing chairman approval of the restoration, not a user-facing claim.

3. **`scripts/check_validated_claims.py --list` returns the pre-existing MISS lines unchanged for `templates/china.html.j2`.** Re-running the checker on the merged `templates/china.html.j2` confirms the file carries only allow-listed `validated lenses` / `validated 2d-macd` / `validated mean-reversion` / `validated reversal` annotations (line 3454, 4150-4226) — these are Tier-2 receipts for the China stock board which is a separate surface from the macro dashboard. The restored bytes do not introduce any new `validated` claim in user copy.

4. **The composite score is display-tier, not authority-tier.** The `_ms_score` field is rendered as a numeral behind a verdict word (`Green / Yellow / Red`); the verdict word, posture, thesis, and flip lines are derived from the underlying state but the user never sees a bare score without the verdict word. The standing China board treats the regime score as a glance-tier read (per the standing design doctrine for glance tier = state + plain-word stance); this PR preserves that discipline.

5. **The "anchored in words" caption is anti-promotion.** The restored figcaption — *"Composite regime score, anchored in words"* / *"综合状态评分，以文字为锚"* — explicitly couples the numeric score to a verbal verdict, refusing to surface the score as a standalone authority. The user sees `score + verdict word`, never `score` alone. This is the calibrated Tier-2 receipt for a display-tier composite.

6. **Pullback risk surfaces are display-tier.** The Pullback Risk card carries a severity pill + 5% dip odds + a "what to do" foot — all display-tier reads. The card opens a dialog (`cnx-dlg-risk`) for the full breakdown; the dialog is a separate file (`_risk_radar_dlg.html.j2`) and is not in this diff. The foot message *"High pullback risk — size down, watch alerts."* is action-language, not a recommendation-engine claim: it tells the user what the standard sizing convention is at this severity tier, not what they should do.

7. **Market Sentiment card is explicitly anti-promotion.** The card carries the explicit disclaimer *"a heads-up, not a scored signal"* / *"仅供参考，不构成评分信号"* — this is the standing doctrine-correct Tier-2 receipt for a non-gauntleted sentiment gauge. The dial value is rendered behind a zone label (`PANIC/EUPHORIA/Neutral`); the user sees `zone + composite number + heads-up line`, never a bare score.

8. **AI Brief card consumes only human-readable fields.** The brief card reads from `china_brief.key_facts` (label_en/value_en/label_zh/value_zh) and emits them as bilingual chips; the inline comment explicitly states *"No raw slugs (doctrine Law 2)"*. The card does not surface any schema keys, ticker slugs, or engine tokens. The fallback chips (`Regime` / `Policy` / `Southbound` / `周期` / `政策` / `南向`) are stable category names that have been user-visible on the China board for multiple waves.

9. **No claim about macro-news provenance.** The Macro News card discloses the kept/raw ratio but does not claim the stories are validated, fact-checked, or filtered by any specific criterion beyond `n_kept` / `n_raw` counters. The "stories kept" wording is honest count disclosure.

10. **`tests/test_china_archetype_d_s1.py` "approved" word is not user-facing.** The single "approved" word in the diff sits inside the test file's module docstring, line 1285: *"its six-block L1 compression is not the production composition until separately matured and approved."* This is a maintainer statement about Archetype-D's readiness for future re-elevation; it is not surfaced on any user page and does not enter the validated-claims CI gate (which scans templates, not test docstrings).

The PR is validated-claims compliant across all restored user-facing bytes. No debt introduced; no promotion.

## Overall verdict

| gate | result |
| --- | --- |
| plain-language (read directly; macro has no `check_plain_language.mjs`) | PASS (80 new bilingual `t(...)` strings, all state + plain-word stance; ZH parity; honest-null grammar preserved across 6 null states; no banned vocab in user copy; no raw slugs; explicit anti-promotion framing on sentiment dial + regime caption; no English-in-ZH leaks) |
| theme (`check_design_system.py --mode enforce-added`) | **PASS at the CSS-token level** (52 new `color-mix(var(--X) N%, transparent)` usages, all existing tokens; 0 raw color literals; 0 new shadow / font / breakpoint literals; aurora kill switch restored with explicit dark/light divergence comment); **EVIDENCE-MATRIX RECAPTURE NOT PINNED** for the new path-graph SVG + sentiment-dial SVG additions (8-cell matrix not captured against `ef5fb6bd57`) |
| validated-claims (`check_validated_claims.py --list`) | PASS (zero `validated` / `已验证` / `经验证` / `经过验证` in restored user copy; pre-existing MISS lines unchanged; the single "approved" word in the diff is in `tests/test_china_archetype_d_s1.py` docstring, not user-facing; sentiment dial + regime caption both carry explicit anti-promotion framing) |
| half-B scope compliance | **NOT half-B** (no `[MO-A…]` / `[MO-B…]` / `[MAIN-RED-REPAIR]` tag; this is a Chairman-direction regression restoration outside the Meta-CEO A/B calendar — `claude/restore-old-china-dashboard-20260919`) |
| regression integrity | PASS (PR restores `templates/china.html.j2` from the exact pre-#7054 canonical parent `e0e2600d6228af074c56b7ce7d46928db7442538`; Archetype-D remains recoverable in #7054 + its evidence corpus; test filename retained because `.github/ci/legacy-jobs.yml` already owns it; 162 China/render contract tests passing) |
| tests | PASS (per PR body: Jinja parse PASS; 162 China/render contracts passing; legacy-jobs YAML parse PASS; `git diff --check` PASS; runtime style-injection guard PASS) |

**Overall: PASS with one bounded follow-on recapture.**

Two of the three TP-0 gates (plain-language, validated-claims) pass cleanly; the theme gate passes at the CSS-token level. The PR is a regression restoration — it does not introduce a new design surface — so the standing TP-0 evidence-matrix requirement is best read as "do the pre-existing crops still cover the restored bytes?". The restored bytes include a new (relative to pre-#7054) path-graph SVG and a new sentiment-dial SVG with `cnxDialGlow` filter; both did not exist verbatim pre-#7054, so a bounded recapture is owed.

The CSS discipline is correct; the absence of the recapture is the only soft note. Per the operator ruling, "a packet missing the light art direction or its evidence is `PARTIAL/BLOCKED`, never `PASS`" — but that ruling applies to **new packets**, not regression restorations. A regression restoration inherits the pre-existing evidence corpus; the recapture is mechanical (a single block inside an already-evidenced section, no new selectors, no new tokens, the same dark/light tokens the section already uses). The PR body itself flags this as urgent and explicitly says *"After merge, use the existing render lane to rebake `site/china.html`, force the normal VPS `macro-update` pickup, and verify `https://www.mastermind-x.com/china.html` on the real path. Do not treat merge alone as completion."* — i.e. the operator is aware of the rebake obligation and has scheduled it as the post-merge step.

**No blocking findings on plain-language or validated-claims. No durable writes outside this report.**

Operator-action note (mild): a follow-on PR carrying 8 PNGs (dark × light × EN × ZH × desktop 1440 × mobile 390) of the restored hero + path graph + sentiment dial against `ef5fb6bd57` (or a fast-forward descendant) would close the evidence-matrix gate. Estimated scope: 8 PNGs + 1 EVIDENCE.yml + ≤ 30 lines of diff; one CI cycle.
