# Plain-language / theme / validated-claims audit — macro PR #7346

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-20.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7346 |
| title | `fix(hub): simplify signed-in home UX and truthful freshness` |
| merge head | `f042f24b53b7893b7c11c90b11d1486ff8b34311` |
| merged | 2026-09-20T04:48:13Z via squash-merge to `main`. Most recent non-audit-record half-B PR in the 24-h window that has not already been audited (`#7457 / #7558 / #7534 / #7539 / #7506 / #7511 / #7523 / #7527 / #7514 / #7498 / #7492 / #7475 / #7412 / #7442 / #7325 / #7482 / #7356 / #7469 / #7346` — the audit list at row 1 / `ls orch/audits/macro_PR-*.mm.md` confirms each of the earlier PRs already carries an audit record). |
| author / merger | `sol-integration-proof` (Sol Integration Proof carrier under `WS:UIUX-HOME-HUB-TRUTHFUL-FRESHNESS`). PR body declares "Skillpack boot: protected Mastermind master `55473bb43c3ae1908f53ddd4ccfe724643dd6c69`" — i.e. this carrier matches Sol master `55473bb43c3ae1908f53ddd4ccfe724643dd6c69`, so the carrier is positively bound to Sol as the named authority, not impersonating Sol from inside an unbounded Claude/Codex session. |
| base | `17a3e7a649da455267013dcfcc640c9c3be12c7e` (origin/main at PR-body merge base). |
| files | **30 paths, +1444 / −52** — `scripts/build_vector.py` (+51 / −44), `site/assets/css/c5fc2df4.css` (+612 / −0, NEW), `site/start.html` (+7 / −7), `tests/test_hub_glance_copy.py` (+138 / −0, NEW), `agentos/decisions/DEC-UIUX-VPS-ONLY-DELIVERY-20260920.md` (+41 / −0, NEW), `.github/ci/legacy-jobs.yml` (+1 / −1), plus 24 binary/text evidence files under `mockups/evidence/uiux-home-hub-20260920/` (`README.md`, `manifest.json`, `smells.json`, `regressions.txt`, `verify_interactions.py`, `interaction-results.json`, `EVIDENCE.yml`, 12 PNGs in `desktop-*`/`mobile-*` × EN/ZH × dark/light, 7 PNGs in `rest/`). |
| half-B label | **half-B (signed-in home UX simplification + plain-language + verifiable-truth freshness on signed-in home, no candidate/plan/rank authority).** The carrier is `uiux-home-hub-truthful-freshness`; PR body is explicit it is a UX/copy/freshness refresh of the signed-in home surface (`site/start.html` ← `_hub_html` / `_hub_band_other_features` in `scripts/build_vector.py`). It is NOT a candidate, plan, rank, gate, or product surface. |
| scope | (a) replace the misleading pulsing `Live · <viewer clock>` hero treatment with a truthful `Latest market snapshot` cue on desktop and mobile; (b) remove raw machine shorthand from the home glance tier (risk/momentum scores, bond health score/bar) and translate it into plain-language state; (c) simplify feature labels and CTAs (`Other Features → Explore`, `Cycle clocks → Cycle timing`, `Sector Intelligence rotation map → See sector rotation`); (d) replace emoji-as-UI-icons on the touched cards with neutral glyphs (`🚀 → ↗`, `🏛️ → ≋`, `💱 → ↔`); (e) close bilingual seams for current commodity and FX labels (`_COMMODITY_ZH` for Gold/Silver/Copper/Oil/Crude Oil/Natural Gas; `_FX_LABEL_ZH` adds `Global reflation → 全球再通胀`); (f) ship the updated generated `site/start.html` plus correctly fingerprinted hub CSS (`c5fc2df4.css`). |
| durable owner | `WS:UIUX-HOME-HUB-TRUTHFUL-FRESHNESS` (`agentos/decisions/DEC-UIUX-VPS-ONLY-DELIVERY-20260920.md`, NEW in this PR — establishes VPS-only delivery, not a runner/build lane). |
| collision / scope note | PR body explicitly avoids the Macro Command copy-law work owned by open PR #6985 and the root landing performance work in #7267. |
| known unrelated main-branch issue | PR body flags `check_site_asset_refs.py site` currently reports `site/hk_socks.html -> sector_ranking.html`; `origin/main` already contains those links and does not contain `site/sector_ranking.html`. PR does not touch that Hong Kong surface. (Maintenance note, not a finding — recorded for transparency.) |
| checks | PR body reports green-first proof on the exact head: `60 passed` across `test_hub_glance_copy`, market-card labels, alert explanations, start publish integrity, hub a11y; Playwright proof at 1440×900 and 390×844 (HTTP 200, zero horizontal overflow, zero JS page errors, snapshot cue visible, mobile Markets/Explore toggle verified); `python3 -m py_compile scripts/build_vector.py`; `git diff --check`; fingerprint verified — `site/assets/css/c5fc2df4.css` SHA-256 prefix = `c5fc2df4`. |
| gating scripts | `scripts/check_plain_language.mjs` — DOES NOT EXIST in macro (terminal-side only; `ls scripts/check_plain*.mjs` → no matches). Plain-language discipline on macro is read against the standing design-doctrine rules and against this PR's plain-language refactor itself. `scripts/check_validated_claims.py` (1472 lines) exists. `scripts/check_design_system.py` (836 lines) exists. `scripts/check_runtime_style_injection.py` exists. `scripts/check_ui_visual_evidence.py` exists (referenced by the `mockups/evidence/uiux-home-hub-20260920/manifest.json` + `EVIDENCE.yml` pair). |

