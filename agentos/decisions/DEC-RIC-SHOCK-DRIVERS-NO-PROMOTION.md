---
key: RIC-SHOCK-DRIVERS-NO-PROMOTION
question: Should the frozen rate-shock driver-state hierarchy acquire rates-direction authority?
answer: No. Preserve the null and move the frontier to catalyst forecasting and qualified policy repricing.
rationale: >
  The 2022-2025 primary sample contained 57 scored non-overlapping shocks and met
  its declared floor. The impulse-direction Brier was 0.665101. Adding nominal/
  real/breakeven composition worsened it to 0.672208; the primary decomposition+
  PIT-term-premium model worsened it to 0.682122 (-2.559% relative), cross-asset
  states to 0.691956, and recent-auction context to 0.700381. The only earlier
  development forecasts numbered two and cannot establish a regime edge.
alternatives:
  - option: Select the development-period driver model because its numeric Brier was lower.
    why_not: Only two forecasts survived the training warm-up; this is below any meaningful descriptive floor.
  - option: Keep adding technical oscillator phase to the driver stack now.
    why_not: Both crossover and phase/reset constructions already failed; adding them after seeing this result would expand seen-history selection.
  - option: Use rolling ZQ/SOFR horizon changes as policy confirmation.
    why_not: The available path history begins in March 2026 and rolling-horizon changes remain contaminated by contract reweighting until RD2 qualifies constituent repricing.
  - option: Treat the negative result as proof that real yields or auctions do not matter.
    why_not: The test rejects only this categorical transition construction; it does not reject economic transmission or explanatory value.
evidence:
  - research/rates_direction/RATE_SHOCK_DRIVER_TRANSITION_V1.md
  - research/rates_direction/RATE_SHOCK_DRIVER_TRANSITION_RESULTS_2026-09-24.md
  - research/rates_direction/rate_shock_driver_transition_results_v1.json
  - research/rates_direction/rate_shock_driver_transition_integrity_v1.json
  - "Freeze cc3b56c1e5c30d1a323f114d460a20315003c599; 5 configurations in ric_rate_shock_driver_transition_v1."
affects: ["WS:RATES-INFLATION-COMMAND", "research/rates_direction/"]
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-09-24
---

This ruling changes the research priority, not the product's descriptive context.
Next work should distinguish vulnerability from catalyst and market response:
prospective macro-release expectations, constituent-qualified policy-path repricing,
and event-timed rates reaction. A later genuinely prospective result may supersede
this ruling through the normal evaluation path.
