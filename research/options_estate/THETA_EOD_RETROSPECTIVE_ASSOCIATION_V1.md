# Theta EOD retrospective association v1

This frozen, fit-free daily-archive study may produce reproducible retrospective associations, nulls, and coverage facts. It cannot establish point-in-time availability, predictive alpha, untouched OOS performance, executable option PnL, or production authority.

Before any outcome or financial value is computed, prepare mode inventories and hashes every selected 2017-2025 Theta and adjusted-price input, including schemas and availability/vintage-column scans. Analyze mode accepts only that exact manifest. The prior metadata audit inventoried 13,119 files (66,282,226,978 bytes; 381 roots), while only a 240-file, 311,665,900-row subset was hash/date/schema scanned and contained zero known-at fields. That sample does not prove a whole-archive vintage fact; the study's full selected-file manifest must make its own scan. Pending attributable availability receipts, every result is `PIT_UNPROVEN`.

The scored universe is 20 ETF/equity roots, including NVDA, after excluding duplicate SPX/SPXW and benchmark-only SPY. DIA and ARKK lack the required native adjusted-price files, so they remain visible non-evaluable and no fallback source is allowed. Each label starts on the first NYSE session after the archive observation date and ends after 5 or 21 NYSE sessions. Root and SPY must both contain every native adjusted-close date in that canonical interval. Labels cannot cross an era seam or 2025-12-31; seam rows are null.

The 60 cells cover ten exact contrasts in Era1 (2017-19), Era2 (2020-22), and Era3 (2023-25): normalized gamma, vanna, charm, Vanna-relief interaction, CW IV-spread level/change, skew acceleration, IV term slope, five-session OI growth, and five-session price momentum. The actual family token is `options_theta_retrospective_association_v1`; it must be registered in `config/ruling_graph.yml` before analyze mode. There is one global BH step-up family at alpha 0.10. Vanna and baseline IC differences are descriptive paired effects only, with no extra p-value or family cell. Return-feature comparisons use identical root/date sets; any gamma/RV momentum comparison must use the same RV target and matched set.

Greeks and OI join one-to-one on `(date, expiration, strike, right)`. Exposures reuse `engine.exposure_math.usable_quote` and `dealer_exposures`, plus a research-only un-crossed quote, positive strike/spot, and non-0DTE screen. CW IV spread uses the existing OI pair weighting `call_OI + put_OI`, same-session unadjusted Greek median spot for moneyness, five-decimal canonical rounding, exact >=7D tenor, and no fallback. Near/back ATM requires both call and put legs and rounds to six decimals. Skew requires valid delta on each leg, has no moneyness fallback, and rounds to four decimals. DOI5 is aggregate-OI growth at two endpoints under the same valid-identity/expiry policy. Returns use adjusted closes only.

Each cell is a date-level cross-root Spearman IC with at least five eligible scored roots. Inference requires 126 observed IC dates and 30 non-overlapping effective label blocks. HAC retains the full canonical calendar index: missing dates do not compress lags, covariance uses observed pairs at their true session separation, and the report includes a 95% HAC confidence interval and Student-t p-value with `df=n_observed-1`. Sparse cells remain visible and consume their registered BH slot.

The package reports all cells, coverage denominators, exclusions, effects, HAC uncertainty, raw and BH-adjusted p-values, and an unsupported matrix. Daily EOD bid/ask cannot support executable option-cost or PnL claims. Intraday, trade-sign/NBBO, dark-pool, known-at/vintage, OOS, training, calibration, scoring, ranking, gating, sizing, alerts, portfolio use, and trading remain outside this study.

## v1.1 pre-outcome determinism amendment (binding implementation)

The implementation that this doc accompanies is frozen at the v1.1 pre-outcome determinism amendment. The amended protocol lives at `research/options_estate/theta_eod_retrospective_association_v1_1_protocol.json` (SHA-256 `67011db3d3aed08827f027cafc5b5a2bf890289a1017b227cad15fc240826e68`); the human-readable amendment memo is `research/options_estate/THETA_EOD_RETROSPECTIVE_ASSOCIATION_V1_1_AMENDMENT.md`. V1 JSON above is preserved unchanged.

The amendment keeps the ten feature formulas and 60 registered cells unchanged. It fixes only deterministic selection, manifest identity, HAC computation, split-seam predicates, tied/constant rank statistics, and effective-block ordering. The canonical manifest uses source-relative identities and canonical compact JSON serialization; absolute host paths and filesystem stat metadata are not manifest identity. Prepare and analyze require identical selected slots and bytes.

The implementation CLI is:

```
python -m scripts.research.options_history_retrospective \
  prepare-manifest --store <theta-root> --price-store <price-root> \
  --protocol research/options_estate/theta_eod_retrospective_association_v1_1_protocol.json \
  --out /outside/source/options_theta_retrospective_20261002_manifest.json

python -m scripts.research.options_history_retrospective \
  analyze --store <theta-root> --price-store <price-root> \
  --protocol research/options_estate/theta_eod_retrospective_association_v1_1_protocol.json \
  --manifest /outside/source/options_theta_retrospective_20261002_manifest.json --manifest-sha <hex> \
  --out /outside/source/options_theta_retrospective_20261002_result.json
```

Analyze does not accept a separate fixture directory: its inputs are fully bound to the bytes that prepare-manifest hashed, and any drift refuses the study. The store/price-store values must be byte-identical to those used at prepare-manifest time. The gauntlet's `--study retrospective-v1` or `--study retrospective-v1.1` delegates to the helper CLI and forwards its remaining arguments; it does not print a usage-only banner.

The first execution used computation head `a7ee15312486cac5992e2fb658135adff465939e` and failed at final JSON serialization because a nullable diagnostic reason became a NaN mapping key. It computed cells internally but emitted no valid result artifact; no numerical cell result was inspected. The diagnostic-only correction preserved the frozen specification and all 435 input entries. The whole manifest changed solely to bind the corrected helper source.

The successful second execution used computation head `07186d356cf2a3ef9d24a2d17fe60bd397f570cd`, manifest `6b678a65f531eb31735cca7641b898887739475a9c1a479c2a0ebbecd8a164dc`, and result `7af1b1ae1c871892384388695d17977cea1a6b6aa4fd21fc1625b5dad55073f3`. All 60 cells are evaluable, with three within-run BH rejections. Independent summary/HAC/BH reproduction passed, as did all 18 fixed-date raw rank checks. The [complete report](../../reports/artifacts/options_theta_retrospective_20261002.md) contains every cell, uncertainty, coverage, exact replay commands and limitations. [PR #8286](https://github.com/mastermindx-market-intelligence/macro/pull/8286) owns publication status. Production authority remains unchanged.
