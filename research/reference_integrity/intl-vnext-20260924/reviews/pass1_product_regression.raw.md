role: product_regression
reviewer_identity: "claude-opus-product-regression-intl-20260924"
pass: 1
verdict: BLOCK
findings:
  - id: PRC-001
    severity: blocker
    capability: shell.theme-language-responsive
    finding: Proposal evidence is dark-EN-desktop only (5 files, all `proposal-*-dark-en.png`) against a baseline that committed all 8 cells of desktop/mobile × dark/light × en/zh (baseline.yml:18-25); there is zero light-mode, zero Chinese, and zero mobile evidence for a core capability, and every string in the frozen images is English except the single eyebrow token "国际市场" (proposal-hero-dark-en.png), so ZH parity for new copy like "The call flips to mixed if breadth falls below 44% while the dollar accelerates" is unevidenced and untestable.
  - id: PRC-002
    severity: blocker
    capability: shell.theme-language-responsive
    finding: The five `proposal-*.png` files are byte-identical duplicates of `mockups/refs/institutionalize/intl/*-reference-dark-en.png` in the same commit (573347/954901/416995/922027/981035 bytes each, `git show --stat f3873dcb`), i.e. the "after" is a static design reference, not a capture of a rendered page — no functional browser evidence of any kind exists, so no responsive, theme, or locale behavior has been demonstrated at all.
  - id: PRC-003
    severity: blocker
    capability: global.regime-verdict
    finding: Production's engine-owned World Risk Appetite dial — score 0-100 with the explicit comment "verdict + tone come from ENGINE truth … never recomputed here … never floored or overridden" (intl.html.j2:522-524), its coverage receipt (n markets, ~% of world market value, breadth above 200d, median 3-mo move, intl.html.j2:551-553), its "Dragged by …" attribution (:557-558) and its four vitals (dominant regime / USD leader / Recession-watch / Avg correlation, :591-621) — is replaced by prose plus two numbers with no engine provenance shown anywhere: "81% CONFIDENCE" and "Risk budget 63 / 100" (proposal-hero-dark-en.png). That is a second scoring system, the exact item named in baseline.yml:59 `rejected_variants`, and it substitutes an unsourced composite for an auditable one.
  - id: PRC-004
    severity: blocker
    capability: action.sector-rotation
    finding: A board production labels "Display-only" and ranks by a stated method ("Ranks regional sectors by 3-month relative strength. Display-only.", intl.html.j2:1967) becomes the "International playbook" with prescriptive verbs OWN/FAVOR, AVOID/REDUCE, HEDGE and named instructions ("Korea until a valid reclaim", "Renewed USD acceleration · Asian FX contagion"), plus "Generate desk brief" and "Alert settings" (proposal-country-inspector-dark-en.png) — no ranking, no relative-strength number, no source, and no display-only label survive. This directly contradicts the lineage implication "display-only risk context" and the build comment "risk organs … remain descriptive rather than trading authority" (baseline.yml:65, scripts/build_intl.py:387-646).
  - id: PRC-005
    severity: blocker
    capability: risk.pressure-flow
    finding: Production's directed-pressure surface is explicitly non-causal — "this is a transmission read, not a causal share" (intl.html.j2:1406) and "Display only — not a signal to trade" (:1814), with the baseline capability text "without treating correlation as causation" (baseline.yml:114). The proposal renders a five-node causal chain "Dollar strengthens → Asia FX weakens → Conditions tighten → Breadth narrows → Reversal risk rises" under the heading "Why the dollar matters now" and asserts "Asia is the current origin" (proposal-transmission-dark-en.png), converting a correlation read into a stated mechanism with no caveat anywhere in frame.
  - id: PRC-006
    severity: blocker
    capability: market.performance-usd
    finding: The core job "Compare local equity return, currency effect, and total USD return" (baseline.yml:80-82) is unperformable: production decomposes every market into local equity + currency tailwind/drag = net USD with a four-item legend and a rotation-rank/3m/6m/12m/ytd selector (intl.html.j2:857-872), while the proposal's Global Pulse cards carry no FX term at all and use three different, non-comparable sublines across six cards — "Local +8.1% · 1M" (Japan), "Breadth 41% · off high −6.2%" (Taiwan), "20D · off high −15.2%" (South Korea) — so the headline −8.4% that drives "Stand aside" is measured over a different window than the +6.8% it sits beside (proposal-desktop-dark-en.png).
  - id: PRC-007
    severity: blocker
    capability: global.us-world-rotation
    finding: Both US-versus-world surfaces are gone with no replacement: the RRG quadrant scatter plus the per-market vs-US 3m/6m/12m relative-return table and its "Positive = beat the S&P 500" caveat (intl.html.j2:879-912), and the hero tug beam with "{n_leading}/{n} ex-US markets ahead" (:572-588). The proposal offers only the prose "leadership is concentrating" and an un-benchmarked rank column, so the user can no longer tell whether any market is beating the US or whether that lead is improving or fading.
  - id: PRC-008
    severity: blocker
    capability: action.prophet-stocks
    finding: The entire Prophet international board is absent from the proposal, removing the page's only stock-level destinations (`intl_stock.html#<ticker>`, intl.html.j2:1991-2061) and its calibrated honesty — verbs deliberately capped at near/hold/wait/avoid because "No entry gauge exists for INTL", the "Mom" edge labelled "not a validated score", vol-squeeze flags, and progressive show-more. The hero link "Stock dashboard →" to `intl_stocks.html` (intl.html.j2:538) also disappears, orphaning the shared surface baseline.yml:14 declares this template owns, for which the proposal supplies no `mode == 'stocks'` evidence whatsoever.
  - id: PRC-009
    severity: blocker
    capability: risk.fragility-map
    finding: Production states its criterion, source, cadence and base rate in-place — "debt-to-GDP above 70% and rising, fiscal deficit below −5%… Source: IMF WEO 2025. Annual data… Berg & Pattillo (1999) criterion adapted… most historically flagged countries did not experience a crisis" plus an honest-null path when WEO data is absent (intl.html.j2:1714-1775). The proposal reduces all of it to a "SLOW VULNERABILITY" toggle and EXTERNAL/POLICY chips reading LOW/WATCH/HIGH (proposal-transmission-dark-en.png): threshold, source, annual cadence, false-positive base rate and the null path are all unrepresented, so a country renders as "HIGH" with no stated meaning.
  - id: PRC-010
    severity: blocker
    capability: n/a (scope)
    finding: The proposal introduces a persistence/publication plane production does not have — "Saved 6", "Compare", "Pin market", "Copy desk brief", "Generate desk brief", "Alert settings", "Export desk view", "View event log", 1M/3M/1Y (proposal-hero/country-inspector/desktop-dark-en.png) — none of which exist anywhere in templates/intl.html.j2. "Saved" and "Alert settings" presuppose per-user state, while baseline.yml:27 records the route as anonymous with "no credentials or premium payload introduced", and baseline.yml:59 rejects "A second lifecycle, scoring, or publication system for international intelligence."
  - id: PRC-011
    severity: major
    capability: market.macro-comparison
    finding: The 15-column cross-country scorecard — policy rate, 10y, curve, real 10y, CPI with a per-field staleness stamp, GDP, unemployment, FX 3m, off-high, drawdown band, market state, plus the "data-limited" chip and "Descriptive only" caveat (intl.html.j2:923-978) — has no counterpart; the nearest surface is a five-row, five-column HIGH/MID/LOW/WATCH chip grid for 5 countries (proposal-transmission-dark-en.png). Every macro quantity (CPI, GDP, unemployment, policy rate, real yield) vanishes from the route, replaced by unquantified categoricals.
  - id: PRC-012
    severity: major
    capability: rates.curve-desk
    finding: The Rates & curve desk (curve shape, real yields, 10-year drift, carry vs US — intl.html.j2:981-1068) and the Eurozone fragmentation panel (peripheral spreads over Bund, :1032) are absent. The proposal footer advertises "12 sovereign curves" as an input while exposing exactly one yield on the page — "10Y YIELD 3.16% · +18 bp" inside one selected country's inspector — so a declared input is consumed but never made inspectable.
  - id: PRC-013
    severity: major
    capability: risk.credit-bonds
    finding: Production's credit surface gives spreads in percentage points, a 20-day velocity arrow, BAML regional subindices, a six-curve inversion board, and the vendor-history caveat "EM spread history collected since Jul 2023 (data-vendor cap)" (intl.html.j2:1558-1645). The proposal reduces it to a "CREDIT" column of LOW/WATCH/HIGH chips, discarding magnitude, direction, regional breakdown and the history-length disclosure that tells the user how far back a comparison is even valid.
  - id: PRC-014
    severity: major
    capability: policy.central-banks
    finding: The Central bank desk — realized 3-month stance (explicitly "not forward guidance or market pricing"), balance sheet for Fed/ECB/BoJ with honest nulls elsewhere, calendar-only meeting dates, "no policy-intent projection" (intl.html.j2:1490-1557) — survives only as "NEXT CATALYST · BoK policy decision · 4 days" inside the selected country's inspector and "BoK decision" in WATCH NEXT. Every other central bank, all stance data, and the balance-sheet honest-null contract are gone from the route.
  - id: PRC-015
    severity: major
    capability: reference.regime-correlation-ranks
    finding: The growth × inflation regime map with "Snapshot only, not a forecast" (intl.html.j2:1880-1895), the cross-market correlation matrix with "Red = more correlated; green = more diversifying. Display-only." (:1901-1922), the ranked reference views (:1928-1947) and the hero's "Avg correlation … cross-market, lower = safer" vital (:611-614) are all absent. The proposal gives the user no diversification read at all, which is the only lens that tells a cross-border allocator whether the positions the playbook prescribes are actually independent.
  - id: PRC-016
    severity: major
    capability: n/a (methodology access)
    finding: Production attaches an in-place `help()` receipt to essentially every section — window lengths, sources, vendor caps and the "not a forecast / not causal / display-only" limits (intl.html.j2:679, 857, 923, 940, 985, 1406, 1490, 1558, 1814, 1880, 1901, 1967, 1991, with "? tips carry Tier-2 receipts. Honest nulls throughout." at :1075). No proposal panel carries any help affordance; methodology collapses to a single footer link "Methodology · Evidence" (proposal-desktop-dark-en.png), so every caveat that currently sits one hover from the number it qualifies moves off-surface.
  - id: PRC-017
    severity: major
    capability: market.turn-state
    finding: Authority inflation on turns — the proposal prints per-candidate "91% confidence / 78% confidence / 69% / 64%" (proposal-rotation-dark-en.png) and "91% CONF" on the country stance (proposal-country-inspector-dark-en.png), quantities production never computes; production's equivalent is a named state from ten enumerated reads with confirmation windows and no probability attached (intl.html.j2:633-668, 713-714). A displayed 91% confidence on "Stand aside" is a precision claim the engine does not make.
  - id: PRC-018
    severity: major
    capability: market.turn-state
    finding: Coverage is silently truncated and the suppression is unauditable: the hero asserts "8 of 14 markets above trend" and "Global breadth 58%", yet only 6 markets appear in Global Pulse and the rotation table, 5 in the risk map, and the Risk Radar states "7 additional risks remain below action threshold" with the threshold undefined and the remainder reachable only via an off-page "Open risk map →" (proposal-desktop-dark-en.png). Production renders a turn tile for every market in the board (intl.html.j2:684-685) and a scorecard row for every record (:944), so the user can verify a breadth claim; here they cannot.
  - id: PRC-019
    severity: major
    capability: n/a (evidence integrity)
    finding: The same component carries two contradictory methodology captions across the frozen set — "Where capital is moving / Trend strength × 20-day acceleration · bubble ring = risk" (proposal-rotation-dark-en.png) versus "Where capital is moving / 20-day rank migration · fast momentum path · state-governed" (proposal-desktop-dark-en.png and proposal-transmission-dark-en.png) — over an identical rank-migration table that contains no bubbles and no risk ring. At least one caption describes a chart that does not exist, and the committed evidence cannot say which measure the bars encode.
  - id: PRC-020
    severity: major
    capability: n/a (freshness disclosure)
    finding: Per-field staleness is replaced by one opaque composite: production stamps the stale as-of span on individual cells (intl.html.j2:957), flags "data-limited" economies (:949), and gives each desk its own as-of line, whereas the proposal collapses this into "DATA HEALTH 97%" with "2 SLOW SERIES DELAYED" (proposal-desktop-dark-en.png) — and the page's own risk-map footnote in the same screenshot insists fast and slow inputs "are not fused into one opaque score", which the health percentage does.
  - id: PRC-021
    severity: minor
    capability: market.performance-usd
    finding: The Global Pulse grid is labelled "SORT BY Rotation rank" but renders #1, #2, #3 / #5, #7, #4 — row two is out of rank order and #6 is absent without explanation (proposal-desktop-dark-en.png); production's leaderboard actually applies the rotation-rank sort it advertises and exposes the alternate horizons as real controls (intl.html.j2:861-864).
  - id: PRC-022
    severity: minor
    capability: market.turn-state
    finding: The country inspector gates depth behind a single selection ("Selected · South Korea", tabs Overview/Equity/FX/Rates & Credit/Flows/Catalysts/Evidence), whereas production presents each market's full read as an in-place hover on every tile (TB_READ_EN, intl.html.j2:633-656) — comparing two markets' diagnostics now costs a selection round-trip per market instead of two hovers.
