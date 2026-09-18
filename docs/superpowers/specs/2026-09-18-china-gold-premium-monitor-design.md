# China Gold Premium Monitor — Design

Date: 2026-09-18
Status: Chairman-approved design; implementation authorized
Operation: gold-china-premium-monitor-20260918-sol-001

## Outcome

Add a China physical-gold premium monitor to the existing Gold detail surface on commodities.html.
The panel must tell a user whether Shanghai physical gold is trading above or below a London
reference without changing commodity conviction, allocation, ranking, Prophet, portfolio, or any
other authority-bearing output.

## Methodology

### Canonical daily benchmark

The canonical series is Shanghai Gold Benchmark PM (SHAUPM) versus LBMA Gold Price AM.

For each admitted observation date:

SGE_USD_OZ = SHAUPM_RMB_PER_GRAM * 31.1034768 / USDCNY
SPREAD_USD_OZ = SGE_USD_OZ - LBMA_AM_USD_OZ
PREMIUM_PCT = (SGE_USD_OZ / LBMA_AM_USD_OZ - 1) * 100

Daily legs must resolve to the same declared observation date. Missing, non-finite, non-positive,
or mismatched values produce an honest unavailable state rather than a proxy.

### Optional intraday proxy

When an entitled provider supplies all three aligned legs, an optional indicative read may use
SGE Au99.99 RMB/gram, a licensed London/global spot USD/oz reference, and USDCNY.
Intraday observations must be timestamped and fall within the configured maximum skew. The
intraday proxy is never spliced into the canonical benchmark history and is always labelled
indicative.

## Source and rights contract

This feature does not scrape SGE, LBMA/IBA, Yahoo, Tushare, or another website. It reads only
provider-neutral store references explicitly configured under commodities.china_gold_premium.

Each leg config requires group, name, column, source_label, and entitled: true. A leg with
entitled != true, missing config, absent data, or bad values is unavailable. This keeps the
user-facing surface safe to ship before an entitled feed is installed and avoids a second
collector, store, queue, or publication plane.

## Engine boundary

Create engine/china_gold_premium.py. It owns source-reference validation, provider-neutral store
reads, daily benchmark alignment, optional intraday alignment, unit conversion, premium/spread
calculation, 5-observation moving average, 30-observation min/max, compact chart-series
serialization, freshness/methodology/source metadata, and honest unavailable reasons. It never
mutates a store and never feeds a score.

## Builder boundary

scripts/build_commodities.py asks the engine for one china_gold_premium view-model and attaches
it only to Gold's detail row. No other asset is changed. Failure is additive and non-fatal.

## UI

Create templates/_china_gold_premium.html.j2 and include it inside the Gold detail panel.

Tier 1 shows: China physical premium, current premium %, Premium/Discount/Near parity,
5-session average, 30-session range, Shanghai USD-equivalent and London reference,
canonical/indicative badge, and a plain context statement.

Tier 2 carries methodology, source labels, observation/freshness dates, unavailable reason,
and formula explanation.

Modes: % Premium, $/oz Spread, Price Level.
Ranges: 1W, 1M, 3M, 6M, 1Y, 3Y, Max.
No Plotly dependency is added. The chart is lightweight inline SVG driven by serialized points.

### Dark treatment

Use existing commodity command-center surfaces and tokens. Positive/negative values use existing
semantic state inks; zero line and moving average are quiet neutral hairlines. No new palette or
glow family.

### Light treatment

Use the existing cool canvas + white research panel + crisp hairlines. No dark chart island.
Use existing light-theme state inks and reduced tint.

### Responsive and bilingual

Desktop may use two metric columns; mobile recomposes to one. Control strips may scroll within
themselves but the document cannot overflow. EN/ZH text is complete at rest and in disclosure.

## Null and correction behavior

The panel remains visible in a degraded state when configuration exists but data does not. If no
entitled source is configured, it says that explicitly. A canonical daily panel never substitutes
GC futures, an ETF, or an unofficial web quote. Source corrections remain owned by the upstream
store; this engine is read-only and recomputes from current stored truth.

## Acceptance

Not done unless:
1. pure math tests prove conversion and premium math;
2. invalid, non-finite, non-positive, unentitled, and mismatched inputs fail closed;
3. intraday skew is enforced and canonical/intraday histories stay separate;
4. Gold gets the view-model and silver/copper/oil do not;
5. commodity conviction/allocation outputs remain unchanged;
6. dark/light × EN/ZH × 1440/390 evidence exists for available and unavailable states;
7. no horizontal document overflow at 390px;
8. design-system, visual-evidence, and runtime-style guards pass;
9. applicable CI concludes;
10. the merged source is rendered normally and the served Gold panel is browser-verified. With no
entitled live feed, production proof may legitimately show the honest unavailable state.
