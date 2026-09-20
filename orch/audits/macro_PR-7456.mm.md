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