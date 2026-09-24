---
key: RIC-PHASE-RESET-NO-PROMOTION
question: Should the seen-history oscillator phase/reset construction acquire rates-direction or equity-risk authority?
answer: No. Preserve it as a frozen exploratory result and move the research frontier to macro-driver-conditioned rate direction.
rationale: >
  The predeclared SHALLOW_MPR primary was active on only three discovery origins and
  changed Brier by zero versus the weaker EMA20 phase baseline. None of seven phase
  candidates reached the 50 resolved-active-episode floor. The EMA20 phase baseline
  itself was 0.574% worse than the incumbent five-bar trend/volatility baseline.
  P_RESET and PR_RESET showed only tiny, non-significant improvements versus that
  weaker phase baseline and remained below the episode floor. The underlying history
  was already seen by prior studies, so no result here could establish validation.
alternatives:
  - option: Promote P_RESET because its Brier was slightly lower than the EMA20 phase baseline.
    why_not: It improved by only 0.049%, had 21 resolved episodes, had HAC p=0.7058, and still underperformed the stronger incumbent baseline.
  - option: Promote the falling-yield side of PR_RESET after the post-result asymmetry diagnostic.
    why_not: The six active falling-trend origins and four directional successes are post-selection, tiny-sample evidence.
  - option: Keep tuning oscillator thresholds on the same two-year source.
    why_not: That would expand seen-history selection without a new validation source and risks converting chart intuition into overfit.
  - option: Reject oscillator phase entirely.
    why_not: The studies reject only these frozen constructions; phase may remain useful as context inside a driver-conditioned model.
evidence:
  - research/rates_direction/SWING_PHASE_RESET_EXPLORATORY_V1.md
  - research/rates_direction/SWING_PHASE_RESET_EXPLORATORY_RESULTS_2026-09-24.md
  - research/rates_direction/swing_phase_reset_exploratory_results_v1.json
  - research/rates_direction/swing_phase_reset_exploratory_integrity_v1.json
  - "Freeze 8e6936cfa4218188cb366c848b1fa83005af5b07; original Studio run 23727; 7 configurations in ric_swing_phase_reset_v1."
affects: ["WS:RATES-INFLATION-COMMAND", "research/rates_direction/"]
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-09-24
---

This ruling removes no indicator from display/context. It withholds predictive and
portfolio authority and changes the next research priority: test rates direction
using macro/policy/real-rate/event/supply state with oscillator phase only as an
incremental timing feature. A future genuinely prospective result may supersede this
ruling through the normal evidence path.
