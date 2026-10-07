---
key: OPTIONS-COMPARE-IN-RISK-DETAIL
question: Where should the cross-name options-cost and downside-protection comparison live on the Macro Dashboard?
answer: >
  Inside the existing Risk Detail dialog, immediately alongside the incumbent
  volatility diagnostics. Keep the established #regime-radar as the primary
  macro surface and link deeper work to the Options workspace.
rationale: >
  The current Macro Dashboard already reserves volatility diagnostics for Risk
  Detail to keep the primary scorecard glance-first, and the prior Chairman
  ruling removed a second standalone risk container for the same viewport-cost
  reason. The new comparison is options-risk context, not a new regime score or
  trading signal, so Risk Detail is the existing semantic and interaction owner.
alternatives:
  - option: Add a new full-width Macro Dashboard panel
    why_not: Reintroduces the duplicated first-level risk surface and vertical cost already rejected.
  - option: Put the comparison only in the Options workspace
    why_not: Loses the macro-risk glance while duplicating none of the existing options depth.
  - option: Fuse the two axes into Market State or Risk Radar scoring
    why_not: The skew owner remains display-only and unscored; a fused score would exceed its authority.
evidence:
  - research/DO_NOT_REBUILD.md HOLD-UD-B1-PRIMARY-MACRO-MIGRATION
  - agentos/decisions/DEC-RISK-ENVELOPE-IN-RADAR-NOT-DASHBOARD-PANEL.md
  - engine/options_skew.py
  - templates/risk_envelope_live.js
  - templates/_risk_envelope_band.css.j2
  - tests/test_options_skew.py
  - tests/test_risk_envelope_radar_integration.py
affects:
  - templates/risk_envelope_live.js
  - site/risk_envelope_live.js
  - templates/_risk_envelope_band.css.j2
  - engine/options_skew.py
  - scripts/build_options_skew.py
confidence: high
reversibility: easy
decided_by: chairman-chris
decided_at: 2026-10-06
---

The comparison remains display-only. "Fast" means unusually large five-session
movement inside the two-axis options-pricing map; it does not mean bullish,
bearish, actionable, validated, or promoted. The axes use the canonical skew
ledger's own-history observations and inherit its source/session limitations.
