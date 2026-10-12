---
key: IC-GATES-AFTER-RANK-LINEAR-CONTROLS-DO-NOT-SEPARATE-PATH-FEATURES-FROM-VOLATILITY
claim: "Residualising a price-path feature rank-linearly on trailing return, volatility and beta and then gating on the sign and significance of its rank IC against forward drawdown does not distinguish it from one more volatility estimate: simulated prices with no drift and no return autocorrelation, only volatility that differs across stocks, clusters in time and rises after falls, pass the same four holdout gates on 14 to 29 of 29 tests."
falsifier: "Read Mastermind research/data/trend_persistence_v2_null.json (specs clustered_leverage and clustered_leverage_jumps, five seeds each): if those simulated markets pass V2's four holdout gates on fewer than 14 of the 29 confirmed tests in every seed, the claim is false. Rebuild with `python3 -m research.trend_persistence_null` in the Mastermind repo."
so_what: "A drawdown or risk feature that survives rank-linear volatility controls has shown an association, not information beyond volatility. Before treating any such survivor as a new signal, score it against a volatility-only simulated market under the same gates, and measure its increment over a model that already has detailed volatility descriptors (walk-forward, with a materiality bar fixed in advance). In the trend-persistence family that increment was 0.001 to 0.002 of rank IC and no capture."
kind: landmine
verified_at: 2026-10-03
verified_by: "Mastermind PR 1155 (1c5bc0c3a978): research/data/trend_persistence_v2_null.json, research/data/trend_persistence_b2_result.json, research/TREND_PERSISTENCE_READOUT.md sections 10 and 11"
scope:
  - "mastermind"
  - "WS:TREND-PERSISTENCE"
  - "research/trend_persistence_null.py"
confidence: verified
---

The benchmark is one calibration (500 simulated names, five seeds, specifications written after
the holdout result was seen). It gives a range for what volatility alone produces, not an
estimate. With more simulated names more tests pass, not fewer.
