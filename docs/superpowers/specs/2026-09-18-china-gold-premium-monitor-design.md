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

### Close-aligned indicative basis

The approved source-integration continuation adds a distinct daily-close proxy that compares
the SGE Au99.99 trade-date close directly with global XAU/CNY at the same Shanghai close clock:

SGE_CNY_OZ = AU9999_RMB_PER_GRAM * 31.1034768

SPREAD_CNY_OZ = SGE_CNY_OZ - GLOBAL_XAUCNY_CNY_OZ

PREMIUM_PCT = (SGE_CNY_OZ / GLOBAL_XAUCNY_CNY_OZ - 1) * 100

This series has its own history and CNY price/spread presentation. It is never promoted into or
spliced with SHAUPM/LBMA canonical history and remains explicitly indicative.

## Source and rights contract

### Initial UI/engine slice

The first slice did not scrape or add a provider collector. It read only provider-neutral
store references explicitly configured under `commodities.china_gold_premium`.

Each leg config requires `group`, `name`, `column`, `source_label`, and
`entitled: true`. A leg with `entitled != true`, missing config, absent data, or bad
values is unavailable.

### Approved source-integration amendment

The Chairman-approved continuation supersedes only the initial-slice "no new provider
collector" constraint so the product can reach a real data path. It adds one bounded
`gold_china_basis` collector that reuses existing governed Tushare and Massive/Polygon
credential surfaces, the existing `lib.store` time-series plane, and the existing nightly
scheduler. It creates no new store authority, queue, credential plane, or publication plane.

The indicative close-aligned source contract is:

- SGE Au99.99 from Tushare `sge_daily`, whose trade-date row comprises the prior-night
  session plus the current 09:00-15:30 Shanghai session; the comparison timestamp is the
  trade-date close at 15:30 Asia/Shanghai;
- Massive Currencies `C:XAUCNY` minute aggregates, aligned within the configured close
  tolerance; the committed capability manifest records the FX probe as entitled;
- raw legs persist under `gold_china_basis/` and are consumed only by this display engine;
- a cold store seeds 90 calendar days before switching to the bounded nightly overlap, so a
  rendered "30-session range" is not synthesized from a handful of observations;
- Massive minute history is requested newest-first. Once a current close-aligned chunk succeeds,
  an older-history request failure degrades depth rather than blacking out the current reading;
- the collector keeps requesting cold-start depth until the persisted raw legs overlap on at
  least 30 observation dates, so a partial first run cannot permanently strand the 30-session
  statistic at null;
- if either persisted leg falls outside the normal overlap, the next run expands to cover the
  observed gap plus overlap, capped at the full-history horizon, rather than leaving a hidden
  discontinuity in the last-30-observation window.

This amendment does not convert the proxy into the official benchmark. SHAUPM/LBMA-AM remains
the canonical method and stays unavailable until its own entitled mapping exists. Missing or
stale proxy sources fail closed; futures, ETFs, Yahoo, or unofficial web quotes remain forbidden
substitutes.

### Production-path proof receipt

Every normal nightly commodity build is followed, in the existing builder band, by a read-only
`scripts.audit_china_gold_premium` check. It independently reads the configured source stores and
premium engine, then compares that truth with both the written `site/commodities.html` Gold panel
and the sibling `data/commodity/latest.json -> gold_context.china_physical_premium` machine
projection. A missing/drifted machine projection is a strict projection mismatch; it cannot leave
page proof green while machine consumers see different context. The result is persisted to the
existing `data/quality/china_gold_premium.json` observability plane and staged by the existing
engine-output commit.

The receipt distinguishes a valid unavailable state from an actual render-contract break:
source absence/staleness does not fail the build, while disagreement in method, state, currency,
source-asof, or headline premium between the engine and rendered panel is a strict audit
violation. It records canonical/intraday/close-proxy availability separately. A second audit pass
runs in the existing engine-output commit script after site-wide normalization and immediately
before staging, overwriting the same receipt so the final proof binds to the exact committed HTML
tree. The receipt has no signal, ranking, lifecycle, retry, or publication authority.

