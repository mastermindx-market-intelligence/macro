STATUS: BLOCKED

RESULT:

```yaml
role: product_regression
reviewer_identity: "claude-opus-product-regression-intl-r2-20260924"
pass: 1
artifact_sha: "62d710eedb9e5cc2a9d9f3e17fc02cc302de39f9"
verdict: BLOCK
findings:
  - id: PRC-R2-001
    severity: blocker
    capability: fx.dollar-drivers
    finding: The core "What's driving the dollar?" desk (regime word + plain-language sentence, 120-day rate-differential vs risk-off vs residual decomposition, safety-bid tag with DXY/2y receipt, dual-window confirmation, honest null — templates/intl.html.j2:1643-1713) is absent from reference-r2.html in every form: grep of the artifact returns no dollar panel, no deep link, and no honest null (only a "Dollar safety bid" chip inside the contagion channel list, reference-r2.html:790). This is not an empty-data case — the committed production baseline for the same 2026-09-23 session renders the panel populated with "Rate-driven / Rate differences between the US and other major economies explain the recent dollar move — not a flight to safety" (baseline-r2-desktop-dark-en.png). A core capability is deleted silently by a page whose own discipline is honest nulls.
  - id: PRC-R2-002
    severity: blocker
    capability: n/a (reachability)
    finding: Every "compact relocation" resolves to nothing. All six deep links — "open full central bank desk" (reference-r2.html:1034), "Open full credit & bond desk" (:1047), "Open full rates & curve desk" (:1059), "Open full correlation matrix" / "Open regime map" / "Open ranked reference views" (:1070-1072) — are `href="intl.html"`, i.e. the very route this artifact replaces, with no fragment. Under the candidate, "+3 more (SNB · BoC · RBA)", the Eurozone fragmentation panel, the 6-curve inversion board, the correlation matrix and the ranked views are unreachable from anywhere, so the compaction of rates.curve-desk, risk.credit-bonds, policy.central-banks and reference.regime-correlation-ranks is a deletion wearing a link.
  - id: PRC-R2-003
    severity: blocker
    capability: shell.theme-language-responsive
    finding: The route's shared shell and its Chairman-directed overview are both gone. Production includes `_site_nav.html.j2` at templates/intl.html.j2:473 and injects `global_regime_html` at :476-480 ("Chairman-directed cross-market overview"); the baseline image shows both — the MASTERMIND masthead with United States / China / Hong Kong / Canada / International / Other Assets / Research tabs, search, Terminal, and the regime desk with its risk-on dial, "Where this shows up" mode table, "What changed since last look", "What we're watching next", the "Go deeper" rail (Macro weather · Sector rotation · Signal Lab · Macro signals · News feed · Macro & Monetary hub) and Ask Mastermind (baseline-r2-desktop-dark-en.png, top ~1900px). reference-r2.html carries none of it and never states it is preserved; its only theme/language switch sits in a header the artifact itself labels "Design harness controls — not product features" (:364, :394). On the committed evidence the candidate ships no product-level theme or language control and no site navigation.
  - id: PRC-R2-004
    severity: blocker
    capability: n/a (designed states)
    finding: The error and empty states are whole-page takeovers that contradict the page's own copy and the route's fail-open contract. `body.is-error .real-content { display: none }` (reference-r2.html:319-320) hides everything, yet the error panel asserts "Still working: rotation ranks, the turn-state board, and the country inspector — all read from a separately cached feed" (:432) — proposal-r2-desktop-dark-en-error.png shows a page on which none of those are visible. Same for empty (:317-318, :422): two named engines returning zero rows blanks the IMF-WEO fragility map, the central bank desk and the credit board, which do not depend on them. baseline.yml:65 and scripts/build_intl.py:387-646 require risk organs to fail open independently.
  - id: PRC-R2-005
    severity: major
    capability: market.turn-state
    finding: Turn-state coverage is silently cut from 10 to 7 and the page contradicts itself about it. Production computes states over the full universe so "the turn board gets US/CN/HK rows for free" (scripts/build_intl.py:729-734) and the baseline renders 10 tiles including China, United States and Hong Kong (baseline-r2-desktop-dark-en.png, "World markets — turns & rotation"). reference-r2.html lists 7 rows (:677-703) with no disclosure, while its own gauge receipt says "Weighs 10 markets" (:473), its empty state says "all 10 tracked markets" (:422), and its "What changed" log prints "🇨🇳 China — Momentum turned up" (:748-749) for a market that has no state row anywhere on the page.
  - id: PRC-R2-006
    severity: major
    capability: market.macro-comparison
    finding: Comparison is no longer possible and 4 of 7 economies lose their macro row entirely. Production's cross-country scorecard carries every economy × ~15 columns (templates/intl.html.j2:923-978). The candidate moves those fields into a "Macro comparison row" inside a single-selection inspector (reference-r2.html:896-908, :936-948, :976-988) that exists for South Korea, Japan and the United Kingdom only — Taiwan, Eurozone, India and Australia have no regime, policy rate, 10y, curve, real 10y, CPI, GDP, unemployment, FX 3m, off-high or equity-stretch value anywhere in the artifact, and no honest null covers them. A tabbed one-at-a-time panel also cannot answer "compare … by economy" at all.
  - id: PRC-R2-007
    severity: major
    capability: market.performance-usd
    finding: Fixing R1's mixed-window defect removed the horizon capability rather than aligning it. Production's leaderboard exposes a real product control — `<div class="seg" id="lb-seg">` with Rotation rank plus every `perf.horizons` button, documented as "12m sort still available via buttons" (templates/intl.html.j2:857, 861-864) — plus the stacked local-equity/currency-tailwind/currency-drag/net-USD bar and its four-item legend (:867-873). reference-r2.html:537-539 hard-codes one 3-month window with no selector and numeric triplets only, so 12-month USD return survives for exactly 3 markets (inspector cards) while the hero's "USD leader" vital ranks on 12m (:510-512) — a claim the user can no longer verify across markets.
  - id: PRC-R2-008
    severity: major
    capability: risk.contagion
    finding: The dip-odds figure production deliberately demoted is re-promoted to an at-rest column, and it reinstates exactly the defect that was ruled off. templates/intl.html.j2:814-818 states the "≥5% dip within a month: ~29% vs ~29% base" line "used to print here on EVERY tile. It is a bare statistic with no stance attached, and on most tiles the two figures are equal — i.e. it says 'no lift' … Moved to the hover receipt." reference-r2.html:624-647 gives it a dedicated column on all 7 rows, and all 7 are equal (~29/29, ~31/31, ~27/27, ~20/20, ~19/19, ~18/18, ~15/15) — tautological by construction, since the caveat at :651 concedes the odds source is "own history only for every row". Worse, the adjacent State column inverts against it with no stated basis: TW "Elevated" at ~27% ranks above JP "Watch" at ~31%.
  - id: PRC-R2-009
    severity: major
    capability: market.turn-state
    finding: The rotation ranking cannot be reconciled with the fields the artifact prints. Its own help tip says "20-day fast momentum, state-governed (a topping/parabolic market is capped even with strong momentum)" (reference-r2.html:666), yet TW rs20 +6.87 sits below KR rs20 +5.03 while KR is the one marked "held back — crash in progress" (:677-684), and GB rs20 −1.45 with no hold-back note ranks #5 below JP −1.93 and EZ −2.77, both explicitly "held back" (:685-695). A held-back market outranking an unconstrained one with better relative strength makes the stated derivation falsifiable on its face, and the artifact prints no third input.
  - id: PRC-R2-010
    severity: major
    capability: risk.pressure-flow
    finding: Directed-pressure coverage is truncated from 10 rows to 3 with no count, no threshold and no link. Production's "Where crash pressure is flowing now" lists United Kingdom, India, United States, Euro Area, Canada, China, Hong Kong, Japan, Taiwan and Australia with per-source exposure (baseline-r2-desktop-dark-en.png; templates/intl.html.j2:1813-1879); reference-r2.html:797-818 shows United Kingdom, India and the United States only and stops — the same unauditable suppression pattern PRC-018 blocked in R1, now applied to a different board.
  - id: PRC-R2-011
    severity: major
    capability: action.prophet-stocks
    finding: The shared surface baseline.yml:14 declares this template owns (`intl_stocks.html` behind `mode == 'stocks'`, templates/intl.html.j2:481) still has zero design and zero evidence in the frozen set — all 12 proposal-r2 images are the non-stocks route. The Prophet board itself is reduced to a single link (reference-r2.html:1084) with none of its calibrated honesty (near/hold/wait/avoid capping because "No entry gauge exists for INTL", the "not a validated score" edge label, vol-squeeze flags) and no per-ticker `intl_stock.html#<ticker>` destinations surviving on the route.
  - id: PRC-R2-012
    severity: major
    capability: risk.fragility-map
    finding: The honest null miscounts and drops an economy. reference-r2.html:852 asserts "the other 5 tracked economies (Japan, South Korea, Taiwan, India, Eurozone) show no concurrent structural warning" — but the page's own universe is 7 economies (:507, :517, "0/7", :494), the flagged rows are United Kingdom and the United States (:828-851), and the United States is not one of those 7. Subtracting the UK leaves six unflagged economies; Australia is named nowhere in the fragility section. An absence statement that omits one of the economies it claims to account for is a false receipt, which is strictly worse than production's silence here.
  - id: PRC-R2-013
    severity: major
    capability: shell.theme-language-responsive
    finding: Dual-theme/locale/viewport evidence is complete for the default state only. The Japan and United Kingdom inspector panels are `hidden` at rest (reference-r2.html:914, :954) and appear in none of the 12 images, so two thirds of the only surface carrying macro-comparison, central-bank and honest-null copy is unadjudicated in either theme; the four designed states (loading/empty/stale/error) are committed dark-EN-desktop only (proposal-r2-desktop-dark-en-{loading,empty,stale,error}.png), leaving the light rendering of the error card's `color-mix(… var(--act) …)` border, the skeleton shimmer and the 82%-opacity stale treatment unevidenced.
  - id: PRC-R2-014
    severity: minor
    capability: market.performance-usd
    finding: One pulse card violates the identity the panel prints above it. "local equity + currency = USD return" (reference-r2.html:538) holds for six cards but not Australia: −0.9% + 1.2% = +0.3%, and the card prints USD +0.4% (:605-607).
  - id: PRC-R2-015
    severity: minor
    capability: market.macro-comparison
    finding: Two different 3-month FX numbers are printed for the same market without disambiguation: KR pulse card FX +9.8% (:547) vs inspector "FX 3m +8.2%" (:905); JP +2.4% (:567) vs +4.4% (:945); GB −0.9% (:587) vs −1.9% (:985). The inspector is presented as the drill-down of the same card, so the reader has no way to know these are different series.
  - id: PRC-R2-016
    severity: minor
    capability: market.turn-state
    finding: One state, two vocabularies on one page — the pulse cards say "Crash damage unresolved" / "Breaking down" (:549, :569) while the rotation table's State column for the same markets says "Crash" / "Breaking" (:678, :686), against the lineage requirement to "reuse accepted market states" (baseline.yml:52-54).
  - id: PRC-R2-017
    severity: minor
    capability: market.macro-comparison
    finding: The regime field prints an unexplained hazard token — "Stagflation (h 0.04)" (:897), "Reflation (h 0.46)" (:937), "Stagflation (h 0.30)" (:977) — with no legend, help-tip or footnote anywhere defining `h`, on a page whose stated correction was to inline every methodology receipt next to its figure (:1092).
  - id: PRC-R2-018
    severity: minor
    capability: shell.theme-language-responsive
    finding: The RRG quadrant pills set `color:#fff` on `var(--up)` and `var(--orange)` at 10.5px bold (reference-r2.html:238-240), giving ≈2.5:1 (dark #45b873) and ≈3.5:1 (light #1f9a55 / #c4781f) — below WCAG AA 4.5:1 for non-large text in both themes, visible on the "Weakening"/"Lagging" pills in proposal-r2-desktop-{dark,light}-en.png.
  - id: PRC-R2-019
    severity: minor
    capability: n/a (freshness disclosure)
    finding: Staleness is expressed by dimming the whole page — `body.is-stale .real-content { opacity: .82 }` (:334) — which lowers every text/background ratio uniformly (worst in light, where margins are already tighter) and replaces production's per-field as-of stamps (templates/intl.html.j2:957); the banner copy is fixture-meta ("no newer session has been baked", :443), not a product statement about data age.
strengths:
  - "The engine-owned dial is restored intact and verifiably: 66/100 with the verdict word, the full coverage receipt ('Weighs 10 markets by size … ~100% of world market value. 6/10 above their 200-day line · median 3-mo move +2.8%'), the 'Dragged by' attribution and all four vitals (reference-r2.html:461-523) match the production compass in baseline-r2-desktop-dark-en.png field for field — no second score, no invented confidence, and the '81% CONFIDENCE / Risk budget 63' composite that blocked R1 is gone."
  - "Every prescriptive verb is retired and replaced by a projection with its own guard: 'This list restates the stance field already shown per market above. It never originates, sizes or recommends a trade, and carries no OWN/AVOID/HEDGE verb that the engine did not publish' (:1006), and the causal five-node chain is replaced by 'a transmission read, not a statement of cause' plus 'never read as a causal chain' (:783, :792, :819)."
  - "The fragility receipt is restored verbatim rather than paraphrased — threshold, IMF WEO 2025 source, annual cadence, the Berg & Pattillo (1999) attribution and the false-positive base rate all sit in-place at :826, matching templates/intl.html.j2:1714-1775."
  - "Light is authored as a design, not a filter: a full token plane (:55-64) with its own shadow and aurora opacities, a separate light+zh direction quadrant (:67), and a CJK tracking rule that zeroes letter-spacing on eyebrows and h2 (:73-75) — and it holds up as hierarchy and material depth in proposal-r2-desktop-light-en.png rather than merely rendering."
  - "The per-section methodology pattern that PRC-016 blocked is genuinely restored: nine in-place help-tips and eleven caveats carry window length, source, cadence and the not-a-ranking / not-causal / display-only limits next to the figures they qualify, with full EN/ZH spans on every one."
  - "Presentation is a real committed stylesheet in `<style>` (:26-359); the only JavaScript is attribute toggling and tab wiring (:1099-1154) — no runtime-injected material system, and no persistence, alert or export plane anywhere in the artifact."
```

EVIDENCE:
- Artifact read in full: `mockups/refs/institutionalize/intl/reference-r2.html` (1157 lines); link inventory enumerated (9 `href`s, six of them `intl.html`).
- Production source: `templates/intl.html.j2` (:43, :75-77, :386-440, :473, :476-480, :481, :814-818, :857-873, :923-978, :1643-1713, :1714-1775, :1813-1879, :1967, :1991) and `scripts/build_intl.py` (:178-192, :725-770, :387-646).
- House law on direction vs status ink read at `site/theme.css:255-300`; the candidate's `.chip.warn/.ok` direction-ink usage is production-parity (`templates/intl.html.j2:75-77`, `.tb-state.ts-*` :392-407) and is therefore **not** raised as a finding.
- Images adjudicated separately as designs: `proposal-r2-desktop-{dark,light}-en.png`, `proposal-r2-desktop-dark-zh.png`, `proposal-r2-mobile-light-zh.png`, `proposal-r2-desktop-dark-en-{loading,error}.png`, and production `baseline-r2-desktop-dark-en.png`.
- Evidence-matrix completeness: all 8 baseline cells (desktop/mobile × dark/light × en/zh) are committed in `62d710ee`, plus 4 state captures; dual-theme evidence is therefore present, and the BLOCK is on product/content grounds, not on a missing light art direction.

GAPS:
- Baseline visual coverage stops before `action.sector-rotation` and `action.prophet-stocks`: `baseline-r2-desktop-dark-en.png` ends at "The deep dive / Regimes, correlations & rankings" (templates/intl.html.j2:1880-1966), so the artifact's honest-null claim that the sector board "carried zero rows in this session's bake" (reference-r2.html:1079) cannot be confirmed or refuted from the permitted evidence set. Builder must supply the bake receipt.
- `baseline.yml` itself under-specifies the route: `global.regime-verdict` is scoped to `templates/intl.html.j2:475-676`, a range that silently contains two distinct surfaces — the injected `global_regime_html` Chairman overview (:476-480) and the Global Macro Compass — and `shell.theme-language-responsive` folds `_site_nav.html.j2` (:473) into "shell". PRC-R2-003 would have escaped a purely capability-id-driven review.
- Inspector panels for Japan and the United Kingdom, and the entire `mode == 'stocks'` shared surface, have no frozen image in any theme or locale.

DEVIATIONS:
- Undeclared-to-me but disclosed-in-source theme deviation: the candidate's light canvas is `--bg:#f7f8fa` (reference-r2.html:56) against production's `html[data-theme="light"] body { --bg:#e8ebf1 }` (templates/intl.html.j2:43). The source comment (:30-35) justifies this by citing `docs/DESIGN_DOCTRINE.md §5.8`, which is outside my permitted read set — routed to Fable for adjudication rather than scored as a finding.
- The artifact classifies the Country Inspector tabs as a "local design-harness control" (reference-r2.html:1131) while they are the sole access path to macro-comparison, central-bank and honest-null content. Under the standing rule that static design-harness controls are not product capabilities, that self-classification, if taken literally, means `market.macro-comparison` has no product affordance at all. Needs an explicit ruling.
- Output format: the commission requested bare YAML; the governing worker contract requires the five top-level labels. Resolved by returning the requested YAML verbatim inside `RESULT`.
