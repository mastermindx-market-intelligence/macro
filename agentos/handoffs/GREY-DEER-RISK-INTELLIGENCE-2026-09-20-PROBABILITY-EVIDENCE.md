---
workstream: "WS:GREY-DEER-RISK-INTELLIGENCE"
session: "claude/risk-radar-forecast-evidence-20260920"
model: sol
ended_because: blocked
mission: >
  Continue Chairman's Risk Radar UI, research and model upgrade: publish the
  accepted live-explanation slice and add honest issued-probability diagnostics
  through the existing scorecard, without promoting or recalibrating a model.
state_before: >
  PR7467 removal was public-production-proven. PR7482 live explanations were
  built and awaiting release. Existing scorecards described alert outcomes but
  did not compare recorded probabilities with outcomes on matched horizons.
changed:
  - path: engine/risk_radar_scorecard.py
    what: Added pure US probability diagnostics to the existing producer, preserving legacy fields.
  - path: tests/test_risk_radar_scorecard.py
    what: Added numerical, exclusion, receipt, duplication and denominator tests.
  - path: tests/test_rr_scorecard_card.py
    what: Proved the existing Market State reader preserves the new diagnostic and nulls.
  - path: research/grey_deer/RISK_RADAR_PROBABILITY_AUDIT_RESULTS_2026-09-20.md
    what: Recorded real-ledger results under the pre-outcome frozen descriptive protocol.
verified:
  - claim: The protocol was committed before ledger-outcome inspection.
    command: "git show 9659c1b7b41efc6c54e32c3cd79ba91c060e287b"
    result: Prereg-only commit precedes all diagnostic/result changes on this branch.
  - claim: The existing scorecard and its reader pass the expanded owning tests.
    command: "python3 -m pytest tests/test_risk_radar_scorecard.py tests/test_rr_scorecard_card.py tests/test_risk_radar_audit.py -q"
    result: "88 passed; research/grey_deer/evidence/probability-audit-20260920/tests.log"
  - claim: Real-input diagnostics preserve the ledger and every old scorecard field.
    command: "Compare build(root,today=2026-09-20) against parent module, excluding generated_at and the additive block; hash ledger before/after."
    result: "Equal legacy fields; unchanged ledger SHA256 612c4ecb5cfe1d794b42953ca0d0c8c9d5f43a294e7b03e60d10f74e5fc468a6."
  - claim: PR7482 is merged and its button/context source is publicly served.
    command: "Native GitHub merge with expected head; VPS read-only SHA check; canonical browser capture and DOM assertions."
    result: "Merge 6be4906dc765bf0b15037ce237568f6d08d0f040; live JS SHA256 47a6eb04c763621586810accfc35777113ccaa982be3a520716f97f989428abd; 8 public browser cells pass."
unverified:
  - claim: The new probability diagnostic is deployed and visible in Risk Radar.
    what_would_verify: >
      Diagnostic source must merge and the existing scorecard writer must publish.
      UI creation was platform-blocked; no new probability table exists or is claimed.
  - claim: The forward sample validates today's model or its downside discrimination.
    what_would_verify: >
      Separately frozen version-specific evaluation with actual downside events,
      issue-time provenance, held-out windows and episode-aware assessment.
  - claim: Live-member behavior has been witnessed in authenticated production.
    what_would_verify: Actual authorized signed-in browser evidence, not local synthetic feeds.
unresolved:
  - "33 eligible overlapping forecast dates contain zero recorded >=5% target events; 18 rows lack grades. No model promotion follows."
  - "Four early rows lack h5/h10 recorded baselines; paired comparisons retain 29 rather than 33 dates."
  - "templates/_risk_probability_audit.html.j2 write was blocked before execution; original path confirmed absent. No retry or alternate implementation."
next_actions:
  - "Publish and validate this exact diagnostic carrier; consume concluded CI before normal merge."
  - "Verify the existing scorecard's production output; the renderer lane remains explicitly blocked until its platform gate changes."
  - "Use existing backtest/episode-atlas owners for a fresh version-specific downside evaluation; do not tune on this zero-event sample."
do_not_redo:
  - "PR7467 removal and PR7482 explanations/button release are accepted at their documented proof level."
  - "Do not alter scores, probabilities, risk-policy permission, ledgers or accepted GD-3 natural-event proof."
  - "PR6989, PR7236 and PR6685 retain their own holds and writers; no release is implied here."
  - "Never fill missing historical baselines from today's calibration or call daily rows independent episodes."
danger_areas:
  - "No positive target events means lower Brier loss can come merely from forecasting less risk; it is not validated skill."
  - "Logged-before-graded does not prove publication before the first outcome bar or homogeneous model identity."
  - "The concurrent unified dashboard hero is preserved; do not overwrite the whole rendered page with this branch's older artifact."
prs: [7467, 7482]
---

# Risk Radar probability evidence continuation

Protected source: Mastermind `b75a491db408892dfe6fe7c4bb9d40cfad8efcb3`,
compatible Skillpack1.0.1/bootstrap1. Base `9a481ef520e397853c9f5a8edd120cfff528ce16`.
Direct execution was PRINCIPAL_JUDGMENT / LOWER_TOTAL_OVERHEAD; no child START,
source-writer transfer, alternate publishing system or new model/control plane.

Real source/result receipts live in `research/grey_deer/evidence/probability-audit-20260920/`.
PR7482's release and eight public browser cells are separately preserved under
`mockups/evidence/risk-radar-forecast-evidence-20260920/parent-live/`.
The new model diagnostic is additive descriptive evidence, not an action gate.