strengths:
  - "The TIER 1 · ORIGIN STRESS / TIER 2 · US TRANSMISSION split states the masterplan's origin-versus-US-transmission distinction (baseline.yml:51) more legibly at a glance than production's contagion board, which buries it in a help receipt (intl.html.j2:1406)."
  - "The risk-map footnote 'Fast market stress tells us whether pressure is igniting; slow fundamentals tell us who is fragile. They are not fused into one opaque score' correctly refuses the fast/slow fusion the fragility lineage warns against, and is an honest, user-legible statement of the separation."
  - "'Why the state changed' (CONFIRM / ACTIVE / AGREE agreements) and 'Stance & thresholds' (CONFIRMS THE BREAK: off-high reaches −18% / INVALIDATES THE CALL: reclaims MA20 with breadth > 50%) promote production's hover-only confirmation windows (intl.html.j2:713-714) into persistent, falsifiable, in-place conditions — a genuine improvement in auditability."
  - "The hero's 'The call flips to mixed if breadth falls below 44% while the dollar accelerates' gives the top-level verdict an explicit invalidation condition, which production's hero verdict does not carry at all."
  - "Turn candidates rendered as dated state transitions (PARABOLIC → BREAKING · today, LEADING → WEAKENING · 3d ago) raise production's 'What changed' section (intl.html.j2:834) to a higher tier and make the direction of change, not just the state, the unit of attention."
