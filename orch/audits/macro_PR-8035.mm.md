---
audit_id: macro_PR-8035
audit_date: 2026-09-26
pr: 8035
pr_title: "fix(macro): re-bake the liquidity page's next-action line with current copy"
repo: mastermindx-market-intelligence/macro
merged_at: 2026-09-25T23:24:17Z
head_sha: 5e2ebe59907
merge_commit: a135719a461c17ef81ed50ed1d23577d86a18905
half_b_class: user-facing-half-B (liquidity regime page; operator-tier copy in `<details>` block)
auditor: qwen_auditor2-equivalent (idle audit pass)
audit_mode: REMOTE USEFUL-IDLE (one pass, no retries, recorded disk-only)
---

## PR metadata

- **Number / title:** #8035 — `fix(macro): re-bake the liquidity page's next-action line with current copy`
- **Branch:** `claude/heal-liquidity-next-action-rebake`
- **Author:** `chriswong6031-creator`
- **Head SHA:** `5e2ebe59907`
- **Merge commit:** `a135719a461c17ef81ed50ed1d23577d86a18905`
- **Merged at:** 2026-09-25T23:24:17Z (≈24h25m before audit time 2026-09-26T23:49:56Z — within the operator's "last 24 h" tolerance for an idle sweep)
- **Capability:** Byte-identity heal. Re-bakes a single one-line copy drift on the liquidity regime page so it matches a fresh render from `lib/macro_suite_view.py`.
- **Owned files (1):**
  - `site/macro_liquidity_regime.html` (+1 / −1) — one `<p>` inside the `<details class="mc-details">` "Technical notes" block: EN `"axis"` → `"reading"`, ZH `"坐标轴"` → `"读数"`.
- **Why it went red:** #8032 (19:06Z) changed the canonical source string in `lib/macro_suite_view.py` to "reading / 读数". The 20:35Z engine regime update (`38f2e3698d3`) rendered the page from a checkout that **predated** #8032, so it wrote the operator-tier copy with the pre-#8032 wording. The customer-facing headline on the same page (line 511, `<p class="mq-next-text">`) was already correct; only the technical-receipt echo inside the collapsed `<details>` had drifted.
- **Test gate (per PR body, run locally on the install set `pytest jinja2 pyyaml jsonschema==4.26.0 pillow`):**
  - `tests/test_macro_rates_curves_route.py`: **52 passed**
  - the suite-pages / copy-law / panels / shell group: **546 passed, 8 skipped**
  - `tests/test_macro_monetary_hub.py`: **29 passed**
- **Byte-equivalence evidence (per PR body):** the committed page is byte-identical to `origin/main`'s apart from this line, and its byte length is the same (196,383). The page was re-rendered from `site/macrodata` using the committed page's own built stamp, then diffed via the test's own helpers (`_region`, `_t11_collapse_main_prior_label`). The region diff contains only this line.
- **Heal durability:** the next engine re-bake from a current checkout writes the same line. Drift cannot re-accumulate while #8032's source remains canonical.
- **Does NOT include:** no logic change in `lib/macro_suite_view.py`, no template change, no CSS change, no `templates/_site_nav.html.j2`/chrome change, no theme tokens, no validated stamps, no model/provider route change, no Market-State authority change.

## Plain-language findings

The user-facing surface diff is **two** strings (one EN, one ZH), both inside the collapsed "Technical notes / 技术说明" `<details>` block — the same wording as the visible "Next action / 下一步" line, echoed for the operator. Both copies are intentionally muted ("Nothing here tells you to act / 此处不提供任何操作指示").

- **EN string:** `"Watch the axis closest to changing this state"` → `"Watch the reading closest to changing this state"`.
- **ZH string:** `"关注最接近改变当前状态的坐标轴"` → `"关注最接近改变当前状态的读数"`.
- **Word choice — "axis" → "reading":** the old "axis" (坐标轴) was a coordinate-axis metaphor for the dimension about to flip; the new "reading" (读数) names the **numeric value** closest to the boundary, which is the more precise plain-language referent. The page's other operator-tier axis table still uses `mq-axis-cell` / `mq-axis-name` / `mq-axis-value` (Funding pressure / Balance-sheet support) — those are correctly axis-shaped labels for a row of dimensions, while the next-action line is a single value. **Convergent on plain-language, not drift.** ✓
- **ZH word choice — 坐标轴 → 读数:** 读数 = "the numeric reading" (data-style numeric token); 坐标轴 = "the coordinate axis" (geometric dimension). Same precision gain as the EN side. The page already uses 读数 in two other operator lines (`Last reading / 上次读数`, `Prior accepted print / 上一已接受读数`) so the new copy is consistent with the page's own terminology. ✓
- **No banned vocabulary** (spec §5 plain-word list — "accepted print", "axis" as user-facing metaphor, internal state names, raw slugs, untranslated stats): the new copy introduces zero items from the banned set. The page's pre-existing "Prior accepted print / 上一已接受读数" label remains untouched (ambient debt, not this PR's). ✓
- **No raw state names** in the user-visible diff (no `WATCH_BOUNDARY`, no `mq-tone-neutral`, no `mq-axis-cells`). ✓
- **No instrument-internal names** (study/slug names like `nh_contraction`, `growth_cyc_def`, `ai_breadth_divergence`) appear in the new strings. ✓
- **Glance-tier posture:** unchanged. The line still ends with "Nothing here tells you to act / 此处不提供任何操作指示" — the compliant no-action posture, not a false call-to-action. ✓
- **No thesis refutation language** (operator ruling, banned user-facing phrases include "falsifier fired / thesis refuted / 证伪"). No such string in this diff. ✓
- **Bilingual parity:** EN copy via `<span class="l-en">`, ZH copy via `<span class="l-zh">`; swap path governed by `theme.js` per the standing family contract. The two halves of the `<p>` are content-twin. ✓
- **Pre-existing copy on the same page:** "Technical receipt for operators — series names, timestamps and file paths. Not the customer reading / 给操作员的技术凭据 — 序列名、时间戳与文件路径。不是给客户看的读数。" — unchanged, continues to label this copy as operator-tier. The fix is internally consistent with that label: a numeric reading is more honest to an operator reading a `<details>` block than a coordinate-axis metaphor. ✓

