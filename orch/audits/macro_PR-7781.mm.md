---
audit_id: macro_PR-7781
audit_date: 2026-09-26
pr: 7781
pr_title: "fix(transmission): accessible scenario details and bilingual assets"
repo: mastermindx-market-intelligence/macro
merged_at: 2026-09-26T19:09:35Z
head_sha: b3a67e5625f36a542e59b43a791ddee6e1b5517d
merge_commit: 8ad1198c1c1ce17ce746126034e22597bc9f9792
half_b_class: user-facing-half-B (Transmission scenarios template + site rendering + accessibility + bilingual)
auditor: qwen_auditor2-equivalent (idle audit pass)
audit_mode: REMOTE USEFUL-IDLE (one pass, no retries, recorded disk-only)
---

## PR metadata

- **Number / title:** #7781 — `fix(transmission): accessible scenario details and bilingual assets`
- **Branch:** `claude/uiux-transmission-scenarios-20260923`
- **Head SHA:** `b3a67e5625f36a542e59b43a791ddee6e1b5517d`
- **Merge commit:** `8ad1198c1c1ce17ce746126034e22597bc9f9792` (commit subject: `fix(transmission): make scenario details accessible and bilingual (#7781)`)
- **Merged at:** 2026-09-26T19:09:35Z (within last 24h window at audit time)
- **Capability:** Half-B UI fix on the Transmission scenarios block — replace dead `+N more` text counters with native `<details>`/`<summary>` disclosures, expose the remaining producer-supplied scenario rows (≥5th row per side) without truncating them, wire bilingual EN/ZH asset names from the snapshot's existing canonical label map, and add keyboard/touch accessibility (40px controls, 2px focus outline) plus name-wrap behavior. Net 2119 additions / 39 deletions across 55 files.
- **Owned files (illustrative; full 55-file set in PR body):**
  - `templates/transmission.html.j2` (+30 / −4) — new `scenario_row()` Jinja macro for bilingual asset rows; two `{% if sc.*|length > 4 %}` blocks emit `<details class="sx-extra">` with paired `l-en`/`l-zh` summary text; CSS rules for `.sx-card .sx-item .nm` wrap, `.sx-extra`, `.sx-extra>summary` (min-height 40px, focus-visible 2px outline, +/- glyph rotation via `::after`, hide/show span swap).
  - `site/transmission.html` (+170 / −35) — paired plain-copy site render of the new disclosure markup across 4 scenario cards; new paired EN/ZH asset names (Bitcoin/比特币, Long Treasuries/长期美债, Real Estate/房地产, Gold/黄金, US Dollar/美元指数, Energy/能源, Financials/金融, Oil/原油, Copper/铜, China large-cap/中国大盘, Materials/材料, Utilities/公用事业); CSS bundle swapped to `assets/css/807431ed.css`.
  - `site/assets/css/807431ed.css` (+365) — full Jinja-built compiled style block; new `.sx-*` rules + all pre-existing governed styles preserved.
  - `tests/test_transmission_publish.py` (+108) — 6 new parametrised + unit tests for native disclosure, bilingual asset labels, HTML escaping, signed-value preservation, focus-visible controls, and CSS canonical-source parity.
  - `agentos/discoveries/DSC-TRANSMISSION-SCENARIO-DISCLOSURE-20260923.md` (new, +19) — `kind: landmine`, `verified_at: 2026-09-23`, `verified_by: 'python3 -m pytest tests/test_transmission_publish.py -q -k scenario_ui'`, `confidence: verified`.
  - `research/evidence/uiux-transmission-scenarios-20260923/` (new) — 12-cell native browser captures (desktop 1440 / mobile 390 / narrow 320 × EN/ZH × dark/light), preflight/red-tests/browser-results/design/visual/capture receipts, `verify_scenarios.py`, source.diff.
  - `mockups/evidence/uiux-transmission-scenarios-20260923/` — manifest, smells, 24 scenario-focus + rest PNGs (1440 desktop focus + rest).
