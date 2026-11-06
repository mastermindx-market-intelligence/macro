# Options historical signal science: revival and corpus evidence

Research-only exploratory result, 2026-10-02. **Historical alpha validation is not established.** The current assignment reopens research into previously retired factors and combinations. Prior negative results remain evidence; production scoring and trading authority are unchanged.

## Reuse decision

Build on the existing Macro Options estate. It already owns live-flow events, immutable decision-time episodes, separately matured outcomes, campaign identities, the Flow grader/trainer, the historical gauntlet, and governed evaluation. No new collector, store, scheduler, score or UI is needed for this mission. Existing #7711/#7728 audit candidates are reuse references, not accepted replacements.

## Frozen descriptive study

The protocol was fixed before return aggregation at 2026-10-02T08:21:46Z: `options_historical_signal_science_20261002_protocol.json`, SHA-256 `ae3576837efdc66ef47d4cfdcf288c63a3b9938599c83d87d13c356af42b4ae8`. Schema, covariate, join and coverage metadata had already been inspected. This is exploratory; the historical corpus is not an untouched out-of-sample test.

Source: Macro `dc4fd0766709188cba8d16a9fc16479c0e9c110f`. All 9,641 episodes from 2026-08-10 through 2026-09-04 are retained as each horizon denominator. There are 86 source tickers and 15 entry sessions. Campaign ledgers are excluded entirely, avoiding the separate unresolved campaign correction problem without inventing a quarantine view. No M1 Theta archive or mutable price cache was accessed.

The canonical full validators accepted 9,641 episodes, 7,843 H+60 outcomes and 30,327 session outcomes with zero errors. IDs/joins are unique with no orphan outcomes. These checks verify stored schemas, clocks, receipt arithmetic and path commitments; they do not independently authenticate or replay the referenced original Polygon source bytes.

## Observed results

All complete rows are research-only underlying-price proxies and have `target_aligned=false`. All option returns are unavailable. These are unsigned underlying returns after C/P-tagged flow episodes, not call/put strategy returns. Every registered aligned-true cell remains explicitly empty.

Values below are percentages. Absent means no row at the frozen source snapshot, not an imputed zero return. Equal-session mean gives each represented entry session equal weight; it is a weighting disclosure, not an independent-sample estimate.

| Horizon | Complete | Terminal incomplete | Absent / 9,641 | Mean | Median | Q10 | Q90 | Equal-session mean | Entry sessions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| h60 | 7314 | 529 | 1798 | 0.107% | 0.030% | -0.696% | 1.082% | 0.145% | 15 |
| eod | 7569 | 466 | 1606 | 0.292% | 0.144% | -1.022% | 1.806% | 0.149% | 15 |
| 1d | 7285 | 0 | 2356 | 0.391% | 0.263% | -2.610% | 3.852% | 0.265% | 14 |
| 3d | 6254 | 0 | 3387 | 0.724% | 0.180% | -2.988% | 5.415% | 1.144% | 12 |
| 5d | 5442 | 0 | 4199 | 0.971% | 0.951% | -4.279% | 6.210% | 0.949% | 10 |
| 10d | 3311 | 0 | 6330 | 0.973% | 0.403% | -4.061% | 8.778% | 0.166% | 5 |

The complete machine artifact retains all 36 horizon/right/alignment cells, including C/P strata and empty aligned-true cells. No cells were selected after viewing returns. Independent recomputation matched all 36 counts, ordinary means and equal-session means to 1e-14.

The 10-session mean falls from 0.973% to 0.166% under equal-session weighting, with only five represented entry sessions and 6,330 absent labels (65.66%). H+60 has 1,798 mature episodes without an outcome (18.65%); the canonical ledger-inference census attributes 1,556 to structural price-source gaps and 242 to source-dependent pending cases. This is evidence that coverage and weighting matter. It does not establish predictive skill, an executable edge, or a reason to promote any factor.

## Method repairs and remaining scientific gaps

The bounded repair in #8268 corrects BH rejection decisions from final monotone adjusted p-values, maps the DOI pre-2016 era to Era0, and requires matching native ticker/SPY fill and endpoint dates before computing Flow excess returns. Its original worker reported 68 passing targeted tests; independent review requested concise mathematical explanations and reuse of the canonical return primitive. Acceptance depends on the final reviewed head and CI, not this earlier worker receipt.

#7401 is merged as `dc4fd076...` and freezes the Flow evaluation contract. #7395 retains its reviewed study definition; a CI-discovered prose-policy key is being corrected from `bh_fdr_family` to `bh_fdr_policy`, without registering a fictitious family or changing the policy. These are prerequisites, not empirical acceptance.

The existing gauntlet can describe retrospective daily associations, but a full run alone cannot satisfy this mission:

- Its loaders retain dates and values without proving known-at/vintage clocks. OI and Greek observations need publication/availability semantics before any point-in-time claim.
- Several return and SPY comparisons use row offsets without proving common trading endpoints. The Flow grader repair does not silently repair those separate gauntlet paths.
- The SKEW benchmark and part of the CWIV test/weighting differ from the earlier registration. Those differences must be frozen explicitly before a family verdict.
- Static era tests do not provide untouched final OOS, walk-forward model selection or calibration.
- Underlying return/volatility associations do not provide option fills, spreads, fees, slippage, executable option PnL, or component-ablation evidence.

The accessible corpus supports this limited H+60 and EOD/1/3/5/10-session descriptive report. It does not establish the requested 5-minute, 30-minute, 2-hour or four-week studies, nor a PIT multi-factor Greek/OI/dark-pool/sector/regime joint study. No missing data or exact timing was fabricated.

## Reproduction and finite next gate

Artifacts in this directory:

- `options_historical_signal_science_20261002_protocol.json`: exact frozen exploratory protocol.
- `options_historical_signal_science_20261002.json`: all 36 registered cells and validation receipts.
- `options_historical_signal_science_20261002_quality.json`: canonical coverage census and source hashes.
- `options_historical_signal_science_20261002_reproduce.py`: read-only regeneration from exact Git objects using canonical validators.

Run with a Python environment containing pandas, numpy, jsonschema and pyyaml:

```sh
python reports/artifacts/options_historical_signal_science_20261002_reproduce.py --repo /path/to/macro --protocol reports/artifacts/options_historical_signal_science_20261002_protocol.json > /tmp/options-descriptive-reproduction.json
```

The next historical-data action is the bounded schema/vintage/coverage census of M1 `/Users/chriswong/theta-ops-wt/data/thetadata_eod`. The connector explicitly denied that path; exact-path authorization is pending. No SSH, alternate tool, copy or symlink was used to evade that denial. Once accessible, first establish source timing and actual supported horizons, then freeze a small complete study with baselines, ablations, chronological splits, costs, missingness and multiplicity before outcomes. Report non-evaluable or null results when evidence does not support a claim.

This report is a completed descriptive work package within an unfinished broader historical-validation mission. It grants no training, ranking, sizing, publication or trading authority.
