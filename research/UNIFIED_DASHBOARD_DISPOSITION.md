# Unified Macro Dashboard — RIG capability disposition

**Packet:** UD-B1 · retained design candidate; **not mounted on the primary route** as of 2026-09-20.
**Source census:** `mockups/refs/unified-dashboard/census_macro_modules.md` (2026-09-19,
55-module census of `site/macro.html` rendered from `templates/dashboard.html.j2`
with `mode="macro"` by `scripts/build_site.py`).
**Historical design spec:** `mockups/refs/unified-dashboard/UNIFIED_DASHBOARD_SPEC.md`.

## Primary-route override — 2026-09-20

UD-B1's first production composition stacked a second, global/cross-market regime hero above the
established US macro dashboard. The candidate is visually useful, but the shipped composition adds
too much prose and vertical space, duplicates the existing regime decision surface, and exposes four
of five cross-market spine rows as designed-null `BLOCKED_DATA`. More importantly, its top score and
verdict are **not a global composite**: `_unified_dashboard_hero.html.j2` binds the default
`market_state`, whose default tape is the US `SPY / QQQ / IWM` profile. A US-derived verdict must not
be relabeled as a global market verdict. It therefore does **not** currently clear the replacement
bar for decision speed, information density, or semantic truth.

The primary `macro.html` route returns to the established `#regime-radar` composition. UD-B1 source,
primitives, specs and evidence are retained for redesign; do not delete or rebuild them. B2+ may not
resume a primary-route migration until a successor is compared against the current dashboard and
proves a materially better glance path without stacking a parallel dashboard above it.

Do **not** move this block wholesale to `intl.html`: that route owns the ex-US international-economies
comparison. The repository's current global-cycle route is `markets.html`; any compact global-regime
successor should be evaluated there (or through the existing route owner) before publication.

### Current-main reconciliation — 2026-09-21

Two B2 slices reached `main` after the first primary-route override and are reconciled rather than
blindly reverted. **UD-B2-W1** improved the real US dashboard's existing `.mx5-sc-left` risk surface
by folding volatility-weather chips into that surface; that useful US-route capability stays.
**UD-B2-W2** added HK/CN market-state persistence plus truthful lighter-evidence caveats and bound
those feeds inside the retained hero candidate. Its engines, persisted artifacts, component source,
tests, and evidence stay; only the candidate's `#ud-hero` / five-market spine is kept **off**
`macro.html`. Component-level tests prove the retained HK/CN bindings while the committed-page gate
proves that the US route opens on `#regime-radar` with no stacked candidate.

Relocation is therefore a recomposition, not a copy: reuse the strongest visual primitives and the
now-real HK/CN bindings in the `markets.html` global-cycle owner, alongside that route's existing
country-cycle/global-equity evidence. Do not label the default US `market_state` score as a global
composite, and do not re-home the whole hero into `intl.html`.

The disposition table below remains a design inventory for the retained candidate, not current
primary-route deployment authority. **No module may be silently dropped.**

### Markets-route recomposition — 2026-09-22

Shipped as macro #7712 (merge `9ecdadc8`, live-verified on `www.mastermind-x.com` the same hour). Per the
route ruling above, the global-cycle successor on `markets.html` is a compact **risk-regime strip**
(`templates/_market_regime_strip.html.j2`, included between `section.cyc-stage` and `section.mkt-grid`):
three rows — US stocks, Hong Kong, China — each carrying ONE state word (Risk-on / Risk-off / the
designed-null "Read being updated") bound to `market_state` / `hk_market_state` / `cn_market_state` through
the same persisted reader `scripts/build_site.py` uses, plus the hero's stance sentence verbatim
(parity-pinned by `tests/test_markets_regime_strip.py`). The HK/CN lighter-evidence caveat is a tier-2
popover, never glance text. The header names the instrument ("Risk regime today — same-day read, not the
cycle position above").

Rulings embedded in that build (binding for any follow-on):

- **No second integer, no rail, no marker.** `markets.html` already prints one integer and one state word
  per market (cycle position); a rail or score would re-create the two-verdicts disease named above. The
  strip's text nodes contain zero digits (CI-asserted).
- **No composite / "Global" verdict.** A cross-market composite is signal origination and stays forbidden
  without a ratified contract.
- **No bonds / commodities rows on the equities route.** The retained hero candidate keeps its designed-null
  rows untouched; the strip does not carry them (a stated deviation, not a silent drop).
- **Placement C, not the census's A or B.** A strip under the h1 (a new per-market integer where none
  existed) and a strip inside `#mkt-snap` (a duplicate integer) were both rejected. `#regime-prior-banner`
  (W4.5 contradiction / staleness notices) prints no per-market state word, so the strip is additive and the
  banner is untouched.
