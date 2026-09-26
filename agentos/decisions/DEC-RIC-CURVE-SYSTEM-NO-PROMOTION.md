---
key: RIC-CURVE-SYSTEM-NO-PROMOTION
question: Should the fixed Nelson-Siegel curve-dynamics construction acquire 10Y rates-direction authority?
answer: No. Preserve the null; no-change remains the stronger primary level forecast.
rationale: >
  On the declared 2021-2025 primary 20-observation horizon, no-change MSE was
  740.153 bp^2 versus 881.014 for DNS-VAR, so the primary candidate was 19.03%
  worse. Direct AR and diagonal DNS were also worse. The same no-change advantage
  held on MSE at 5 and 60 observations and in the 2010-2020 context period.
alternatives:
  - option: Select a longer-horizon DNS model because some directional probability scores were better.
    why_not: Continuous 10Y level error was the frozen primary objective; selecting a different objective after outcomes would be post-selection.
  - option: Tune Nelson-Siegel lambda or add lags on the same primary sample.
    why_not: V1 explicitly froze lambda and model form; retuning after a failed primary would expand seen-history selection.
  - option: Treat the null as proof the curve contains no information.
    why_not: The result rejects this forecast construction, not the descriptive or economic information in curve level/slope/curvature.
evidence:
  - research/rates_direction/CURVE_SYSTEM_DNS_V1.md
  - research/rates_direction/CURVE_SYSTEM_DNS_RESULTS_2026-09-24.md
  - research/rates_direction/curve_system_dns_integrity_v1.json
  - "Freeze 08ddb2c550ec84a4de9c780121a938dc0d02a1cf; 12 configurations in ric_curve_system_dns_v1."
affects: ["WS:RATES-INFLATION-COMMAND", "research/rates_direction/"]
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-09-24
---

This ruling withholds predictive and portfolio authority. It does not remove curve
state from descriptive context. The research frontier remains catalyst/expectation
forecasting and constituent-qualified policy repricing.
