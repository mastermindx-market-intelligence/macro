---
key: RISK-RADAR-DISPLAYED-PROBABILITY-GRADIENT-NOT-PRECISION
claim: >-
  Under the corrected live-equivalent replay, the complete shipped US Risk Radar
  probability surface (state plus hot-Tier-A conjunction count) improves Brier
  score versus the unconditional base at H5/H10/H21, but is not numerically
  calibrated cell-by-cell. In the 2020+ H21 slice Brier skill is +8.8% while
  weighted absolute exact-cell calibration error is 6.1pp. Non-thin cells remain
  point-ordered (13%->1.3%, 16%->12.2%, 19%->24.8%, 39%->49.0%), so the surface
  is useful as a risk gradient rather than precision-grade odds.
falsifier: >-
  Re-run scripts/research/risk_radar_displayed_probability_audit.py from its
  accepted revision on the receipt-bound inputs. The H5/H10/H21 canonical
  population fingerprints, exact probability-cell counts, Brier metrics, and
  calibration errors must reproduce.
so_what: >-
  Preserve the surface as directional risk context but do not present its
  percentages as exact actuarial frequencies or retune them from this historical
  reconstruction alone. The clearest modern mismatch is the 13% calm/watch H21
  floor versus 1.3% realized in the replay. Any replacement surface needs a
  separately preregistered candidate and prospective/issued evidence.
kind: data
verified_at: 2026-09-22
verified_by: "python3 -m pytest tests/test_risk_radar.py tests/test_risk_radar_recovery.py tests/test_risk_radar_review.py tests/test_risk_radar_scorecard.py tests/test_macro_radar_audit_2026_07_29.py -q"
scope:
  - macro
  - grey-deer-risk-intelligence
  - engine/risk_radar.py
  - scripts/research/risk_radar_displayed_probability_audit.py
confidence: verified
---