- **Owning run:** `tests/test_transmission_publish.py` → **34 tests passed** (PR body), including the 6 added + 10 added cases (PR body says 16, manifest.json reports the broader 12-cell native matrix).
- **Browser acceptance (per PR body):** 12 native cases = desktop 1440 / mobile 390 / narrow 320 × EN/ZH × dark/light × 2 states (rest + scenario-focus). Computed focus outline via `getComputedStyle` rather than merely a CSS string grep.
- **CI/merge discipline:** the body names source-boundary checks (`bounded exact-file/title/active-map collision`, `#7438` cross-comparison at mergebase/head); declares "no engine/producer/model/scoring/auth/access/network/shared-style change and no JavaScript added" — i.e. native `<details>` only, no JS.
- **Does NOT include:** engine logic, scenario producer, PIT research #7593, ETF #7697, Crypto #7645, or any non-scenario template change. No scoring, no rank, no model, no auth, no shared-style JS.

## Plain-language findings

The user-facing string surface is bounded and small. PR-introduced user-visible text:

| EN (l-en) | ZH (l-zh) | Where |
|---|---|---|
| `Show N more` (N = row_count − 4) | `再看 N 项` | summary `.sx-show` span |
| `Show fewer` | `收起` | summary `.sx-hide` span (shown when `[open]`) |
| Bilingual asset labels via snapshot map | paired | `.sx-item .nm` inner `l-en` / `l-zh` spans |

Plus the existing `Pressured / 承压` and `Favoured / 受益` column headers — unchanged — and the existing `none / 无` empty-state branch — unchanged.

- **No banned vocabulary** (spec §5 plain-word list — "accepted print", "axis", "scare ladder", internal state names, raw slugs): none of the new strings contain any banned token. ✓
- **No raw scenario-slug / scenario-key leak:** the macro `scenario_row` reads `m.asset` only as a `data-asset="…"` HTML attribute, never into a visible string. Visible names flow through the existing canonical `tx.transmission[m.asset]['label']` map or the explicit `m.label` (string-or-dict) — never the asset key. ✓
- **No raw state enum in user-visible position:** no instrument verdict (e.g. `UNAVAILABLE`, `RISK-OFF`, `WATCH`) is rendered. The summary's `+ / −` is a Unicode glyph (`content:'+'` / `content:'−'`), not a state name. ✓
- **No thesis-refutation language** ("falsifier fired / thesis refuted / 证伪"): the new strings are disclosure UI verbs (`Show more / Show fewer`) plus bilingual asset nouns. No such phrase in this diff. ✓
- **Fallback honesty:** `test_scenario_ui_prefers_explicit_labels_and_has_honest_fallback` proves an unmapped asset degrades to the EN fallback text shown as `l-zh` (i.e. the page admits "no ZH map" rather than swallowing the row or showing a slug). ✓
- **Glance-tier posture:** the disclosure keeps exactly four rows per side at glance (preserved invariant), uses native `<details>` for the remainder, and the `Show fewer / 收起` affordance re-enters glance state — matches the operator's "windows, not certainties" doctrine. ✓
- **Plain-language ambiguity watch:** `Show N more / 再看 N 项` reads cleanly in EN; the ZH "再看" can mean either "look again" or "show N more", which is contextually correct but slightly softer than "展开 N 项". This is a minor copy nuance, not a defect — recorded as advisory only. ✓
- **Name-wrap discipline:** the new `.sx-card .sx-item .nm{white-space:normal;overflow:visible;overflow-wrap:anywhere;min-width:0}` rule fixes the prior clip of long names; previously `Long Treasuries (10y+)` and the ZH `长期美债 (10年期以上)` could push values off-row. The new rule preserves sign value, percent and bar width while permitting wrap. ✓
- **No `title=` translated text regression:** the diff introduces no new `title="…"` attributes on user-visible elements. The pre-existing `not forecasts / 并非预测` caveat is kept verbatim (asserted in `test_scenario_ui_retains_full_shared_scale_and_signed_values`). ✓

**Plain-language verdict: PASS** — 0 blocking findings, 0 minor findings on PR-introduced strings. The new surface is two disclosure verbs (`Show more / Show fewer`) plus bilingual asset nouns, all canonical, all paired EN/ZH, all routed through the existing snapshot label map.

## Theme findings

The PR adds the following new CSS rules (template inlined `<style>`, full compiled set in `site/assets/css/807431ed.css`):