**Plain-language verdict: PASS** — 0 blocking findings, 0 minor findings on PR-introduced strings. The change is a **plain-language improvement** (more precise referent for "the value closest to flipping the state"), with EN/ZH parity and no banned vocab.

## Theme findings

The PR touches **no CSS, no design tokens, no template chrome, and no theme-aware structure**. The diff is a one-line copy swap inside an existing `<p>` inside an existing `<details>` block.

- **No CSS rules added or modified.** ✓
- **No color, fill, or stroke changes.** ✓
- **No `color-mix(...)`, no rgba, no opacity tricks, no inline `style.textContent` injection.** ✓
- **No design-token reference changes** (no `--panel2`, `--ink-3`, `--muted`, `--line` references added or removed). ✓
- **No `data-band`, `data-reading-state`, `data-tone`, or other theme-aware attribute hooks added.** ✓
- **No template family change** — still inside the `_site_nav.html.j2` family per the standing chrome contract; copy lives inside `<span class="l-en">…<span class="l-zh">` swap shape. ✓
- **Dark/light parity:** the copy string is identical in both themes (no theme-conditional branching needed); the swap between EN/ZH is theme.js-driven and unchanged by this PR. ✓
- **Mobile layout:** the changed `<p>` lives inside `<details class="mc-details">` which is collapsed by default on mobile; no overflow risk introduced by a one-word copy swap. ✓
- **ZH width:** 读数 is two characters, 坐标轴 is three characters — net ZH line gets **shorter**, which is a benign mobile-width win. ✓
- **No theme debt introduced** by this PR.

**Theme verdict: PASS** — 0 blocking findings, 0 minor findings. The PR is theme-inert by construction (text-only, no styling).

## Validated-claims findings

- **No `validated` keyword in user-facing strings:** grep over the diff (the one EN swap and the one ZH swap) returns 0 hits on `validated` / `验证` / `已验证` / `已校`. ✓
- **No `VALIDATED` prefix/stamp/banner introduced** anywhere on the page; the changed paragraph does not gain or lose a chip, badge, or stamp. ✓
- **No instrument verdict surfaced as a market verdict:** the line still reads "Nothing here tells you to act / 此处不提供任何操作指示" — the textbook compliant "this is data, not a call" posture. ✓
- **No new chip or badge label added** that could collide with the validator's banned-phrase list (e.g., "validated", "confirmed", "verified", "live", "real-time"). The two existing chips on the page (`Descriptive / 描述性` on the glance row, `Current / 当前有效` on each axis cell) are unchanged. ✓
- **Test surface:** the change is exercised by `test_11_thirteen_other_suite_pages_byte_identical` — that test is a byte-identity assertion, not a marketing-claim check, so the fix tightens the gate rather than loosening it. ✓
- **No `check_validated_claims.py` regression risk** — neither the old ("axis") nor the new ("reading") strings match any banned pattern. The change is in the validator's safe zone. ✓
- **Capability framing:** the PR body explicitly frames this as a **byte-identity heal** for a stale-render drift, not as a fresh analytical claim. No marketing-style wording introduced. ✓
- **`scripts/check_validated_claims.py --selftest` relevance:** no synthetic pattern from the selftest set is touched by this PR. ✓

**Validated-claims verdict: PASS** — 0 blocking findings, 0 minor findings. The PR adds zero new claim surface; the operator-tier paragraph it edits never claimed anything actionable, and the fix preserves that posture.

## Overall verdict

**PASS** on all three dimensions (plain-language, theme, validated-claims).

The PR is a **text-only byte-identity heal** on one operator-tier paragraph of `site/macro_liquidity_regime.html`. It eliminates a single-line drift between the committed page and a fresh render after #8032's canonical-source change. Side-benefit: the swap from "axis / 坐标轴" to "reading / 读数" is a small plain-language precision improvement (the more accurate referent for a single numeric value approaching a boundary), with EN/ZH parity and zero theme or claim surface touched. No blocking, no major, no minor findings on the three audit dimensions.