Post-merge acceptance uses the same checker with an explicit completion gate:

`python -m scripts.audit_china_gold_premium --strict-render --require-live-ready --require-method close_proxy`

This mode exits nonzero unless the Shanghai-close proxy is the selected fresh method, the rendered
panel and incumbent machine projection both match the engine, and both the 5-session average and
30-session range are ready. The scheduled nightly keeps honest unavailability nonfatal; only the
explicit acceptance invocation requires live readiness.

The 5-session average is emitted only after five aligned observations exist, and the 30-session
range only after thirty. Until then those statistics are null/“—” rather than mislabeled
short-history aggregates.

Data OS ids are declared before live acceptance only as `PROPOSED`:
`commodity.gold.sge_au9999.close` and `commodity.gold.xaucny.close_ref`. Once the normal nightly
has actually landed and validated the two `data/gold_china_basis/*.parquet` stores, closeout
promotes those same rows to `PRODUCED` only when the same receipt proves the machine projection
consistent. Promoting them before that effect, or from page-only proof, would violate the
registry's own truth rule.

Promotion evidence is artifact-bound, not inferred from a green UI alone. The production quality
receipt includes one SGE and one global-source artifact record with stable dataset id,
repo-relative path, row count, SHA-256, and latest observation timestamp. The promotion-ready bit
remains false unless both artifacts are present and non-empty, their hashes are bound, and their
latest timestamp matches the close-proxy headline that was also proven through the page and
machine projection.

## Engine boundary

Create engine/china_gold_premium.py. It owns source-reference validation, provider-neutral store
reads, daily benchmark alignment, optional intraday alignment, unit conversion, premium/spread
calculation, 5-observation moving average, 30-observation min/max, compact chart-series
serialization, freshness/methodology/source metadata, and honest unavailable reasons. It never
mutates a store and never feeds a score.

## Builder boundary

scripts/build_commodities.py asks the engine for one china_gold_premium view-model and attaches
it only to Gold's detail row. No other asset is changed. Failure is additive and non-fatal.

The incumbent `data/commodity/latest.json` feed also receives one compact
`gold_context.china_physical_premium` projection derived from that same view-model. The machine
object is explicitly `context_only`, excludes vendor/source internals and excludes every
conviction/action/ranking field; it cannot become a hidden trade signal.

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
themselves. The Gold panel must fit at 390px and must add zero horizontal document-width
regression versus its exact parent. A separately owned pre-existing whole-page overflow is
recorded as adjacent debt rather than silently reassigned to this feature. EN/ZH text is complete
at rest and in disclosure.

## Null and correction behavior

The panel remains visible in a degraded state when configuration exists but data does not. If no
entitled source is configured, it says that explicitly. A canonical daily panel never substitutes
GC futures, an ETF, or an unofficial web quote. Source corrections remain owned by the upstream
store; this engine is read-only and recomputes from current stored truth.

## Acceptance

Not done unless:
1. pure math tests prove conversion and premium math;
2. invalid, non-finite, non-positive, unentitled, and mismatched inputs fail closed;
3. intraday skew is enforced and canonical/intraday/close-proxy histories stay separate;
4. Gold gets the view-model and silver/copper/oil do not;
5. commodity conviction/allocation outputs remain unchanged;
6. dark/light × EN/ZH × 1440/390 evidence exists for available and unavailable states;
7. the Gold panel fits at 390px and adds zero horizontal document-width regression versus
   its exact parent; pre-existing whole-page overflow remains with its incumbent owner;
8. design-system, visual-evidence, and runtime-style guards pass;
9. applicable CI concludes;
10. the merged source is rendered normally and the served Gold panel is browser-verified. With no
entitled live feed, production proof may legitimately show the honest unavailable state.
