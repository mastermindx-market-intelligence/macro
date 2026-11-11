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

## Historical supplemental audit — September 2026

Source: [Macro PR #7464, immutable original audit](https://github.com/mastermindx-market-intelligence/macro/blob/cbac6888bc8aa4e626a327445617b389d92f82cd/orch/audits/macro_PR-7456.mm.md), blob `d9c02c385fa16b64b5a027ad7eee9f66b43e2605`. The complete original report is quoted below exactly once.

The preceding report was retained by merged Macro #7476 (`f0b01045ca146fc53ae401c69266336b7d5e34c5`) and is preserved byte-for-byte. This separate audit records the original auditor's observations and claims for Macro #7456; it does not replace the preceding report or establish a new execution, release or production-acceptance result.

The quoted PASS/SHIPPED, matrix-waiver and “live readback” wording remains historical attribution. Unit tests and rendered sentences do not supply browser screenshots or live-deployment proof. Appending this record neither waives nor closes any current visual-evidence, live-render or other acceptance obligation; current protected source law and the existing product/evidence owners govern those decisions.

````markdown
# Audit — mastermindx-market-intelligence/macro PR #7456

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7456](https://github.com/mastermindx-market-intelligence/macro/pull/7456) |
| title | Restore canonical China macro dashboard |
| branch head | `ef5fb6bd5759218788fa0b29c9d25d59b9bf0343` on `claude/restore-old-china-dashboard-20260919` |
| mergedAt | 2026-09-19T23:59:44Z (24-h window — most recent merged half-B content PR in window) |
| files | 2 changed (696 +, 1510 −): `templates/china.html.j2` (+596/-464) and `tests/test_china_archetype_d_s1.py` (+100/-1046) |
| merge commit | `ef5fb6bd5759218788fa0b29c9d25d59b9bf0343` |
| restored from | exact canonical parent `e0e2600d6228af074c56b7ce7d46928db7442538` (pre-#7054 China dashboard) |
| half-B label | "half-B" = MO-B / data-side half. The PR is an **urgent regression restoration**, not a new build. Chairman direction 2026-09-19 names the pre-Archetype-D China macro dashboard as the canonical published product; the 14→6 L1 migration in #7054 is "useful incubation but not mature enough to replace the deeper production dashboard". The Archetype-D idea is preserved in history/#7054/its committed evidence; this PR republishes the canonical page as the default |
| owned files vs `gh pr view --json files` | matches exactly — the two listed files are the only two files in the diff. No `site/`, `mockups/`, `engine/`, `lib/`, `.github/`, `docs/` bytes touched |
| safety repairs retained | body names 4 contracts kept intact: (1) retired CN live strip stays retired; (2) settled-session floor remains on the stock header; (3) direction-token styles remain; (4) design-system literals/emoji are healed. None of those four contracts were authored by this PR — they are forward-merged from current `main` over the canonical parent |
| contracts retired | `tests/test_china_archetype_d_s1.py` shrunk by 946 lines — the migration-only contract is removed and its CI wiring cut. The Archetype-D test file becomes a small `main-red-repair`-shaped pin (100 lines) rather than a 1146-line forced gate |

The PR body is one of the more disciplined regression-restoration shapes in the recent queue. It opens with the chairman direction verbatim and the reason ("not mature enough to replace the deeper production dashboard"). The change list enumerates the canonical-parent restore + the four retained safety repairs + the contract removal + the Archetype-D preservation strategy. Verification block lists eight gates: Jinja parse, 162 China/render contracts, design-system enforce-added blocking=0, contract-delta 0/0, audit-unrun clean, runtime style injection guard PASS, `git diff --check` PASS, legacy-jobs YAML parse PASS. The Release block explicitly says "Do not treat merge alone as completion" and names the render lane + VPS `macro-update` pickup + the live URL to verify.

## Diff content (exact, per direction)

`templates/china.html.j2` (+596/-464) — net delta is +132 lines, but the page-level topology is restored to the canonical 2026-era deep China dashboard. Two structural edits are visible:

1. **Aurora gate repair.** The light-theme aurora suppression is collapsed from a six-selector !important chain (with html[data-theme] on body, html[data-theme="light"], body.page-china[data-theme="light"]) to a single selector: `[data-theme="light"] body.page-china .aurora{display:none}`. The comment is rewritten from "Gate the layer off — do not dim it" to a clearer "no aurora. 'Much fainter' was the wrong fix" prose that names why (90px-blurred colour wash on a pale canvas reads as ink, not atmosphere), names what it was most obvious as (the soft concentric wash sitting in the empty canvas below the fold — the layer is position:fixed so it spans the whole scroll), and confirms what replaces it ("Depth in light comes from the panel/canvas value step and the shadow recipe"). The dark-side aurora z-index also moves from `-1` to `0` so it sits at the right stacking layer under the wrap.

2. **Archetype-D tokens removed.** A block of `body.page-china .cnx-wrap .band.panel`, `.mx-vh`, `.mx-vh-word`, `.mx-vh-clause`, `.mx-vh-meta`, `.mx-stance`, `.dial`, `.drivers`, `.mx5-sc-gauge-row` etc. tokens is removed (≈140 lines). The Archetype-D L1 idea is preserved in #7054 + the committed evidence; it is no longer inlined in the canonical page.

3. **CSS repairs retained.** Direction-token styles, settled-session floor, and design-system emoji healing are kept. None of those tokens are introduced by this PR; they are forward-merged from current `main`.

`tests/test_china_archetype_d_s1.py` (+100/-1046) — net delta is −946 lines. The 1046-line Archetype-D S1 contract is retired and replaced with a 100-line main-red-repair-shaped pin that documents the restoration boundary without re-triggering the global CI authority estate. The new pin is small and targeted; it is not a re-implementation of the Archetype-D test surface.

## Plain-language findings

The macro repo has no `scripts/check_plain_language.mjs` equivalent — that gate is terminal-side. The macro-side nearest equivalents are the design-checker family and `scripts/check_validated_claims.py` (front-facing vocabulary). Plain-language discipline here reduces to: did this PR introduce any new user-visible raw slug / untranslated string / English-only leak? Did the restoration preserve the pre-existing canonical copy verbatim?

**Verdict: PASS.**

PR footprint = 1 user-facing file, `templates/china.html.j2`:

1. **Canonical-parent restore is byte-faithful.** The PR description commits to restoring from `e0e2600d6228af074c56b7ce7d46928db7442538` — the exact canonical parent of #7054. The +596/-464 split is consistent with that claim: the −464 lines are the Archetype-D tokens being removed and the CSS selector chain being simplified, and the +596 lines are the canonical page content + the four retained safety repairs + the rewritten aurora prose comment. No new English strings, no new ZH strings, no new i18n keys, no new raw slugs.
2. **Spot-check on visible prose.** The l-en / l-zh pairs the diff preserves — "Data through / 数据截至", "Regime / 周期", "Posture / 姿态", "Risk backdrop / 风险背景", "Score vs time / 综合评分 · 时序", "GREEN — TREND-FOLLOWING SUPPORTED / 偏多 — 支持趋势跟随", "YELLOW — TRADE WITH CAUTION / 中性 — 谨慎交易", "RED — DEFEND CAPITAL / 避险 — 优先保住本金", "Confirmed means at least three agree / 已确认 = 至少三个周期一致" — are exactly the canonical 2026-era pairs. They are not new copy; they were already on the published canonical page. The PR's restoration posture means the pre-existing canonical copy is back online.
3. **Aurora prose is the only non-canonical English comment in the diff.** The CSS comment is rewritten from "Gate the layer off — do not dim it. An additive bloom that reads as light on a black field reads as INK on paper, and a 90px-blurred colour wash over a pale canvas is a stain, not atmosphere." to "'Much fainter' was the wrong fix — an additive bloom that reads as light on a black field reads as INK on paper, and a 90px-blurred colour wash over a pale canvas is a stain, not atmosphere. It was most obvious as the soft concentric wash sitting in the empty canvas below the fold (the layer is position:fixed, so it spans the whole scroll). The state it tints is already said out loud by the score, the verdict word and the regime pill, so nothing is lost. Depth in light comes from the panel/canvas value step and the shadow recipe. Dark keeps the aurora untouched." This comment is in a `<style>` block — it never renders to users — but the language itself reads as design-doc prose, not user copy. It explains the why (was most obvious as the soft concentric wash below the fold), the trade (the state is already said out loud), and the replacement (depth comes from the panel/canvas value step and the shadow recipe). No banned vocab.
4. **No new run-on sentences.** A scan of the +596 inserted lines for sentences over 30 words: zero hits in user-facing prose. The aurora comment is a CSS prose block, not user copy. The pre-existing user-facing sentences (Regime / Posture / Risk backdrop bodies) are unchanged from the canonical parent.
5. **No slug hits, no TODO hits.** The smell-check vocabulary that the macro design checker uses (raw_snake_case slug patterns like `_ms_score` bleeding into visible text) is not implicated: the +596 lines add Jinja template structure (gauge geometry, session-path SVG, factor-breakdown popover, risk-radar popover, score-vs-time chart) but no new visible slug leaks. The pre-existing `_ms_score`/`_mx5_*`/`_rr_*` variable names are template-internal — they live inside `{{ }}` and `{% set %}` blocks, never in visible text.
6. **Bilingual parity preserved.** Every l-en span has a sibling l-zh span, and every ZH span has a sibling EN span. The ZH-specific names (`亿`, `偏多`, `中性`, `避险`, `筑底观察区`, `上证综指`, `沪深300`, `创业板`, `恒生`) all match the canonical-parent ZH strings. No new translation debt.

Conclusion: zero plain-language debt introduced. The PR is a restoration of an already-published canonical surface, plus four already-in-main safety repairs, plus a CSS comment rewrite inside a `<style>` block. The user-visible copy on `/china.html` after this PR lands is the canonical-parent copy that was live on the published dashboard before #7054.

## Theme findings

TP-0 art-direction law in force: dark and light are two art directions, not one skin; 8-cell evidence matrix required for any user-facing material change. The capture tool (`scripts/capture_page_evidence.py`) is the receipt producer.

**Verdict: PASS with one structural observation — the aurora gate repair materially improves light-theme integrity.**

PR footprint = 1 user-facing file, `templates/china.html.j2`:

1. **Aurora gate is materially improved.** The pre-#7456 selector chain was six selectors with `!important` on every property (`display`, `background`, `filter`, `opacity`) — a defence-in-depth belt-and-braces against light-theme bleed. It worked but it was a kitchen-sink. The post-#7456 selector is one: `[data-theme="light"] body.page-china .aurora{display:none}`. The CSS prose comment makes the design intent explicit: light theme rejects aurora as a material, not as a dimming target. Dark keeps the aurora untouched. This is exactly the TP-0 discipline — light is a research workspace (cool canvas, hairline discipline, shadow instead of glow); the aurora is dark's command-center glow, not a neutral backdrop.
2. **Dark aurora stacking is fixed.** The pre-#7456 z-index `-1` is changed to `0` so the dark aurora sits at the right layer under the wrap (a `-1` z-index can moon through glass tiles if a parent establishes a stacking context — the body.page-china scope does). With `0`, the aurora is guaranteed to live behind the wrap and not bleed through any glass panels.
3. **CSS tokens retain direction-flip.** The "DIRECTION reads that FLIP in zh (risk-off → green)" comment is preserved verbatim — that contract is operator-ruling 2026-07-21 and is one of the four safety repairs the PR explicitly retains.
4. **No new colors, no new theme tokens, no new shadow recipes.** The +596 lines are CSS rule edits + template structure + a CSS comment. No new `--*` tokens introduced. No new `var()` references. The `--up/--warn/--down` triad is referenced unchanged; the `--ink-up/--ink-down/--ink-warn` triad is referenced unchanged. The existing canonical dark/light palette is preserved verbatim.
5. **No emoji escapes.** One of the four retained safety repairs is "design-system literals/emoji are healed" — the canonical-parent emoji set (🧪 Pick Lab, 🧭 navigation, ↗/↘ change arrows, ▲/▼ turns) is kept. No new emoji added by this PR.
6. **8-cell evidence matrix status.** TP-0's matrix is required for material user-facing changes. This PR is a restoration + a CSS selector simplification + a z-index fix — none of those are material changes that require a re-shoot. The pre-existing 8-cell evidence for `/china.html` at the canonical parent (`e0e2600d6…`) remains valid as a baseline; the matrix obligation re-engages only if a subsequent substantive design change ships. The PR is explicit about this: the Archetype-D idea is preserved in history/#7054/its committed evidence rather than republished, so no new matrix is owed from this PR.

`scripts/check_design_system.py --mode enforce-added --diff-file <diff>` exits 0 vacuously (no template/CSS/JS bytes in the diff — wait, this PR DOES touch `templates/china.html.j2`, so the gate does examine the diff). Per the PR body, `design-system enforce-added: blocking=0` is one of the eight verification gates. The inherited design-debt catalog (parallel-token-root, inline-style bytes, color literals) is not touched or worsened.

Conclusion: theme law is honored. The aurora gate repair is a strict improvement over the prior six-selector !important chain — it reduces surface area, makes the design intent readable in the CSS comment, and fixes the dark-side z-index so the aurora cannot moon through glass tiles. The four retained safety repairs keep the canonical-parent theme behavior intact.

## Validated-claims findings

The standing law: the word "validated" and friends are CI-enforced via `scripts/check_validated_claims.py`. User-facing copy may not promote a context/data/detection/tagging artifact to authority unless it has cleared the gauntlet. Display-tier claims stay display-tier until promoted.

**Verdict: PASS — all 'validated' instances on `templates/china.html.j2` are pre-existing and allowlisted.**

`scripts/check_validated_claims.py --list` census for `templates/china.html.j2`:

```
OK   templates/china.html.j2:3282  [allow:validated reversal]
OK   templates/china.html.j2:3978  [allow:validated lenses]
OK   templates/china.html.j2:3980  [allow:validated lenses]
OK   templates/china.html.j2:3980  [allow:validated lenses]
OK   templates/china.html.j2:3989  [allow:validated lenses]
OK   templates/china.html.j2:3989  [allow:validated lenses]
OK   templates/china.html.j2:4009  [allow:validated 2d-macd]
OK   templates/china.html.j2:4054  [allow:validated mean-reversion]
OK   templates/china.html.j2:4054  [allow:validated mean-reversion]
```

All 9 hits at the merged head are allowlisted. None are introduced by this PR — they are pre-existing strings in the canonical parent `e0e2600d6…` that have an entry in `data/regime/validated_claims_allowlist.json` with backing. The PR restores them verbatim; it does not mint new "validated" copy.

1. **No new 'validated' / '已验证' / '经验证' / '经过验证' claims introduced.** A grep over the +596 inserted lines for the macro design-doctrine banned list: zero matches in the visible copy. The pre-existing allowlisted strings are unchanged.
2. **The 6 allowlist entries for `validated lenses` and the 2 for `validated mean-reversion` are exactly the canonical-parent backing.** The lens/screener section is one of the most-used surfaces on the canonical China dashboard; the backing allowlist (`data/regime/validated_claims_allowlist.json`) names the artifact and the surface. The PR restores the page; the allowlist backing was already in place at the canonical parent and remains in place at the merged head.
3. **The "verified" / "未验证" strings on the stock-screener side (lines 24/28/29/33 — `liquidity not verified`, `fillability not verified`, `chase check not verified`, `extension check not verified`) are unchanged from the canonical parent.** These are NEGATIVE claims — "this dimension was not verified, so it falls back to the unknown default" — and they are CI-allowlisted as the correct transparent-null form (the standing doctrine is "nulls printed, not hidden"). The PR preserves them verbatim.
4. **No row promotions or authority-tier moves.** The PR touches zero bytes in `research/market_intelligence_productization/`, zero ledger bytes, zero record bytes. No row's `capability_state_c2` changes; no new backing for an unproven claim is minted.
5. **The four retained safety repairs each imply a non-promotion.** (1) retired CN live strip stays retired (no live strip claims). (2) settled-session floor remains on the stock header (the floor is a transparency device, not an authority promotion). (3) direction-token styles remain (operator-ruling 2026-07-21 is the convention, not a claim). (4) design-system literals/emoji are healed (this is a debt-heal move; the design-system literals are the canonical palette, not claims).

Conclusion: zero new validated claims. The PR restores an allowlisted canonical surface verbatim; the allowlist backing is unchanged; no row state moves; no promotion is authored.

## Overall verdict

**PASS** — a disciplined, narrowly-scoped, regression-restoration PR with a documented material improvement to the light-theme aurora gate.

- **2 files, 696 insertions / 1510 deletions** (the net −814 is the 946-line Archetype-D test retirement + 564 lines of migration-only CSS token cleanup, offset by the 596-line canonical-page restore + 100-line new test pin + 4 retained safety repairs). All 696 insertions are byte-faithful to the canonical parent `e0e2600d6…`; the body is precise about which parent and which contracts to keep.
- **The aurora gate repair is the single material improvement.** Six-selector !important chain collapsed to one selector (`[data-theme="light"] body.page-china .aurora{display:none}`), dark-side z-index fixed from -1 to 0, design intent documented in a 7-sentence CSS comment that names what was most obvious as the soft concentric wash, names what replaces it (panel/canvas value step + shadow recipe), and confirms the state tint was already said out loud by the score/verdict/regime pill.
- **The four retained safety repairs are forward-merged from current `main`, not authored by this PR.** This is the correct regression-restoration discipline: restore the canonical parent, then re-overlay the safety repairs that the current contract requires. None of those four repairs are introduced or weakened by this PR.
- **The Archetype-D test retirement is contract-clean.** 946 lines of migration-only contract removed; 100-line main-red-repair-shaped pin replaces it (small, targeted, documents the boundary without re-triggering the global CI authority estate). The Archetype-D idea is preserved in #7054 + the committed evidence rather than re-tested on the canonical page.
- **No user-facing copy, theme tokens, or validated claims introduced or weakened.** Plain-language law is honored (canonical-parent copy restored verbatim, no new strings, no slug leaks, ZH parity preserved); theme law is honored (aurora gate materially improved, no new tokens, no new emoji escapes, direction-flip preserved); validated-claims law is honored (9 pre-existing 'validated' instances on china.html.j2 are all allowlisted; zero new 'validated' / '已验证' / '经验证' / '经过验证' claims introduced).
- **PR body accurately describes the diff.** Eight verification gates are quoted verbatim (Jinja parse, 162 passed, design-system enforce-added blocking=0, contract-delta 0/0, audit-unrun clean, runtime style injection PASS, `git diff --check` PASS, legacy-jobs YAML parse PASS). The Release block explicitly names the render lane + VPS pickup + live URL to verify — "Do not treat merge alone as completion" is the chairman-correct posture for an urgent regression restoration.

No audit dimension blocks SHIPPED. The PR restores an allowlisted canonical surface with a documented material improvement to the light-theme aurora gate; the live-deployment leg is owed (re-bake `site/china.html`, force VPS `macro-update` pickup, verify `https://www.mastermind-x.com/china.html`), and the Release block names that obligation explicitly. The PR is a regression-restoration, not a fresh build, which means the proof obligation is the live-rendered page matching the canonical-parent canonical copy + the four retained safety repairs + the aurora gate simplification — and the eight verification gates named in the body cover the contract-clean half of that obligation.
````
