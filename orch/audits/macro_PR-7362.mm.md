# Audit — mastermindx-market-intelligence/macro PR #7362

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7362](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/7362) |
| title | [MO-B W7-1] F02: Europe official-press panel on euro_area.html over the existing qbus join (MO-PAID-034) |
| workplan | MO-B (Mastermind O-B), packet B-W7-1 / MO-PAID-034 (F02 user-facing half) |
| mergedAt | 2026-09-19T10:53:30Z |
| merge commit | `01042c7731ee80687ace943e2ae8d75ffd99bf5d` onto `origin/main` |
| PR head (last commit) | `ce816cdafa26b93985943fba7d646bed093b1dc4` — "drop the receipt-shaped evidence stub; recapture: NEEDED lives in the PR body and the ledger" |
| feature head | `24f260a2c8965782f64cc165d1996465ffc033e4` (r3 — restored the builder gate after r2 regressed) |
| audit base | `ac50412cb294d3da9992b338f94d01f11f11d43c` (parent of r1 `8dc918a8…`) |
| files | 5 changed (614 +, 8 −) at the r3 head; +1 deletion at ce816cdafa (evidence stub): `engine/europe_news_intel.py`, `scripts/build_international_macro.py`, `templates/international_macro.html.j2`, `.github/ci/legacy-jobs.yml`, `tests/test_europe_news_panel.py` (new, 434 lines) |
| half-B label | "half-B" = MO-B F02 (user-facing read-out) half. Europe ingest is pre-existing (read_events + accrual + schema). This PR adds a render-time display packet `panel()` and an `#europe-news` section on the `euro_area.html` join surface. Ledger move: `next_bounded_child` from "rendered Europe panel owed" → "Europe panel on euro_area.html #europe-news. Live GET owed."; `capability_state_c2` `PARTIAL` → `BUILT_NOT_PROVEN` (rendered-but-gated) until Live GET confirms. RULED cells untouched. |
| programme surface | Two surfaces: (a) `engine/europe_news_intel.panel(asof)` — pure, no ambient clock, no network, no `now()`, consumes `read_events(asof)` only, 14-day recency window, capped at 12 rows, returns `None` (never raises) when parquet is missing/empty/old; (b) `templates/international_macro.html.j2` adds `<section id="europe-news">` between the policy section and the source-health section, gated on `{% if europe_news %}`, render-only when `cc == "EZ"`. |

The PR went through 3 rounds (r1 `8dc918a8`, r2 `2844ca98` regressed by reverting the builder gate, r3 `24f260a2` restored it). The seat deterministic ratification at 24f260a2 named it `BUILT_NOT_PROVEN` and merged-on-green; the seat evidence-law fix at `ce816cdafa` removed the receipt-shaped `EVIDENCE.yml` stub because the +12-line template change is not material under `check_ui_visual_evidence.py`'s three regexes (`<style(?:\s|>)` literal tag in templates; new content in `templates/*.css`; runtime-style signatures in user-facing .js). Recapture: NEEDED is recorded in the PR body and the ledger; the follow-on lane is `scripts/capture_page_evidence.py` at the merged code head.

## Plain-language findings

Macro has no `terminal/scripts/check_plain_language.mjs` equivalent — that gate is terminal-side. The macro-side equivalent is the bilingual `t(en, zh)` idiom (`templates/international_macro.html.j2:6` defines `{% macro t(en, zh='') -%}` wrapping `<span class="l-en">` / `<span class="l-zh">`), which is the bilingual-parity enforcement mechanism. The plain-language lens reduces here to: did this PR introduce any new user-visible raw slugs / untranslated strings / English-only leaks / ZH orphans?

**Verdict: PASS (0 new bilingual debt; 0 new strings-without-ZH-twin).**

Manual inspection of every new visible string in the PR's diff:

- **`templates/international_macro.html.j2`** (+12 lines, MODIFIED) — the `#europe-news` section introduces six new bilingual pairs and one mixed-pattern call:

  | New visible string | ZH twin | Source |
  | --- | --- | --- |
  | `Europe official press` (h2) | `欧洲官方新闻` | inline `t('…','…')` |
  | `Public official and central bank press wires, CC BY 4.0 / OGL v3.` (subtitle) | `公共官方与央行新闻稿，CC BY 4.0 / OGL v3。` | inline `t('…','…')`, ZH twin uses Chinese full-stop `。` |
  | `Date` (th) | `日期` | inline `t('…','…')` |
  | `Source` (th) | `来源` | inline `t('…','…')` |
  | `Headline` (th) | `标题` | inline `t('…','…')` |
  | `Jurisdiction` (th) | `司法管辖区` | inline `t('…','…')` |
  | `{{ item.title }}` (headline cell) | `{{ item.title }}` (same string for both) | `t(item.title, item.title)` — honest content rendering: real press-wire headlines are usually available in only the publisher's language, so passing the same string for both is the lawful pattern. The `l-en`/`l-zh` macro will show that headline under whichever language the UI is set to. |

  Six inline `t(en, zh)` pairs with the second argument non-empty → ZH parity for every static UI string. The two `<span class="l-en">{{ item.source }}</span><span class="l-zh">{{ item.source_zh }}</span>` cells and the same for jurisdiction also have ZH twins supplied by the engine payload (`source_zh`, `jurisdiction_zh`), not raw concatenation. The `t(item.title, item.title)` self-pairing for headline cells is the same pattern the rest of the file uses for any content field where the source itself is monolingual (e.g. the table subtitle on the policy section).

- **`engine/europe_news_intel.py`** (+127 lines, MODIFIED, NO new user-visible strings) — adds `_JURISDICTION_LABELS: dict[str, tuple[str, str]]` (5 entries: EU/EA/UK/EFTA/AMBIGUOUS_JURISDICTION, each a real EN/ZH pair: `("European Union","欧盟")`, `("Euro Area","欧元区")`, `("United Kingdom","英国")`, `("EFTA","欧洲自由贸易联盟")`, `("Europe (unassigned)","欧洲（未归属）")`); `_jurisdiction_label(jurisdiction)` returns `(en, zh)` with a lawful fallback `("Europe","欧洲")` for unknown jurisdictions (m2); `_source_labels(source_key)` returns `(en, zh)` with the documented honest defaults `("Official source","官方来源")` (m1 — uses config `publisher`/`publisher_zh` when present, else these exact strings). `_panel_origin_ts(asof, seendate)` is a clock helper, no strings. `panel(asof)` returns `None` (never raises) and assembles items with `source`, `source_zh`, `jurisdiction_en`, `jurisdiction_zh` — every visible field has its ZH twin. The module does not write any user-visible string outside of the two honest fallback labels above, both of which have explicit EN/ZH pairs.

- **`scripts/build_international_macro.py`** (+35 lines, MODIFIED) — adds the EZ-only `europe_news = eni.panel(asof_date)` call inside a `try/except Exception` so any panel error logs at warning and renders the page without the section. No new visible strings.

- **`tests/test_europe_news_panel.py`** (NEW, +434 lines) — tests only. Contains fixture strings like `"官方来源"` and `("European Commission", ...)` used as test inputs/assertions, not user-visible.

- **`.github/ci/legacy-jobs.yml`** (+6 lines, MODIFIED) — adds `jinja2` to the europe pip-install line and `tests/test_europe_news_panel.py` to the europe pytest step; widens `unrun-picks-boards` paths by one entry (`engine/europe_news_intel.py`). YAML; no strings.

Spot-check on the bilingual idiom for ZH parity:

```
$ grep -nE "l-en|l-zh" templates/international_macro.html.j2 | head -3
6:{% macro t(en, zh='') -%}<span class="l-en">{{ en|safe }}</span><span class="l-zh">{{ (zh if zh else en)|safe }}</span>{%- endmacro %}
386:... <span class="l-zh">{{ item.source_zh }}</span> ... <span class="l-zh">{{ item.jurisdiction_zh }}</span> ...
```

Every new user-visible string routes through the bilingual idiom; no raw English literals leak; no ZH orphan.

