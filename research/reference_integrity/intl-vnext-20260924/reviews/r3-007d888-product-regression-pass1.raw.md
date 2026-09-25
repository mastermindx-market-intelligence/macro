```yaml
role: product_regression
reviewer_identity: "R3-007d fresh Opus product critic A"
pass: 1
verdict: BLOCK
findings:
  - id: PRC-001
    severity: blocker
    capability: risk.fragility-map
    finding: "Production's fragility map (baseline-r2-desktop-light-en.png, 'Fragility map — slow-moving structural vulnerabilities') flags two economies — United Kingdom AND United States — each with three named breached criteria carrying their values (debt/GDP, current-account %, fiscal balance %), while the proposal's fragility grid (reference-r3.html:513-526) covers only the seven international economies, drops the United States row entirely, reduces the UK to one unvalued chip 'Debt above 70% and rising', and then asserts completeness with a '7 / 7' chip and 'Every economy is accounted for' (:511,:527), so the reader of the reference cannot learn that the page's own anchor market carries structural warnings."
  - id: PRC-002
    severity: blocker
    capability: risk.contagion
    finding: "Production answers 'Where is risk building?' with a four-tile International Risk Desk (baseline-r2-desktop-light-en.png) giving a per-domain state and a re-check trigger for Emerging markets ('1 of 6 stress signals firing', 'No action needed'), Contagion to US ('Early signs of contagion — transmission channel hot', 'check again if EM worsens'), Dollar, and Dollar funding ('Ignore — no funding stress'); the proposal deletes that synthesis with no replacement — grep of reference-r3.html returns no 'emerging' or 'funding' occurrence, the EM-stress aggregate exists nowhere, dollar funding survives only as one of five channel rows that all read identically 'Transmission channel / Observe' (:481-485) so no channel is hot where production reported one, and the top-3 shock senders lose their magnitude bars to bare ordinals 'Top sender / Second / Third' (:477-480)."
  - id: PRC-003
    severity: major
    capability: global.us-world-rotation
    finding: "Production renders the US-vs-world capital rotation as a plotted quadrant scatter (flag markers positioned on improving/leading/weakening/lagging axes) beside its data table (baseline-r2-desktop-light-en.png, '⇅ US vs the World — capital rotation'); the proposal keeps only the table (reference-r3.html:447-469) and contains no scatter anywhere, converting a two-dimensional at-a-glance position read into seven rows of quadrant labels plus three return columns."
  - id: PRC-004
    severity: major
    capability: market.performance-usd
    finding: "Act 2's per-market chart is a fixed 84-session path that does not follow the horizon control (reference-r3.html:302 data-horizon-independent=\"true\"; browser-proof-v2.json:29 'fixed_chart_horizon_independent': true), so selecting 12M or YTD rewrites every USD/local/FX figure while all seven shapes stay unchanged — a mismatch the artifact must disclaim three separate times (:293, :302, :375) — and each chart is painted uniform link-blue regardless of direction (browser-proof-v2.json:1074 'neutral_link_ink': true), removing the green/red directional ink production carries on the same seven rows (baseline-r2-desktop-light-en.png, 'Performance in US dollars', India's line red among green) together with production's local/currency/USD decomposition bars."
  - id: PRC-005
    severity: major
    capability: market.turn-state
    finding: "Production's ten turn cards each carry state, plain-language instruction, per-market figures, a Pullback-risk chip and a driver→consequence line with a hover-for-full-read affordance (baseline-r2-desktop-light-en.png, 'World markets — turns & rotation'); the proposal's turn cells hold only a state chip and one stance line (reference-r3.html:382-401), the material driver is recovered only for the seven international markets via the radar table (:403-416) leaving United States, China and Hong Kong with no driver and no numbers anywhere on the page, and the demoted pullback probabilities are deferred to 'each market's evidence receipt' (:417) which has no link, disclosure or hover target in the artifact."
  - id: PRC-006
    severity: major
    capability: null
    finding: "The upstream regime overview is simultaneously declared canonical and preserved (reference-r3.html:244 'production shell and upstream overview remain canonical', :246 data-preserve-overview) yet rendered as a reduced stand-in (:246-260) that drops production's five-market 'Where this shows up' scale with per-market position, move and what-to-do (US stocks, Government bonds and Commodities vanish entirely), the four dated signal rows with their per-row Watch actions, the three 'why this week' panels, the 'what we're watching next' condition cards, and three of six Go-deeper destinations (Signal Lab, Macro signals, Macro & Monetary hub), so a builder reproducing the reference faithfully would ship the reduction."
  - id: PRC-007
    severity: major
    capability: reference.regime-correlation-ranks
    finding: "The capability's three named views — growth-inflation placement map, correlation heatmap and ranked league tables (baseline.yml:116-119; production's 'The deep dive — Regimes, correlations & rankings') — exist nowhere in the proposal, which replaces them with four summary metrics including correlation collapsed to a single 0.49 average and three in-page anchors (reference-r3.html:717-722) that resolve to #macro-comparison, #rotation-turns and #global-pulse, none of which contains a growth-inflation map, a pairwise correlation view or a league table."
  - id: PRC-008
    severity: major
    capability: rates.curve-desk
    finding: "The capability is defined as curve shape, real yields, long-yield drift and carry versus the US (baseline.yml:88-90), but the proposal's rates desk (reference-r3.html:708-716) offers only short/policy, 10Y, curve and real 10Y — no yield-drift column and no US row at all, so carry versus the US cannot be read on the page — and Taiwan is silently absent from the six rows rather than rendered as the typed null the proposal itself mandates elsewhere ('Missing is a state, not zero', :541)."
  - id: PRC-009
    severity: minor
    capability: risk.pressure-flow
    finding: "Production's 'Where crash pressure is flowing now' rows attribute each market's pressure to three or more named contributors with their shares (baseline-r2-desktop-light-en.png), while the proposal caps every row at two unquantified source names and rules magnitude out by policy — 'no decorative magnitude is implied' (reference-r3.html:488-507) — so the user can see that pressure is Building but not how much of it comes from where."
  - id: PRC-010
    severity: minor
    capability: null
    finding: "Act 6 opens with a full-width Desk posture panel (reference-r3.html:681-688) that renders the accepted stance field for a fourth time — after the Act 2 card state-line, the Act 2 radar 'Accepted stance' column and the Act 3 rotation 'Stance' column — adding no new field and repeating the identical disclaimer 'Projection of the accepted stance field only' seven times plus a closing caveat, pushing the central-bank, credit, rates and correlation desks further down for zero information gain."
  - id: PRC-011
    severity: minor
    capability: action.prophet-stocks
    finding: "baseline.yml:43 places sector rotation and Prophet signals in production's intl.html information hierarchy, but the frozen production captures end at 'The deep dive' header (baseline-r2-desktop-*.png, 6387px) so their on-route rendering is UNKNOWN from the allowed evidence; on the proposal side both capabilities (with action.sector-rotation) are reduced to prose cards with cross-route links and zero rows or tickers (reference-r3.html:723-728), a disposition that cannot be verified as equivalent without the unretrievable source."
strengths:
  - "Population honesty is materially better than production: every board states its coverage ('10 / 10 Ten markets, no suppressed rows' reference-r3.html:381, '10 published rows, each named' :487, '7 / 7' :540) and the pressure board reconciles its own differing population out loud — Canada in, South Korea out (:508) — which production never does."
  - "Authority is genuinely held flat: the stance vocabulary is copied rather than escalated, with 'A rank is not a trade command' (:446), 'Display only' (:402), 'Projection only' (:681), 'this reference never mints another score' (:280) and 'no causal overclaim' (:474), and no entry/exit geometry, sizing or probability is introduced anywhere."
  - "The long-standing production ambiguity of two different scores on one page is fixed explicitly: the 61/100 US-only upstream score and the 66/100 world risk-appetite verdict are each labelled and reconciled in a caveat (:254, :274-276)."
  - "Degraded states are organ-local and honest: loading, empty, stale and error are scoped to the performance organ with copy naming what stays available (:294-297), stale keeps the values on screen with disclosure rather than blanking, and all four states are captured full-page with all six acts still rendered (browser-proof-v2.json:542-764)."
  - "Typed nulls survive the redesign intact — Taiwan's '0 · 1/3 legs' recession cell (:551), 'Balance-sheet data exists only for the Fed, ECB, and BoJ; every other dash is an honest null' (:699), and 'Awaiting verified annual data, never a reassuring zero' (:527) — matching the masterplan lineage in baseline.yml:51-53."
  - "The Country Inspector is a real interaction gain: a roving-tabindex tablist with Arrow/Home/End support (:768-781, evidenced by the eight per-country captures and keyboard_next fields in browser-proof-v2.json:256-540) gives mobile users every field of the 1180px-wide macro row without horizontal scrolling, and each panel warns that 'currency move' is not the Act 2 FX contribution (:589)."
  - "intl_stocks.html is preserved as exact committed bytes rather than redesigned, with a named non-regression boundary covering the dashboard, per-ticker destinations, capped stance vocabulary and evidence receipts (:726-728) and eight preservation captures bound to stocks_sha256 77d44314… (browser-proof-v2.json:6-8, 766-1060)."
  - "Bilingual parity is complete and locale-correct: direction ink inverts for Chinese convention (:32-39), horizon labels resync on language switch (:749-753), and the zh captures show no English leaks or missing translations (browser-proof-v2.json:1096-1104)."
  - "The decomposition is arithmetically honest at every horizon — local + FX equals the displayed USD return for all seven markets across 1M/3M/6M/12M/YTD in the data-returns attributes (:298-374) — and the 0.1pp rounding divergence from the engine's unrounded total is disclosed rather than hidden (:293)."
```