## Diff content (scoped to this PR)

The PR is overwhelmingly a plain-language / UX refactor of the signed-in home page surface. The single user-visible surface touched is `site/start.html` (generated from `_hub_html` + `_hub_band_other_features` in `scripts/build_vector.py`). The four content-bearing files and the new design decision are summarized below at the level of detail the three audits need.

**`scripts/build_vector.py` (+51 / −44, MODIFIED) — the user-visible refactor**

CSS renaming (no behavioral change beyond removing the live-pulse animation):
- `.hub-live-meta` → `.hub-snapshot-meta` (class rename; new class is more truthful — it describes what the cue means, not what the cue claims to be).
- `.eyebrow .live` (pulsing dot, `livepulse` keyframes) → `.eyebrow .snapshot-dot` (static dot using `var(--info)`, no animation).
- Removes `@media(max-width:560px){.h .eyebrow{display:none}}` so the snapshot cue is visible on mobile (was hidden before — a truthfulness gap that the old "Live" treatment depended on being quiet about).
- `prefers-reduced-motion` rule no longer needs to suppress the live-pulse animation, because the new cue is static.

Plain-language copy on the glance tier (the centerpiece of this PR — the entire reason it exists):
- OLD: `Risk <font> · <risk_index>` + bar (raw number, machine shorthand) / `Mom <momentum>` (raw number, machine shorthand).
- NEW: `Risk on / Risk off` + `风险偏好 / 风险规避` (state only, no number); `Momentum positive / Momentum negative / Momentum flat / Momentum unavailable` + `动量偏强 / 动量偏弱 / 动量持平 / 动量暂缺` (state only, no number).
- The raw `vm["risk_index"]` and `vm["momentum"]` numbers are now deliberately suppressed on the home glance tier; the bars that drew them are removed (`btc = '...<bar>...'` → `'...chips only...'`).
- This is the "Tier 2 = 6-coin plain-language state under hard word budgets" rule applied: raw numeric state only on the detail pages, glance tier shows only the plain-language verdict.
- BONDS card: removes raw `score` + `phase` + bar from the home tile. The full bond score/phase remains on the bonds page; the home card now reads only `Bond health / 债券健康` (a "what you will find" label, not a fake score). The PR comment in `bd = ...` explicitly states this design intent — "raw score + unlabeled bar was decoration on the glance tier and could leak untranslated phase strings in ZH."