Conclusion: this PR adds **zero** new plain-language debt. The bilingual pairs are inline (not LEX catalogue entries, which is consistent with the rest of `international_macro.html.j2`'s 18 inline pairs), ZH twins use CJK punctuation correctly (the `。` in the subtitle, the `（…）` in the unassigned jurisdiction), and the engine payload always ships both `*_en` and `*_zh` keys for any field the template reads.

## Theme findings

Laws in force: TP-0 art direction (dark + light are TWO art directions, not one skin; required evidence matrix dark × light × EN/ZH × desktop(1440) / mobile(390) = 8 cells minimum for any user-facing material change). The capture receipt producer is `scripts/capture_page_evidence.py`; the evidence corpus lives at `mockups/evidence/<route>/{manifest.json,smells.json,smells.md,EVIDENCE.yml}`. Material-change detection (`scripts/check_ui_visual_evidence.py`) is intentionally mechanical and narrow: three regexes — `<style(?:\s|>)` literal tag in templates; new content in `templates/*.css`; runtime-style signatures in user-facing `.js`.

**Verdict: PARTIAL — gate agrees this is not material under its three regexes (no receipt required); `recapture: NEEDED` lives in the PR body and the ledger; the seat explicitly defers the dark × light × EN/ZH × 1440/390 capture to a follow-on lane as `BUILT_NOT_PROVEN`.**

Findings, ranked:

1. **`recapture: NEEDED` — recorded in body and ledger, NOT a gate violation** (`templates/international_macro.html.j2` edited; +12 lines; `engine/europe_news_intel.panel()` is a new public function read by the international_macro builder; `mockups/evidence/euro_area/` directory was deleted in the seat commit `ce816cdafa`). Body quote: "MO-PAID-034 is BUILT_NOT_PROVEN until the Europe panel is captured at the merged code head with `scripts/capture_page_evidence.py` (follow-on lane)." The ledger move reflects the same: `next_bounded_child` "Live GET owed" + `capability_state_c2` `BUILT_NOT_PROVEN`. This is the lawful posture per `DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06`-style art-direction discipline: when a follow-on capture lane exists, the gate does not block, the body and ledger record the gap.

2. **Gate check — `check_ui_visual_evidence.py` on the diff file** — body claim is correct: the +12-line template change is **not** material under the gate's three regexes. The three new `style="..."` attributes on `<div class="imd-card">` (`padding:0;overflow:hidden`), `<table class="imd-table">` (`min-width:0`), and three `<td>` elements (`white-space:nowrap`) are HTML inline attributes — they do NOT match `<style(?:\s|>)` literal-tag regex (which requires a `<style…>` tag, not an inline `style="…"=""` attribute), they are not in a `templates/*.css` file, and there is no `.js` runtime-style signature added. The gate's mechanical material-change detection therefore returns False for this file, and no `EVIDENCE.yml` receipt is required to merge.

3. **`check_design_system.py --mode enforce-added --diff-file templates/international_macro.html.j2`** returned `0 blocking finding(s)` (estate pre-existing, non-blocking: 18 976 — the project-wide ratchet noise that the gate enumerates but does not regress on). The new `<section id="europe-news">` reuses the existing `.imd-section`, `.imd-section-head`, `.imd-card`, `.imd-table`, `.l-en`/`.l-zh` classes — all canonical design-system tokens from `theme.css`. No new CSS variables, no new colour literals, no new font-family literals, no new radius literals, no new iconography. The inline `style="…"` attributes are layout-only (`padding:0`, `overflow:hidden`, `min-width:0`, `white-space:nowrap`) — they do not introduce new design tokens; they reproduce the table-card pattern the file already uses on other sections.

4. **`check_runtime_style_injection.py`** — returned `OK (195 .js files scanned, 44 injecting, 89 total hits — all within frozen allowances)`. The PR adds no `.js` files; nothing to flag.

5. **Inline-style hygiene** — the diff adds 3 inline `style="…"` attribute lines (one on `.imd-card`, one on `.imd-table`, three on `<td>` elements). The file already has 6 such inline styles pre-PR (lines 240, 348, 428, 429, 443, 457 — `--score:{{ D.decision.score }}`, `padding:20px`, `margin-top:18px`, `width:{{ [val|abs*3,100]|min }}%`, and the policy section's `margin-top:18px` headers). The new styles match the file's established pattern (table-card `padding:0;overflow:hidden;min-width:0` and tabular `white-space:nowrap` for short cells). **Not a regression**; the file's own established idiom. A future refactor could move these into `theme.css` under a `.imd-card--flush` / `.imd-table--flush` modifier — that's a separate clean-up lane, not this PR's debt.

6. **Bilingual idiom — dark and light both render** — the `<span class="l-en">` / `<span class="l-zh">` cells rely on the `l-en`/`l-zh` class swap driven by the language toggle (the same mechanism the rest of `international_macro.html.j2` uses). Both classes resolve to the same parent layout cell in dark and light — no theme-specific tweak is required for this section. The `t(en, zh)` macro on the header / subtitle / th cells renders the active-language span with no theme coupling. **Same idiom as the rest of the page; no theme-specific debt.**

Conclusion: the PR adds **zero** design-system debt (enforce-added blocking = 0); theme debt is unchanged from `ac50412c` to `01042c77`. The standing TP-0 evidence matrix is **NOT YET CAPTURED** at the merged code head; this is recorded honestly in the PR body and the ledger as `recapture: NEEDED` / `BUILT_NOT_PROVEN`, and the seat explicitly defers the 8-cell capture to a follow-on lane. The Live GET (`https://www.mastermind-x.com/euro_area.html` → HTTP 200 with `id="europe-news"`) is the verification gate that closes the loop.

## Validated-claims findings

Tool: `python3 -m scripts.check_validated_claims` (BC-2 — the 'validated' grep gate; D2 §4.3). Scans user-facing surfaces in both EN and ZH and fails on an affirmative 'validated' / '已验证' / '经验证' / '经过验证' claim that maps to no backing artifact (allowlist entry with matching `surfaces` list, or referenced artifact JSON with `validated == true`). Negated / hedged uses are NOT claims and are auto-skipped.

**Verdict: PASS (0 new validated-claim debt in this PR's footprint).**

Direct grep across the 5 PR files for the BC-2 trigger phrases:

```
$ grep -niE "(validated|已验证|经验证|经过验证)" \
    engine/europe_news_intel.py scripts/build_international_macro.py \
    templates/international_macro.html.j2 tests/test_europe_news_panel.py \
    .github/ci/legacy-jobs.yml
(no matches)
```

The PR introduces zero BC-2 claim-class vocabulary. The only literal new English strings on a user-facing surface are:

- `Europe official press` / `欧洲官方新闻` (section header)
- `Public official and central bank press wires, CC BY 4.0 / OGL v3.` / `公共官方与央行新闻稿，CC BY 4.0 / OGL v3。` (subtitle)
- `Date` / `日期`, `Source` / `来源`, `Headline` / `标题`, `Jurisdiction` / `司法管辖区` (table headers)
- `Official source` / `官方来源` (publisher fallback when config has no `publisher` / `publisher_zh`)
- `(European Union, 欧盟)`, `(Euro Area, 欧元区)`, `(United Kingdom, 英国)`, `(EFTA, 欧洲自由贸易联盟)`, `(Europe (unassigned), 欧洲（未归属）)` (jurisdiction labels)

None of these is the "validated" claim class. "Official" in the publisher fallback (`"Official source"` / `"官方来源"`) is a publisher-label placeholder, NOT a claim about the platform's signal/score/rank/gate — it is the human-readable name for a press wire whose URL is rendered next to the headline (so the user can verify provenance themselves). Per BC-2's doctrine ("the word 'validated' in user-facing text"), this is the lawful `is_context_only=True` posture already encoded in `panel()` (`items` carry title / url / source / source_zh / seendate / jurisdiction_en / jurisdiction_zh only; `importance_raw`, `event_key`, `item_id`, and theme slugs are explicitly absent — no scores, no ranking, no LLM signals).

Global check on the merged head (estate-wide):

```
$ python3 -m scripts.check_validated_claims 2>&1 | head -3
::error:: 38 UNEARNED 'validated' claim(s) — each must map to a backing artifact ...
```

All 38 unearned claims are pre-existing on files this PR does NOT touch:

- `templates/_macro_suite_shell.html.j2` (lines 17, 798) — pre-existing shell template.
- `templates/canada.html.j2:2309`, `templates/hk.html.j2:3528`, `templates/hk.html.j2:3655` — pre-existing.
- 14× `templates/macro_*.html.j2:6-8` — pre-existing macro-suite shells (capital structure, consumer payments, financial conditions, growth real economy, housing real estate, inflation system, labor markets, liquidity central banks, liquidity regime, monetary policy, national debt liabilities, rates curves, trade flows).
- `templates/macro_business_activity.html.j2:6`, `templates/macro_capital_structure.html.j2:6`, … — pre-existing.
- `templates/macro_suite.js:4`, `templates/mm_brain.js:3584`, `site/macro_suite.js:4`, `site/mm_brain.js:3584` — pre-existing.
- 14× `site/macro_*.html` lineage notes — pre-existing rendered output.
- `engine/market_os/macro_workspaces/consumer.py:106` — pre-existing engine source.

Cross-check: `git diff ac50412c…ce816cdafa -- '*.j2' '*.py' '*.js' '*.yml'` and grep for the BC-2 trigger phrases — **zero matches**. The PR adds no new BC-2 claims. The 38 estate-wide unearned claims are an upstream pre-existing pile (unchanged from `ac50412c` to `ce816cdafa`) and are out of scope for this audit.

Conclusion: this PR adds **zero** new validated-claim debt. BC-2's posture for this PR is correct: an explicit `is_context_only=True` payload with no scores / ranks / LLM signals, no "validated" vocabulary on the user-facing surface, and the publisher-name placeholder is a provenance label, not a signal-class claim.

## Overall verdict

**PARTIAL — ship-chain correct; evidence gap honestly recorded as `BUILT_NOT_PROVEN`.**

| Law | Status | Evidence |
| --- | --- | --- |
| Plain-language / bilingual parity | **PASS** | All 6 new static strings ship EN/ZH pairs via the `t(en, zh)` inline idiom; ZH twins use CJK punctuation correctly; engine payload supplies both `*_en` and `*_zh` for every cell field; `t(item.title, item.title)` is the lawful self-pairing pattern for monolingual external content. |
| Theme / art-direction | **PARTIAL** | `check_ui_visual_evidence.py` confirms the +12-line template change is not material under its three regexes (no `<style>` tag, no `.css` edit, no runtime `.js` injection); `check_design_system.py --mode enforce-added` returns 0 blocking findings on the diff file; `recapture: NEEDED` is recorded in the PR body and the ledger as `BUILT_NOT_PROVEN` until a follow-on lane runs `scripts/capture_page_evidence.py` at the merged code head. |
| Validated-claims | **PASS** | Zero BC-2 trigger phrases in the PR's 5 files; `panel()` is `is_context_only=True` with no scores / ranks / LLM signals; publisher-name placeholder (`"Official source"` / `"官方来源"`) is a provenance label, not a signal-class claim. |

Recommended close-out lane (not this PR's debt, but the follow-on to convert BUILT_NOT_PROVEN → BUILT_PROVEN):

1. **Recapture the 8-cell evidence matrix for the `#europe-news` section on `euro_area.html`** at the merged code head (`01042c77…`) via `scripts/capture_page_evidence.py`. Required keys per TP-0: dark × light × EN/ZH × desktop(1440) / mobile(390) = 8 PNGs + `manifest.json` + `smells.json` + `smells.md` + `EVIDENCE.yml` (with the three required keys `schema`, `changed_paths`, `manifest`) under `mockups/evidence/euro_area/`.
2. **Live GET verification** — `GET https://www.mastermind-x.com/euro_area.html` → HTTP 200 with `id="europe-news"`, bilingual "Europe official press" / "欧洲官方新闻" header, and `panel()` rows inside the 14-day window when the desk parquet is fresh.
3. **Ledger move** on `MO-PAID-034` from `BUILT_NOT_PROVEN` to `BUILT_PROVEN` once both above are green.

Standing laws observed: `MERGE_ON_CONCLUDED_CHECKS` (seat ratified after 32 passing tests + contract-delta 0 introduced + 13 pending / 0 binding fails); `DEC:EVIDENCE-HEAD-LAW` (`# recapture: NEEDED` recorded honestly in body and ledger); `DEC:HEAL-EXECUTION-INVARIANTS` (the r2 regression was caught by the r3 review and the builder gate restored before merge); `DEC:BLOCKER-FREEZE-NOT-MISSION-FREEZE` (M1–M4 minors + B1–B3 blockers all closed in r3, no carryover). No IN-FLIGHT cover needed (this is a closed ship-state with a recorded evidence gap, not a contested lane).
