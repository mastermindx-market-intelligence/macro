# Captured Sector context through the incumbent owners

Status: source-qualified, not activated. Base: `68d836353d8021f9d5c6d5b010cd6d795a2a4dec`. Governing [Macro #10779](https://github.com/mastermindx-market-intelligence/macro/issues/10779), convergence [PR #10780](https://github.com/mastermindx-market-intelligence/macro/pull/10780), protected Mastermind law `49c2e1d93e5e080b1671c98087a845e5beb09dd5`.

## Source boundary

Four existing owners now expose explicit-value calculations. Their legacy wrappers retain acquisition behavior and delegate to shared mathematical bodies. No collector, scheduler, auth rule, calibration value or publication owner changes.

| Existing owner | New value entry | Captured inputs |
|---|---|---|
| Theme scoring | `macro_context_from_inputs` | Region's regime document, bonds, global Forex, explicit region |
| Conditions | `mrs_weights_from_inputs`, `macro_risk_score_from_inputs` | One captured macro-overlay configuration and the existing latest-document shape |
| Conditions | `sector_macro_beta_from_inputs` | Existing key and one captured beta table |
| Crowding | `compute_fragility_from_inputs` | Full broad-market close panel, full FINRA short-interest cross-section, benchmark |
| Sector Central | `regime_anchor_from_inputs` | Captured latest plus already resolved macro-risk and Market State readings |
| Sector Central | `market_context_from_inputs` | Captured latest/overlay/resolved Market State/heatmap, broad closes, FINRA and benchmark |

The complete Central value path invokes the actual explicit MRS and fragility calculations and the existing heatmap aggregator. Its low-level anchor projection shares the original gate/headline transformation with the legacy wrapper. It does not accept a replacement scoring formula.

## Preserved behavior

The Theme path keeps all existing rates, NFCI, growth, inflation, risk-on and sector-RS calculations and English/Chinese labels. Non-US regions keep their original empty bonds/Forex scoring context; global Forex remains display-only there. The output date remains the regime document's own date.

The dict-MRS path retains available-leg renormalization, original defaults, conditional transition conversion, zero-valued scores and zero-denominator absence. Its original wrapper reads weights first and loads the transition setting only for TRANSITIONING/NEW_REGIME, preserving both order and failure behavior. The captured path derives weights and the conditional transition setting from one detached overlay. This does not change the separate causal historical-series/live-snapshot MRS owner or substitute a persisted macro-risk field for the calculation.

Sector beta preserves exact-key priority, case-insensitive normalized-name fallback, zero for unknown/empty keys and existing numeric conversion. No new clipping or alias authority is introduced.

Crowding preserves benchmark reindex/forward-fill, each name's trailing RS rank, the broad price cross-section's stretch rank and the full FINRA cross-section's days-to-cover rank. Filtering either population to thematic members would change the original statistics and remains prohibited at the capture adapter. Explicit None means captured absence and returns the existing empty result; it never requests a loader.

Central preserves macro-risk fallback truthiness. A nonempty dictionary with score=None remains a resolved result and does not fall back to persisted risk; score zero remains valid. Market State headline labels remain distinct from the MRS-derived gate labels. Legacy Market State acquisition still occurs after risk calculation/gate construction, including its failure ordering.

Heatmap aggregation retains tile weighting, missing observations, unchanged-tile exclusion, weight coverage and absent breadth when no tile moved. The same existing aggregator is reused.

## Market State dependency remains explicit

The new value path does not implicitly call `load_persisted` or `market_state_snapshot`. The latter still has its own configuration, calibration, radar, liquidity and market-catalyst acquisition dependencies.

The future capture adapter may supply the actual captured published Market State snapshot, preserving its own date. If that snapshot is absent, the incumbent fallback must be resolved through its own admitted capture before its result can be supplied. **Unbound is not captured absence.** Passing None is valid only when that dependency has actually resolved unavailable; it is not a shortcut around the missing fallback closure.

These helpers do not certify the source provenance or freshness of caller-supplied values. That responsibility remains with the capture adapter and final generation admission. No build or poll clock is introduced into the contextual source fields.

## Verification and limits

**67 focused tests passed.** The nine affected suites returned **262 passed** and one missing sparse-checkout precondition: an unchanged UI test reads `site/theme.css`, which is omitted in this workspace. The exact test bytes match base 68d836; its original function reproduces FileNotFoundError in the original path and passes unchanged against that same base commit's CSS bytes in an isolated temporary tree. No assertion was weakened or production artifact synthesized. Counts overlap.

Four retained source fixtures contain the literal prior owner functions/module. Tests compare the new shared calculations and legacy wrappers with those originals, including conditional configuration call counts, stale source dates, empty documents, zero risk/weights, market-headline/gate divergence, invalid-risk acquisition order, full/subset populations, missing fields and both heatmap weighting modes. The pure complete context runs under an ambient read/write/clock/provider observer. The resulting Theme and Central contexts also feed the real five-document composer.

[Exact source hashes, commands and receipts](SECTOR_CONTEXT_INPUTS_SOURCE_REVIEW_2026-11-06.json) include the baseline CSS reproduction and the original source hashes.

This source milestone does not complete the genuine member OHLCV byte binding, sponsor holdings, remaining calibration/archive capture, Market State fallback, source updater barrier, CI registration, protected Macro merge, native shared-shell generation consumer or authenticated beta acceptance.