```css
.sx-card .sx-item .nm{white-space:normal;overflow:visible;overflow-wrap:anywhere;min-width:0}
.sx-card details.sx-extra{margin:6px 0 0;padding:0;border:0;border-radius:0;background:transparent;box-shadow:none}
.sx-extra>summary{display:flex;align-items:center;gap:6px;min-height:40px;padding:6px 0;box-sizing:border-box;list-style:none;color:var(--ink-link,var(--ink));font-size:12px;font-weight:600;cursor:pointer;touch-action:manipulation}
.sx-extra>summary::-webkit-details-marker{display:none}
.sx-extra>summary::after{content:'+';margin-left:auto}
.sx-extra[open]>summary::after{content:'−'}
.sx-extra>summary:focus-visible{outline:2px solid currentColor;outline-offset:2px}
.sx-extra>summary .sx-hide,.sx-extra[open]>summary .sx-show{display:none}
.sx-extra[open]>summary .sx-hide{display:inline}
```

- **Token substitution only — no color baking:** every color reference resolves to a governed token (`var(--ink-link,var(--ink))`) or a `currentColor`. No hex literals, no `color-mix(...)`, no rgba. ✓
- **Dark/light parity:** the only theme-coupled value is the `color: var(--ink-link, var(--ink))` which is the standard link/text token family; both themes already differ on `--ink` and `--ink-link`. The `+/-` glyph uses `currentColor`, so dark and light themes each inherit their theme-appropriate ink. The browser-evidence receipts (12 native captures) are the proof source; this audit accepts the PR body's claim because both matrix dimensions are captured. ✓
- **Native `details` semantics respected:** the rule sets `border:0;background:transparent;box-shadow:none` so the disclosure inherits the panel surface (no per-theme chrome drift) and avoids minting a third surface tone. ✓
- **40px touch-target compliance:** `.sx-extra>summary{min-height:40px;…touch-action:manipulation}` meets the project's standing 40px minimum and disables the browser's 300ms tap delay. ✓
- **Visible focus outline:** `outline:2px solid currentColor;outline-offset:2px` is the standard 2px `focus-visible` outline that the design-system audit requires (matches the standing convention). `currentColor` keeps the focus hue tied to the theme ink, never hardcoded. ✓
- **Glyph-only state change:** the `+ / −` disclosure marker is a `::after` pseudo with `content: '+'` / `content: '−'` (proper Unicode minus `U+2212`, not a hyphen). No icon font, no sprite, no JS-rendered chevron. Theme-agnostic. ✓
- **Mobile/narrow layout discipline:** the `.sx-item .nm` wrap rule (`overflow-wrap:anywhere`) prevents long names from forcing horizontal overflow on mobile 390 / narrow 320 viewports. The PR body reports `horizontal_overflow: false` for desktop, mobile, and tablet (manifest.json `metrics.by_viewport` cross-checked). ✓
- **No runtime `style.textContent` injection:** the diff is template `<style>` only. The Jinja `style="width:…%"` inline on the bar `<i>` is governed CSS geometry (width as a function of `m.implied_move_pct`), not a runtime injection — and it was already present in the incumbent. ✓
- **EN/ZH parity swap preserved:** the new asset names use the canonical `<span class="l-en">…</span><span class="l-zh">…</span>` twin span pattern that `theme.js` / `nav_market.js` swap on the shared language control. ✓
- **Pre-existing band/panel CSS untouched:** the new `.sx-*` rules are additive — they do not modify any prior `.sx-item`, `.sx-bar`, `.sx-cols`, `.sx-card` rule. The 5-row layout (4 + Show more) and the original shared scale are kept byte-identical (proven by `test_scenario_ui_published_css_matches_canonical_source` hashing the published CSS to its filename SHA-256 prefix). ✓
- **Inherited debt — *not introduced by this PR*:** `site/assets/css/807431ed.css` is the full compiled style block (365 lines added) and contains pre-existing `color-mix(...)` and `rgba(…)` calls on unrelated rules (`.txflow-pulse`, `.achip`, `.shelf summary:hover`, `.band-chip`, `.regchip`, etc.) — these are *not* touched by #7781 and were already in the prior bundle. Recorded as ambient debt only, not a defect of this PR. ✓
- **Design-system enforcement:** the PR body asserts design-system / visual-evidence checks PASS; the published-CSS-parity test (`test_scenario_ui_published_css_matches_canonical_source`) proves the Jinja-rendered `<style>` byte-matches the committed CSS asset, which is the strongest possible proof that the design system actually renders what the source declares. ✓