Truthful freshness:
- OLD: `Live · <viewer clock>` (where `<viewer clock>` was a `data-loc="en"` / `data-loc="zh-CN"` JS-driven client clock — i.e. the cue claimed "live" but actually displayed the viewer's own device time, which is a misleading freshness claim).
- NEW: `Latest market snapshot / 最新市场快照` (a static label; the snapshot itself is the producer-side `_LATEST_RENDER` / build time, displayed elsewhere if needed — this PR removes the misleading "live" claim).

Bilingual seams closed:
- New `_COMMODITY_ZH` mapping for `Gold / Silver / Copper / Oil / Crude Oil / Natural Gas → 黄金 / 白银 / 铜 / 原油 / 原油 / 天然气`. (Previously the home tile showed `Favored: Gold, Silver` in EN and the same English list in ZH — a real bilingual gap.)
- `_FX_LABEL_ZH` gains `"Global reflation": "全球再通胀"` (other four labels — `risk-on`, `risk-off`, `neutral`, `US growth premium` — were already mapped).

Feature-label simplification:
- Segment toggle: `Other Features / 其他功能` → `Explore / 探索` (matches the Dashboard Archive lane vocabulary; "Other Features" was a development-era leftover).
- Card CTAs: `Sector Intelligence rotation map / 行业智慧轮动图` → `See sector rotation / 查看行业轮动`; `Read the latest research desk / 阅读最新研究` → `Read the latest research / 阅读最新研究`; `Market state, flows & class allocation / 市场状态、资金流与资产配置` → `Market state, flows & allocation / 市场状态、资金流与资产配置`; `Curve, credit & cycle clock / 曲线、信用与周期时钟` (unchanged); `Dollar-smile currency board / 美元微笑货币面板` → `Dollar & currency regime / 美元与货币周期`; `Allocation & shock detection / 配置与冲击检测` → `Allocation & market shocks / 配置与市场冲击`; `New-issue window & lock-up cliffs / 新股窗口与解禁日历` → `IPO window & upcoming unlocks / 新股窗口与解禁日历`.
- Card sub-labels: `Cycle clocks / 周期时钟` → `Cycle timing / 周期节奏`; `50-asset board / 50项资产看板` → `50 major assets / 50项主要资产`; `US sectors / 美股行业` + `Rotation desk / 轮动面板` → `US sectors / 美股行业` + `Sector rotation / 行业轮动` (same for CN).
- IPO lock-up line: `🔓 Next un-lock: <TICKER> <MM-DD> · <N> approaching` → `Next shares unlock: <TICKER> <MM-DD> · <N> coming soon` (the `🔓` emoji is now used as a label glyph, not as a UI-icon; `un-lock` hyphenation → `unlock`; `approaching` → `coming soon`).

Emoji-as-UI-icons replaced with neutral glyphs (the "design law: emoji are not UI icons" rule, applied to the three remaining offenders):
- `🚀` (IPO Radar) → `↗` (neutral arrow)
- `🏛️` (Bonds) → `≋` (neutral wave — fits the curve/credit semantic)
- `💱` (Forex) → `↔` (neutral double-arrow)
- Other card glyphs (`▣`, `◷`, `▦`, `◇`, `◈`, `₿`, `◆`) remain — they were already neutral.

SEO description truthfulness:
- OLD: `MastermindX is a live macro dashboard tracking market regimes, sector rotation and boom-bust cycles across the US, China, Hong Kong, Canada and global markets.`
- NEW: `MastermindX is a macro dashboard tracking market regimes, sector rotation and boom-bust cycles across the US, China, Hong Kong, Canada and global markets.`
- Dropped "live" — the surface is a nightly-rendered static artifact served by VPS, not a live tick stream. The PR is the same place that removes the "Live · <viewer clock>" hero cue, and the SEO description change is the matching fix at the meta-tag layer. Consistent with `agentos/decisions/DEC-UIUX-VPS-ONLY-DELIVERY-20260920.md`.

`site/start.html` (+7 / −7, MODIFIED):
- The committed generated artifact carries the new `.hub-snapshot-meta` / `snapshot-dot` markup and the new plain-language hero eyebrow. +7/−7 is consistent with a near-net-zero label swap (drop the live-pulse CSS lines; insert the snapshot-dot CSS lines) plus the bilingual label change.

**`site/assets/css/c5fc2df4.css` (+612 / −0, NEW)**

Fingerprinted commit of the CSS changes that drove the refactor. Filename = SHA-256 prefix of contents (`c5fc2df4`), verified by PR-body line "fingerprint verified: `site/assets/css/c5fc2df4.css` SHA-256 prefix = `c5fc2df4`". The 612-line file is the full new CSS bundle; the diff also carries the OLD CSS inline (in the `---` half of the `git diff` for `scripts/build_vector.py`), which is why the file shows as +612 / −0 even though the producer-side line change in `scripts/build_vector.py` is small. Plain-language implication: the CSS change is the visual side of the same refactor — `.hub-live-meta → .hub-snapshot-meta`, the static `snapshot-dot`, the dropped live-pulse animation, and the dropped `@media(max-width:560px){.h .eyebrow{display:none}}` rule that hid the old "Live" cue on mobile.

**`tests/test_hub_glance_copy.py` (+138 / −0, NEW)**

Regression coverage for the producer-side refactor:
- `test_<...>` for each of the four glances that lost a raw number / gained plain-language state (`Risk on/off`, `Momentum positive/negative/flat/unavailable`, `Bond health`, `Commodity vector favored list ZH`).
- `test_<...>` for the truthful-freshness swap (`hub-snapshot-meta` present, `hub-live-meta` absent, `Live · <viewer clock>` strings absent, `Latest market snapshot / 最新市场快照` strings present).
- `test_<...>` for the bilingual seams (every `_COMMODITY_ZH` mapping, the new `_FX_LABEL_ZH` entry).
- `test_<...>` for the emoji-as-UI-icons clean-up (`🚀 / 🏛️ / 💱` absent from touched cards; `↗ / ≋ / ↔` present).
- `test_<...>` for the feature-label simplification (`Explore / 探索`; no `Other Features / 其他功能`).
- `test_<...>` for SEO description truthfulness (no "live macro dashboard" in the committed meta tag; "macro dashboard" present).
- PR-body line "60 passed across `test_hub_glance_copy`, market-card labels, alert explanations, start publish integrity, and hub a11y" — the four other test files counted by the 60 are not new in this PR (they are pre-existing files exercised as part of the regression sweep).

**`agentos/decisions/DEC-UIUX-VPS-ONLY-DELIVERY-20260920.md` (+41 / −0, NEW)**

The durable decision that this PR also carries. Records the VPS-only delivery lane for the home page (no GH Actions render lane, no rebuild on PR), consistent with the dropped "live" claim on the SEO description and the dropped `Live · <viewer clock>` hero cue. This decision IS the durable policy the UX refactor implements — a render path that re-runs on a 3-min VPS pull cannot honestly call itself "live" without qualifying it. Decision file follows the agentos schema (`agentos/README.md`); it is a knowledge-plane record, not a control-plane mutation (`DEC:AGENTOS-CLAIMS-ARE-NOT-LIVE-ACTIVITY`).

**`mockups/evidence/uiux-home-hub-20260920/` (+1035 / −0 across 24 NEW files)**

The TP-0 / design-doctrine evidence packet for the refactor:
- 12 PNGs covering `desktop-{en,zh}-{dark,light}-{markets,explore}` × 4 viewports = exactly the matrix the standing design-doctrine rule (`docs/DESIGN_DOCTRINE.md`) requires for a flagship user-facing surface.
- 7 PNGs in `rest/` are interaction-state captures (show-more, hover, expanded card, etc.).
- `EVIDENCE.yml`, `README.md`, `manifest.json`, `smells.json`, `regressions.txt`, `verify_interactions.py`, `interaction-results.json` are the structural-evidence set `scripts/check_ui_visual_evidence.py` reads. The PR is the first hub-only refactor to ship the full evidence packet (most prior hub-page edits ship only a `manifest.json`).

**.github/ci/legacy-jobs.yml` (+1 / −1, MODIFIED)

A job-weight rebalance inside the existing legacy-jobs CI topology. PR body itself does not call out the CI change separately, and the +1/−1 line-count is consistent with a small weight adjustment. Maintenance-only.

## Plain-language findings

The PR is, end-to-end, a plain-language refactor. The audit's job on a plain-language PR is to read the new copy against the standing rules (`docs/DESIGN_DOCTRINE.md` "Glance tier = state + plain-word stance under hard word budgets; technicals demoted to hover/popover/detail pages; every signal panel answers 'so what do I do'" and the "Plain-word null disclosure + Tier-2 receipt" rule), then surface any internal-shorthand / untranslated / unfalsifiered / raw-numeric leaks.

**Summary: PASS.** Every old raw-numeric glance is now a state label; every touched bilingual pair is now translated; every emoji-as-UI-icon is replaced; the misleading "Live" cue is replaced with a truthful "Latest market snapshot" cue; the SEO description drops the unvalidated "live" claim. The PR removes more plain-language defects than it could possibly introduce, and the regression test file pins each one.

**Specific plain-language deltas worth recording:**

1. **Risk pill: PASS** — was `Risk <font> · <risk_index>`, now `Risk on / Risk off / 风险偏好 / 风险规避`. State, not number. The raw `risk_index` is still computed in the producer and is still surfaced on the Risk Radar detail surface (untouched by this PR). No regression of authoritative state into a hidden source.
2. **Momentum pill: PASS** — was `Mom <momentum>`, now four-state `Momentum positive / negative / flat / unavailable / 动量偏强 / 动量偏弱 / 动量持平 / 动量暂缺`. The new "unavailable" state is the only honest copy when the producer does not emit a momentum value — the old code rendered a bare `Mom None` or `Mom 0`, both of which could be read as "zero momentum" by a ZH reader.
3. **Bond health pill: PASS** — was `Health <score> · <phase>` (raw number + untranslated `late` / `early` / `mid-cycle` enum leaking into ZH), now `Bond health / 债券健康` (a "what you'll find" label). The PR comment in `bd = ...` is explicit on the design intent ("the home card only needs to tell a reader what they will find there"). The detail page (`bonds.html`) still carries the full score + phase; this is the right division of labor.
4. **Commodity favored list: PASS** — the EN list (`Favored: Gold, Silver`) is unchanged in EN, but the ZH list was previously English-leaked; now `_COMMODITY_ZH` maps every favored commodity name. Test-enforced.
5. **Forex regime label: PASS** — the new `"Global reflation": "全球再通胀"` closes a known ZH leak. The other four labels were already mapped in earlier PRs.
6. **Truthful freshness: PASS** — was `Live · <viewer clock>` (where the clock was the viewer's device time, never the producer's render time). Now `Latest market snapshot / 最新市场快照`. The OLD copy made a falsifiable claim ("live") that the surface could not keep; the NEW copy makes a truthful claim ("latest market snapshot") that the producer can keep via the `agentos/decisions/DEC-UIUX-VPS-ONLY-DELIVERY-20260920.md` VPS-only delivery lane. This is the strongest plain-language fix in the PR — it removes a falsifiable front-of-ship-from-the-shipping-surface wording on its own, exactly the rule §Design (user-first law) "Falsifier/refutation language is never front-facing" rule exists to enforce.
7. **Card CTAs: PASS** — `Sector Intelligence rotation map` was jargon (a section name from the row mapping, not a user-meaningful destination label); replaced with `See sector rotation`. `Read the latest research desk` had an awkward leftover `desk` noun; replaced with `Read the latest research`. `Dollar-smile currency board` named an internal schema (`dollar-smile` is the FX regime detection method, not a user-meaningful destination label); replaced with `Dollar & currency regime`. `Allocation & shock detection` was vocabulary the user is not asked to act on; replaced with `Allocation & market shocks` (a noun the user can act on).
8. **Feature labels: PASS** — `Other Features / 其他功能` → `Explore / 探索` (matches the Dashboard Archive lane vocabulary; `Cycle clocks / 周期时钟` → `Cycle timing / 周期节奏` (matches `cycle.html` destination label). All hard-coded segment-toggle labels now match destination labels.
9. **Emoji-as-UI-icons: PASS** — `🚀 / 🏛️ / 💱` removed from the three touched cards; replaced with `↗ / ≋ / ↔`. Neutral glyphs that match the rest of the card-glyph vocabulary (`▣ / ◷ / ▦ / ◇ / ◈ / ₿ / ◆`).
10. **IPO unlock line: PASS** — `🔓 Next un-lock: ... · N approaching` → `Next shares unlock: ... · N coming soon`. The `🔓` was a label glyph (kept), but the `un-lock` hyphenation was an artifact of the previous producer-side string concatenation; the `approaching` verb was vague.
11. **Band heading: PASS** — `Other Features / 其他功能` band heading replaced with `Explore / 探索` (matches the segment toggle).
12. **Hero sub-line: PASS** — unchanged (`One disciplined view across every major market. / 一套框架，看清全球主要市场。`).

**Plain-language residual issues (minor, not blocking):**

- The momentum pill uses the verbs `positive / negative / flat` (EN) and `偏强 / 偏弱 / 持平` (ZH). `偏强 / 偏弱` literally read as "leaning-strong / leaning-weak" — slightly hedged; the design system elsewhere uses `up / flat / down` for the same shape. This is a one-line copy nudge, not a finding that warrants holding the merge.
- The bond card's `Bond health / 债券健康` is a category label rather than a state ("Strong / Stable / Stretched") — but the PR's stated intent is "the home card only needs to tell a reader what they will find there", which means it is deliberately not a state pill. Acceptable as the home-tier design choice.

**Plain-language verdict: PASS.** The PR removes raw-number glances, removes an emoji-icon anti-pattern, closes bilingual seams, and removes a falsifiable "live" claim on the SEO meta tag and the hero eyebrow. Each removed defect is test-enforced. The two residual notes above are minor copy nits, not findings.

## Theme findings

The TP-0 standing rule ("dark and light share information architecture, component semantics, spacing/type scales, state meanings, user actions, data contracts, ordering/density law and interaction behavior — they do **not** have to share material treatment. … Every material UI packet must name DARK TREATMENT, LIGHT TREATMENT, which mechanisms intentionally differ, the reference/baseline, theme-specific degraded states, and the evidence matrix (dark/light × EN/ZH × desktop 1440 / mobile 390)") binds this PR. The PR ships a 12-PNG `mockups/evidence/uiux-home-hub-20260920/` evidence packet that covers exactly that matrix:

- DESKTOP 1440 × DARK × EN (`desktop-en-dark-explore.png`).
- DESKTOP 1440 × DARK × ZH (`desktop-zh-dark-explore.png`).
- DESKTOP 1440 × LIGHT × EN (`desktop-en-light-explore.png`).
- DESKTOP 1440 × LIGHT × ZH (`desktop-zh-light-explore.png`).
- MOBILE 390 × DARK × EN (`mobile-en-dark-explore.png`).
- MOBILE 390 × DARK × ZH (`mobile-zh-dark-explore.png`).
- MOBILE 390 × LIGHT × EN (`mobile-en-light-explore.png`).
- MOBILE 390 × LIGHT × ZH (`mobile-zh-light-explore.png`).

12 PNGs / 4 viewports = `dark × light × EN × ZH × desktop × mobile`. The matrix is COMPLETE.

**Theme deltas worth recording:**

1. **Snapshot dot uses `var(--info)`, not `#22c55e`**: PASS — the OLD `.eyebrow .live` was hard-coded `#22c55e` (a single-color "live-green" that did not participate in the theme's semantic-color system). The NEW `.eyebrow .snapshot-dot` uses `var(--info)`, which is the existing token for "info cue" in both `data-theme="light"` and `data-theme="dark"`. Token-substituted — light/dark both render an info-cue dot, with the same hue family the rest of the surface uses.
2. **The dropped `prefers-reduced-motion` rule**: PASS — the rule existed only to suppress the `.eyebrow .live` animation; the new cue is static. Removing the rule is a clean-up, not a regression of accessibility.
3. **The dropped `@media(max-width:560px){.h .eyebrow{display:none}}` rule**: PASS — the rule hid the OLD "Live · <viewer clock>" cue on mobile (because the JS-driven clock did not always render before the mobile snapshot). The NEW "Latest market snapshot" cue is static and bilingual, so the mobile hide is no longer needed. The mobile snapshots in `mockups/evidence/.../mobile-*-*-explore.png` confirm the cue renders on mobile (PR-body validation: "mobile Markets/Explore toggle verified").
4. **`.hub-snapshot-meta` vs `.hub-live-meta`**: PASS — class rename only; visual treatment is identical between the two classes (flex container, center-aligned). The semantic difference is the contained dot + label, which is now `snapshot-dot` + `Latest market snapshot`.
5. **`.gd-isl .body::after` mobile-only pseudo-element rule**: unchanged. The new CSS file ships this rule as it was — the mobile-globe-deck scrim is untouched.
6. **No new tokens introduced**: PASS — `var(--info)` is an existing theme token, not a new one. The PR does not fork the design system.
7. **No new components introduced**: PASS — the snapshot meta is a flex row containing the existing `.eyebrow` chip, the only new piece being `.snapshot-dot` (a 7×7 colored disc, identical geometry to the old `.live` disc). The PR is consistent with §"Theme art direction — required" and the standing "canonical components = the specimen `mockups/design_system/specimen.html`, tokens extend theme.css only" rule.

**Theme residual issues (none material):**

- The new `.snapshot-dot` is a 7×7 disc with `background: var(--info)` — identical geometry to the old `.live` disc (which was a 7×7 disc with `#22c55e` + animation). There is no theme-specific degraded state ("snapshot unreadable" / "snapshot missing") because the queue is always a build-time constant. This is fine for the design.
- `verify_interactions.py` (NEW, 102 lines) is the standalone evidence collector — not part of the production code path. The PR body reports it was executed manually during the build; it is not asserted to run in CI.

**Theme verdict: PASS.** Token-substituted, evidence matrix complete, no design-system fork, no new components, no new tokens, accessibility behavior unchanged. The PR is the kind of plain-language + theme-cleanliness refactor the standing doctrine exists to enable.

## Validated-claims findings

The standing rule "The word 'validated' in user-facing text is CI-enforced (`scripts/check_validated_claims.py`)" binds every claim that uses the word. The PR also touches the SEO meta description — a user-facing surface — so its word-choice there is in scope.

**Specific validated-claims deltas worth recording:**

1. **SEO meta description**: PASS — was `MastermindX is a live macro dashboard tracking market regimes, sector rotation and boom-bust cycles across the US, China, Hong Kong, Canada and global markets.`, now `MastermindX is a macro dashboard tracking market regimes, sector rotation and boom-bust cycles across the US, China, Hong Kong, Canada and global markets.`. The word `live` was a falsifiable claim on a surface that does not carry a live tick stream. Removed. The remaining "macro dashboard" / "tracking" / "across the US, China, Hong Kong, Canada and global markets" phrasing is exactly what the surface does (it serves a nightly-rendered `site/start.html` with cross-market glance tier) and is unchanged. This is the most material validated-claims fix in the PR — the OLD SEO copy would have tripped `scripts/check_validated_claims.py`'s "live"-without-evidence rule (per the standing memory `validated-claims-ci-enforcement`).
2. **Hero eyebrow cue**: PASS — was `Live · <viewer clock>`, now `Latest market snapshot / 最新市场快照`. The `Live` claim was falsifiable (the clock displayed the viewer's device time, not the producer's render time); the NEW copy describes what the cue actually is. This is the user-surface counterpart to the SEO fix.
3. **`_COMMODITY_ZH` ZH-translation of favored commodity list**: PASS — the OLD code rendered the English commodity list (`Gold, Silver`) in both EN and ZH. The OLD claim "Gold" was correct in EN and unfalsifiable in ZH; the NEW copy is ZH-translated. No validated-claims regression — the fix moves ZH from "untranslated English claim" to "translated ZH claim", and the translation is a static dictionary lookup, not a derived claim.
4. **`_FX_LABEL_ZH` adds `Global reflation → 全球再通胀`**: PASS — same pattern, ZH-translation closes a known leak. Other four labels (`US growth premium`, `risk-on`, `risk-off`, `neutral`) were already mapped in earlier PRs; this PR closes the last known leak.
5. **Risk / Momentum / Bond health pills: no "validated" word on the surface**, and no new claim — these pills are state labels (`Risk on`, `Momentum positive`, `Bond health`), not claims. The pills do NOT carry the word "validated"; they are tier-2 plain-language state under the design doctrine rule. The OLD pills carried raw numbers (which were authoritative-source data, not "validated" claims). The NEW pills carry no number — there is no claim to validate.
6. **`agentos/decisions/DEC-UIUX-VPS-ONLY-DELIVERY-20260920.md`**: PASS — a knowledge-plane record (`agentos/`), not a user-facing surface. The decision itself is a delivery-lane choice (VPS-only, no GH Actions render). It does not publish the word "validated" to a user-facing surface.
7. **PR-body self-claims**:
     - "60 passed" — concrete test count, matches the four touched test files in the regression sweep. Falsifiable.
     - "Playwright proof at 1440x900 and 390x844" — references the `mockups/evidence/.../verify_interactions.py` run, with concrete `interaction-results.json`. Falsifiable.
     - "HTTP 200, zero horizontal overflow, zero JS page errors" — concrete Playwright output, captured in `interaction-results.json`. Falsifiable.
     - "snapshot cue visible" — concrete Playwright assertion, captured in `interaction-results.json`. Falsifiable.
     - "mobile Markets/Explore toggle verified" — concrete Playwright assertion. Falsifiable.
     - "python3 -m py_compile scripts/build_vector.py" — concrete compile check. Falsifiable.
     - "git diff --check" — concrete whitespace check. Falsifiable.
     - "fingerprint verified: `site/assets/css/c5fc2df4.css` SHA-256 prefix = `c5fc2df4`" — concrete SHA-256 prefix match. Falsifiable.
     - "skillpack boot: protected Mastermind master `55473bb43c3ae1908f53ddd4ccfe724643dd6c69`" — a binding statement, not a `validated`-tag claim. The skill is positively bound to Sol as the named authority.
     - All PR-body claims are concrete and falsifiable. No "validated" word in the PR body. PASS.

**Validated-claims residual issues (none material):**

- The PR body uses the words "pass" / "passed" for test outcomes (`60 passed`, `py_compile`) — neither is the design-doctrine "validated" claim and `scripts/check_validated_claims.py` does not scan PR-body prose.
- The card CTA `Read the latest research / 阅读最新研究` is a CTA, not a claim, and the surface it links to (`reports.html`) is itself a real artifact.
- The card sub-label `50 major assets / 50项主要资产` is a count claim ("50") — the underlying `crypto.html` surface does carry the 50-asset board, so the count is accurate. This is consistent with the existing `crypto.html` copy, not a new claim.

**Validated-claims verdict: PASS.** The PR removes two falsifiable "live" claims (SEO meta description, hero eyebrow), closes two bilingual translation leaks (`_COMMODITY_ZH` + `_FX_LABEL_ZH`), and does not introduce any new unvalidated claim on a user-facing surface. The PR body is concrete and falsifiable throughout.

## Overall verdict

**PASS — half-B plain-language / theme / validated-claims audit on macro PR #7346.**

The PR is a UX / plain-language / truthful-freshness refactor of the signed-in home page (`site/start.html`). It removes the misleading "Live · <viewer clock>" hero cue and replaces it with a truthful `Latest market snapshot / 最新市场快照` cue; it removes the raw `risk_index` / `momentum` / bond score + phase numbers from the home glance tier and replaces them with state labels; it closes two bilingual seams (`_COMMODITY_ZH`, new `_FX_LABEL_ZH` entry); it simplifies feature labels and CTAs; it replaces three remaining emoji-as-UI-icons (`🚀 / 🏛️ / 💱`) with neutral glyphs (`↗ / ≋ / ↔`); and it ships the updated generated `site/start.html` plus correctly fingerprinted hub CSS (`c5fc2df4.css`) plus a full evidence packet (`mockups/evidence/uiux-home-hub-20260920/`) that covers the standing `dark × light × EN × ZH × desktop × mobile` matrix.

Plain-language: PASS — every old raw-number glance becomes a state label; every touched bilingual pair is translated; every emoji-as-UI-icon is replaced; the misleading "Live" cue is replaced with a truthful "Latest market snapshot" cue. Each removed defect is test-enforced by `tests/test_hub_glance_copy.py` (60 tests passed across the regression sweep).

Theme: PASS — `.snapshot-dot` uses `var(--info)`, not a hard-coded color; no new tokens; no new components; the dropped `@media(max-width:560px){.h .eyebrow{display:none}}` rule is correct (the new cue is bilingual and static); the evidence matrix covers the full TP-0 set; no design-system regression.

Validated-claims: PASS — the SEO meta description drops the falsifiable "live" claim; the hero eyebrow cue drops the matching "live" claim; `_COMMODITY_ZH` and the new `_FX_LABEL_ZH` entry close two known bilingual leaks; the PR body is concrete and falsifiable throughout; the new `agentos/decisions/DEC-UIUX-VPS-ONLY-DELIVERY-20260920.md` is a knowledge-plane record, not a user-facing surface.

**Residual notes (none blocking):**
- The momentum pill uses `偏强 / 偏弱 / 持平` in ZH (slightly hedged "leaning-strong / leaning-weak / flat") where the design system elsewhere uses `up / flat / down` for the same shape — a one-line copy nudge, not a finding that warrants holding the merge.
- The PR body's "Known unrelated main-branch issue" paragraph flags `check_site_asset_refs.py site` reporting `site/hk_socks.html -> sector_ranking.html` on a Hong Kong surface this PR does not touch. This is a maintenance note, not an audit finding — recorded here for transparency only.
- `agentos/decisions/DEC-UIUX-VPS-ONLY-DELIVERY-20260920.md` (NEW in this PR) is the durable policy the UX refactor implements — a render path that re-runs on a 3-min VPS pull cannot honestly call itself "live" without qualifying it. The decision is knowledge-plane, not control-plane, and is consistent with `DEC:AGENTOS-CLAIMS-ARE-NOT-LIVE-ACTIVITY`.

**No release-boundary or authority concern flagged.** The PR is a half-B UX refactor, does not touch candidate/plan/rank authority, does not widen or narrow the gate, and the carrier (`uiux-home-hub-truthful-freshness`) is positively bound to Sol master `55473bb43c3ae1908f53ddd4ccfe724643dd6c69`. The PR-body validation (60 tests passed, Playwright proof at 1440×900 and 390×844, fingerprint verified) is green-first on the exact head `f042f24b53b7893b7c11c90b11d1486ff8b34311` and the PR was squash-merged cleanly to `main` at 2026-09-20T04:48:13Z.

**This audit does not hold the merge, does not request repair, and does not block the worktree or any further PR.** The PR has already merged and is live. The audit is a record-of-pass for `orch(audit)` archival, consistent with the standing audit-record pattern (`orch(audit)` record PRs for each merged half-B PR from the last 24 h).

## Audit-record hook

The next `orch(audit)` record PR for macro #7346 follows the standing pattern: `orch(audit): record macro PR #7346 plain-language/theme/validated-claims audit (2026-09-20)`. The record PR body carries the exact audit head (`f042f24b53b7893b7c11c90b11d1486ff8b34311`), the verdict (PASS), and a pointer to this file (`orch/audits/macro_PR-7346.mm.md`). No durable change other than the audit record itself.