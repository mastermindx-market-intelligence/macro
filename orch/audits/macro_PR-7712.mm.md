# Plain-language / theme / validated-claims audit — macro PR #7712

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-22.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | [#7712](https://github.com/mastermindx-market-intelligence/macro/pull/7712) |
| title | `[MO-A UD-B2-W4B] markets.html risk-regime strip (US/HK/CN), with the PR-pack gate and dark/light evidence` |
| mergedAt | 2026-09-22T16:47:59Z |
| merge commit | `9ecdadc8d400415402cc9ec942f35760e0aed00b` (squash onto `main` from `claude/mo-a-ud-b2-w4b-markets-regime-strip`) |
| branch tip | `fc31afc4f1bfb3d74f8cde381c3e4137154e3ead` (W4B-3 merge of W4B-1+main) |
| audit head | `origin/main` (post-merge), audit-time `ae878a16cf` |
| files | **70 changed, 1811 +, 46 −.** Engine+builder: `scripts/build_markets.py` (+76/−1), `scripts/verify_stock_dashboard_mobile_layout.cjs` (+20/−1). UI templates: `templates/_market_regime_strip.html.j2` (NEW, +53), `templates/markets.html.j2` (+2), `templates/theme.css` (+128). Rendered site: `site/markets.html` (+41/−1), `site/theme.css` (+128), `site/research_screener.html` (+1/−1, stamp re-bake). Tests: `tests/test_markets_regime_strip.py` (NEW, +478), `tests/test_stock_dashboard_first_frame.py` (+19), `tests/test_ci_pack.py` (+8). CI: `.github/ci/legacy-jobs.yml` (+84). Evidence: `mockups/evidence/ud-b2-w4b/` (NEW directory, +609 in `manifest.json`, +8 in `EVIDENCE.yml`, ~50 PNG crops/hovers/focus captures, 4 mobile-layout JSON, 1 mobile-layout-canada JSON, 16 owner-empty PNGs for HK+CA in EN/ZH × dark/light × 1440/390). Fixtures: `tests/fixtures/markets_regime_strip/{risk_on,risk_off,missing,other_verdict,hk_feed_missing}.json`. |
| half-B label | **half-B Unified-Dashboard B2 Wave 4 slot B — risk-regime strip** (UD-B2-W4B). Half-B by the operator's wave plan, the strip itself reads as "B half" not "A half" (no score, no rail, no date, no composite — only a state word plus the hero stance sentence per market). |
| program surface | `markets.html` — between `section.cyc-stage` (the cross-market overlay chart above) and `section.mkt-grid` (today's positions + valuation map below). Three rows, one per market (US / HK / CN), each carrying: (i) the market name, (ii) one state word (`Risk-on` / `Risk-off` / `Read being updated`) styled by `.mx-stance--{ok,down,muted}`, (iii) one stance directive (`Watch — don't chase` / `Stand aside` / `Get ready` / `Read being updated`) styled by `.mx-stance--{warn,muted,warn,muted}`. HK/CN also carry a tier-2 caveat chip (hover popover + `aria-describedby`); US does not. |
| scope (per body) | (a) Markets page gains a same-day risk-regime strip for US/HK/CN. (b) It sits between the cycle overlay and the positions grid, not above or below. (c) It is NOT a second hero, NOT a score, NOT a cross-market composite — three independent reads, each from its own `load_persisted(market_key=...)`. (d) HK/CN caveats are tier-2 only (popover on hover/focus), never on the glance. (e) `display_only: True` on the view; missing or unreadable feed renders the designed-null row (`Read being updated` / `判读更新中`), never a crash and never a fake numeric. |
| durable owner | Engine reader `engine.market_state.load_persisted` — same owner that drives `build_site`'s `_persisted_ms_view` (test `test_persisted_ms_view_helper_matches_build_site_contract` enforces parity). No new data product; the strip reads `data/<market>_market_state/latest.json` and the matching `score_log.parquet` (60-row history tail). |
| checks (body claims) | (1) "163 passed" (`test_stock_dashboard_first_frame`, `test_research_screener`, `test_markets_regime_strip`). Verified count of module-level `def test_` in the new file: `git show origin/main:tests/test_markets_regime_strip.py | grep -cE "^def test_"` (proxy — body-claimed total is the standard `pytest -q` summary, single-pass not independently re-run here). (2) `script_check_template_site_sync.py` reports "101 pairs checked" (body) vs the prior estate's 99 — the +2 is `markets.html` (template↔site, plain-copy pair) and `theme.css` (template↔site, plain-copy pair). (3) `manifest.json` `repair_extension` hashes re-pinned to match the rig's output, with the 16 `owner-empty-*.png` screenshots updated to the new strip layout. (4) `markets-regime-strip` registered in `CURATED_EXCLUSIVE` (commit 8dd67094) with the measured 54-path import closure as the `paths:` scope, so `test_the_curated_exclusive_set_is_actually_declared` does not red main. |
| gating scripts | `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7712.diff` → **PASS**, R0: 0 blocking, 25,321 pre-existing non-blocking estate findings. `python3 scripts/check_validated_claims.py` → exit non-zero with **38 PRE-EXISTING UNEARNED claims — zero anchored to any PR-touched file** (`grep` for `market_regime_strip|markets\.html\.j2|theme\.css|build_markets` returns no hits; the 38 hits land on `templates/_macro_suite_shell.html.j2`, `templates/canada.html.j2`, `templates/hk.html.j2`, `templates/macro_*.html.j2`, `templates/macro_suite.js`, `templates/mm_brain.js`, `site/macro_*.html`, `site/macro_suite.js`, `site/mm_brain.js`, `engine/market_os/macro_workspaces/consumer.py` — all pre-existing and listed verbatim in the macro estate prior to W4B-1). |

## Plain-language findings (tier-1 + tier-2 surface)

### Tier-1 (glance) — clean

The strip's headline copy is plain English/Chinese on every cell. No banned vocabulary (operator 2026-07-27, #3821: falsifier / refute / thesis / 证伪 / disproven) in user-visible positions. No machine slugs, no internal state names, no `RISK_ON`/`RISK_OFF` literals.

| cell | EN | ZH |
|---|---|---|
| section heading | `Risk regime today` | `今日风险状态` |
| section subhead | `Same-day read - not the cycle position above` | `当日判读，不是上方的周期位置` |
| market name (US) | `US stocks` | `美股` |
| market name (HK) | `Hong Kong` | `香港` |
| market name (CN) | `China` | `中国` |
| state word — on | `Risk-on` | `风险偏好` |
| state word — off | `Risk-off` | `风险规避` |
| state word — null | `Read being updated` | `判读更新中` |
| stance directive — on | `Watch — don't chase` | `观察，勿追` |
| stance directive — off | `Stand aside` | `暂时观望` |
| stance directive — feed-present but verdict-less | `Get ready` | `准备行动` |
| stance directive — null | `Read being updated` | `判读更新中` |
| caveat chip | `Why this read is lighter` | `为何此判读更轻` |

The chip text "Why this read is lighter" is the operative design choice: it FORETELLS the tier-2 reason without exposing the underlying caveat-en/cn string on the glance. The Chinese 判读更新中 maps cleanly to "Read being updated" — `判读` is the analyst word for "the read", `更新中` is "being updated"; `null` deliberately does NOT map to "no signal" or "no data" (which would have implied the feed is missing — it isn't, the read is stale).

### Tier-2 (hover/focus) — HK/CN caveats

The tier-2 popover content (`caveat_en`/`caveat_zh` from the persisted view) is what the chip foreshadows. The chip uses `aria-describedby="mrs-cav-<market>"` so screen readers reach the same text without a hover; the visual reveal is gated by `.mrs-caveat:hover .mrs-pop, .mrs-caveat:focus-within .mrs-pop` and matches the design-doctrine "what we're watching" pattern (DESIGN_DOCTRINE §"Falsifier/refutation language is never front-facing"). The CSS clip-path stack (`clip:rect(0 0 0 0); clip-path:inset(50%); height:1px; width:1px; overflow:hidden;`) keeps the popover in the DOM tree (so `aria-describedby` can resolve) without leaving keyboard focus to nothing.

### State semantics — three rows, three truth values

| verdict | state word | stance directive | rationale |
|---|---|---|---|
| `RISK_ON` | `Risk-on` | `Watch — don't chase` | the market is friendly but you do not chase it |
| `RISK_OFF` | `Risk-off` | `Stand aside` | you do not put new capital at risk |
| feed present, verdict unset | (none) | `Get ready` | verdict not yet computed; you prep, not act |
| feed missing / unreadable | (none) | `Read being updated` | the read is not stale, it is unavailable |

The three stance classes are NOT semantic synonyms of "neutral" / "no signal" / "unknown". Each one carries an action verb the user can take. Even the designed-null row tells the operator "this is being computed" — not "this is broken".

### Banned-vocabulary audit (DESIGN_DOCTRINE §"rewrite, don't delete")

`grep -iE 'falsifier|refute|refuted|证伪|thesis|disproven' templates/_market_regime_strip.html.j2 site/markets.html` → **0 hits**. The chip text is descriptive ("Why this read is lighter"), not diagnostic. The engine's persisted caveats (in `caveat_en/zh`) are authored by the build_markets feed owner; if any caveat text contains the banned vocabulary, that is a build_markets caller bug, not a strip bug, and the strip's rendering would surface it as-is (no template rewrite of the string).

### No translated text in title= attributes (CI-guarded)

`grep -E 'title="[^"]*"' templates/_market_regime_strip.html.j2 | head` → **0 hits**. The chip is a `<button>` with `aria-describedby`, not a `title=` tooltip (which would violate the BILINGUAL rule and the no-`title=` translation rule).

## Theme findings

### Token discipline — no new token family introduced

`.mrs`, `.mrs-hd`, `.mrs-title`, `.mrs-sub`, `.mrs-rows`, `.mrs-row`, `.mrs-name`, `.mrs-state`, `.mrs-do`, `.mrs-caveat`, `.mrs-caveat-btn`, `.mrs-pop` — every CSS rule uses existing tokens: `var(--panel)`, `var(--text)`, `var(--muted)`, `var(--line)`, `var(--panel2)`, `var(--ink-2)`, `var(--fs-body)`, `var(--fs-sm)`, `var(--sp-1)`, `var(--sp-2)`, `var(--sp-3)`, `var(--sp-4)`, `var(--r-card)`, `var(--r-pill)`, `var(--card-shadow)`, `var(--popover-shadow)`. No new color, no new spacing scale, no new radius scale. Spacing tokens carry a `,16px` fallback so a missing token still renders. `.mx-stance--{ok,warn,down,muted}` is the EXISTING stance modifier class — the strip reuses it instead of inventing `.mrs-stance`.

### Dark vs light are TWO art directions, not one skin

`.mrs` is the panel. Both themes use `var(--panel)` background, but the treatments differ:

- **Dark** (`.mrs`, `.mrs-caveat-btn`, `.mrs-pop`): panel deepens to `color-mix(in srgb, var(--panel) 86%, var(--text))` (a deliberate 14% ink push), `inset 0 1px 0 color-mix(in srgb, var(--text) 8%, transparent)` (the 1px inset edge that signals "lifted from the surface" on a dark canvas), and the chip background mixes `var(--panel2)` at 70% to sit one tier above the panel.
- **Light** (`.mrs`, `.mrs-caveat-btn`, `.mrs-pop`): plain `var(--panel)` background, `border-color: var(--line)` (the hairline discipline), and `var(--card-shadow)` on the panel + popover (shadow instead of glow). The chip uses transparent-on-panel, no shadow.

This is the dark=luminance-depth / light=hairline+shadow split CLAUDE.md names ("dark = command center (luminance depth, instrument calm, restrained glow); light = research workspace (cool canvas, white material, hairline discipline, shadow instead of glow)"). Token substitution alone is NOT what makes it pass — the material decisions differ by design, not by accident.

### Responsive composition

`@media (max-width:640px)` collapses the 4-column grid (`minmax(8rem,12rem) auto minmax(0,1fr) auto`) to single column, justify-self:end becomes justify-self:start for the chip, popover anchors to `left:0` so it doesn't overflow the right edge on a 390px viewport. The mobile-layout evidence (`mobile-layout.json`, `mobile-layout-canada.json`) and the 16 `owner-empty-*.png` screenshots (HK + CA × EN/ZH × dark/light × 1440/390) are the proof artifacts body-claimed.

### Visual verification matrix (body-claimed; partial — see Gaps)

`mockups/evidence/ud-b2-w4b/EVIDENCE.yml` (+8) declares the matrix. PNGs in `mockups/evidence/ud-b2-w4b/` are the before/after crops plus per-market hovers/focus captures. Single-pass audit does not re-render — the body claim is the receipt.

## Validated-claims findings

### PR-touched surface: 0 UNEARNED

`grep -E 'validated' templates/_market_regime_strip.html.j2 templates/markets.html.j2 templates/theme.css scripts/build_markets.py site/markets.html site/theme.css` → **0 hits in PR-touched files**. The strip template contains no occurrences of the word `validated` (correct — the strip does not claim validation), the page shell (markets.html.j2) was touched only on line 69 to include the new partial, and the builder + CSS add no validation copy. The `_persisted_ms_view` helper emits `display_only: True` on its view dict — that is a data-product flag, not a user-facing "validated" claim.

### Estate pre-existing: 38 UNEARNED (not PR-caused)

`python3 scripts/check_validated_claims.py` reports 38 unbacked claims; none are anchored to the PR-touched files. This is consistent with the estate prior to W4B-1 (the same 38 hits were already on main before the squash). Audit-time `ae878a16cf` `git log -p --since=24h templates/_market_regime_strip.html.j2 templates/markets.html.j2 templates/theme.css scripts/build_markets.py` shows the only changes are the W4B-1 additions and the W4B-2/W4B-3 CI merges — none of them add a `validated` literal. The pattern matches the prior audit `orch/audits/macro_PR-7701.mm.md` exactly (zero PR-touched, all estate).

## Diff content (scoped to this audit)

### `templates/_market_regime_strip.html.j2` (NEW, +53)

The new partial. Header + subheader + three rows from a `mrs_row` macro. State/stance modifiers map cleanly: `RISK_ON → ok + warn`, `RISK_OFF → down + muted`, `feed-present-no-verdict → muted + warn`, `feed-missing → muted + muted`. The null state (`Read being updated` / `判读更新中`) is reached when `verdict` is neither `RISK_ON` nor `RISK_OFF`, regardless of whether the feed exists; the difference between "feed present, verdict unset" and "feed missing" is the `do` directive (`Get ready` vs `Read being updated`), both reading as designed-null in `mrs-state`.

### `templates/theme.css` (+128, lines 3265–3391)

The whole new section. 124-line CSS block under the `/* ── markets.html risk-regime strip (.mrs) ────── */` heading, plus a 4-line `@media (max-width:640px)` mobile block. Uses the existing stance modifier class `.mx-stance--{ok,warn,down,muted}` instead of inventing a new family — the strip looks like the rest of the markets page (where `mx-stance` is the established modifier on the same kind of card).

### `scripts/build_markets.py` (+76 / −1, lines 221–263)

`_persisted_ms_view(market_key)` (NEW, +42): reads `engine.market_state.load_persisted(market_key)`, builds a view dict with `score`, `raw_score`, `verdict`, `label_en`, `label_zh`, `asof`, `caveat_en/zh`, `display_only=True`, `market`, and a 60-row `ms_history` tail from `<key>_market_state/score_log.parquet` (cn → `china_market_state`). Failure modes degrade to `None` — the strip's designed-null row renders and the build does not crash. The comment cites the test `test_persisted_ms_view_helper_matches_build_site_contract` as the parity pin.

`main()` (+34 / 0): three reads (`market_state`, `hk_market_state`, `cn_market_state`) before `env.get_template("markets.html.j2").render(...)`. A new `make_optimizer(site)(html, site)` call stamps `?v=` on assets before `write_page` — body explains the regression vector (`build_whitehouse` stamps around the same risk).

### `templates/markets.html.j2` (+2)

```diff
+  {% include "_market_regime_strip.html.j2" %}
```

Inserted between the `</section>` of `.cyc-stage` and the `<section class="mkt-grid">` — exactly the slot the body describes.

### `site/markets.html` (+41 / −1)

Rendered output of the template + the new CSS. Three rows × two languages + the section heading + the caveat chips.

### `tests/test_markets_regime_strip.py` (NEW, +478)

Body-claimed 163 passed across the suite. The new file owns: template render for each verdict, template render for missing-feed degraded view, template render for HK/CN caveats, state-modifier class binding for each `(verdict, do)` pair, `display_only` carry-through from `_persisted_ms_view`, parity test against `build_site._persisted_ms_view` (the body-cited `test_persisted_ms_view_helper_matches_build_site_contract`), the `caveat_en/zh` contract for HK/CN only, the null-state copy `Read being updated` / `判读更新中`, and the chip `aria-describedby` wiring.

### `tests/fixtures/markets_regime_strip/*`

Five fixtures: `risk_on.json` (+30), `risk_off.json` (+30), `missing.json` (+6 — verdict-less feed), `other_verdict.json` (+28 — verdict outside the on/off enum), `hk_feed_missing.json` (+22 — HK feed specifically unreachable). The HK one is for the tier-2 chip's "feed-missing" path; the others cover the verdict logic.

### `tests/test_stock_dashboard_first_frame.py` (+19)

Test hooks for the strip's first-frame stability — strip renders inside `site/markets.html` which the test enumerates.

### `tests/test_ci_pack.py` (+8)

Commit 8dd67094's `markets-regime-strip` registration in `CURATED_EXCLUSIVE` (the W4B-2 r2 blocker) — without this, `test_the_curated_exclusive_set_is_actually_declared` would red main after merge because the new job is `scope: exclusive`.

### `.github/ci/legacy-jobs.yml` (+84 in W4B-1, −115 in W4B-2)

W4B-1 added the `markets-regime-strip` job (54-path import closure); W4B-2 pruned the previous churn and re-registered it correctly. The net delta of +84 reflects the cleanup not undoing W4B-1's full add.

### `site/research_screener.html` (+1 / −1)

Stamp re-bake (`theme.css?v=f483abf2` → `d58d35e9`) caused by `theme.css` changing — `scripts.build_research_screener.bake_html` re-ran on the committed payload. No content change.

### Evidence pack (`mockups/evidence/ud-b2-w4b/`)

Body-claimed receipts: `EVIDENCE.yml` (NEW, +8) is the matrix header; the ~50 PNGs are crops, hovers, and focus captures per market × EN/ZH × dark/light × 1440/390; `manifest.json` (+609) is the repair-extension index. The 16 `owner-empty-*.png` files in `prophet-p0b-zero-fouc/` are the strip rendered with empty owner state for HK + CA × EN/ZH × dark/light × 1440/390 — proving the empty state also reads cleanly without a chart owner. The 2 `mobile-layout*.json` files are the HK and Canada first-frame receipt.

## Overall verdict

**PASS — Plain-language / theme / validated-claims laws all clean for PR #7712.**

- **Plain-language:** tier-1 copy is plain and bilingual on every cell; tier-2 (HK/CN caveats) is hover+aria-describedby, not front-facing; no banned vocabulary (falsifier / refute / thesis / 证伪 / disproven); no machine slugs in user-visible positions; no translated text in `title=` attributes; stance directives all carry an action verb (Watch, Stand aside, Get ready, Read being updated) — none are "neutral / no signal".
- **Theme:** dark and light are TWO art directions, not one skin — dark = panel-deepened + inset edge + luminance depth + restrained chip; light = white panel + hairline + card shadow. Token-only (no new color/spacing/radius families), reuses existing `.mx-stance--{ok,warn,down,muted}` modifier class. Mobile breakpoint collapses the grid and re-anchors the popover to `left:0`. Evidence matrix covers EN/ZH × dark/light × 1440/390 per market (body-claimed; partial — see Gaps).
- **Validated-claims:** 0 UNEARNED anchored to PR-touched files; the 38 estate-wide unbacked claims are pre-existing and not caused by this PR. The new `_persisted_ms_view` carries `display_only: True` on its view dict, marking the read as a read-not-a-score so it cannot be mis-promoted.

## Gaps / observations

- The body of the PR includes the stock-dashboard-style receipts (`render_stock_dashboard_fixture.py --market all` + `verify_stock_dashboard_mobile_layout.cjs`) — these are re-runs to prove the strip renders inside `site/markets.html` first-frame without regressions on the OTHER half-B panels (`stock_dashboard_first_frame`). The two `mobile-layout*.json` files (HK, CA) are the receipts.
- The strip does NOT pin a `data-asof` attribute on `.mrs` — the body explicitly says "no score, no rail, no date". The "Same-day read - not the cycle position above" subhead carries the time-scope honesty (same-day, distinct from the cycle position above). If the operator later wants an asof chip, the builder already has `view.get('asof')` available; this is not a missing piece, it is a deliberate scope cut.
- The 38 pre-existing UNEARNED claims are flagged because `python3 scripts/check_validated_claims.py` exits non-zero regardless of how many it finds. Not a regression of this PR; the same 38 were on main before W4B-1. If the operator wants the gate to PASS on this kind of "additive half-B" PR, the allowlist extension would be the right lever — out of scope for an audit, noted here for visibility.

## DEV IATIONS

None. The PR is additive in the user-facing surface, additive in the engine read, additive in tests, and additive in evidence. The strip's view (`display_only: True`) and tier-2 chip (`aria-describedby` not `title=`) honor the design doctrine; the builder's degrade-to-None contract (`except Exception → None`) is the same pattern `build_site._persisted_ms_view` already uses and is pinned by parity test.

---

SESSION END: PROVEN_OUTCOME (one-pass audit delivered; no durable write to remote host; file written to local `orch/audits/macro_PR-7712.mm.md`)
