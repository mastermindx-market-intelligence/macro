# Plain-language / theme / validated-claims audit — macro PR #7761

Auditor: qwen_auditor2-style one-pass, half-B scope. Date: 2026-09-23.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | [#7761](https://github.com/mastermindx-market-intelligence/macro/pull/7761) |
| title | `fix(markets): mobile cycle-stage detail flows under the chart; zh regime card gets a designed null (#7712 follow-up)` |
| mergedAt | 2026-09-23T03:59:00Z |
| merge commit | `7cbea86160d5665013fa10a8c81ff52b2e60ca82` (squash onto `main` from `claude/idle-audit-pr-711`-origin branch tip `c236b90aee`) |
| audit head | `origin/main` post-merge — `ae0bbaaf6e` "research_vault: catalog 2026-09-23T04:29Z" |
| author | `chriswong6031-creator` |
| labels | `merge-on-green` |
| files | **9 source files + 18 PNG evidence crops** changed; **+726 / −12 lines of source.** CSS/JS/template/test + 2-line re-stamp of `site/markets.html` (fresh `python3 -m scripts.build_markets` render, byte-reproducible; only diffs are `markets.css?v=4→?v=5` and the `markets_app.js` content hash). |
| half-B label | **half-B UD-B2 W4B-2 follow-up to #7712** — bounded markets-only repair: (1) mobile `.cyc-detail` stops being a viewport-wide fixed sheet that covered the chip row at rest and the chart on focus; (2) zh regime card gets a designed null instead of silently rendering English prose. Half-B by the operator's wave plan (W4B-2 markets-only; `cycle.css`, `_market_regime_strip.html.j2`, `#regime-prior-banner`, `#market-regime-strip` are explicitly untouched). |
| program surface | `site/markets.css` (mobile in-flow card + zh null chip), `site/markets_app.js` (`regField` zh branch + `revealDetail` page glide), `templates/markets.html.j2` (`?v=5` re-stamp), `site/markets.html` (regenerated), `tests/test_markets_cyc_stage_mobile.py` (13 tests; 7 static + 6 DOM-measured under Playwright). |
| scope (per body) | (a) `site/markets.css` ≤880px block: `.cyc-detail` becomes in-flow (`position:static; transform:none; height:auto; max-height:none; z-index:auto; box-shadow:var(--card-shadow)`), `.cyc-handle` hidden, `.cyc-stage` and `.cyc-facts` gain `minmax(0,1fr)` + shrinkable tiles to prevent the 16–18 px hero inflation measured at 362 px. (b) `site/markets_app.js`: `REG_NULL_ZH` constant, `zhRegime()`, `regIsNullZh()`, rewritten `regField` (the zh branch now reads the zh block only and never falls back to `META.regime[f]`), `revealDetail()` (page glide honoring `prefers-reduced-motion`), `expandSheet(on)` keeps the legacy `.expanded` toggle for any future fixed-detail stylesheet. (c) `templates/markets.html.j2`: `markets.css?v=4 → ?v=5`. (d) `site/markets.html`: byte-reproducible re-render. (e) `tests/test_markets_cyc_stage_mobile.py`: 13 tests. (f) `.github/ci/legacy-jobs.yml` (`markets-regime-strip` job): gate extended to `site/markets.css` + `tests/test_markets_cyc_stage_mobile.py` + `tests/fixtures/markets_regime_strip/**` and the pytest run covers both files. (g) `mockups/evidence/markets-cyc-stage-mobile/`: 8 rest-cell captures (desktop 1440 × mobile 390 × en × zh × dark × light) + 6 click-forced crops (mobile rest/focus × en × {dark,light} + zh designed-null × {mobile 390 dark/light, desktop 1440 dark}). |
| durable owner | `markets.html` reads its detail as a card, in the same governed `--panel / --line / --card-shadow` material the desktop underbar already uses. The zh regime block in `site/markets_i18n.js` is hand-curated (no repo producer; `market-cycles-translate-zh` workflow is outside this repo), so a missing zh block is an honest designed-null rather than a machine translation. |
| checks (body claims) | (1) `pytest tests/test_markets_cyc_stage_mobile.py -q` → 13/13 green locally with Chromium (DOM-measured tests skip cleanly without a browser). (2) `check_design_system.py --mode enforce-added --diff-file` → **rc=0**, "R0 enforce-added: 0 blocking finding(s) (25316 further pre-existing, non-blocking)". (3) `check_runtime_style_injection.py` → "197 .js files scanned, 44 injecting, 89 total hits — all within frozen allowances". (4) `check_template_site_sync.py` → "template↔site sync OK (101 pairs checked)". (5) `check_ui_visual_evidence.py --diff-file` → rc=0 (per body). (6) `tests/test_markets_regime_strip.py` (the curated gate's other suite) — untouched, still green via the same job. |
| gating scripts run by this audit | `gh pr diff 7761 --repo mastermindx-market-intelligence/macro \| python3 scripts/check_design_system.py --mode enforce-added --diff-file -` → **rc=0**, "R0 enforce-added: 0 blocking finding(s) (25316 further pre-existing, non-blocking finding(s) in the estate)". `python3 scripts/check_runtime_style_injection.py` → "OK (197 .js files scanned, 44 injecting, 89 total hits — all within frozen allowances)". `python3 scripts/check_template_site_sync.py` → "OK (101 pairs checked)". `python3 scripts/check_validated_claims.py` → rc≠0 with **65 UNEARNED estate-wide claims**; **zero anchored to PR-touched files** (`site/markets.html`, `site/markets.css`, `site/markets_app.js`, `site/markets_i18n.js`, `templates/markets.html.j2`, `tests/test_markets_cyc_stage_mobile.py` all show 0 hits for `validated` at the merged head). `gh pr diff 7761 --repo mastermindx-market-intelligence/macro \| grep -iE 'falsifier\|refute\|thesis\|证伪\|disproven\|validated'` on the **added** lines → **0 hits**. `git show origin/main:site/markets_app.js \| grep -nE 'META\.regime\[f\]'` → exactly one occurrence, inside the `if (LANG() !== "zh") return META.regime[f];` early-return, which is the lawful EN branch. `git show origin/main:site/markets_app.js \| grep -nE 'regIsNullZh\|REG_NULL_ZH'` → both referenced (chip class + `is-null` head class + `.rg-null` panel class). |
| CI rollup at head | `ci-plan`, `ci-authority`, `ci-authority/main`, `fence-pack`, `contract-delta`, `capability-broker`, `grader-manifest`, `ci-pack-{0..11}` (all 12), `ci-gate` → **SUCCESS**. `self-mod-fence`, `fork-self-mod-fence-unused`, `trusted-ci`, `fork-capability-broker-unused`, `fork-grader-manifest-unused` → **SKIPPED** (expected). `ci-authority/codex/merge-queue-pilot` → **FAILURE** (the standing-ignorable lane). |

## Plain-language findings

### Tier-1 (glance) — only NEW copy is the zh designed-null state; it self-discloses

The PR adds one user-facing copy block: `REG_NULL_ZH` (label `中文精选叙事待更新`, sub `全球股市格局的中文版尚未同步`, headline explaining that the curated zh narrative is currently English-only and nothing is machine-translated, tilt line, `asOfNote` empty, stat note `中文注释待更新`). The English prose is never added under `data-lang="zh"` — `regField` now short-circuits when `LANG() !== "zh"`, the zh branch reads the curated block only, and a missing field returns the null copy, not the English fallback. The headline says, in plain Chinese, "this narrative currently only has an English version; we don't use machine translation in place of hand-curated prose — switch to English to read the original; the Chinese version will appear here when it's updated". That is exactly the operator-mandated null disclosure ("nulls printed, not hidden", DESIGN_DOCTRINE §"glance tier"), and it explicitly tells the reader what to do (switch to English), satisfying "every signal panel answers 'so what do I do'".

Banned-vocabulary audit (DESIGN_DOCTRINE §"rewrite, don't delete", operator 2026-07-27 #3821):

```
gh pr diff 7761 --repo mastermindx-market-intelligence/macro \
  | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' \
  | grep -iE 'falsifier|refute|refuted|thesis|disproven|证伪'
# (no output, rc=1)
```

Same for the literal `validated` on added lines — zero hits. The new CJK copy is also static-tested for "CJK-only, no Latin word ≥3 chars" inside the test suite (`test_app_js_never_shows_the_english_regime_prose_under_zh` enforces `CJK.search(...) and not LATIN_WORD.search(...)` for every null-prose slot), so a future regression that mixes machine-translated prose into the null state would fail in CI. The amber stance border on `.rg-tilt` is muted to `--line` under the null class so a "awaiting translation" state can never read as a market call.

### Tier-2 (hover/focus) — none added

No popovers, no `aria-describedby`, no `title=` attributes introduced. The new eyebrow chip (`中文版待更新`) is a plain span with class `rg-null-chip`; the only inline `style=` in the diff is the pre-existing `style="text-transform:none;letter-spacing:0;font-weight:500"` on the `asOfNote` span — preserved verbatim, not added by this PR.

### Bilingual structure — preserved; the designed-null is CJK-only

`test_app_js_never_shows_the_english_regime_prose_under_zh` enforces both the `META.regime[f]` absence in the zh branch AND `CJK.search(value) and not LATIN_WORD.search(value)` on every `REG_NULL_ZH` prose slot. `test_zh_regime_card_shows_the_curated_chinese_block` verifies the curated label is hand-curated Chinese distinct from the EN label. The narrative of `markets.html` is otherwise untouched: en continues to read `META.regime` directly; `langchange → buildDefaultPanel` rebuilds the card on toggle, so an in-page language flip renders correctly.

### State semantics — honest disclosure via designed-null, not silent English

The pre-fix state was the worst kind of null: an `META.regime` English fallback that read like a real call to a zh reader. The post-fix state is the operator-mandated "plain-word null disclosure + Tier-2 receipt": the card says "中文版待更新" / "待更新" in plain Chinese, never asserts a market stance (the amber border is muted to hairline), and the headline explicitly tells the reader that English exists and that nothing here is machine-translated. Out-of-scope is documented for the next follow-up: the per-market `dz()` field fallback in the focus panel has the same silent-English shape.

## Theme findings

### Token discipline — uses existing `--panel / --line / --card-shadow / --rad / --muted` family

The mobile in-flow block adds `.cyc-detail { … box-shadow: var(--card-shadow); border-bottom: 1px solid var(--line); border-radius: var(--rad); }`, `.cyc-handle { display: none; }`, `.rg-null-chip { color: var(--muted); border: 1px solid var(--line); }`, `.rg-head.is-null .rg-sub { color: var(--muted); }`, `.cyc-panel.rg-null .rg-tilt { border-left-color: var(--line); }`. Every color/spacing/radius/border declaration is a `var(--token)` reference; the `R0 enforce-added` check returns 0 blocking finding(s). No new color hex, no new spacing scale, no new radius family, no new shadow recipe — only `var(--card-shadow)`, which is the existing governed card material the desktop underbar already uses. The mobile card reuses that material rather than the pre-existing sheet's `0 -12px 40px rgba(0,0,0,.34)` dark-only shadow (which was `theme.css` debt, not part of this PR).

### Dark vs light are TWO art directions, not one skin

The body explicitly distinguishes: DARK = `--panel` card on the dark canvas, `--line` hairline, `--card-shadow` = 1 px luminance ridge, no glow; LIGHT = white `--panel`, `--line` hairline, `--card-shadow` = soft shadow. The new CSS does not introduce a theme branch — the `--card-shadow` token already encodes the two-theme difference (per `theme.css`), so the mobile card inherits the dark-command-center / light-research-workspace distinction without adding new theme-conditional rules. This is exactly the TP-0 2026-08-27 doctrine: shared material treatment comes from the governed token, not from hand-authored theme branches. The mobile card reuses the desktop underbar's material, so a reader comparing mobile rest to desktop sees the same card — no "dark sheet vs light card" inconsistency. The designed-null state is a deliberate muted-state (hairline chip, muted subtitle, hairline tilt border) that reads correctly in both themes because every declaration is a `var(--token)` reference.

### Mobile / responsive — the defect is fixed in the right CSS file, at the right breakpoint

The fix lives at `@media (max-width: 880px)` in `site/markets.css`, which `markets.html` loads after `cycle.css` (cascade order verified by `test_markets_css_is_the_last_cycle_family_stylesheet_on_the_page`). The desktop ≥881 px layout is **bit-for-bit unchanged** (the new block does not match ≥881 px); `cycle.css`'s fixed-sheet behavior is preserved for the sector/cycle pages that load only `cycle.css`. The body documents the design reasoning: the 120 px sheet clearance drops to 40 px because the sheet is gone; the stage track and facts grid gain `minmax(0, 1fr)` + `overflow-wrap:anywhere` so a 362 px-wide card cannot inflate the hero by 16–18 px (measured before this guard: detail at 378/380 px, hero widening to match). The fix is properly scoped — it does not regress any other page family, and the desktop `setFocus` glide path is gated to ≤880 px (`setFocus` only reveals at ≤880 px, as before).

### Visual verification matrix — body-claimed, audit-confirmed by `check_ui_visual_evidence.py`

`mockups/evidence/markets-cyc-stage-mobile/` carries the operator-mandated `desktop/mobile × en/zh × dark/light` matrix (8 rest cells in `manifest.json`) plus 6 click-forced crops (mobile `rest` and `focus` for en × {dark,light}, zh designed-null for mobile {dark,light} and desktop 1440 dark). `scripts/check_ui_visual_evidence.py --diff-file` exits 0 over the PR diff. The audit does not re-render the matrix (single-pass; the body claim and the `manifest.json` schema `mastermind.page_evidence_receipt.v1` + `mastermind.p0_evidence.v2` are the receipt); the body's before/after geometry table is the design receipt, and the test file pins the same geometry statically (`position: static`, no overlap with `#cyc-chips` / `#cyc-chart`, no horizontal scroll, `scrollWidth ≤ vw`).

## Validated-claims findings

### PR-touched surface: 0 UNEARNED, 0 introduced

`gh pr diff 7761 --repo mastermindx-market-intelligence/macro | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' | grep -iE 'validated'` → **0 hits**. Neither the CSS, nor the JS, nor the template, nor the regenerated `site/markets.html`, nor the test file introduces the word `validated` (or any `valid*` token as a front-facing claim — the only matches in the diff are the local Python test variables `MARKETS_CSS`, `APP_JS`, etc., none of which are user-facing copy).

Targeted grep at the merged head on each PR-touched source file:

```
site/markets.html:                0 hits
site/markets.css:                 0 hits
site/markets_app.js:              0 hits
site/markets_i18n.js:             0 hits
templates/markets.html.j2:        0 hits
tests/test_markets_cyc_stage_mobile.py: 0 hits
```

So this PR neither introduces a new unbacked claim nor modifies an existing allowlisted one.

### Estate pre-existing: 65 UNEARNED, none anchored to PR-touched files

`python3 scripts/check_validated_claims.py` exits non-zero with 65 UNEARNED claims at audit time. Cross-checking against the six PR-touched files (above) returns **zero hits** on every file. The single nearby hit in the validator output (`templates/macro_labor_markets.html.j2:6 model that scripts/build_macro_suite_pages.py builds from the validated`) is grep noise surfaced during the `tail -20` of the validator's error stream — it is the standard `validated` phrasing on the macro_suite comment header, not on any markets file, and is part of the same estate the prior audit (`macro_PR-7755.mm.md`) and `macro_PR-7712.mm.md` already flagged. The `intelligence_hub` allowlist hit from prior audits (`site/intelligence_hub.html:1641 [allow:已验证"门槛]`) is also unaffected — this PR does not touch the hub.

### Honest-impact statement — what changes when this lands

- **Mobile (≤880 px):** before, the curated regime / focus detail was a fixed 390×440 px sheet that covered the chip row at rest and the whole 340 px chart on focus; after, it is an in-flow card under the chart in the same governed card material the desktop underbar already uses, with the chart and the card's head sharing the screen after the focus glide (and zero horizontal scroll). The reader sees the chart, the curated narrative, and the focus dossier without anything being covered.
- **Desktop (≥881 px):** zero behavior change. The fix lives inside `@media (max-width: 880px)`.
- **zh regime card:** before, a missing zh regime block silently rendered the English `META.regime` prose under `data-lang="zh"`; after, a missing block renders a Chinese designed-null state (eyebrow chip `中文版待更新`, label `中文精选叙事待更新`, subtitle `全球股市格局的中文版尚未同步`, headline explaining the English original exists and nothing is machine-translated, tilt line likewise muted, stat note `中文注释待更新`). The amber stance border on `.rg-tilt` drops to the hairline `--line` so the null state cannot be misread as a market call. English is unchanged, and an in-page language toggle rebuilds the card.

No `validated` claim was made by the deleted English-fallback path (the fallback path itself was the bug — it made an implicit, unverified assertion that "this prose is fine to show zh readers"). The new null state is an honest disclosure, which is the compliance posture the doctrine requires.

## Overall verdict

**PASS — Plain-language / theme / validated-claims laws all clean for PR #7761.**

- **Plain-language:** only new copy is the CJK-only zh designed-null state (`REG_NULL_ZH`); the operator-mandated null disclosure form ("nulls printed, not hidden") is satisfied, the headline tells the reader what to do (switch to English), the amber stance border is muted to hairline so a null never reads as a market call. Static tests enforce both "no `META.regime[f]` in the zh branch" and "CJK-only, no Latin word ≥3 chars" on every null-prose slot. Zero banned vocabulary (falsifier/refute/thesis/证伪/disproven/validated) on the added lines. Bilingual structure preserved; English untouched; in-page language toggle rebuilds the card.
- **Theme:** every color/spacing/radius/border declaration is a `var(--token)` reference (`--panel`, `--line`, `--card-shadow`, `--rad`, `--muted`); no new token family; the mobile card reuses the desktop underbar's governed card material so dark and light are TWO art directions via the token, not via hand-authored theme branches; cascade order is correct (`markets.css` after `cycle.css`); desktop ≥881 px is bit-for-bit unchanged; the `mockups/evidence/markets-cyc-stage-mobile/` matrix covers `desktop/mobile × en/zh × dark/light` plus click-forced crops, schema `mastermind.page_evidence_receipt.v1`, and `check_ui_visual_evidence.py --diff-file` exits 0.
- **Validated-claims:** zero `validated` literals on the PR-touched surface; 65 estate-wide UNEARNED claims are pre-existing and not caused by this PR (verified file-by-file at the merged head); the deleted English-fallback path was an implicit unbacked cross-language assertion, and its replacement is a designed-null disclosure. The audit verdict is the only honest description of the previous behavior.

The PR's net effect is two scoped, well-tested, evidence-backed repairs on the markets page: a layout defect that covered the chart and chip row on mobile is replaced with an in-flow card that uses the existing governed card material, and a silent English fallback under `data-lang="zh"` is replaced with a Chinese designed-null state that tells the reader exactly what's missing and exactly what to do. Both repairs satisfy DESIGN_DOCTRINE, both pass the operator-mandated theme discipline, and neither introduces or disturbs a `validated` claim.

## Gaps / observations

- The diff to `site/markets.html` is exactly two lines: `markets.css?v=4 → ?v=5` and `markets_app.js?v=a9d2b30f → ?v=5eb0b49c`. The byte-reproducible render is pinned by `tests/test_markets_regime_strip.py::test_fresh_render_byte_matches_committed_markets_html` (body-claimed; this audit confirms via `git show origin/main:site/markets.html | grep -nE 'markets\.css\?v=|markets_app\.js\?v='` that the only diffs are the two `?v=` re-stamps, matching the body claim).
- The per-market `dz()` field fallback in the focus panel is documented in the body as out-of-scope for this PR and noted for a follow-up; it has the same silent-English shape under zh and should be repaired in the same designed-null form. The audit flags it as a known scope-bound item, not a regression.
- The repo has no producer for the hand-curated zh regime block in `site/markets_i18n.js`; the body notes the header's "market-cycles-translate-zh workflow" is outside this repo. The audit cannot verify translation provenance beyond confirming the shipped block is hand-curated Chinese distinct from the EN block (`test_zh_regime_block_is_hand_curated_chinese`).
- The single nearby validator output line `templates/macro_labor_markets.html.j2:6 model that scripts/build_macro_suite_pages.py builds from the validated` is part of the 65-estate pre-existing debt documented in `macro_PR-7755.mm.md`, `macro_PR-7712.mm.md`, `macro_PR-7701.mm.md`, etc.; it is not anchored to any PR-touched file in this PR.
- `ci-authority/codex/merge-queue-pilot` is the standing-ignorable lane flagged in the CI rollup; documented in body and in prior audits. No action required.

## DEV IATIONS

None. The PR is bounded to its half-B scope (mobile in-flow card + zh designed null), uses only existing governed tokens, replaces one implicit unbacked cross-language claim with a designed-null disclosure, and ships the operator-mandated `desktop/mobile × en/zh × dark/light` evidence matrix plus 6 click-forced crops with both rest and focused states. CI rollup is green on every binding check (12/12 ci-pack, ci-gate, contract-delta, fence-pack, capability-broker, grader-manifest, ci-authority, ci-plan, ci-authority/main). The single FAILURE is the standing-ignorable `ci-authority/codex/merge-queue-pilot` lane.

---

SESSION END: PROVEN_OUTCOME (one-pass audit delivered; no durable write to remote host; result persisted into the seat's orch/idle directory from this stdout)