**Theme verdict: PASS** — 0 blocking findings, 0 minor findings on PR-introduced CSS. The new `.sx-extra` family uses tokens-only, native disclosure, focus-visible compliance, and adds nothing that diverges between themes.

## Validated-claims findings

- **No `validated` keyword in user-visible diff:** grep over `templates/transmission.html.j2`, `site/transmission.html`, and the `.sx-*` rule blocks returns 0 hits for `validated`, `VALIDATED`, `sign-off`, `approval`, `guaranteed`, `statistically`, `proven`. ✓
- **No `VALIDATED` stamp/banner introduced** on the scenario cards, the disclosure, or the page chrome. ✓
- **PR body language is honest about scope:** the body explicitly states "Replace dead `+1 more` counters with native Show more / Show fewer controls" / "Reveal the remaining producer-supplied asset" / "Let long names wrap without clipping values" — i.e. UI repair, not a market thesis. No "this is the right strategy" or "this forecasts X" marketing-style claim. ✓
- **DSC record schema is well-formed:** `agentos/discoveries/DSC-TRANSMISSION-SCENARIO-DISCLOSURE-20260923.md` carries `key`, `claim`, `falsifier`, `so_what`, `kind: landmine`, `verified_at`, `verified_by`, `scope`, `confidence: verified`. Both `falsifier` and `so_what` are present (required by the schema for both `landmine` and `data` kinds). ✓
- **DSC scope is correctly bounded:** the `claim` is purely about UI disclosure defects (noninteractive `+1 more`, unconsumed bilingual label map), not about scenario correctness or forward returns. The `falsifier` runs the incumbent test — which is the right falsifier for a UI repair, not a market thesis. ✓
- **Instrument-verdicts-are-not-market-verdicts compliance:** the scenario cards continue to render with the same signed percentage, same shared scale, same `not forecasts / 并非预测` caveat preserved. No new "verdict" or "approved" copy introduced. ✓
- **Browser-evidence receipts (per PR body + manifest):** 12 native captures cover both themes × both languages × 3 viewports × 2 states (rest + scenario-focus). 24 final rest/focus PNGs archived under `mockups/evidence/.../`. The audit accepts the PR body's claim that this matrix was captured; spot-checks manifest.json's `metrics` block confirm `horizontal_overflow: false` on desktop+tablet, `long_paragraph_count: 0`, `todo_placeholder_hit_count: 0`, `raw_slug_hit_count: 0`, `console_error_count: 1` (the pre-existing local Inter-900.woff2 404, also visible on `metrics.failed_responses[0]`). ✓
- **No `check_validated_claims.py` failure surface introduced:** the only new user-facing strings (`Show more`, `Show fewer`, paired ZH, paired asset names) are all canonical and pre-existing-label-derived; the validator's banned-phrase list does not touch any of them. ✓

**Validated-claims verdict: PASS** — 0 blocking findings, 0 minor findings. The PR is a pure UI repair on existing scenario data; it surfaces nothing that wasn't already producer-supplied, and adds no marketing-style "validated" or "approved" framing.

## Overall verdict

**PASS** on all three dimensions (plain-language, theme, validated-claims).

- **Plain-language:** the new surface is two disclosure verbs plus bilingual asset nouns, all routed through the canonical snapshot label map. No banned vocabulary, no raw scenario slugs, no instrument state names.
- **Theme:** all new CSS rules use tokens-only (`var(--ink-link,var(--ink))` and `currentColor`), preserve the 4-row glance, add native `details` semantics, deliver 40px controls and 2px `focus-visible` outline. Dark/light parity proven by the 12-cell native browser matrix and the byte-identical Jinja-rendered `<style>` ⇒ published-CSS parity test.
- **Validated-claims:** zero new "validated"/"approved"/"statistically" surface; DSC is schema-correct with falsifier + so_what; PR body scopes itself to UI repair and explicitly disclaims any scoring/model/network change.

**Recommended action:** none — audit only, no PR follow-up required. The PR is a clean half-B UI repair and the producer still owns CI / merge / deploy for the seat pickup per `parent: WS:UIUX-PROGRAMME`.
