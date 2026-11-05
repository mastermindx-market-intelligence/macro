---
key: RISK-ENVELOPE-IN-RADAR-NOT-DASHBOARD-PANEL
question: Where should the Risk Envelope's trend, stress and source-evidence readings appear on the macro dashboard?
answer: >
  Inside the existing Risk Radar, reached through the existing risk button.
  Remove the separate full-width dashboard container. Show compact Trend and
  Stress readings with a short disagreement warning; put source clocks,
  contradictions, technical receipts and inactive capital controls behind Evidence.
rationale: >
  Chairman Chris explicitly rejected the second container's viewport cost and
  wordy presentation on 2026-09-19. Its intelligence remains useful, but should
  integrate with the established risk workflow rather than displace the dashboard.
alternatives:
  - option: Keep the full-width panel with shorter copy
    why_not: Retains the first-level viewport obstruction the Chairman requested removed.
  - option: Delete the engine or fuse its readings into the radar score
    why_not: Loses the independent hazard reading and violates the standing separation contract.
evidence:
  - Current Chairman instruction and screenshots in the risk-container redesign conversation, 2026-09-19.
  - research/grey_deer/RISK_RADAR_INTEGRATION_2026-09-19.md
  - tests/test_risk_envelope_radar_integration.py
affects:
  - WS:GREY-DEER-RISK-INTELLIGENCE
  - templates/dashboard.html.j2
  - templates/_risk_envelope_band.html.j2
  - templates/risk_envelope_live.js
confidence: high
reversibility: easy
decided_by: chairman-chris
decided_at: 2026-09-19
---

Only the GD-2 standalone-band placement and density are superseded. The accepted
settled/live engine, distinct Trend/Stress/Policy semantics, promotion holds,
source clocks and authority booleans are unchanged. This is not authorization to
start other Grey Deer waves or change scores, position sizing or trade gates.