- **CI home.** `markets-regime-strip` is a `gate: code`, `scope: exclusive` job registered in
  `CURATED_EXCLUSIVE`; its thematic neighbours (`engine-render-guards`, `unrun-picks-boards`) are `gate: data`
  and never run in PR packs. Any change to the `theme.css` pair is a pinned p0b construction input and owes
  the receipt re-mint in the same PR (done in #7712).

Recorded follow-ups, not part of #7712: the #7503 re-stack pins and the W2 HK/CN binding tests sit on
`gate: data` jobs and do not gate PRs; at 390px the cyc-stage detail aside overlaps the chip row and the
curated global-equity regime narrative renders English under zh. Both are filed for separate heals.

The primary-route override above is unchanged: `DNR:HOLD-UD-B1-PRIMARY-MACRO-MIGRATION` stands.

---

## Seat rulings (binding — embed as-is)

| Ruling | Subject | Verdict |
|---|---|---|
| **R1** | Census **#6** (Leadership context strip — "Under the surface: Health Care / Staples / Utilities held …") | **IMPROVE** — folds into spec §6 *Drivers* block (defense-vs-cyclical read becomes one of three driver tiles, not its own strip) |
| **R2** | Census **#19 / #20** (Markets isle + dialog — 4-tile futures grid + tabbed deep dialog) | **RETAIN** as glance tile row + dialog per spec §4 (component inventory `DecisionRow` / `dlg-markets`); on the page it lands on the §2 spine row (US / HK / China A / Gov bonds / Commodities) |
| **R3** | Census **#21 + #35** (Risk isle absorbs the volatility-weather chips) | **IMPROVE** — the risk isle keeps its dial + scar chips; the **volatility-weather chips** (`calm / breeze / gust / storm`) fold INTO the risk isle instead of sitting as a sibling stack |
| **R4** | Census **#29** (Deep context isle — "Where next", three wnx-cards) | **RETAINED** as the **single deep-context surface** — the three wnx-cards stay grouped |
| **R5** | Census **#44** (dlg-deep-context) | **REMOVE** (absorbed into #29 — single deep-context surface, seat ruling) — the dialog content rolls into the isle body or its disclosure |
| **R6** | Census **#36** (AI / non-AI breadth split) | **RELOCATE** to `advanced.html` with a chip link from the breadth surface — display-tier clutter has no place on the hero glance |
| **R7** | Census **#54** (Macro & Monetary hub pill link) | **IMPROVE** — the `mq-suitenav-home` pill joins the canonical chrome link family (sits with the suite-nav surfaces, not as a one-off) |

Every other module is **RETAIN** with its spec landing named below. No module is
silently dropped; no module is relocated or removed without a seat ruling.

---

## Disposition table (55 rows, all census modules)

| # | Module | Disposition | Landing (spec §) | Rationale |
|---|---|---|---|---|
| 1 | Site nav + mega-menu | RETAIN | chrome above §1 | Standing nav chrome per CLAUDE.md §Navigation source-of-truth |
| 2 | Public footer | RETAIN | §6 page footer | Required footer; plain-language disclaimer |
| 3 | Market-state hero (`ms-front`, "The Regime") | RETAIN | §1 VerdictHero | Top-of-page state command center; binds `.mx-vh` (eyebrow · two-tone verdict word · clause · stance · live chip · as-of) |
| 4 | Big score (`mx2-score`) | RETAIN | §1 gauge column | Headline 0–100 number inside the gauge; uses `MS.score` / `MS.raw_score` (capped-vs-uncapped) |
| 5 | Score progress bar | RETAIN | §1 gauge column (inner rail) | Visual scale under the score; risk-off / mixed / risk-on anchors retained |
| 6 | Leadership context strip | IMPROVE (R1) | §6 *Drivers* block — defense-vs-cyclical becomes one of three driver tiles | "Held while X faded" is informative; folded into the drivers 2×2 to free an island |
| 7 | Fired-alerts popover | RETAIN | §1 live chip anchor (count + click) | Designed-fire discipline is a core epistemic surface; surfaced via the live chip |
| 8 | Regime context pill + flip-ctx popover | RETAIN | §1 VerdictHero caveat (beside the headline, never behind hover) | Plain-language null disclosure for the regime call's own evidence |
| 9 | v-thesis + v-override + v-flip copy | RETAIN | §1 VerdictHero — verdict word + clause + flip clause | The three-line `ms-verdict` block becomes the verdict word + plain clause |
| 10 | Regime ARC gauge + needle | RETAIN | §1 gauge column (semicircular SVG) | Visual companion to #4; capped arc solid, uncapped remainder as 26% ghost |
| 11 | Regime quadrant map (SVG) | RETAIN | §2 regime spine (quad subsumed — see spec §3) | Discrete axis lives on the spine as the subject row's zone tick; no separate panel |
| 12 | "What To Do Now" isle (sx-evidence) | RETAIN | §1 stance chip + §4 *Drivers* (the action card sits beside the drivers, not as a top-line button) | Display-tier "what to do" surface — must stay adjacent to the verdict |
| 13 | "Upcoming Events" isle (sx-events-v2) | RETAIN | §6 *Watching* (top row — five highest-impact prints with HIGH/MED badges) | Lets the reader see the noisy week at a glance; engines stay `event_strip` |
| 14 | Event detail dialog (dlg-events) | RETAIN | companion to §6 *Watching* | Detail surface; engines stay `event_risk` |
| 15 | Risk Envelope band (gde-band) | RETAIN | §6 *Drivers* — one driver tile ("three reads, never a fused score") | Composition "do the reads agree?" survives the redesign |
| 16 | Fed Path isle (sx-v5-fed) | RETAIN | §6 *Watching* (fed-watch tile) | Belt under the news event pane; rates_command + prediction_markets |
| 17 | Market Sentiment isle (sx-v5-sentiment) | RETAIN | §4 *Drivers* block — one driver tile | Display-tier context; never a signal |
| 18 | Sector Temperature isle (sx-v5-sector) | RETAIN | §6 *Go deeper* — sector rotation chip | "Compass card" link to sector_central.html |
| 19 | Markets isle (sx-markets-v2 — 4-tile futures grid) | RETAIN (R2) | §2 spine — five markets on one rail (US / HK / China A / Gov bonds / Commodities) | The 4-tile glance row becomes a row in the spine; deep stays in the dialog |
| 19a | Spine feed · US stocks (`market_state.score`) | BOUND | §2 spine · subject row | `vm["market_state"]["score"]` is the regime score; the row carries today's marker + the stance derived from `vm["stance"]`. Real published data. |
| 19b | Spine feed · Hong Kong | BOUND | §2 spine · HK row | **UD-B2-W2 (DEC-SPINE-SCALE-BINDINGS).** Source = `HK_PROFILE` `market_state.score` persisted by `build_hk` to `data/hk_market_state/latest.json`; macro vm reads `{score, label_en, label_zh, asof, caveat_en, caveat_zh, display_only:true}` per `R-W2-4`. Same blender, identical leg weights 0.24/0.18/0.16/0.16/0.14/0.12 and verdict cuts 60/42 as the US subject row. Lighter evidence (no VIX term, no HY, uncalibrated downturn gauges, no hard overrides); the engine caveat travels with the number on the row's disclosure. Row carries `data-blocked-feed="hk_market_state"` (renamed from the quad's `hk_regime` slug, which was a wiring trap), real today marker, month-ago travel from `score_log.parquet` (≥22 rows → real; shorter → designed-null travel with a real today marker — never `raw_score`). Stance = verdict-band fallback (no HK `regime_stance` is in the macro vm). |
| 19c | Spine feed · China A-shares | BOUND | §2 spine · CN row | **UD-B2-W2 (DEC-SPINE-SCALE-BINDINGS).** Source = `CN_PROFILE` `market_state.score` persisted by `build_china` to `data/china_market_state/latest.json` (the existing convention used by `build_china.py:1888` for the CN score_log); macro vm entry shape identical to HK above. Same blender; lighter evidence (QVIX, no HY, PBoC overlay, uncalibrated downturn gauges). The ROW rejects `intl_market_state.market_states()` (`CN` not covered; turn-state is not risk-on — `crash`/`parabolic` would lie on this axis) and the `china_regime` quad (cycle location ≠ risk-on). Row carries `data-blocked-feed="cn_market_state"` (renamed from the would-be `china_a_regime` slug, which would have wired the quad). Travel + stance follow the HK row pattern. |
| 19d | Spine feed · Government bonds | BLOCKED_DATA | §2 spine · designed-null row | `gov_bonds_regime` is not yet wired. **R-W2-3 (ratified product state, not deferral):** no published 0-100 on the same kind of evidence; bond health (`engine/bonds.py`) is economic/credit stress, not a bond-market risk-on read, and bond_compass duration lean's polarity is the opposite of the spine unless inverted (which would originate a new signal). Slug stays UNCHANGED — `gov_bonds_regime` stays honest as a not-yet-existing contract. Row keeps dashed rail + "Read being updated" chip. |
| 19e | Spine feed · Commodities | BLOCKED_DATA | §2 spine · designed-null row | `commodities_regime` is not yet wired. **R-W2-3 (ratified product state, not deferral):** spec mockup already designed this row as null (UNIFIED_DASHBOARD_SPEC.md §3:128–129, §7:248); the complex is internally mixed (gold vs copper) and no published 0-100 exists. Inverted `risk_index` or `ts_trend` mappers would originate a complex-level risk-on identity the engine does not publish. Slug stays UNCHANGED — `commodities_regime` stays honest as a not-yet-existing contract. Row keeps dashed rail + "Read being updated" chip. |
| 20 | Markets dialog (dlg-markets) | RETAIN (R2) | companion to §2 spine | Hub-and-spoke — index-health · sector heatmap · cross-asset preview |
| 21 | Risk isle (sx-risk-v2, Risk Radar) | IMPROVE (R3) | §2 spine — receives the vol-weather chips (see R3) | The risk isle keeps its dial + scar chips; absorbs the vol-weather chips below |
| 22 | Risk dialog (dlg-risk) | RETAIN | companion to §2 spine — risk state band + leading-signal stack + themes-rot | The deepest risk read; daily |
| 23 | Policy Monitor isle (sx-policy-v2) | RETAIN | §6 *Watching* — policy-lever tile | ELEVATED / CALM signal with rate-path sparkline + hawkish / dovish chips |
| 24 | Policy Monitor dialog (dlg-policy) | RETAIN | companion to #23 | Detail surface |
| 25 | AI Brief isle (sx-aibrief-v2) | RETAIN | §6 *Watching* — AI Brief chip (rates channel + 1 high-impact item) | Parity with the full page; macro_brief engine |
| 26 | AI Brief dialog (dlg-aibrief) | RETAIN | companion to #25 | Deep page is also `aibrief.html` — same body renderer |
| 27 | Alerts Centre isle (sx-news-v2) | RETAIN | §1 live chip + §6 *What changed* (top row — fired-alerts stack) | The only "what fired" surface; alerts are rare by law |
| 28 | News dialog (dlg-news) | RETAIN | companion to #27 | Deep news experience gated to `alerts.html` |
| 29 | Deep context isle (sx-deep-context, "Where next") | RETAINED (R4) | §6 *Go deeper* (wrapped chip rail) — the **single deep-context surface** | Three wnx-cards stay grouped; dialog (was #44) absorbed here |
| 30 | Release Radar panel | RETAIN | §6 *Go deeper* — release radar chip | Standalone panel; the only forward-looking forecasting surface |
| 31 | Release Radar track-record overlay | RETAIN | companion to #30 | Disclosure law — calibration visible |
| 32 | Release Radar detail modal | RETAIN | companion to #30 | Per-release detail dialog |
| 33 | Fear / Euphoria dial (Sentiment mix) | RETAIN | §4 *Drivers* block — one driver tile | Display-tier; never a signal |
| 34 | Froth / Fragility bar | RETAIN | §4 *Drivers* block — folded into sentiment driver tile | Display-tier counterpart |
| 35 | Volatility weather chips | IMPROVE (R3) | absorbed into the Risk isle (#21) | Display-tier; redundant with the risk isle as a sibling — fold in |
| 36 | AI / non-AI breadth split | RELOCATE (R6) | `advanced.html` with chip link from the breadth driver tile | Display-tier clutter; no place on the hero glance |
| 37 | Event-window phase / collision chips (EVW) | RETAIN | §6 *Watching* — event-window chip | Standalone; clear payoff |
| 38 | Event-Risk window chip | RETAIN | §1 live chip area — inline 2-Year Note reminder | Useful one-line reminder |
| 39 | Factor Breakdown popover (`mx5PopFactors`) | RETAIN | §1 VerdictHero caveat anchor (six factors; WEAKEST LEG) | Mirrors dlg-evidence in a lighter form |
| 40 | Risk dial button launcher | RETAIN | companion to §2 spine — click-to-open dlg-risk | Discoverability nudge |
| 41 | Sentiment detail dialog (dlg-sentiment) | RETAIN | companion to #33 | Deep sentiment read |
| 42 | Sector detail dialog (dlg-sector) | RETAIN | companion to #18 | Deep sector read |
| 43 | Fed detail dialog (dlg-fed) | RETAIN | companion to #16 | Companion deep |
| 44 | Deep-context dialog (dlg-deep-context) | REMOVE (R5) | folded into #29 — one surface, not two | The dialog content rolls into the isle body / its disclosure |
| 45 | Live quote tiles (`nb-px` / `nb-chg`) | RETAIN | §2 spine — five markets tile row mount points | Always live tiles; data-sym attributes kept |
| 46 | Heatmap lazy-load | RETAIN | companion to dlg-markets — sector treemap | 79% size cut; lazy-load discipline retained |
| 47 | Theme switch | RETAIN | chrome — top right (nav) | Always-on chrome |
| 48 | Language switch | RETAIN | chrome — top right (nav) | Bilingual law |
| 49 | Search box (nav) | RETAIN | chrome — top of nav | Global |
| 50 | Sparklines (mx2-prog-wrap, mx5-path-plot, plf-spark-row, mx5-popover factor bars, mxqm- mini history rows) | RETAIN | §1 VerdictHero mini chart + §4 *Drivers* sparklines | Lightweight, no JS framework |
| 51 | Risk-curve my "fbm-chart-svg" (dlg-fed) | RETAIN | companion to dlg-fed | Companion chart |
| 52 | Pullback-odds ring (`riskdlg-odds-h`) | RETAIN | companion to dlg-risk | Visualized odds |
| 53 | Inscribed `mxqm-glance` rule-out table inside `mx5-flipctx-pop` | RETAIN | §1 VerdictHero caveat anchor (the rule-out plain-language table) | Plain-language null disclosure |
| 54 | Macro & Monetary hub pill link (`mq-suitenav-home`) | IMPROVE (R7) | chrome — joins the canonical chrome link family (suite-nav surfaces) | Hub pill is not a one-off; sits with the suite-nav chrome |
| 55 | Heatmap scorecard mount (`#heatmap-scorecard`) | RETAIN | companion to §2 spine markets row — mini sector treemap | Companion surface to sx-markets-v2 |

---

## Stage 1 implementation notes (binding for B1)

- **Hero binding** uses real engine view-model keys: `vm["market_state"]` (census #3 / #4 / #5 / #9 / #10) and the regime spine (#11 quad map subsumed per spec §3).
- **What changed / Drivers / Watching** bind to `vm["alerts"]`, `vm["event_strip"]`, `vm["sector_heat"]`, and `vm["vol_weather"]` (absorbed into the risk isle, R3). The hero template does NOT read `vm["risk_state"]` — that key was a comment-only claim in earlier drafts and has been removed.
- **All remaining isles** KEEP their current rendering below the new hero in B1 — B2+ migrates them per the table above.
- **Glance copy** ships spec §6 EN+ZH verbatim — every user-facing string is a plain sentence in both languages; one-integer law applied (no competing integers; the score 62 prints once, with 71 only as the caveat).
- **No falsifier language** is shipped in any of the new copy (per doctrine; see spec §6).