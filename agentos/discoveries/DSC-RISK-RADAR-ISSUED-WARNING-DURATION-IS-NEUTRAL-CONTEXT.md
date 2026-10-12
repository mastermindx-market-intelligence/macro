---
key: RISK-RADAR-ISSUED-WARNING-DURATION-IS-NEUTRAL-CONTEXT
claim: >-
  US Risk Radar can surface five-session caution-or-higher persistence without
  creating a new alert or model authority by deriving duration only from the
  incumbent keep-FIRST forward ledger. The current settled session must have a
  matching issued state, missing NYSE sessions break the streak, and duplicate or
  malformed ledger rows fail closed. The result rides only in Risk Envelope source
  detail and renders as quiet Risk Radar metadata at five or more issued sessions.
falsifier: >-
  Run python3 -m pytest tests/test_risk_envelope.py
  tests/test_live_risk_envelope.py tests/test_risk_envelope_radar_integration.py
  tests/test_macro_risk_dialog.py -q. The claim is falsified if a missing session
  does not break the streak, a duplicate/state mismatch earns duration, fewer than
  five sessions render persistence, the live builder manufactures duration, or the
  display changes probability/state/policy semantics.
so_what: >-
  Users can distinguish transient caution from persistent risk pressure in the
  existing Risk Radar detail without another giant container or louder warning.
  Preserve the research ceiling: duration is context only, not evidence to raise
  odds, escalate state, size positions or create capital policy.
kind: data
verified_at: 2026-09-24
verified_by: "python3 -m pytest tests/test_risk_envelope.py tests/test_live_risk_envelope.py tests/test_risk_envelope_radar_integration.py tests/test_macro_risk_dialog.py -q"
scope:
  - macro
  - grey-deer-risk-intelligence
  - scripts/build_risk_envelope.py
  - templates/_risk_envelope_band.html.j2
confidence: verified
---
