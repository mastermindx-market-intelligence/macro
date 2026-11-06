# Result dictionary and interpretation

## Files

| File | Meaning |
|---|---|
| `frozen_rule_audit.csv` | All 34 inherited finalists, historical periods, 21/63-session outcomes, primary/stocks/crypto pools and original per-rule nonoverlap sensitivity. |
| `frozen_rule_subgroups.csv` | Prespecified asset, class, year, market-state and concentration views. Sparse groups do not confer rule-selection authority. |
| `recent_audit_events.csv` | Compact 2020–2026 event/horizon ledger. A signal may appear in multiple rule families and horizons. |
| `mechanism_summary.csv` | Fixed reset/reclaim and leadership/oscillator subsets; original roster is primary. Its `nonoverlap` rows select separately within each arm and are policy-roster sensitivities. |
| `mechanism_events.csv` | Complete shared price-event ledger, including rejected gates, inputs, outcomes and comparators. |
| `mechanism_subgroups.csv` | Fixed sector proxy, asset, market state, year and two concentration checks. |
| `state_census.csv` | Leader/nonleader × reset/no-reset daily state census; highly overlapping, not a trade ledger. |
| `shared_nonoverlap.csv` | Review supplement: select one nonoverlap price-event roster first, then partition leader and oscillator arms. This preserves common opportunity identity. |
| `gate_contrasts.csv` | Accepted-minus-rejected and leader-minus-nonleader differences; the same calendar-block draws resample both arms. Includes usable-draw fraction. |
| `top_exit_comparators.csv` | Dedicated top cash-exit diagnostic and ordinary/peer/SPY comparisons, all transformed consistently. |
| `leadership_input_coverage.csv` | Fixed sector map and missing leadership history. Unknown is excluded from both sides of the leadership comparison. |
| `registration.json`, `run_summary.json` | Frozen hashes, dates, input provenance, record counts and original result hashes. |
| `review_supplement.json` | Supplement hashes and verification that the original eight CSV result files are unchanged. |

`ordinary_panel.parquet`, `audit_events.parquet` and `mechanism_events.parquet` are reproducible local caches, excluded from Git. They are needed by the supplement and recreated by `analyze.py`.

## Core fields

- `horizon`: 21 or 63 entry sessions. Entry at signal t+1 open; endpoint at t+horizon close.
- `net20`, `net50`: underlying LONG return after assumed 20 or 50 **basis points of roundtrip cost**. These names do not encode the holding horizon.
- `gross`: underlying LONG dividend-adjustment-factor return proxy, before assumed cost.
- `positive`, `mean`, `median`, `p05`, `worst5_mean`: summary outcomes for the indicated policy. Bottom summaries are long outcomes; top summaries use `-gross-0.002`, a zero-yield-cash avoided-return approximation after fixed friction.
- `mean_winner`, `mean_loser`: conditional means of positive and nonpositive policy outcomes. They describe payoff shape, not position sizing.
- `stop_net20`, `stop_net50`: LONG outcomes with the fixed initial 3-ATR stop or the common fixed endpoint if untouched. Stop based on signal ATR and next-open entry; gaps preserved.
- `stop_hit`: whether the stop was touched. This is different from `stop_positive`, the stopped-policy positive fraction.
- `positive_endpoint_stopped_loss`: fraction of all paired observations that ended positive without the stop but lost under it.
- `stopped_loss_given_positive`: the same conversion conditional on an unstopped positive endpoint.
- `mae`: minimum entry-relative underlying-LONG adjusted low return through the fixed endpoint, clipped at zero. It is not a portfolio drawdown. `top_adverse` is the corresponding forgone-upside path for a cash exit.
- `ordinary_*`: leave-one-out same asset/half-year/own-state/market-state comparison, at least ten other dates. Coverage and matched counts must accompany any claim.
- `state_*`: same asset/half-year/lagged-leader/reset/market-state comparison for the stock experiment.
- `peer_*`: same-date, same-asset-class mean excluding the focal asset. This is not a beta-neutral or industry-neutral portfolio.
- `spy_*`, `sector_*`: same-date reference instrument. Crypto weekend SPY comparisons can be unavailable.
- `*_delta_mean`: mean of matched event-minus-comparator differences. Whole-event mean minus matched comparator mean is not generally the same calculation.
- `*_ci_lo`, `*_ci_hi`: pointwise exploratory 95% intervals, 2,000 consecutive-two-half-year circular block resamples. Not corrected for research selection or multiple comparisons.
- `halfyears`, `dates`, `quarters`: count distinct observed calendar units. These do not assert independence.
- `original_qualified_fraction`, `original_timely_durable63`: inherited pivot labels, kept separate from executable returns; the 63 label is reported only on 63-session summaries.

## Critical top-ledger distinction

In `recent_audit_events.csv`, rows with `side=top` still retain `net20`, `net50`, stop fields and `mae` as **counterfactual underlying-LONG outcomes**. They are not short profits or cash-exit returns. Use the transformed `frozen_rule_audit.csv` top summary or `top_exit_comparators.csv` for top-policy conclusions. The top diagnostic omits cash interest, taxes and borrow because it is an exit/re-entry comparison, not a short strategy.

## Roster distinctions

The original 21-session cooldown applies before oscillator gates in the fixed price-event experiment. Original gated and rejected arms exactly partition the shared leader events. The first run's per-arm `nonoverlap` sensitivity instead selects the first eligible event in each arm and may retain different future opportunities. It must not be read as a paired partition. The supplement's `shared_nonoverlap.csv` first deduplicates the parent price roster through the fixed holding endpoint, then partitions it; that is the controlled nonoverlap gate comparison. Neither convention removes correlations between different securities.

## Limits

Current survivors, current-vintage adjustment factors and fixed sector proxies are not a historical constituent/fundamental database. Entry fractions and means are event diagnostics, not portfolio CAGR, Sharpe, calibrated probabilities or trading authority. All recent history is exposed for this continuation.
