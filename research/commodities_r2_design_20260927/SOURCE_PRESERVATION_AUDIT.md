# Commodities R2 — current-source preservation audit

**Status:** design input for R2; current-production-capability audit, **not** a replacement for the frozen analytical snapshot, **NOT_APPLIED_TO_PAPER**, not production acceptance.

## Two source clocks must remain separate

R2 uses two different evidence roles:

1. **Frozen analytical evidence** for the actual research values shown in the R2 study: Macro commit `7150f29a765387f1c14fbae086314af6e0d6bddc`, analysis as-of `2026-09-25`, `complex_latest.json` blob `0079f305817cf18f79892ab752d683b504d81765`, companion `latest.json` blob `05fa7ef08c94bd8aa3b97f514a8759eacf2b04a7`.
2. **Current product-capability evidence** for what the redesign must preserve: Macro main `5f2bf9ae44ea06fd79bf81780ae1b2fce371af3c`, audited 2026-09-27. This current audit does **not** silently refresh the frozen R2 analytical snapshot.

Current product source anchors:

| Artifact | Git blob |
|---|---|
| `templates/commodities.html.j2` | `5b9ce7f42c2a5fad6baebf707893f0ba88ec126f` |
| `site/commodities.html` | `82b318965eb70269b8af78038d923106bd107ee6` |
| `scripts/build_commodities.py` | `704d6ea19ce633d96d25eccfeb8b219567489462` |
| `engine/commodity_coverage_matrix.py` | `5e4ce156e13440ceefd77825bdec1e8f3a8ce11d` |
| `data/commodity/latest.json` | `9e7f84b4e092318efa64c58a476b10d7db63f577` |
| `data/commodity/complex_latest.json` | `0079f305817cf18f79892ab752d683b504d81765` |

## Capabilities the redesign must preserve

### 1. Separate quote and analysis clocks

The current built page has a four-instrument quote strip for Gold, Silver, Copper and WTI (`GC=F`, `SI=F`, `HG=F`, `CL=F`). The audited server-rendered sample is:

- Gold 4,321.20, +0.5% 1-day quote layer;
- Silver 64.25, +1.2%;
- Copper 6.70, −0.3%;
- WTI 92.41, −2.3%.

R2 may show this capability, but the quote clock must be visually separate from the daily research build. A fresh quote must never imply that trend/momentum/cycle research recomputed.

### 2. Cross-asset Oil → Canadian energy context

The current product has a display-tier oil trend-episode → XEG context. In the audited state Oil is in a confirmed up-trend; in 32 past Oil up-trend episodes, XEG averaged about +1.9% over the following four weeks. The current copy correctly frames this as **a tailwind, not a trigger**. The downside relation is underpowered and must not be turned into an XEG sell rule.

The R2 redesign should preserve this as contextual research, not hide it and not promote it to trade authority.

### 3. Existing early-warning producer

The current commodity engine already aggregates bottom/top clues from overbought/oversold state, shock, positioning, cycle and momentum-turn features. R2 should reorganize these into a user-first watch workflow rather than delete them.

Examples from current `latest.json`:

- Copper: `Extended — late cycle`, top score 40.9; clues include longer-term overbought, COT crowded long, momentum rolling over, cycle peak/downturn.
- Coffee: bottom score 36.8; longer-term oversold, COT crowded short, momentum curl up.
- Live Cattle: basing / armed recent; bottom score 17.4; longer-term oversold + COT crowded short.
- Heating Oil: top score 27.8; longer-term overbought + price stretched above 200-day.

These scores remain producer outputs. R2 labels them **top/bottom watch scores**, not rankings of expected return, confidence, or trade triggers.

### 4. Commodity index / long-cycle / MTF capability

The current page exposes the complex index, multi-timeframe agreement, trend/breadth, long-cycle summary, per-commodity multi-timeframe Trend/RSI/Stoch/MACD rows, cycle context, shock state, model lean and dollar sensitivity. The redesign must retain a route to these advanced capabilities through progressive disclosure.

Do not force every indicator onto the overview. The product requirement is preservation and inspectability, not visual density. If exact MTF rows are not present in the frozen R2 payload, the mockup should describe the destination/contract rather than fabricate values.

### 5. Core-four model lean

Current producer outputs include:

- Gold: −15.0 / 100, legacy producer action `SELL`;
- Silver: −20.7 / 100, `SELL`;
- Copper: −7.5 / 100, `HOLD`;
- Oil: −15.7 / 100, `SELL`.

R2 preserves the numeric producer output for continuity but explicitly labels the action text **legacy producer label** and states that it is not a trade instruction and does not originate or size a position.

### 6. Gold China premium

Gold has an existing display-only China physical-premium context:

- available: true;
- method: Shanghai-close / close proxy;
- current premium: ~0.162%;
- 5-observation average: ~0.163%;
- source as-of: 2026-09-24 07:30 UTC;
- 30-observation range: −0.258% to +0.330%;
- official canonical source available: false;
- context-only: true.

It may establish a regional relative-price proxy difference. It does not establish a global physical shortage, expected return, or executable spread. It has no ranking/sizing/gate/trade authority.

### 7. Build-specific five-family coverage

The canonical coverage matrix is an inventory of actual build readers, not a new entitlement or scoring system. Current built output:

- Energy — crude & fuels: **Prices + supply**, including Yahoo daily prices plus US weekly petroleum stocks against the five-year seasonal norm from the EIA WPSR.
- Precious metals: **Prices only**; physical supply not covered yet.
- Industrial metals: **Prices only**.
- Grains & softs: **Prices only**.
- Semiconductors & critical tech materials: **Not covered yet** in this commodity build.

The registry uses all-of artifact checks and can return `Built, waiting on data`. Future views must read the build-specific matrix again; do not hard-code these states as permanent capabilities.

### 8. Current schedule and alert history are different products

The current built page renders EIA crude/petroleum inventory events on 30 Sep 2026 and 7 Oct 2026 at 10:30 ET. Production must still recheck the canonical calendar at view time.

Separately, the built page exposes **84 alerts over the last 60 days**, with filters Shock / Risk / Driver / Allocation / Other. Sample history includes:

- Gold structure → broken;
- Gold / Silver ratio silver rich;
- Oil risk turned Elevated;
- Gold macro backdrop turned headwind;
- Copper momentum → bull;
- Commodity complex → Reflation;
- Oil price shock stabilizing;
- Oil intraday price shock (down).

Alert history is not a forecast. R2 should preserve history/review capability without turning every past alert into a new recommendation.

### 9. Localization boundary is evidence too

The current coverage owner already supplies Chinese family/state/detail semantics, so the study must render those source-backed meanings rather than leak English implementation copy into a Chinese view. Current built alert history is different: the rendered alert headlines audited here are source-English only. R2 therefore keeps the original headline and explicitly tells Chinese readers that some historical alert titles are untranslated; it does **not** manufacture Chinese headlines that were not verified from the exact source artifact.

Localization rules follow evidence availability: translate from an owned bilingual producer where verified; otherwise preserve source text and disclose the language limitation. Theme or locale changes must never change the analytical meaning.

## Product consequence

The production-ready redesign should not be a prettier subset of today’s Commodities page. It should organize the existing capability into a clearer research journey:

**Orient → inspect quote-vs-analysis timing → find signal disagreement / warning → open commodity brief → inspect advanced producer evidence → validate physical/positioning coverage → compare → prepare catalyst → save falsifiable case → later review exact change/history.**

New R2 research-continuity features (cases, falsifiers, evidence receipts, revision-safe review, effect-safe persistence) add workflow value around the existing engines; they do not replace those engines.
